"""Receipt integrity tests; synthetic gates never exercise hardware or firmware."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from scripts import system_v1_check as check


@unittest.skipUnless(shutil.which("git"), "Git is required for provenance integration tests")
class ReceiptRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        (self.root / "scripts").mkdir()
        (self.root / "scripts/check.py").write_text("print('SYNTHETIC SOFTWARE GATE')\n", encoding="utf-8")
        (self.root / "source.txt").write_text("original\n", encoding="utf-8")
        self.git("init", "-q")
        self.git("config", "user.name", "Receipt Test Fixture")
        self.git("config", "user.email", "receipt-fixture@example.invalid")
        self.commit()
        self.output = self.root / "evidence[0]" / "new run"
        self.inventory_failures = set()
        self.git_failures = set()
        self.real_rf_collection = False
        self.command_calls = []
        original_command = check.command

        def scoped_command(args, env):
            self.command_calls.append(args)
            if args[0] == "git":
                if args[1] in self.git_failures:
                    return {"command": subprocess.list2cmdline(args), "exit_code": 128, "stdout": "", "stderr": "injected Git failure"}
                return original_command(args, env)
            inventory_key = args[3] if len(args) > 3 and args[2] == "pytest" else "rf_lab/tests"
            if self.real_rf_collection and args[1] == "-c":
                return original_command(args, env)
            # Isolate receipt logic from optional application and toolchain packages.
            return {"command": subprocess.list2cmdline(args), "exit_code": 1 if inventory_key in self.inventory_failures else 0,
                    "stdout": "synthetic collection result\n", "stderr": ""}

        self.patch_root = mock.patch.object(check, "ROOT", self.root)
        self.patch_root.start()
        self.addCleanup(self.patch_root.stop)
        self.patch_command = mock.patch.object(check, "command", side_effect=scoped_command)
        self.patch_command.start()
        self.addCleanup(self.patch_command.stop)
        self.patch_packages = mock.patch.object(check.importlib.metadata, "distributions", return_value=[])
        self.patch_packages.start()
        self.addCleanup(self.patch_packages.stop)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout.strip()

    def commit(self):
        self.git("add", ".")
        self.git("commit", "-qm", "Synthetic test fixture")

    def run_receipt(self):
        with mock.patch.object(sys, "argv", ["system_v1_check.py", "--output", str(self.output)]), redirect_stdout(io.StringIO()):
            code = check.main()
        return code, json.loads((self.output / "check_result.json").read_text(encoding="utf-8"))

    def test_clean_run_passes_and_new_receipt_directory_is_excluded(self):
        code, result = self.run_receipt()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["gate_exit_code"], 0)
        self.assertEqual(result["evidence_status"], "COMPLETE")
        self.assertEqual(result["source_snapshot_at_end"]["git_status"], [])
        self.assertEqual(result["source_git_sha"], self.git("rev-parse", "HEAD"))
        for filename, digest in result["files_sha256"].items():
            self.assertEqual(digest, hashlib.sha256((self.output / filename).read_bytes()).hexdigest())
        self.assertEqual((self.output / "full_check.log").read_text().count("SYNTHETIC SOFTWARE GATE"), 1)
        self.assertIn("NOT_EVALUATED", json.loads((self.output / "environment.json").read_text())["hardware_status"])
        self.assertTrue(result["collection_is_not_execution"])

    def test_failed_pytest_collection_cannot_be_overall_pass(self):
        self.inventory_failures.add("scripts/tests")
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)
        self.assertEqual(result["gate_exit_code"], 0)
        self.assertIn("Test inventory failed: scripts/tests", result["evidence_errors"])

    def test_failed_rf_collection_cannot_be_overall_pass(self):
        self.inventory_failures.add("rf_lab/tests")
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)

    def test_failed_git_head_cannot_be_overall_pass(self):
        self.git_failures.add("rev-parse")
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)
        self.assertIsNone(result["source_git_sha"])

    def test_real_rf_import_error_cannot_be_overall_pass(self):
        folder = self.root / "rf_lab/tests"
        folder.mkdir(parents=True)
        (folder / "test_broken.py").write_text("raise ImportError('synthetic broken module')\n")
        (self.root / ".gitignore").write_text("__pycache__/\n")
        self.commit()
        self.real_rf_collection = True
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)
        inventory = json.loads((self.output / "test_inventory.json").read_text())["rf_lab/tests"]
        self.assertEqual(inventory["exit_code"], 1)
        self.assertTrue(json.loads(inventory["stdout"])["collection_errors"])

    def test_real_empty_rf_collection_cannot_be_overall_pass(self):
        folder = self.root / "rf_lab/tests"
        folder.mkdir(parents=True)
        (folder / ".keep").write_text("Synthetic empty suite\n")
        self.commit()
        self.real_rf_collection = True
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)
        inventory = json.loads((self.output / "test_inventory.json").read_text())["rf_lab/tests"]
        self.assertEqual(inventory["exit_code"], 1)
        self.assertEqual(json.loads(inventory["stdout"])["count"], 0)

    def test_real_rf_collection_does_not_execute_test_body(self):
        folder = self.root / "rf_lab/tests"
        folder.mkdir(parents=True)
        (folder / "test_collect.py").write_text("import unittest\nclass CollectionFixture(unittest.TestCase):\n    def test_never_run(self):\n        raise AssertionError('Collection is not execution')\n")
        (self.root / ".gitignore").write_text("__pycache__/\n")
        self.commit()
        self.real_rf_collection = True
        code, result = self.run_receipt()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PASS")
        inventory = json.loads((self.output / "test_inventory.json").read_text())["rf_lab/tests"]
        self.assertEqual(json.loads(inventory["stdout"])["count"], 1)
        self.assertEqual(json.loads(inventory["stdout"])["collection_errors"], [])

    def test_failed_git_status_cannot_be_overall_pass(self):
        self.git_failures.add("status")
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)

    def test_dirty_tracked_source_cannot_be_overall_pass(self):
        (self.root / "source.txt").write_text("uncommitted change\n")
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)

    def test_output_exclusion_does_not_hide_neighbor_untracked_source(self):
        (self.root / "evidence[0]").mkdir()
        (self.root / "evidence[0]" / "untracked-source.py").write_text("# not this receipt\n")
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)

    def test_source_edit_during_gate_cannot_be_overall_pass(self):
        (self.root / "scripts/check.py").write_text("from pathlib import Path\nPath('source.txt').write_text('changed during gate')\n")
        self.commit()
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)
        self.assertIn("Source working tree was not clean at end", result["evidence_errors"])

    def test_head_change_during_gate_cannot_be_overall_pass(self):
        (self.root / "scripts/check.py").write_text(
            "from pathlib import Path\nimport subprocess\nPath('source.txt').write_text('new commit')\n"
            "subprocess.run(['git', 'add', 'source.txt'], check=True)\n"
            "subprocess.run(['git', 'commit', '-qm', 'Synthetic change during gate'], check=True)\n")
        self.commit()
        code, result = self.run_receipt()
        self.assertEqual(result["status"], "INCOMPLETE")
        self.assertEqual(code, 2)
        self.assertIn("Git HEAD changed during the run", result["evidence_errors"])
        self.assertEqual(result["source_snapshot_at_end"]["git_status"], [])

    def test_gate_failure_keeps_original_exit_code_even_with_collection_failure(self):
        (self.root / "scripts/check.py").write_text("raise SystemExit(7)\n")
        self.commit()
        self.inventory_failures.add("scripts/tests")
        code, result = self.run_receipt()
        self.assertEqual(code, 7)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["gate_exit_code"], 7)
        self.assertEqual(result["evidence_status"], "INCOMPLETE")

    def test_external_output_directory_is_supported(self):
        with tempfile.TemporaryDirectory() as destination:
            self.output = Path(destination) / "new receipt"
            code, result = self.run_receipt()
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "PASS")

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir(parents=True)
        sentinel = self.output / "preserve.txt"
        sentinel.write_text("previous evidence")
        with self.assertRaises(FileExistsError):
            self.run_receipt()
        self.assertEqual(sentinel.read_text(), "previous evidence")
        self.assertEqual(self.command_calls, [])


class ReceiptUnitTests(unittest.TestCase):
    def test_missing_executable_is_recorded(self):
        with mock.patch.object(check.subprocess, "run", side_effect=FileNotFoundError("missing git")):
            result = check.command(["git", "rev-parse", "HEAD"], {})
        self.assertEqual(result["exit_code"], 127)
        self.assertIn("missing git", result["stderr"])

    def test_gate_launch_failure_is_logged(self):
        with tempfile.TemporaryDirectory() as directory, mock.patch.object(check.subprocess, "Popen", side_effect=OSError("cannot start gate")), redirect_stdout(io.StringIO()):
            log = Path(directory) / "full_check.log"
            code = check.run_gate(["missing-python", "scripts/check.py"], {}, log)
            self.assertEqual(code, 127)
            self.assertIn("cannot start gate", log.read_text())

    def test_malformed_successful_git_head_is_not_accepted(self):
        for value in ("", "main", "abc123", "z" * 40):
            with self.subTest(value=value), mock.patch.object(check, "command", side_effect=[
                {"exit_code": 0, "stdout": value, "stderr": ""},
                {"exit_code": 0, "stdout": "", "stderr": ""},
            ]):
                result = check.source_snapshot({}, check.ROOT / "new-output")
            self.assertIsNone(result["source_git_sha"])
            self.assertTrue(result["errors"])

    def test_sha1_and_sha256_git_hashes_are_accepted(self):
        for length in (40, 64):
            with self.subTest(length=length), mock.patch.object(check, "command", side_effect=[
                {"exit_code": 0, "stdout": "a" * length + "\n", "stderr": ""},
                {"exit_code": 0, "stdout": "", "stderr": ""},
            ]):
                result = check.source_snapshot({}, check.ROOT / "new-output")
            self.assertEqual(result["source_git_sha"], "a" * length)
            self.assertEqual(result["errors"], [])


if __name__ == "__main__":
    unittest.main()
