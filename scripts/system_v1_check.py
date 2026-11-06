"""Capture one sequential scripts/check.py run, environment and test identity.

A failing gate keeps its exit code. A successful gate returns 2 if its source
provenance or collection inventory is incomplete. Collection inventories are
not test executions; the two explicit GNC pytest groups are repeated subsets.
No firmware upload, device access or RF command is included.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_INCOMPLETE_EXIT = 2


def command(args, env):
    try:
        result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"command": subprocess.list2cmdline(args), "exit_code": 127, "stdout": "", "stderr": str(exc)}
    return {"command": subprocess.list2cmdline(args), "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def source_snapshot(env, output):
    """Exclude only this new receipt directory, never unrelated source edits."""
    status_args = ["git", "status", "--porcelain=v1", "--untracked-files=all", "--", "."]
    try:
        relative_output = output.relative_to(ROOT.resolve())
    except ValueError:
        pass  # An external output directory cannot dirty this repository.
    else:
        status_args.append(f":(top,exclude,literal){relative_output.as_posix()}")
    head = command(["git", "rev-parse", "--verify", "HEAD"], env)
    status = command(status_args, env)
    sha = head["stdout"].strip()
    errors = []
    if head["exit_code"] != 0 or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", sha):
        errors.append("Git HEAD could not be verified")
        sha = None
    if status["exit_code"] != 0:
        errors.append("Git working-tree status could not be read")
    dirty = status["stdout"].splitlines()
    return {"source_git_sha": sha, "git_status": dirty, "errors": errors,
            "commands": {"head": head, "status": status}}


def evidence_errors(start, end, inventories):
    errors = [f"source at start: {item}" for item in start["errors"]]
    errors.extend(f"source at end: {item}" for item in end["errors"])
    if start["git_status"]:
        errors.append("Source working tree was not clean at start")
    if end["git_status"]:
        errors.append("Source working tree was not clean at end")
    if start["source_git_sha"] != end["source_git_sha"]:
        errors.append("Git HEAD changed during the run")
    errors.extend(f"Test inventory failed: {path}" for path, result in inventories.items() if result["exit_code"] != 0)
    return errors


def run_gate(args, env, log_path):
    with log_path.open("w", encoding="utf-8") as log:
        try:
            process = subprocess.Popen(args, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                       text=True, encoding="utf-8", errors="replace")
        except OSError as exc:
            message = f"Unable to start software gate: {exc}\n"
            log.write(message)
            print(message, end="", flush=True)
            return 127
        with process:
            for line in process.stdout:
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
            return process.wait()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("QT_OPENGL", "software")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    start = source_snapshot(env, output)
    source = start["source_git_sha"]
    environment = {
        "source_git_sha": source, "git_status_at_start": start["git_status"],
        "source_snapshot_at_start": start,
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "dependencies": dict(sorted((dist.metadata["Name"], dist.version) for dist in importlib.metadata.distributions() if dist.metadata.get("Name"))),
        "platformio_system": command([sys.executable, "-m", "platformio", "system", "info", "--json-output"], env),
        "hardware_status": "NOT_EVALUATED; no hardware actions authorized",
    }
    (output / "environment.json").write_text(json.dumps(environment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # One gate process; its own stages execute strictly sequentially.
    check_command = [sys.executable, "-u", "scripts/check.py"]
    gate_exit_code = run_gate(check_command, env, output / "full_check.log")
    inventories = {}
    for path in ("ground_station/tests", "scripts/tests", "docs/aerospace-knowledge/examples"):
        inventories[path] = command([sys.executable, "-m", "pytest", path, "--collect-only", "-q"], env)
    inventories["rf_lab/tests"] = command([sys.executable, "-c", (
        "import json,sys,unittest; "
        "loader=unittest.TestLoader(); suite=loader.discover('rf_lab/tests'); "
        "flatten=lambda s: [t.id() for t in s if isinstance(t,unittest.TestCase)] + [i for t in s if not isinstance(t,unittest.TestCase) for i in flatten(t)]; "
        "ids=flatten(suite); print(json.dumps({'count':len(ids),'ids':ids,'collection_errors':loader.errors},indent=2)); "
        "sys.exit(1 if loader.errors or not ids else 0)"
    )], env)
    (output / "test_inventory.json").write_text(json.dumps(inventories, indent=2) + "\n", encoding="utf-8")
    end = source_snapshot(env, output)
    errors = evidence_errors(start, end, inventories)
    exit_code = gate_exit_code or (EVIDENCE_INCOMPLETE_EXIT if errors else 0)
    result = {
        "status": "FAIL" if gate_exit_code else ("INCOMPLETE" if errors else "PASS"), "exit_code": exit_code,
        "gate_status": "PASS" if gate_exit_code == 0 else "FAIL", "gate_exit_code": gate_exit_code,
        "evidence_status": "INCOMPLETE" if errors else "COMPLETE", "evidence_errors": errors,
        "source_git_sha": source, "source_snapshot_at_end": end,
        "source_provenance_limit": "Start/end Git snapshots do not prove the absence of transient edits or attest ignored/external inputs",
        "command": subprocess.list2cmdline(check_command),
        "collection_is_not_execution": True,
        "repeated_groups": ["scripts/tests/test_gnc_offline_oracle.py", "scripts/tests/test_gnc_dual_period.py"],
        "evidence_ceiling": "TESTED_SOFTWARE only; no hardware qualification",
        "files_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(output.iterdir()) if path.is_file()},
    }
    (output / "check_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
