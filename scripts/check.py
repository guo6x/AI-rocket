"""Unified R0/R1/R2/R2.1 software gates; never uploads or touches hardware."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def find_platformio() -> str | None:
    command = shutil.which("platformio") or shutil.which("pio")
    if command:
        return command
    suffix = ".exe" if os.name == "nt" else ""
    candidate = Path(sys.executable).with_name(f"platformio{suffix}")
    return str(candidate) if candidate.exists() else None


def add_platformio_mingw_to_path(env: dict[str, str], platformio: str) -> None:
    if os.name != "nt" or shutil.which("gcc", path=env.get("PATH")):
        return
    result = subprocess.run(
        [platformio, "system", "info", "--json-output"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return
    core_dir = Path(json.loads(result.stdout)["core_dir"]["value"])
    compiler_bin = core_dir / "packages" / "toolchain-gccmingw32" / "bin"
    if (compiler_bin / "gcc.exe").exists():
        env["PATH"] = str(compiler_bin) + os.pathsep + env.get("PATH", "")


def run_step(label: str, command: list[str], env: dict[str, str]) -> bool:
    print(f"\n=== {label} ===", flush=True)
    print("$ " + subprocess.list2cmdline(command), flush=True)
    result = subprocess.run(command, cwd=ROOT, env=env)
    print(f"{label}: {'PASS' if result.returncode == 0 else 'FAIL'}", flush=True)
    return result.returncode == 0


def main() -> int:
    env = os.environ.copy()
    env.setdefault("PYTHONUTF8", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    env.setdefault("QT_QPA_PLATFORM", "offscreen")

    platformio = find_platformio()
    if not platformio:
        print("PlatformIO is missing. Install requirements-dev.txt before running checks.")
        print("R0 SOFTWARE CHECK: FAIL")
        print("R1 COMMAND SAFETY CHECK: FAIL")
        print("R2 PHYSICAL BASELINE STRUCTURE CHECK: FAIL")
        print("R2.1 COMPATIBILITY STRUCTURE CHECK: FAIL")
        return 1
    add_platformio_mingw_to_path(env, platformio)

    steps = [
        (
            "Python syntax",
            [
                sys.executable,
                "-m",
                "compileall",
                "-q",
                "aero_sim",
                "dynamics_sim",
                "ground_station",
                "flight_computer",
                "scripts",
            ],
        ),
        ("Engineering YAML", [sys.executable, "-c", (
            "import pathlib,yaml; "
            "[yaml.safe_load(p.read_text(encoding='utf-8')) "
            "for p in sorted(pathlib.Path('engineering').rglob('*.yaml'))]"
        )]),
        ("Ground station tests", [sys.executable, "-m", "pytest", "ground_station/tests", "-q"]),
        ("Simulation smoke", [sys.executable, "scripts/simulation_smoke.py"]),
        ("Flight core native tests", [platformio, "test", "-d", "flight_computer", "-e", "native"]),
        ("ESP relay native tests", [platformio, "test", "-d", "esp8266_firmware", "-e", "native"]),
        ("STM32 source build", [platformio, "run", "-d", "flight_computer", "-e", "bluepill_f103c8"]),
        ("APM32 experimental compatibility build", [platformio, "run", "-d", "flight_computer", "-e", "apm32f103c8_compat"]),
        ("ESP8266 source build", [platformio, "run", "-d", "esp8266_firmware", "-e", "nodemcuv2"]),
        ("ESP-01S source build", [platformio, "run", "-d", "esp8266_firmware", "-e", "esp01_1m"]),
        (
            "R2 physical baseline structure",
            [sys.executable, "scripts/r2_physical_baseline_check.py"],
        ),
        (
            "R2.1 ownership and dependency structure",
            [sys.executable, "scripts/r2_1_check.py"],
        ),
        (
            "R2 and R2.1 deterministic gate tests",
            [sys.executable, "-m", "pytest", "scripts/tests", "-q"],
        ),
        (
            "Preserved research offline regressions",
            [sys.executable, "-m", "pytest", "docs/aerospace-knowledge/examples", "-q"],
        ),
    ]

    results = [run_step(label, command, env) for label, command in steps]
    passed = all(results)
    print("\nHardware checks: MANUAL / HARDWARE-GATED (not part of this exit code)")
    print(f"R0 SOFTWARE CHECK: {'PASS' if passed else 'FAIL'}")
    print(f"R1 COMMAND SAFETY CHECK: {'PASS' if passed else 'FAIL'}")
    print(f"R2.1 SOFTWARE REGRESSION CHECK: {'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
