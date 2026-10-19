"""Standalone offline regression tests; run: python -m unittest -v test_simulation_manifest.py"""
import json
import tempfile
import unittest
from pathlib import Path

from simulation_manifest import sha256_file, validate_manifest


class ResearchManifestTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.a = self.root / "input.json"
        self.b = self.root / "output.csv"
        self.a.write_text('{"value": 1}', encoding="utf-8")
        self.b.write_text("x,y\n1,2\n", encoding="utf-8")
        self.data = {
            "schema_version": 1, "run_id": "DEMO-OFFLINE-001", "classification": "SOFTWARE_SIMULATION_ONLY",
            "intended_use": "Exercise offline manifest validator only",
            "unsupported_uses": ["flight readiness", "structural approval", "physical hardware validation"],
            "model": {"name": "synthetic-demo", "version": "0.0.0", "coordinate_system": "none", "units": {"value": "dimensionless"}, "assumptions": ["synthetic"], "physical_correlation_status": "NOT_APPLICABLE"},
            "source": {"repository": "synthetic/not-a-real-repo", "commit": "a" * 40},
            "runtime": {"python_version": "3.11", "dependencies": {}, "command": "none - fixture only", "random_seed": 0},
            "inputs": [{"path": "input.json", "sha256": sha256_file(self.a)}],
            "outputs": [{"path": "output.csv", "sha256": sha256_file(self.b)}],
        }
        self.manifest = self.root / "manifest.json"

    def check(self, expected_fragment=None):
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")
        errors = validate_manifest(self.manifest)
        if expected_fragment is None:
            self.assertEqual(errors, [])
        else:
            self.assertTrue(any(expected_fragment in x for x in errors), errors)

    def test_valid_archive(self): self.check()
    def test_tampered_output(self):
        self.b.write_text("x,y\n1,999\n", encoding="utf-8")
        self.check("content mismatch")
    def test_missing_artifact(self):
        self.a.unlink()
        self.check("inaccessible")
    def test_path_traversal(self):
        self.data["inputs"][0]["path"] = "../input.json"
        self.check("dot segments")
    def test_unsafe_absolute_path(self):
        self.data["inputs"][0]["path"] = "/etc/passwd"
        self.check("absolute")
    def test_malformed_sha(self):
        self.data["outputs"][0]["sha256"] = "00"
        self.check("64-hex")
    def test_duplicate_artifact(self):
        self.data["inputs"].append(self.data["inputs"][0].copy())
        self.check("duplicate")
    def test_wrong_git_commit(self):
        self.data["source"]["commit"] = "abcd"
        self.check("40-hex")
    def test_wrong_evidence_classification(self):
        self.data["classification"] = "VERIFIED_HARDWARE"
        self.check("SOFTWARE_SIMULATION_ONLY")
    def test_missing_unsupported_uses(self):
        self.data["unsupported_uses"] = []
        self.check("unsupported_uses")
    def test_missing_outputs(self):
        self.data["outputs"] = []
        self.check("nonempty list")
    def test_windows_path(self):
        self.data["inputs"][0]["path"] = "C:\\work\\input.json"
        self.check("absolute/Windows/backslash")
    def test_manifest_self_reference(self):
        self.data["inputs"][0] = {"path":"manifest.json", "sha256":"0"*64}
        self.check("manifest cannot hash itself")
    def test_external_symlink(self):
        outside = self.root.parent / (self.root.name + "_external.txt")
        outside.write_text("external", encoding="utf-8")
        self.addCleanup(outside.unlink)
        p = self.root / "link.txt"
        try:
            p.symlink_to(outside)
        except OSError:
            self.skipTest("symlinks not supported")
        self.data["inputs"][0] = {"path": "link.txt", "sha256": sha256_file(outside)}
        self.check("escapes manifest directory")


if __name__ == "__main__":
    unittest.main()
