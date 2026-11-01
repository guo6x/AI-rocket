"""R2.5: read-only GNC/avionics evidence-boundary report, never a hardware GO.

Derives the first unpowered observation from existing authority documents.
Does not access hardware, upload firmware, or authorize powered tests.
Run: python -m scripts.r2_5_entry_gate --json
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
from typing import Any
from scripts.r2_1_check import _load_yaml, validate as validate_r21

ROOT = Path(__file__).resolve().parents[1]
INPUTS = {
    "assets": "engineering/assets/project-asset-registry.yaml",
    "lines": "engineering/experimental-lines.yaml",
    "plan": "engineering/bringup/gnc-avionics-bringup.yaml",
    "baseline": "engineering/current-baseline.yaml",
    "cad": "engineering/cad-authority.yaml",
    "measurements": "engineering/as-built/measurement-plan.yaml",
}
SATISFIED = {"COMPLETE_SOFTWARE", "COMPLETED", "NOT_REQUIRED"}
FIRST_BOUNDARY = "S2A-UNPOWERED-BOARD-OBSERVATION"
RECOVERY_BLOCKER = "R2_1-005"

def _index(rows: Any, key: str, errors: list[str], context: str) -> dict[str, dict[str, Any]]:
    if not isinstance(rows, list):
        errors.append(f"{context} is not a list")
        return {}
    result = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, dict) or not isinstance(row.get(key), str):
            errors.append(f"{context}[{idx}] lacks {key}")
            continue
        ident = row[key]
        if ident in result:
            errors.append(f"{context}: duplicate {ident}")
        result[ident] = row
    return result

def evaluate(docs: dict[str, Any], authority_errors: list[str] | None = None) -> dict[str, Any]:
    """Pure evaluation, no inferred measured values or physical readiness grant."""
    errors = list(authority_errors or [])
    assets = _index(docs.get("assets", {}).get("assets"), "asset_id", errors, "assets")
    lines = _index(docs.get("lines", {}).get("lines"), "line_id", errors, "lines")
    stages = _index(docs.get("plan", {}).get("stages"), "stage_id", errors, "stages")
    measurements = _index(docs.get("measurements", {}).get("measurements"), "measurement_id", errors, "measurements")
    gnc, avionics = lines.get("GNC"), lines.get("AVIONICS")
    if gnc is None or avionics is None:
        errors.append("GNC and AVIONICS article lines are required")
    owned_ids = []
    if gnc is not None:
        for asset_id in gnc.get("current_assets", []):
            asset = assets.get(asset_id)
            if not asset:
                errors.append(f"GNC asset missing: {asset_id}")
            elif asset.get("ownership") != "OWNED":
                errors.append(f"GNC asset is not purchase-confirmed as owned: {asset_id}")
            else:
                owned_ids.append(asset_id)
    board, sensor, servo = (
        assets.get("AST-MCU-APM32-001"),
        assets.get("AST-SENSOR-GY91-001"),
        assets.get("AST-SERVO-SG92R-001"),
    )
    for ident, item in [("APM32", board), ("GY-91", sensor), ("SG92R", servo)]:
        if item is None or item.get("ownership") != "OWNED":
            errors.append(f"Required candidate {ident} not supported by owned asset record")
    if servo is not None:
        ids = servo.get("unit_ids", [])
        if (servo.get("quantity") != 2 or not isinstance(ids, list)
                or any(not isinstance(x, str) for x in ids) or len(set(ids)) != 2):
            errors.append("GNC two-servo unit IDs/quantity are not uniquely bound")
    s2a = stages.get(FIRST_BOUNDARY)
    if not s2a or not s2a.get("physical_action") or s2a.get("energy_scope") != "unpowered observation only":
        errors.append("First human boundary must remain an unpowered physical observation")
    if s2a and s2a.get("status") not in ("PENDING_HARDWARE", "COMPLETED"):
        errors.append("Unpowered observation has an unexpected stage status")
    for name in (
        "S0-HISTORICAL-EVIDENCE-RECOVERY",
        "S1-ASSET-AND-TARGET-RECONCILIATION",
        "S2-MINIMUM-REGRESSION-PLAN",
        "S2B-GNC-ONLY-BENCH-SOFTWARE-ISOLATION",
    ):
        if stages.get(name, {}).get("status") != "COMPLETE_SOFTWARE":
            errors.append(f"Expected software preparation not closed: {name}")
    ready_unpowered = False
    if s2a:
        prereqs = s2a.get("depends_on", [])
        ready_unpowered = (
            s2a.get("status") == "PENDING_HARDWARE"
            and isinstance(prereqs, list)
            and all(stages.get(dep, {}).get("status") in SATISFIED for dep in prereqs)
        )
        if s2a.get("status") == "COMPLETED" and not s2a.get("evidence_records"):
            errors.append("Unpowered observation cannot be completed without physical evidence records")
    for stage in stages.values():
        if stage.get("physical_action") and stage.get("status") in ("READY", "COMPLETED") and not stage.get("evidence_records"):
            errors.append(f"{stage['stage_id']}: hardware promotion lacks evidence records")
    cad = docs.get("cad", {})
    cad_state, cad_start = cad.get("status"), cad.get("cad_start_status")
    missing_cad = sorted(
        ident for ident, item in measurements.items()
        if "CAD_START" in item.get("required_for", [])
        and item.get("status") == "MISSING"
        and not item.get("condition")
    )
    conditional_cad = sorted(
        ident for ident, item in measurements.items()
        if "CAD_START" in item.get("required_for", [])
        and item.get("status") == "MISSING"
        and item.get("condition")
    )
    if missing_cad and (cad_state != "NOT_STARTED" or cad_start != "BLOCKED_BY_MEASUREMENT"):
        errors.append("CAD authority promoted while CAD_START measurements are still missing")
    if cad.get("manufacturing_release") is not False:
        errors.append("No manufacturing release can be claimed by this pre-hardware gate")
    current_blockers = docs.get("baseline", {}).get("current_blockers", [])
    blockers = {r.get("id") for r in current_blockers if isinstance(r, dict)} if isinstance(current_blockers, list) else set()
    if RECOVERY_BLOCKER not in blockers:
        errors.append("Unreachable automatic recovery threshold blocker was dropped without independent resolution")
    human_task = None
    if ready_unpowered and not errors:
        human_task = {
            "stage_id": FIRST_BOUNDARY,
            "energy_scope": "unpowered observation only",
            "required_evidence": list(s2a.get("required_evidence", [])),
            "owner": s2a.get("owner"),
        }
    return {
        "schema_version": 1,
        "scope": "READ_ONLY_PRE_HARDWARE_HANDOFF",
        "result": "PASS_PREPARATION_ONLY" if not errors else "FAIL_AUTHORITY_CHECK",
        "errors": sorted(set(errors)),
        "gnc_purchased_candidate_asset_ids": sorted(set(owned_ids)),
        "asset_evidence_ceiling": "PURCHASE_CONFIRMED_NOT_AS_BUILT",
        "software_preparation": "COMPLETE_IN_CURRENT_R2_1_PLAN" if not any("software preparation" in err for err in errors) else "INCOMPLETE",
        "first_human_boundary": human_task,
        "powered_bench_authorized": False,
        "hardware_verified": False,
        "physical_actions_performed": False,
        "recovery": "BLOCKED_UNREACHABLE_THRESHOLD" if RECOVERY_BLOCKER in blockers else "NOT_ESTABLISHED",
        "cad": {
            "authority_status": cad_state,
            "cad_start_status": cad_start,
            "missing_cad_start_measurement_ids": missing_cad,
            "missing_cad_start_count": len(missing_cad),
            "conditional_cad_start_not_evaluated_ids": conditional_cad,
            "manufacturing_release": False,
        },
        "external_gate": "BLOCKED_BY_EXTERNAL_EVIDENCE",
    }

def build_report(root: Path = ROOT) -> dict[str, Any]:
    root = Path(root)
    docs, hashes, load_errors = {}, {}, []
    for name, relative in INPUTS.items():
        path = root / relative
        try:
            hashes[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
            docs[name] = _load_yaml(path)
        except Exception as exc:
            load_errors.append(f"{relative}: cannot read/parse authority: {exc}")
    if load_errors:
        return {"schema_version": 1, "scope": "READ_ONLY_PRE_HARDWARE_HANDOFF",
                "result": "FAIL_AUTHORITY_CHECK", "errors": sorted(load_errors),
                "hardware_verified": False, "powered_bench_authorized": False,
                "physical_actions_performed": False}
    report = evaluate(docs, authority_errors=validate_r21(root))
    report["input_sha256"] = hashes
    return report

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    report = build_report(args.root)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(f"R2.5 pre-hardware evidence gate: {report['result']}")
        if report.get("first_human_boundary"):
            print(f"First pending task: {report['first_human_boundary']['stage_id']}")
        for issue in report["errors"]:
            print(f"ERROR: {issue}")
        print("Hardware status: NOT_VERIFIED; powered operations: NOT_AUTHORIZED")
    return 1 if report["errors"] else 0

if __name__ == "__main__":
    raise SystemExit(main())
