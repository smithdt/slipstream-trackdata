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
import argparse, json, os, re, zipfile, hashlib, math, struct

def slug(s):
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", s.lower())).strip("-")

def referenced_files(manifest):
    files = [manifest["full"]["file"]]
    files.extend(c["file"] for c in manifest.get("corners", []))
    files.extend(t["file"] for t in (manifest.get("live_tiles") or {}).get("tiles", []))
    if manifest.get("hero3d"):
        files.append(manifest["hero3d"]["file"])
    return files

def hero_imagery_fingerprint(live_tiles):
    digest = hashlib.sha256(b"SlipstreamHeroImagery/v1")
    digest.update(struct.pack("<d", float(live_tiles.get("ground_mpp", 0))))
    digest.update(struct.pack("<i", int(live_tiles.get("tile_size", 0))))
    digest.update(struct.pack("<i", int(live_tiles.get("gutter_px", 0))))
    for tile in sorted(live_tiles.get("tiles", []), key=lambda item: item["file"]):
        digest.update(tile["file"].encode("utf-8"))
        for value in tile["frame"]:
            digest.update(struct.pack("<d", float(value)))
    return digest.hexdigest()

def as_float32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]

def load_elevation_profile(path, track_id):
    try:
        if not os.path.isfile(path):
            return None
        payload = json.load(open(path, encoding="utf-8"))
        covered = payload.get("coveredBuckets")
        total = payload.get("totalBuckets")
        samples = payload.get("samples")
        if (payload.get("schemaVersion") != 1 or payload.get("trackId") != track_id
                or not isinstance(covered, (int, float)) or not isinstance(total, (int, float))
                or not math.isfinite(covered) or not math.isfinite(total)
                or total <= 0 or total > 4096 or total != int(total)
                or covered < 0 or covered != int(covered) or covered > total or covered / total < 0.60
                or not isinstance(samples, list) or len(samples) < 8 or len(samples) > 4096):
            return None
        totals = [0.0] * 512
        counts = [0] * 512
        for sample in samples:
            pct, altitude = sample.get("pct"), sample.get("altitudeMeters")
            if (not isinstance(pct, (int, float)) or not isinstance(altitude, (int, float))
                    or not math.isfinite(pct) or not math.isfinite(altitude) or pct < 0 or pct > 1):
                continue
            bucket = int(max(0, min(511, pct * 511)))
            totals[bucket] += altitude
            counts[bucket] += 1
        if sum(count > 0 for count in counts) < 512 * 0.60:
            return None
        profile = [as_float32(totals[i] / counts[i]) if counts[i] else math.nan for i in range(512)]
        first = next((i for i, value in enumerate(profile) if math.isfinite(value)), -1)
        if first < 0:
            return None
        for i in range(first):
            profile[i] = profile[first]
        previous = first
        for i in range(first + 1, len(profile)):
            if not math.isfinite(profile[i]):
                continue
            gap = i - previous
            if gap > 1:
                start, end = profile[previous], profile[i]
                delta = as_float32(end - start)
                for j in range(1, gap):
                    ratio = as_float32(j / gap)
                    profile[previous + j] = as_float32(start + as_float32(delta * ratio))
            previous = i
        for i in range(previous + 1, len(profile)):
            profile[i] = profile[previous]
        minimum, maximum = min(profile), max(profile)
        if not math.isfinite(minimum) or not math.isfinite(maximum) or maximum - minimum < 0.5:
            return None
        return [as_float32(value - minimum) for value in profile]
    except (OSError, TypeError, ValueError, json.JSONDecodeError):
        return None

def hero_elevation_fingerprint(elevation_dir, track_id):
    digest = hashlib.sha256(b"SlipstreamHeroElevation/v1")
    profile = load_elevation_profile(os.path.join(elevation_dir, f"{track_id}.json"), track_id)
    if profile is not None:
        for value in profile:
            digest.update(struct.pack("<f", value))
    return digest.hexdigest()

def validate_hero3d(surface, manifest, hero3d, directory):
    data = open(surface, "rb").read()
    actual = hashlib.sha256(data).hexdigest()
    if actual.lower() != hero3d["sha256"].lower():
        raise SystemExit(f"hero3d hash mismatch: {directory}")
    header_format = "<4s4i5d32s32s"
    header_size = struct.calcsize(header_format)
    if len(data) < header_size:
        raise SystemExit(f"invalid hero3d binary header: {directory}")
    magic, version, track_id, columns, rows, latitude, min_x, min_y, max_x, max_y, imagery, elevation = \
        struct.unpack_from(header_format, data)
    vertices = columns * rows
    expected_imagery = hero_imagery_fingerprint(manifest["live_tiles"])
    if (magic != b"SLH3" or version != 1 or track_id != manifest["ir_id"]
            or columns < 2 or columns > 420 or rows < 2 or rows > 560 or vertices > 420 * 560
            or not all(math.isfinite(value) for value in (latitude, min_x, min_y, max_x, max_y))
            or max_x <= min_x or max_y <= min_y or len(data) != header_size + vertices * 4
            or imagery.hex().lower() != expected_imagery.lower()
            or imagery.hex().lower() != hero3d["imagery_sha256"].lower()
            or elevation.hex().lower() != hero3d["elevation_sha256"].lower()
            or any(not math.isfinite(value[0]) for value in struct.iter_unpack("<f", data[header_size:]))):
        raise SystemExit(f"hero3d companion is stale or invalid: {directory}")

def validate_assets(directory, manifest, elevation_dir):
    root = os.path.realpath(directory)
    live_tiles = (manifest.get("live_tiles") or {}).get("tiles", [])
    hero3d = manifest.get("hero3d")
    if live_tiles and not hero3d:
        raise SystemExit(f"live-tile set is missing required hero3d companion: {directory}")
    for rel in referenced_files(manifest):
        path = os.path.realpath(os.path.join(root, rel))
        if os.path.commonpath([root, path]) != root:
            raise SystemExit(f"manifest asset escapes track directory: {directory} -> {rel}")
        if not os.path.isfile(path):
            raise SystemExit(f"manifest references missing asset: {directory} -> {rel}")
    if hero3d:
        if hero3d.get("format") != "surface-v1":
            raise SystemExit(f"unsupported hero3d format: {directory}")
        for field in ("sha256", "imagery_sha256", "elevation_sha256"):
            value = hero3d.get(field, "")
            if not re.fullmatch(r"[0-9a-fA-F]{64}", value):
                raise SystemExit(f"invalid hero3d {field}: {directory}")
        surface = os.path.join(root, hero3d["file"])
        expected_elevation = hero_elevation_fingerprint(elevation_dir, manifest["ir_id"])
        if expected_elevation.lower() != hero3d["elevation_sha256"].lower():
            raise SystemExit(f"hero3d companion is stale against elevation data: {directory}")
        validate_hero3d(surface, manifest, hero3d, directory)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, help="satellite/ source tree (satellite/{ir_id}/...)")
    ap.add_argument("--meta", required=True, help="iracing-tracks-metadata.json (ir_id -> venue)")
    ap.add_argument("--elevation-dir", default=None,
                    help="authoritative track-elevation directory; defaults beside --meta")
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
    elevation_dir = a.elevation_dir or os.path.join(os.path.dirname(os.path.abspath(a.meta)), "track-elevation")

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
        validate_assets(d, m, elevation_dir)
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
                        if rel == (m.get("hero3d") or {}).get("file"):
                            # JPEGs are already compressed, but the float terrain grid is highly compressible
                            # (especially flat fallbacks). Keep it small on the wire without duplicating imagery.
                            z.write(path, f"{ir}/{rel}", compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
                        else:
                            z.write(path, f"{ir}/{rel}")
        sha = hashlib.sha256(open(zpath, "rb").read()).hexdigest()[:16]
        asset = f"{a.base_url}/{a.version}/{vslug}.zip"
        for ir, m in sets:
            index["tracks"][str(ir)] = {
                "venue": venue, "asset": asset, "version": a.version, "sha256": sha,
                "corners": len(m.get("corners", [])), "provider": m.get("provider"),
                "live_tiles": len((m.get("live_tiles") or {}).get("tiles", [])),
                "hero3d": bool(m.get("hero3d")),
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
