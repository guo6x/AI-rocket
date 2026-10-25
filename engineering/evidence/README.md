# Physical evidence records

This directory will hold evidence for `AA-TVC-BENCH-001`. R2 creates templates only; it does not fabricate observation or measurement records.

Create future records under `engineering/evidence/records/` from the templates. Keep original photos outside Git only if necessary for privacy/size, but record stable references, hashes, and storage location. A value may be marked `MEASURED` only when its record includes the physical component ID, date, operator, method, tool, raw value, unit, uncertainty, photo references, and source commit.

Do not edit historical prose or CAD to simulate an evidence record.

## Record-integrity gate (restored from historical R2 branch)

The current R2 check now validates any indexed local record under `engineering/evidence/records/` for its exact SHA-256 bytes, record identity, associated component/measurement, required observation or measurement metadata, and hashed photo references. Invalid or missing evidence **fails closed**, without upgrading any gate to READY. Run `python scripts/r2_physical_baseline_check.py`. This is metadata validation only: a matching hash is **not** a guarantee that physical data is truthful. Do not backfill missing data with historical AI CAD geometry.

