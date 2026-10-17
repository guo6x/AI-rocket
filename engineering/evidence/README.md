# Physical evidence records

This directory will hold evidence for `AA-TVC-BENCH-001`. R2 creates templates only; it does not fabricate observation or measurement records.

Create future records under `engineering/evidence/records/` from the templates. Keep original photos outside Git only if necessary for privacy/size, but record stable references, hashes, and storage location. A value may be marked `MEASURED` only when its record includes the physical component ID, date, operator, method, tool, raw value, unit, uncertainty, photo references, and source commit.

Do not edit historical prose or CAD to simulate an evidence record.

## Register a record

Copy the appropriate template to `engineering/evidence/records/`, then fill its
fields with actual observations. Do not commit an unfilled template as evidence.
Each `photo_refs` entry must contain `location` (a stable local or external storage
reference) and `sha256` (the lowercase SHA-256 of the original photo bytes).
Measurement records also require `measurement_id`, raw readings, a unit, and
uncertainty; if uncertainty is not quantified, record that limitation explicitly.
Use the full capture-source Git SHA for `source_commit`.

Add an entry to `evidence_records` in `../as-built/evidence-index.yaml` with these
fields: `record_id`, `record_type` (`measurement` or `hardware_observation`),
`article_id`, repository-relative `path`, and lowercase `sha256` of the completed
record's bytes. On PowerShell, compute the record digest with:

```powershell
(Get-FileHash engineering/evidence/records/YOUR-RECORD.yaml -Algorithm SHA256).Hash.ToLowerInvariant()
```

Reference the record ID from the matching component and measurement-plan item.
Record files must stay under `engineering/evidence/records/`, including after
resolving symlinks. Update the digest whenever the record changes. References to
another component or another measurement are rejected. `NOT_APPLICABLE` requires
observation evidence; `MEASURED` requires measurement evidence.

Run `python scripts/r2_physical_baseline_check.py` from the repository root before
committing. Missing files, changed hashes, placeholders, invalid metadata and
broken references fail the structure check. The validator does not fetch or
authenticate photos, verify the existence of capture commits, judge measurement
accuracy, or prove physical completeness. Human review of the original evidence
remains required; a metadata/hash pass is not hardware verification.
