import hashlib
import json
import subprocess
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


SCRIPT = Path(__file__).with_name("package_release.py")


class PackageReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.src = self.root / "satellite"
        self.src.mkdir()
        self.meta = self.root / "meta.json"
        self.meta.write_text(json.dumps({
            "tracks": [
                {"track_name": "Venue One", "configurations": [{"track_id": 1}]},
                {"track_name": "Venue Two", "configurations": [{"track_id": 2}]},
            ]
        }), encoding="utf-8")

    def tearDown(self):
        self.temp.cleanup()

    def write_set(self, ir_id, include_tile=True, include_surface=True, surface_hash=None):
        directory = self.src / str(ir_id)
        (directory / "tiles").mkdir(parents=True)
        (directory / "full.jpg").write_bytes(b"overview")
        (directory / "corner.jpg").write_bytes(b"corner")
        if include_tile:
            (directory / "tiles" / "0-0.jpg").write_bytes(b"tile")
        live_tiles = {
            "ground_mpp": 0.25,
            "tile_size": 512,
            "gutter_px": 2,
            "corridor_m": 160,
            "tiles": [{"file": "tiles/0-0.jpg", "frame": [0, 0, 1, 1, 516, 516]}],
        }
        imagery = hashlib.sha256(b"SlipstreamHeroImagery/v1")
        imagery.update(struct.pack("<dii", live_tiles["ground_mpp"], live_tiles["tile_size"], live_tiles["gutter_px"]))
        for tile in live_tiles["tiles"]:
            imagery.update(tile["file"].encode("utf-8"))
            imagery.update(struct.pack("<6d", *tile["frame"]))
        imagery_hash = imagery.hexdigest()
        elevation_hash = hashlib.sha256(b"SlipstreamHeroElevation/v1").hexdigest()
        surface = struct.pack(
            "<4s4i5d32s32s4f", b"SLH3", 1, ir_id, 2, 2, 0, 0, 0, 1, 1,
            bytes.fromhex(imagery_hash), bytes.fromhex(elevation_hash), 0, 0, 0, 0)
        if include_surface:
            (directory / "hero3d").mkdir()
            (directory / "hero3d" / "surface-v1.bin").write_bytes(surface)
        surface_hash = surface_hash or hashlib.sha256(surface).hexdigest()
        manifest = {
            "ir_id": ir_id,
            "approved": True,
            "provider": "test",
            "attribution": "Test imagery",
            "full": {"file": "full.jpg", "frame": [0, 0, 1, 1, 1, 1]},
            "corners": [{"file": "corner.jpg", "frame": [0, 0, 1, 1, 1, 1]}],
            "live_tiles": live_tiles,
            "hero3d": {
                "format": "surface-v1",
                "file": "hero3d/surface-v1.bin",
                "sha256": surface_hash,
                "imagery_sha256": imagery_hash,
                "elevation_sha256": elevation_hash,
                "builder": "test",
            },
        }
        (directory / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    def run_package(self, *extra):
        command = [
            sys.executable, str(SCRIPT),
            "--src", str(self.src),
            "--meta", str(self.meta),
            "--out", str(self.root / "dist"),
            "--version", "imagery-v2",
            "--index", str(self.root / "index.json"),
            "--attribution", str(self.root / "ATTRIBUTION.md"),
            *extra,
        ]
        return subprocess.run(command, cwd=self.root, capture_output=True, text=True)

    def test_nested_tiles_are_packaged_and_indexed(self):
        self.write_set(1)

        result = self.run_package()

        self.assertEqual(0, result.returncode, result.stderr)
        with zipfile.ZipFile(self.root / "dist" / "venue-one.zip") as archive:
            self.assertIn("1/tiles/0-0.jpg", archive.namelist())
            self.assertIn("1/hero3d/surface-v1.bin", archive.namelist())
            self.assertEqual(zipfile.ZIP_DEFLATED, archive.getinfo("1/hero3d/surface-v1.bin").compress_type)
        index = json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(1, index["tracks"]["1"]["live_tiles"])
        self.assertTrue(index["tracks"]["1"]["hero3d"])

    def test_unreferenced_files_are_excluded_from_the_public_archive(self):
        self.write_set(1)
        directory = self.src / "1"
        (directory / "resolution-upgrade-receipt.json").write_text(
            '{"stage":"C:\\\\private\\\\review"}', encoding="utf-8")
        (directory / "review").mkdir()
        (directory / "review" / "source.jpg").write_bytes(b"private review image")

        result = self.run_package()

        self.assertEqual(0, result.returncode, result.stderr)
        with zipfile.ZipFile(self.root / "dist" / "venue-one.zip") as archive:
            self.assertEqual({
                "1/corner.jpg",
                "1/full.jpg",
                "1/hero3d/surface-v1.bin",
                "1/manifest.json",
                "1/tiles/0-0.jpg",
            }, set(archive.namelist()))

    def test_local_path_metadata_stops_packaging(self):
        self.write_set(1)
        manifest_path = self.src / "1" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["alignment"] = {"review": "ToDelete/_review/private/"}
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = self.run_package()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("manifest contains local-only path metadata", result.stderr)

    def test_missing_manifest_tile_stops_packaging(self):
        self.write_set(1, include_tile=False)

        result = self.run_package()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("manifest references missing asset", result.stderr)

    def test_live_tiles_without_surface_stop_packaging(self):
        self.write_set(1)
        manifest_path = self.src / "1" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        del manifest["hero3d"]
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = self.run_package()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("missing required hero3d companion", result.stderr)

    def test_surface_hash_mismatch_stops_packaging(self):
        self.write_set(1, surface_hash="0" * 64)

        result = self.run_package()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("hero3d hash mismatch", result.stderr)

    def test_stale_surface_for_changed_tiles_stops_packaging(self):
        self.write_set(1)
        manifest_path = self.src / "1" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest["live_tiles"]["ground_mpp"] = 0.3
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

        result = self.run_package()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("hero3d companion is stale or invalid", result.stderr)

    def test_flat_surface_stale_after_elevation_is_added_stops_packaging(self):
        self.write_set(1)
        elevation_dir = self.root / "track-elevation"
        elevation_dir.mkdir()
        (elevation_dir / "1.json").write_text(json.dumps({
            "schemaVersion": 1,
            "trackId": 1,
            "coveredBuckets": 512,
            "totalBuckets": 512,
            "samples": [
                {"pct": index / 511, "altitudeMeters": index / 10}
                for index in range(512)
            ],
        }), encoding="utf-8")

        result = self.run_package()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("hero3d companion is stale against elevation data", result.stderr)

    def test_partial_release_preserves_unselected_index_entries(self):
        self.write_set(1)
        self.write_set(2)
        (self.root / "index.json").write_text(json.dumps({
            "version": "imagery-v1",
            "tracks": {"2": {"venue": "Venue Two", "version": "imagery-v1", "sentinel": True}},
        }), encoding="utf-8")

        result = self.run_package("--only-ids", "1")

        self.assertEqual(0, result.returncode, result.stderr)
        index = json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        self.assertTrue(index["tracks"]["2"]["sentinel"])
        self.assertEqual("imagery-v2", index["tracks"]["1"]["version"])

    def test_partial_release_retains_credits_from_an_authoritative_source_tree(self):
        self.write_set(1)
        attribution_src = self.root / "production-satellite"
        production = attribution_src / "2"
        production.mkdir(parents=True)
        (production / "manifest.json").write_text(json.dumps({
            "approved": True,
            "attribution": "Historic imagery credit",
            "source": "Historic source URL",
        }), encoding="utf-8")

        result = self.run_package("--only-ids", "1", "--attribution-src", str(attribution_src))

        self.assertEqual(0, result.returncode, result.stderr)
        attribution = (self.root / "ATTRIBUTION.md").read_text(encoding="utf-8")
        self.assertIn("Test imagery", attribution)
        self.assertIn("Historic imagery credit", attribution)
        self.assertIn("Historic source URL", attribution)


if __name__ == "__main__":
    unittest.main()
