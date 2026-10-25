# Repository closure and local cleanup — 2026-10-25

This reference is for maintainers reviewing the remaining-branch closure. It records current observations separately from work already completed by other runs. It does not qualify CAD, physical evidence, recovery, radio operation or flight.

## Starting state, independently refreshed

GitHub branches API returned only `main`, at `60055a86e8e8a49fddb75d8faca1805219d2346b`. The user's six-branch list and main `3a38e74e...` were historical checkpoints. No second merge or remote branch deletion was needed for work already completed. Local `origin/*` tracking refs were stale, not live GitHub branches.

| Historical branch | Content audit / actual disposition |
| --- | --- |
| `chore/cad-rejected-exports-phase1-20261025` | PR #21 CLOSED, replaced by MERGED #29 (`7561921fc779461618f2d2cb28c8081fd8312f95`). The two PRs delete exactly the same 22 rejected binary exports. All are absent from main and recoverable from `03fbd826031f24055bf5de79c7aa4aa72810b451:path`. No current runtime consumer reads them. Historical generators/render scripts are not current geometry authority. |
| `feat/r2-as-built-mechanical-intake` | PR #3 was merged, but later `c2e5709` was genuinely distinct. PR #28 restored the physical-record hash validator and its tests. A further audit found omitted intake-dependency and malformed-document guards; the narrow follow-up accompanying this record restores those protections, not historical CLI conveniences or old baseline files. |
| `research/aerospace-knowledge-base-20261019` | Original head `37c093c5...` and PR #4 squash merge `44edda14...` have identical complete tree `5783739e9acc599263b943997cd26b7c9ada3ce0`. No second integration. |
| `research/kb-v2-source-audit-20261019` | Original head `80658df0...` and PR #5 squash merge `25b0f6c3...` have identical tree `67946b33c9492c02b7751b53c3d6ee6a4b6fabc3`. No second integration. |
| `research/kb-v3-analytic-benchmark-20261020` | Original head `30027d51...` and PR #6 squash merge `f59dc2c5...` have identical tree `ace542245e78ee6dc61767d8a80fc95466aa0de3`. No second integration. |

All three knowledge-base merge commits are main ancestors. `git diff f59dc2c5 origin/main -- docs/aerospace-knowledge` is empty at the stated starting main. An ahead count alone would have misclassified the squash-merged research.

CAD deletion removed 58,571,601 bytes of historical blob content from the current tree, **not** from Git history and **not** a claim of local disk space reclaimed in this run. `3d_print_files`, generators, NX source artifacts and provenance/measurement documents remain. CAD authority remains `NOT_STARTED` / `BLOCKED_BY_MEASUREMENT`; manufacturing and flight authorization remain false.

## Local cleanup actually performed

- `D:\AI_rocket_system_v1_verify` was already absent. Only its prunable Git registration was removed. No directory-space credit is assigned to this run, and no missing two-hour run is called completed evidence.
- `D:\AI_rocket_codex_gl_20261025` was an unused, clean auxiliary worktree at the current main. It had 380 files, 21,851,033 logical bytes, no unique commits, no modified/untracked/ignored files, no reparse entries, and no process command line pointing to it. App task inventory showed no other active task in that checkout. Removed with `git worktree remove`, without force, then pruned only the already-missing registration.
- D free bytes immediately before/after cleanup: **51,359,109,120 → 51,382,005,760**, observed increase **22,896,640 bytes (21.84 MiB)**. This is an actual filesystem observation; concurrent applications can affect free space. It is not the earlier worktree's unknown historical size.
- Formal `D:\AI_rocket`, its existing `.venv`, code, tracked historical evidence and other projects were preserved. Existing screenshots/logs were not recopied. No new clone, worktree, environment or large test copy was created.

Machine-readable receipt: [repository_cleanup_20261025.json](../engineering/offline-evidence/system_v1/repository_cleanup_20261025.json).

### Preserved / unresolved temporary items

| Item | Decision |
| --- | --- |
| 104 `C:\Windows\Temp\ai_rocket_gnc_{trace,dual_period}_*` directories | Verified compiler-probe residue: only one known executable each, total 12,432,902 logical bytes; recursive removal was rejected by execution policy before running. Retained; no bypass and no reclaimed-space claim. |
| `C:\Windows\Temp\ai-rocket-system-v1-py311-20261025` | 802,562,115 logical bytes of a temporary Python environment. An inaccessible Python process's ownership could not be established, so preserved rather than assuming it unused. Not used to create another environment. |
| Downloaded final-CI caches in system temp | Retained; no broad cleanup of system temp or unrelated processes. |

The first two paths are a bounded pending-cleanup list, not permission to recursively delete Windows Temp. Other projects' Git/Python/Node processes were not stopped.

## Regression attribution

Previously completed, reused evidence: main [40188209208](https://github.com/guo6x/AI-rocket/actions/runs/40188209208), push exact `60055a86...`, SUCCESS; 447 executions / 437 distinct identities, five builds PASS. Qt smoke exited zero but remained `PARTIALLY_VERIFIED`; this is not native visible-3D evidence.

The narrow R2 follow-up restored fixed intake gate sets, unique/non-empty and same-article evidence-index IDs, fail-closed malformed-input diagnostics, and evidence requirements for observation/measurement declarations. It does not restore obsolete CLI conveniences or change physical authority data. Initial negative tests reproduced 21 failures (plus one baseline pass), followed by six further failing semantic-declaration cases. Final affected suite: **60 passed**, exit 0 (28 new guard cases, 9 existing checker cases, 23 existing evidence cases). Repeated red/green executions are not additional distinct tests. CLI still reports 40 planned measurements and five BLOCKED gates with blocker counts 1/19/5/3/10.

Commands, environment, source-byte hashes and explicitly labelled console excerpts: [r2_intake_guard_tests_20261025.txt](../engineering/offline-evidence/system_v1/r2_intake_guard_tests_20261025.txt), SHA256 `d43d6a0be13932e9faa60d46708c4b2200266f92b5d6614a36821388e1355692`. The existing full GitHub Actions gate is required before integration. Exact final refs and new run URLs are reported in the PR/delivery receipt, without self-referential Git SHA fields.

The branch-closure phase must finish before Issue #26 renderer work. No control gains, safety permissions, recovery thresholds, firmware hardware operations or CAD design are part of this closure.
