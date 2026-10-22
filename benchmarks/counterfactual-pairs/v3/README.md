# Counterfactual pairs, corpus v3

A held-out successor to the [v2 corpus](../v2/README.md), built after the [ablation arms](../ablation/README.md) were tuned on v2. **No reviewer arm has run on it.** It has 64 cases in 16 families: 8 whose twin is a defect and **8 whose twin leaves one decisive fact unestablished**, the family that v2 had only one of. Its design, metrics, hypotheses and limits are fixed in the [preregistration](PREREGISTRATION.md), pinned by the manifest.

| | v2 | v3 |
| --- | --- | --- |
| Cases | 40 (10 families) | 64 (16 families) |
| Evidence-gap families | 1 (4 observations per trial pair) | 8 (32 units per arm over 2 trials) |
| Evidence-gap labels | the author's judgment; the one twin had a cancel-and-report rule that let a reader defend `GO` | no fallback in any plan; two independent blind readers classified all 64 plans and matched the intended class every time |
| Authorship | the benchmark's author | four independent model authors from a written specification ([brief](audit/author-brief.txt)), no edits afterwards |
| Case ids | `P-xxxxxx` | `Q-xxxxxx` (disjoint from v2) |
| Used to tune an arm | yes | no |

Families. Defect: cache key and tenant isolation, lock order, rate-limit arithmetic, idempotency key per retry, certificate rotation order, feature-flag default, backup retention against the restore window, credential logging. Evidence gap: batch capacity against a hard window, upgrade compatibility of existing callers, retry safety against idempotency, third-party rate limit, unique constraint against existing data, rollback duration, payload size against a hard limit, storage write permission.

Files: `packets/` and `prompt.txt` are the only reviewer-visible files (the prompt is byte-identical to v1's and v2's); `oracle/`, `families.json`, `rubric.json`, `audit/` and `PREREGISTRATION.md` are never sent to a reviewer; `manifest.json` pins everything; `build_corpus.py --check` regenerates the packets, oracle and manifest from `families.json` and compares; `test_corpus.py` tests the corpus, the rubric and the metrics with simulated reviewers.

## Authorship and audit

Four fresh model authors wrote the families without seeing any arm, result or the sentence the fourth ablation arm adds. Two blind gap audits and two blind classification audits ran before freezing, and nothing was edited. Results, method and limits: [audit/README.md](audit/README.md). All authors and auditors are Claude models, and I wrote the specification and the themes after seeing the v2 results, so independence is partial; the preregistration says so.

## Running it

The three-arm run is [preregistered](../v3-run/PREREGISTRATION.md) and has a [gated runbook](../v3-run/HANDOFF.md). The arms' own manifests still name corpus v2 and are untouched; a [run manifest](../v3-run/manifest.json) binds the skill-style, defined and defined-plus-sentence arms to this corpus, and `run_pilot_claude.py` and `verify_run.py` take it with `--run-manifest`. [analyze.py](../v3-run/analyze.py) takes this corpus's rubric and computes the preregistered rates, comparisons and labels. **Nothing has been run on v3 yet.**

```bash
python3 -B -I benchmarks/counterfactual-pairs/v3/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3/test_corpus.py
python3 -B -I benchmarks/counterfactual-pairs/v3-run/test_run.py
```

## Limits

- Audited, not proven sound, and audited by Claude models only.
- The evidence-gap plans have no absorbing fallback by construction, so v3 says nothing about a reviewer's behaviour on gaps that a plan's own rules make harmless.
- Short plan notes; nothing about the skill's citation check or adjudication step, Gemini, or real repositories.
- The keyword rubric is recall-only.
