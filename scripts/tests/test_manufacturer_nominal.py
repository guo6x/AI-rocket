from __future__ import annotations

from copy import deepcopy

from scripts.manufacturer_nominal_check import (
    ASSET_PATH,
    REGISTRY_PATH,
    load_yaml,
    validate_documents,
)


def _documents():
    return load_yaml(REGISTRY_PATH), load_yaml(ASSET_PATH)


def _first_parameter(registry):
    return registry["manufacturer_nominal"]["parameters"][0]


def test_repository_nominal_layer_is_source_bound_and_complete():
    registry, assets = _documents()
    errors = validate_documents(registry, assets)
    layer = registry["manufacturer_nominal"]
    assert errors == []
    assert len(layer["parameters"]) == 44
    assert len(layer["unresolved_assets"]) == 15
    assert {
        row["conflict_group"]
        for row in layer["parameters"]
        if row["conflict_group"]
    } == {"SG92R-GEAR-MATERIAL-AND-WEIGHT", "ESP32S3-MEMORY-SUFFIX"}


def test_wrong_unit_is_rejected():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    _first_parameter(mutated)["unit"] = "cm"
    errors = validate_documents(mutated, assets)
    assert any("does not match" in error for error in errors)


def test_unknown_asset_id_is_rejected():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    _first_parameter(mutated)["asset_id"] = "AST-NOT-REGISTERED-999"
    errors = validate_documents(mutated, assets)
    assert any("asset_id must resolve" in error for error in errors)


def test_missing_source_url_or_revision_is_rejected():
    registry, assets = _documents()
    for field in ("source_url", "source_revision"):
        mutated = deepcopy(registry)
        _first_parameter(mutated)[field] = None
        errors = validate_documents(mutated, assets)
        assert any(f"{field}" in error for error in errors)


def test_missing_source_index_file_is_rejected():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    mutated["manufacturer_nominal"]["source_index"] = "engineering/references/does-not-exist.md"
    errors = validate_documents(mutated, assets)
    assert any("source_index must reference an existing file" in error for error in errors)


def test_manufacturer_nominal_cannot_be_labeled_measured():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    _first_parameter(mutated)["evidence_level"] = "MEASURED"
    errors = validate_documents(mutated, assets)
    assert any("must be MANUFACTURER_NOMINAL_REFERENCE" in error for error in errors)
    assert any("must not present" in error for error in errors)


def test_conflicting_variant_cannot_be_confirmed_series():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    conflict_row = next(
        row for row in mutated["manufacturer_nominal"]["parameters"]
        if row["conflict_group"] == "ESP32S3-MEMORY-SUFFIX"
    )
    conflict_row["model_status"] = "CONFIRMED_SERIES"
    errors = validate_documents(mutated, assets)
    assert any("conflict=true requires model_status VERSION_CONFLICT" in error for error in errors)


def test_known_conflict_group_cannot_be_silently_confirmed():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    conflict_row = next(
        row for row in mutated["manufacturer_nominal"]["parameters"]
        if row["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT"
    )
    conflict_row["conflict"] = False
    conflict_row["model_status"] = "CONFIRMED_SERIES"
    errors = validate_documents(mutated, assets)
    assert any("known conflict group cannot be silently confirmed" in error for error in errors)


def test_known_conflict_binding_cannot_be_cleared_by_removing_all_row_flags():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    conflict_row = next(
        row for row in mutated["manufacturer_nominal"]["parameters"]
        if row["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT"
    )
    conflict_row["model_status"] = "CONFIRMED_SERIES"
    conflict_row["conflict"] = False
    conflict_row["conflict_group"] = None
    errors = validate_documents(mutated, assets)
    assert any("known conflict parameter" in error and "must retain" in error for error in errors)


def test_conflict_resolution_requires_an_auditable_record():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    layer = mutated["manufacturer_nominal"]
    for row in layer["parameters"]:
        if row["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT":
            row["model_status"] = "CONFIRMED_SERIES"
            row["conflict"] = False
            row["conflict_group"] = None
    binding = next(
        entry for entry in layer["conflict_bindings"]
        if entry["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT"
    )
    binding["status"] = "RESOLVED"
    errors = validate_documents(mutated, assets)
    assert any("requires an auditable resolution record" in error for error in errors)


def test_explicit_conflict_resolution_can_be_reviewed_and_accepted(tmp_path):
    registry, assets = _documents()
    mutated = deepcopy(registry)
    layer = mutated["manufacturer_nominal"]
    parameter_ids = []
    parameter_rows = []
    for row in layer["parameters"]:
        if row["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT":
            row["model_status"] = "CONFIRMED_SERIES"
            row["conflict"] = False
            row["conflict_group"] = None
            parameter_ids.append(row["id"])
            parameter_rows.append(row)
    binding = next(
        entry for entry in layer["conflict_bindings"]
        if entry["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT"
    )
    binding["status"] = "RESOLVED"
    review_path = tmp_path / "engineering" / "reviews" / "sg92r-variant-resolution-20261027.md"
    review_path.parent.mkdir(parents=True)
    review_path.write_text("Reviewed SG92R source-bound resolution", encoding="utf-8")
    source_index = tmp_path / "engineering" / "references" / "purchased-component-nominal-specs-20261027.md"
    source_index.parent.mkdir(parents=True)
    source_index.write_text("source index", encoding="utf-8")
    layer["conflict_resolutions"] = [
        {
            "conflict_group": "SG92R-GEAR-MATERIAL-AND-WEIGHT",
            "parameter_ids": parameter_ids,
            "asset_ids": sorted({row["asset_id"] for row in parameter_rows}),
            "source_index": layer["source_index"],
            "source_refs": [
                {
                    "parameter_id": row["id"],
                    "source_url": row["source_url"],
                    "source_revision": row["source_revision"],
                }
                for row in parameter_rows
            ],
            "status": "RESOLVED",
            "resolution_id": "RES-SG92R-2026-10-27-01",
            "review_reference": "engineering/reviews/sg92r-variant-resolution-20261027.md",
            "source_url": "https://example.invalid/sg92r-resolution",
            "source_revision": "review revision 1",
            "resolved_on": "2026-10-27",
            "decision": "A reviewed received-unit identity record supersedes the nominal conflict.",
        }
    ]
    assert validate_documents(mutated, assets, root=tmp_path) == []


def test_conflict_resolution_requires_existing_local_review_and_bound_sources(tmp_path):
    """A formatted citation must not resolve a conflict without local evidence."""
    registry, assets = _documents()
    mutated = deepcopy(registry)
    layer = mutated["manufacturer_nominal"]
    parameter_rows = [
        row
        for row in layer["parameters"]
        if row["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT"
    ]
    parameter_ids = [row["id"] for row in parameter_rows]
    asset_ids = sorted({row["asset_id"] for row in parameter_rows})
    source_refs = [
        {
            "parameter_id": row["id"],
            "source_url": row["source_url"],
            "source_revision": row["source_revision"],
        }
        for row in parameter_rows
    ]
    for row in parameter_rows:
        row["model_status"] = "CONFIRMED_SERIES"
        row["conflict"] = False
        row["conflict_group"] = None
    binding = next(
        entry for entry in layer["conflict_bindings"]
        if entry["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT"
    )
    binding["status"] = "RESOLVED"
    layer["conflict_resolutions"] = [
        {
            "conflict_group": "SG92R-GEAR-MATERIAL-AND-WEIGHT",
            "parameter_ids": parameter_ids,
            "asset_ids": asset_ids,
            "source_index": layer["source_index"],
            "source_refs": source_refs,
            "status": "RESOLVED",
            "resolution_id": "RES-SG92R-2026-10-27-01",
            "review_reference": "engineering/reviews/missing.md",
            "source_url": "https://example.invalid/sg92r-resolution",
            "source_revision": "review revision 1",
            "resolved_on": "2026-10-27",
            "decision": "A reviewed received-unit identity record supersedes the nominal conflict.",
        }
    ]

    # The review path is intentionally absent.  A URL-shaped citation alone
    # must not be enough to clear the immutable conflict binding.
    source_index = tmp_path / "engineering" / "references" / "purchased-component-nominal-specs-20261027.md"
    source_index.parent.mkdir(parents=True)
    source_index.write_text("source index", encoding="utf-8")
    errors = validate_documents(mutated, assets, root=tmp_path)
    assert any("review_reference" in error and "existing file" in error for error in errors)


def test_conflict_resolution_rejects_group_asset_parameter_and_source_mismatch(tmp_path):
    registry, assets = _documents()
    mutated = deepcopy(registry)
    layer = mutated["manufacturer_nominal"]
    parameter_rows = [
        row
        for row in layer["parameters"]
        if row["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT"
    ]
    parameter_ids = [row["id"] for row in parameter_rows]
    for row in parameter_rows:
        row["model_status"] = "CONFIRMED_SERIES"
        row["conflict"] = False
        row["conflict_group"] = None
    binding = next(
        entry for entry in layer["conflict_bindings"]
        if entry["conflict_group"] == "SG92R-GEAR-MATERIAL-AND-WEIGHT"
    )
    binding["status"] = "RESOLVED"
    review_path = tmp_path / "engineering" / "reviews" / "sg92r.md"
    review_path.parent.mkdir(parents=True)
    review_path.write_text("Reviewed source-bound resolution", encoding="utf-8")
    source_index = tmp_path / "engineering" / "references" / "purchased-component-nominal-specs-20261027.md"
    source_index.parent.mkdir(parents=True)
    source_index.write_text("source index", encoding="utf-8")
    layer["source_index"] = "engineering/references/purchased-component-nominal-specs-20261027.md"
    layer["conflict_resolutions"] = [
        {
            "conflict_group": "ESP32S3-MEMORY-SUFFIX",  # wrong group
            "parameter_ids": parameter_ids[:-1],  # incomplete binding
            "asset_ids": ["AST-SERVO-SG92R-001"],  # wrong asset
            "source_index": "engineering/references/not-the-index.md",  # unassociated source
            "source_refs": [
                {
                    "parameter_id": parameter_rows[0]["id"],
                    "source_url": "https://example.invalid/not-the-row-source",
                    "source_revision": "not-the-row-revision",
                }
            ],
            "status": "RESOLVED",
            "resolution_id": "RES-SG92R-2026-10-27-02",
            "review_reference": "engineering/reviews/sg92r.md",
            "source_url": "https://example.invalid/sg92r-resolution",
            "source_revision": "review revision 1",
            "resolved_on": "2026-10-27",
            "decision": "The received unit was reviewed.",
        }
    ]
    errors = validate_documents(mutated, assets, root=tmp_path)
    assert any("conflict resolution" in error for error in errors)
    assert any("parameter_ids" in error for error in errors)
    assert any("asset_ids" in error for error in errors)
    assert any("source_index" in error for error in errors)
    assert any("source_refs" in error for error in errors)


def test_malformed_conflict_resolution_is_rejected_without_raising():
    registry, assets = _documents()
    mutated = deepcopy(registry)
    mutated["manufacturer_nominal"]["conflict_resolutions"] = [
        {
            "conflict_group": "SG92R-GEAR-MATERIAL-AND-WEIGHT",
            "parameter_ids": [{}],
        }
    ]
    errors = validate_documents(mutated, assets)
    assert any("parameter_ids must match" in error for error in errors)


def test_gy91_chip_and_lm2596_chip_scopes_do_not_claim_board_geometry_or_capacity():
    registry, assets = _documents()
    layer = registry["manufacturer_nominal"]
    gy91 = [row for row in layer["parameters"] if row["asset_id"] == "AST-SENSOR-GY91-001"]
    lm2596 = [row for row in layer["parameters"] if row["asset_id"] == "AST-POWER-LM2596-001"]
    assert gy91 and all("module PCB" in row["applicability"] or "chip" in row["applicability"] for row in gy91)
    assert lm2596 and all(
        "assembled seller module" in row["applicability"]
        or "purchased module" in row["applicability"]
        or "purchased adjustable buck board" in (row["conflict_note"] or "")
        for row in lm2596
    )
    assert validate_documents(registry, assets) == []
