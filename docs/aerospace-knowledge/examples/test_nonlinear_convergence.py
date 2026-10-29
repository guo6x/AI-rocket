"""Isolated regression tests for KB4 nonlinear convergence experiment."""
import tempfile
import unittest
from pathlib import Path

from nonlinear_convergence import CASE, archive, evaluate, independent_rhs, integrate_original, reference_solvers
from simulation_manifest import validate_manifest


class NonlinearConvergenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo = Path(__file__).resolve().parents[3]
        cls.summary, cls.table, cls.report = evaluate(cls.repo)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_passes_in_nonlinear_case(self):
        self.assertEqual(self.summary["status"], "PASS_NUMERICAL_CONVERGENCE_ONLY")

    def test_four_step_sizes_are_strictly_decreasing_in_error(self):
        errors = [r["angle_error_to_DOP853_rad"] for r in self.summary["rk4_results"]]
        self.assertEqual(len(errors), 4)
        self.assertTrue(all(a>b>0 for a,b in zip(errors,errors[1:])))

    def test_step_halving_ratios_compatible_with_fourth_order(self):
        for ratio in self.summary["rk4_step_halving_angle_error_ratios"]:
            self.assertGreater(ratio, 10.0)
            self.assertLess(ratio, 20.0)

    def test_independent_radau_dop853_agreement(self):
        self.assertLess(self.summary["independent_solver_max_state_disagreement"], 1e-10)

    def test_fine_step_error_bound(self):
        self.assertLess(self.summary["rk4_results"][-1]["angle_error_to_DOP853_rad"], 1e-7)

    def test_archive_validates_and_does_not_overwrite(self):
        d=self.root/"run";archive(self.repo,d)
        self.assertEqual(validate_manifest(d/"manifest.json"),[])
        with self.assertRaises(FileExistsError):archive(self.repo,d)

    def test_two_archives_byte_identical(self):
        a=self.root/"a";b=self.root/"b";archive(self.repo,a);archive(self.repo,b)
        for name in ("manifest.json","inputs/physics_engine.py","inputs/case.json","outputs/convergence.csv","outputs/summary.json"):
            self.assertEqual((a/name).read_bytes(),(b/name).read_bytes(),name)

    def test_tamper_detected(self):
        d=self.root/"run";archive(self.repo,d)
        p=d/"outputs/convergence.csv";p.write_bytes(p.read_bytes()+b"tamper")
        self.assertTrue(any("content mismatch" in x for x in validate_manifest(d/"manifest.json")))

    def test_nonzero_thrust_not_accepted(self):
        bad=dict(CASE);bad["actual_thrust_N"]=1.0
        with self.assertRaises(ValueError):evaluate(self.repo,bad)

    def test_nonlinear_rhs_odd_about_origin(self):
        plus=independent_rhs(0.0,[0.2,0.1],CASE)
        minus=independent_rhs(0.0,[-0.2,-0.1],CASE)
        self.assertAlmostEqual(plus[0],-minus[0],places=12)
        self.assertAlmostEqual(plus[1],-minus[1],places=12)

if __name__ == "__main__": unittest.main()
