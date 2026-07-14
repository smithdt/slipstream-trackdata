#!/usr/bin/env python
"""Package a satellite/ imagery tree for on-demand distribution.

Groups the per-config sets (satellite/{ir_id}/) by their parent venue, writes one zip per venue into --out,
and emits index.json (ir_id -> venue/asset/version/attribution) + ATTRIBUTION.md (the per-source credits the
licenses require). Only APPROVED sets are included. The zips become GitHub Release assets; index.json +
ATTRIBUTION.md are committed to the repo.

Usage:
  python tools/package_release.py --src ../SlipstreamLive/trackdata/satellite \
         --meta ../SlipstreamLive/trackdata/iracing-tracks-metadata.json \
         --out dist --version imagery-v1 --base-url https://github.com/smithdt/slipstream-trackdata/releases/download
"""
import argparse, json, os, re, zipfile, hashlib

def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")

def referenced_files(manifest):
    files = [manifest["full"]["file"]]
    files.extend(c["file"] for c in manifest.get("corners", []))
    files.extend(t["file"] for t in (manifest.get("live_tiles") or {}).get("tiles", []))
    return files

def validate_assets(directory, manifest):
    root = os.path.realpath(directory)
    for rel in referenced_files(manifest):
        path = os.path.realpath(os.path.join(root, rel))
        if os.path.commonpath([root, path]) != root:
            raise SystemExit(f"manifest asset escapes track directory: {directory} -> {rel}")
        if not os.path.isfile(path):
            raise SystemExit(f"manifest references missing asset: {directory} -> {rel}")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="satellite/ source tree (satellite/{ir_id}/...)")
    ap.add_argument("--meta", required=True, help="iracing-tracks-metadata.json (ir_id -> venue)")
    ap.add_argument("--out", default="dist", help="output dir for the per-venue zips")
    ap.add_argument("--version", required=True, help="release/version tag, e.g. imagery-v1")
    ap.add_argument("--base-url", default="https://github.com/smithdt/slipstream-trackdata/releases/download",
                    help="release-asset base URL; asset URL = {base}/{version}/{venue}.zip")
    ap.add_argument("--index", default="index.json")
    ap.add_argument("--attribution", default="ATTRIBUTION.md")
    ap.add_argument("--attribution-src", action="append", default=[],
                    help="additional satellite source tree whose manifest credits are retained; repeatable")
    ap.add_argument("--only-ids", default="",
                    help="comma-separated iRacing track ids for a partial release; preserves all other index entries")
    a = ap.parse_args()

    only_ids = {int(x.strip()) for x in a.only_ids.split(",") if x.strip()}

    meta = json.load(open(a.meta, encoding="utf-8"))
    id2venue = {c["track_id"]: t.get("track_name") or "?"
                for t in meta["tracks"] for c in t.get("configurations", [])}

    # group approved sets by venue
    venues, attributions = {}, {}
    for p in sorted(os.listdir(a.src)):
        d = os.path.join(a.src, p)
        if not (p.isdigit() and os.path.isfile(os.path.join(d, "manifest.json"))):
            continue
        m = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
        if not m.get("approved"):
            continue
        validate_assets(d, m)
        ir = int(p); venue = id2venue.get(ir, f"track-{ir}")
        if not only_ids or ir in only_ids:
            venues.setdefault(venue, []).append((ir, m))
        if m.get("attribution"):
            attributions[m["attribution"]] = m.get("source", m.get("provider", ""))

    # Partial releases are often packaged from an isolated candidate tree. Retain the credits for the rest of
    # the catalog from one or more authoritative production trees rather than shrinking ATTRIBUTION.md to just
    # this batch. The candidate source above already owns duplicate keys, so an updated manifest can refine its
    # own credit without an older production manifest overwriting it.
    for attribution_src in a.attribution_src:
        if not os.path.isdir(attribution_src):
            raise SystemExit(f"--attribution-src is not a directory: {attribution_src}")
        for p in sorted(os.listdir(attribution_src)):
            manifest_path = os.path.join(attribution_src, p, "manifest.json")
            if not (p.isdigit() and os.path.isfile(manifest_path)):
                continue
            m = json.load(open(manifest_path, encoding="utf-8"))
            if m.get("approved") and m.get("attribution"):
                attributions.setdefault(m["attribution"], m.get("source", m.get("provider", "")))

    if only_ids:
        found = {ir for sets in venues.values() for ir, _ in sets}
        missing = sorted(only_ids - found)
        if missing:
            raise SystemExit(f"--only-ids contains missing or unapproved track ids: {missing}")

    os.makedirs(a.out, exist_ok=True)
    if only_ids and os.path.isfile(a.index):
        index = json.load(open(a.index, encoding="utf-8"))
        index.setdefault("tracks", {})
    else:
        index = {"version": a.version, "tracks": {}}
    index["version"] = a.version
    for venue, sets in sorted(venues.items()):
        vslug = slug(venue)
        zpath = os.path.join(a.out, f"{vslug}.zip")
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:   # JPEGs already compressed -> STORED
            for ir, m in sets:
                d = os.path.join(a.src, str(ir))
                for root, dirs, files in os.walk(d):
                    dirs.sort(); files.sort()
                    for fn in files:
                        path = os.path.join(root, fn)
                        rel = os.path.relpath(path, d).replace(os.sep, "/")
                        z.write(path, f"{ir}/{rel}")
        sha = hashlib.sha256(open(zpath, "rb").read()).hexdigest()[:16]
        asset = f"{a.base_url}/{a.version}/{vslug}.zip"
        for ir, m in sets:
            index["tracks"][str(ir)] = {
                "venue": venue, "asset": asset, "version": a.version, "sha256": sha,
                "corners": len(m.get("corners", [])), "provider": m.get("provider"),
                "live_tiles": len((m.get("live_tiles") or {}).get("tiles", [])),
                "attribution": m.get("attribution"),
            }
        print(f"  {venue:<36} {len(sets)} cfg  -> {vslug}.zip  ({os.path.getsize(zpath)//1024} KB)")

    json.dump(index, open(a.index, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    with open(a.attribution, "w", encoding="utf-8") as f:
        f.write("# Imagery attribution\n\n")
        f.write("Slipstream Live track imagery is derived from the public / open-licensed ortho sources below. "
                "Each carries its source's required credit; see the per-source license for terms.\n\n")
        for attr, src in sorted(attributions.items()):
            f.write(f"- **{attr}**" + (f"  \n  _{src}_\n" if src else "\n"))
    mode = f"partial ids={sorted(only_ids)}" if only_ids else "full"
    print(f"\nwrote {a.index} ({len(index['tracks'])} tracks, {len(venues)} packaged venues, {mode}) + {a.attribution}")

if __name__ == "__main__":
    main()
