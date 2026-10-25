"""Fail-closed CAD authority consistency audit, NOT a geometry validator.

A successful exit means the absence of accepted CAD is faithfully reported.
CAD_START and manufacturing release are separate, still blocked gates.
No CAD kernel, motor, radio, hardware or legacy generator is executed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


class CadAuthorityError(ValueError):
    """Current project authority or intake evidence is contradictory."""


def audit(authority: dict, plan: dict, intake: dict) -> dict:
    if authority.get("status") != "NOT_STARTED":
        raise CadAuthorityError("CAD authority must be NOT_STARTED until a separate approved design decision")
    if authority.get("cad_start_status") != "BLOCKED_BY_MEASUREMENT":
        raise CadAuthorityError("CAD_START must be blocked while current measurements are missing")
    if authority.get("accepted_geometry") is not None or authority.get("accepted_assembly") is not None:
        raise CadAuthorityError("current CAD cannot claim approved geometry or assembly")
    if authority.get("accepted_drawings"):
        raise CadAuthorityError("no current CAD drawing has been accepted")
    if authority.get("manufacturing_release") is not False or authority.get("flight_qualification") is not False:
        raise CadAuthorityError("CAD is not manufactured or flight-qualified")
    if authority.get("legacy_policy", {}).get("classification") != "REJECTED_FOR_CURRENT_DESIGN":
        raise CadAuthorityError("rejected legacy AI CAD must not be treated as design authority")
    if authority.get("legacy_policy", {}).get("current_design_sources") != []:
        raise CadAuthorityError("legacy CAD sources cannot be nominated as current models")
    if authority.get("legacy_policy", {}).get("may_supply_actual_dimensions_or_manufacturing_authority") is not False:
        raise CadAuthorityError("legacy dimensions must not become current design inputs")
    if authority.get("current_article") != plan.get("article_id") or authority.get("current_article") != intake.get("article_id"):
        raise CadAuthorityError("article identity mismatch")

    measurements = plan.get("measurements")
    if not isinstance(measurements, list):
        raise CadAuthorityError("missing measurement list")
    by_id = {}
    for row in measurements:
        if not isinstance(row, dict) or not isinstance(row.get("measurement_id"), str):
            raise CadAuthorityError("malformed measurement record")
        ident = row["measurement_id"]
        if ident in by_id:
            raise CadAuthorityError(f"duplicate measurement id: {ident}")
        if row.get("status") == "RECORDED" and not row.get("evidence_refs"):
            raise CadAuthorityError(f"measured claim has no supporting evidence refs: {ident}")
        by_id[ident] = row

    concept = intake.get("concept_intake")
    if not isinstance(concept, dict) or concept.get("status") != "BLOCKED":
        raise CadAuthorityError("current CAD concept intake must remain BLOCKED")
    required = concept.get("blockers")
    if not isinstance(required, list) or not required or len(set(required)) != len(required):
        raise CadAuthorityError("CAD_START blocker identifiers absent or duplicated")
    missing_ids = []
    for ident in required:
        row = by_id.get(ident)
        if row is None:
            raise CadAuthorityError(f"CAD_START references missing measurement ID: {ident}")
        if row.get("status") != "RECORDED" or not row.get("evidence_refs"):
            missing_ids.append(ident)
    if not missing_ids:
        raise CadAuthorityError(
            "CAD_START intake remains BLOCKED but all required evidence is recorded; review and rebaseline instead"
        )
    return {
        "audit": "PASS",
        "cad_status": "NOT_STARTED",
        "cad_start": "BLOCKED",
        "manufacturing_release": "NOT_AUTHORIZED",
        "legacy_ai_geometry": "REJECTED_FOR_CURRENT_DESIGN",
        "accepted_current_models": 0,
        "required_start_measurements": len(required),
        "missing_or_unevidenced_start_measurements": missing_ids,
        "missing_count": len(missing_ids),
        "meaning": "PASS verifies truthful baseline bookkeeping only; no geometry or hardware verified",
    }


def run(root: Path = ROOT) -> dict:
    def load(relative: str) -> dict:
        path = root / relative
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise CadAuthorityError(f"expected YAML mapping: {relative}")
        return data

    return audit(
        load("engineering/cad-authority.yaml"),
        load("engineering/as-built/measurement-plan.yaml"),
        load("engineering/aeroforge-intake/tvc-assembly-intake.yaml"),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="check authority records (never certify CAD geometry)")
    args = parser.parse_args()
    try:
        result = run()
    except (CadAuthorityError, OSError, yaml.YAMLError, TypeError, KeyError) as exc:
        print(json.dumps({"audit": "FAIL", "error": str(exc)}, ensure_ascii=False))
        return 1
    if args.check:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
