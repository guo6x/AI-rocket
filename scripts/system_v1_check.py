"""Capture one sequential scripts/check.py run, environment and test identity.

This wrapper preserves the real gate's exit code. Collection inventories are
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
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def command(args, env):
    result = subprocess.run(args, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"command": subprocess.list2cmdline(args), "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    env.setdefault("QT_OPENGL", "software")
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    source = command(["git", "rev-parse", "HEAD"], env)["stdout"].strip()
    status = command(["git", "status", "--porcelain"], env)["stdout"].splitlines()
    environment = {
        "source_git_sha": source, "git_status_at_start": status,
        "python": sys.version, "executable": sys.executable, "platform": platform.platform(),
        "dependencies": dict(sorted((dist.metadata["Name"], dist.version) for dist in importlib.metadata.distributions() if dist.metadata.get("Name"))),
        "platformio_system": command([sys.executable, "-m", "platformio", "system", "info", "--json-output"], env),
        "hardware_status": "NOT_EVALUATED; no hardware actions authorized",
    }
    (output / "environment.json").write_text(json.dumps(environment, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    # One gate process; its own stages execute strictly sequentially.
    check_command = [sys.executable, "-u", "scripts/check.py"]
    log_path = output / "full_check.log"
    with log_path.open("w", encoding="utf-8") as log:
        process = subprocess.Popen(check_command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                   text=True, encoding="utf-8", errors="replace")
        for line in process.stdout:
            log.write(line)
            log.flush()
            print(line, end="", flush=True)
        exit_code = process.wait()
    inventories = {}
    for path in ("ground_station/tests", "scripts/tests", "docs/aerospace-knowledge/examples"):
        inventories[path] = command([sys.executable, "-m", "pytest", path, "--collect-only", "-q"], env)
    inventories["rf_lab/tests"] = command([sys.executable, "-c", (
        "import json,unittest; "
        "suite=unittest.defaultTestLoader.discover('rf_lab/tests'); "
        "flatten=lambda s: [t.id() for t in s if isinstance(t,unittest.TestCase)] + [i for t in s if not isinstance(t,unittest.TestCase) for i in flatten(t)]; "
        "ids=flatten(suite); print(json.dumps({'count':len(ids),'ids':ids},indent=2))"
    )], env)
    (output / "test_inventory.json").write_text(json.dumps(inventories, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": "PASS" if exit_code == 0 else "FAIL", "exit_code": exit_code,
        "source_git_sha": source, "command": subprocess.list2cmdline(check_command),
        "collection_is_not_execution": True,
        "repeated_groups": ["scripts/tests/test_gnc_offline_oracle.py", "scripts/tests/test_gnc_dual_period.py"],
        "evidence_ceiling": "TESTED_SOFTWARE only; no hardware qualification",
        "files_sha256": {path.name: hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(output.iterdir()) if path.is_file()},
    }
    (output / "check_result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
