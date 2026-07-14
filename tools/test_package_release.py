import json
import subprocess
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

    def write_set(self, ir_id, include_tile=True):
        directory = self.src / str(ir_id)
        (directory / "tiles").mkdir(parents=True)
        (directory / "full.jpg").write_bytes(b"overview")
        (directory / "corner.jpg").write_bytes(b"corner")
        if include_tile:
            (directory / "tiles" / "0-0.jpg").write_bytes(b"tile")
        manifest = {
            "ir_id": ir_id,
            "approved": True,
            "provider": "test",
            "attribution": "Test imagery",
            "full": {"file": "full.jpg", "frame": [0, 0, 1, 1, 1, 1]},
            "corners": [{"file": "corner.jpg", "frame": [0, 0, 1, 1, 1, 1]}],
            "live_tiles": {
                "ground_mpp": 0.25,
                "tile_size": 512,
                "gutter_px": 2,
                "corridor_m": 160,
                "tiles": [{"file": "tiles/0-0.jpg", "frame": [0, 0, 1, 1, 516, 516]}],
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
        index = json.loads((self.root / "index.json").read_text(encoding="utf-8"))
        self.assertEqual(1, index["tracks"]["1"]["live_tiles"])

    def test_missing_manifest_tile_stops_packaging(self):
        self.write_set(1, include_tile=False)

        result = self.run_package()

        self.assertNotEqual(0, result.returncode)
        self.assertIn("manifest references missing asset", result.stderr)

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
