# Corpus v4: how a split is made

Nothing here has been run on a model except the [authoring probe](probe/results/RESULT.md). The specification is [SPEC.md](SPEC.md); the plan and its decisions are in [../../../docs/v4-plan.md](../../../docs/v4-plan.md).

| Step | Who | Tool | Output |
| --- | --- | --- | --- |
| 1. Assign domain, length, positions and wording B from a committed seed | repository session | [author/assign.py](author/assign.py) | [author/assignments-dev.json](author/assignments-dev.json), [author/assignments-test.json](author/assignments-test.json) (committed) |
| 2. Author one pair per call (and the 12 test rewordings) through the Flash route; every call recorded, every report checked mechanically | orchestrator, on the owner's go | [author/HANDOFF.md](author/HANDOFF.md), [author/run.sh](author/run.sh), [author/author.py](author/author.py), [author/check_author.py](author/check_author.py) | accepted reports and a call ledger (dev: committed; test: private) |
| 3. Build the corpus directory (packets, oracle with line numbers mapped into the twin, manifest with pins) | repository session | [author/build_corpus.py](author/build_corpus.py) | `dev/` committed; test: private directory plus a hashes-only sealed manifest |
| 4. Blind audit by Claude: each member alone, each pair unlabelled, each gap twin against the author's claim | orchestrator, on the owner's go | [audit/HANDOFF.md](audit/HANDOFF.md), [audit/run.sh](audit/run.sh), [audit/audit.py](audit/audit.py) | audit ledger |
| 5. Read the audit against the oracle; draw the owner's sample of at least a fifth of the pairs | repository session, then the owner | [audit/audit_report.py](audit/audit_report.py) | per-pair decisions; unlabelled files for the owner |
| 6. Rewrite or drop failing pairs (reasons recorded), rebuild, re-audit what changed, freeze | repository session | `build_corpus.py --drops` | the frozen corpus and its manifest |
| Later: score reviewer runs | repository session | [score_v4.py](score_v4.py), [parse_v4.py](parse_v4.py) | gated to reproduce every v1 to v3 score exactly ([test_score_v4.py](test_score_v4.py)) |

The dev split is open and is the only place where prompts, checks and tooling may be tuned. The test split's case text is never committed before the arms are preregistered, and the repository session builds and audits it from the owner's archive without reading the authored text beyond failure messages.

Tests (all offline, no model): `check_families.py`, `test_families.py`, `test_score_v4.py`, `author/test_author.py`, `audit/test_audit.py`, `probe/test_probe.py`.
