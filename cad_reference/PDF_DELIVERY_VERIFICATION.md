# PDF delivery protection and reproducibility

This continuation starts from PR #52 head
`73ef7b79d69b8940f74a8accfc54cfea93b6a6bc`. It changes software delivery checks,
not dimensions, CAD geometry or physical evidence.

## Reproduced problem and correction

The previous `create_review` accepted an output inside either verified input
package. It successfully wrote a 79,848-byte PDF, but the package's next
independent verification failed because its exact file inventory now contained
an extra file. The new check rejects resolved destinations inside either
package, including nested paths and symlink aliases, before writing anything.
An independent review caught an outbound `..` path creating an intermediate
directory inside a package; all writes now use the same validated canonical
path, and a regression covers that case.

The new `--check` mode independently regenerates the review in memory and checks
the delivered PDF itself. A freshly generated temporary PDF alone did not test
whether the committed/downloaded PDF was current. Both are now checked in CI.

## Actual local checks

- All **71 reference tests passed**, including real CadQuery/OpenCascade STEP
  reimports and nine added PDF delivery regressions.
- The existing manufacturer-nominal and CAD-authority suites: **28 passed**.
- The committed PDF reproduced byte-for-byte and passed the read-only checker.
  It remains 79,848 bytes, SHA-256
  `be3dbd9428f1a8edd294dc5d8276b2b56f8b6627d2a270d9c6841ce24d6ec923`.
- Existing STEP, SVG and receipts are unchanged. Rendered-page review exposed
  a pre-existing overlap between the YZ label and scale notice on all three
  pages. The notice was moved down, a minimum-spacing regression was added,
  and the PDF was explicitly regenerated and visually rechecked.
- CAD authority audit: truthful bookkeeping PASS, accepted current models 0,
  all 19 CAD_START blockers unchanged. Manufacturer registry audit: PASS,
  44 nominal parameters, 15 unresolved assets, existing two conflicts unchanged.
- Python compilation and whitespace/error checks passed.
- Full local `scripts/check.py` still stops because PlatformIO is missing.
  The focused tests do not constitute complete project software acceptance.
  Remote CI must be checked for the newly published commit separately.

The base head's two remote workflows were independently confirmed successful:
[reference CAD](https://github.com/guo6x/AI-rocket/actions/runs/42271617057) and
[full software](https://github.com/guo6x/AI-rocket/actions/runs/42271617286).
These older successful runs do not validate this continuation's commit.

## Limits

Exact PDF reproduction depends on the matching trusted source snapshot and
pinned renderer. It is not a signature, PDF-reader qualification, assembly fit,
structural review, manufacturing release or hardware acceptance. No physical
operation, purchase, supplier communication, deployment or merge occurred.
