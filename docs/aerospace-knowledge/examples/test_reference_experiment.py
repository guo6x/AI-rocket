"""Stand-alone offline tests; no hardware, network, non-stdlib dependencies."""
from __future__ import annotations
import tempfile
import unittest
from pathlib import Path
from run_reference_experiment import (CASE, MODEL_GIT_BLOB_SHA, git_blob_sha, linearized_angle, run_experiment, simulate, _model_class)
from simulation_manifest import validate_manifest


class ReferenceExperimentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = Path(__file__).resolve().parents[3]

    def test_model_git_blob_matches_pinned_AdAstra_baseline(self):
        source = (self.repo / "dynamics_sim" / "physics_engine.py").read_bytes()
        self.assertEqual(git_blob_sha(source), MODEL_GIT_BLOB_SHA)

    def test_run_validates_and_archives(self):
        result = run_experiment(self.repo, self.root / "run1")
        self.assertEqual(result["status"], "PASS_NUMERICAL_REFERENCE_ONLY")
        self.assertEqual(validate_manifest(self.root / "run1" / "manifest.json"), [])
        self.assertTrue(result["archive_source_matches_pinned_git_blob"])

    def test_repeated_run_same_data_and_manifest(self):
        run_experiment(self.repo, self.root / "run1")
        run_experiment(self.repo, self.root / "run2")
        a,b=self.root / "run1", self.root / "run2"
        for path in ("manifest.json", "inputs/reference_case.json", "inputs/physics_engine.py", "outputs/samples.csv", "outputs/summary.json"):
            self.assertEqual((a/path).read_bytes(), (b/path).read_bytes(), path)

    def test_tampered_result_detected(self):
        run_experiment(self.repo, self.root / "run1")
        p=self.root / "run1" / "outputs" / "samples.csv"
        p.write_bytes(p.read_bytes()+b"corrupted")
        self.assertTrue(any("content mismatch" in e for e in validate_manifest(self.root / "run1" / "manifest.json")))

    def test_existing_archive_rejected_without_overwrite(self):
        archive=self.root / "run1"
        archive.mkdir()
        (archive/"keep.txt").write_text("do not delete", encoding="utf-8")
        with self.assertRaises(FileExistsError):
            run_experiment(self.repo, archive)
        self.assertEqual((archive/"keep.txt").read_text(), "do not delete")

    def test_small_angle_reference_accuracy(self):
        result=run_experiment(self.repo, self.root / "run1")
        self.assertLessEqual(result["max_abs_analytic_error_rad"], CASE["max_analytic_error_rad"])

    def test_zero_equilibrium_and_signed_symmetry(self):
        result=run_experiment(self.repo, self.root / "run1")
        self.assertLessEqual(result["max_abs_equilibrium_angle_rad"], CASE["max_equilibrium_error_rad"])
        self.assertLessEqual(result["max_abs_equilibrium_rate_rad_s"], CASE["max_equilibrium_error_rad"])
        self.assertLessEqual(result["max_pos_neg_symmetry_angle_rad"], CASE["max_symmetry_error_rad"])
        self.assertLessEqual(result["max_pos_neg_symmetry_rate_rad_s"], CASE["max_symmetry_error_rad"])

    def test_source_change_rejected(self):
        fake_repo=self.root/"other"
        (fake_repo/"dynamics_sim").mkdir(parents=True)
        orig=self.repo/"dynamics_sim"/"physics_engine.py"
        data=orig.read_bytes()
        (fake_repo/"dynamics_sim"/"physics_engine.py").write_bytes(data+b"# mutation\n")
        with self.assertRaisesRegex(RuntimeError, "MODEL_SOURCE_MISMATCH"):
            run_experiment(fake_repo, self.root/"run1")

if __name__ == "__main__": unittest.main()
