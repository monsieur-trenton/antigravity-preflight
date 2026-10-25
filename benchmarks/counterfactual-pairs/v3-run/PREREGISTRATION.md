# Preregistration: the v3 run (three arms on the held-out corpus)

Frozen with `manifest.json`: this file is pinned by hash, and the manifest names the exact corpus v3 manifest, the two ablation arm manifests and the skill-style system prompt. Written before any v3 observation by a reviewer arm exists. The corpus design, the three primary rates, the strict summary and the four hypotheses are in the [corpus preregistration](../v3/PREREGISTRATION.md); this file adds what that one deferred: the arms, the order, the conditions, the comparisons, the labels, the reading and the stopping rules.

## Question

On a held-out corpus with eight evidence-gap families and no absorbing fallbacks, does the one added sentence about optional suggestions (a) still make sound plans come out `GO`, (b) still keep defect twins at `NO_GO`, and (c) cost evidence-gap twins their `GO_WITH_CHANGES`, as it did on v2? And where does the skill-style arm sit between the two?

## Arms

| Arm | What it is | Bound by |
| --- | --- | --- |
| `skill` | the skill-style prompt and numbered packet used in pilots 1 and 2, with the structured report and the citation check | the corpus manifest and the system-prompt hash in this run's manifest |
| `defined` | a plain request with the five-line verdict definitions ([prereg](../ablation/defined/PREREGISTRATION.md)) | its own manifest, hash pinned here |
| `defined-go` | the defined arm plus one sentence about optional suggestions ([prereg](../ablation/defined-go/PREREGISTRATION.md)) | its own manifest, hash pinned here |

The bare arm is not run: its verdicts were already shown not to follow its findings, and it adds cost without bearing on the question. The prompts of the three arms are the frozen ones; **nothing about any arm is changed for this run**, in particular not the sentence, which was written against v2.

## Conditions (identical for every arm)

Route `claude-cli`; model `claude-opus-5-5`; effort `high`; Claude Code 2.1.306; the same binary (`/home/john/.local/bin/claude`, SHA-256 `520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe`, recorded for every earlier arm) on the same machine; tool-free safe mode; one turn per case; no retries; per-case spend cap `--max-budget-usd 5.0`; two trials. The corpus is `benchmarks/counterfactual-pairs/v3`. Each arm has its own working directory (`<root>/work-<arm>`) and each (arm, trial) is one driver invocation in the frozen submission order.

**Order.** The six runs are done in one sitting, in this order, so that the comparison is concurrent rather than across days and no arm is always first:

| Run | Trial | Arm |
| --- | --- | --- |
| 1 | 1 | `skill` |
| 2 | 1 | `defined-go` |
| 3 | 1 | `defined` |
| 4 | 2 | `defined` |
| 5 | 2 | `skill` |
| 6 | 2 | `defined-go` |

Start and end times of every run are recorded. If the sitting is interrupted, the remaining runs continue in this order and the gap is stated in the results.

**Expected cost and time** (an estimate from the v2 runs scaled by 64 cases over 40, not a bound): about $1.5 to $1.9 per run, about $10 in total (range $9 to $13), and 12 to 18 minutes per run. The owner decides whether any call is made and how much may be spent.

## Metrics and comparisons

All as defined in the [corpus preregistration](../v3/PREREGISTRATION.md) and computed by [analyze.py](analyze.py), identical for every arm: the three primary rates (sound plans `GO`, defect twins `NO_GO`, evidence-gap twins `GO_WITH_CHANGES`), the strict-pair summary, ordered pairs, the secondary rates (including gap named but dismissed), a per-family table, and for every pair of arms a paired comparison on matched (case, trial) units with an exact two-sided sign test. The skill-style arm's finding-level scoring (unsupported VERIFIED findings: a gate that must be zero) comes from `score.py --corpus v3`. Wilson 95% intervals; two trials of one case are not independent samples. Stops are removed, not counted as verdicts.

**Views.** The all-pairs analysis is the headline. Pre-specified sensitivity views, each its own call: excluding any family named in an adjudication written before the adjusted figures are computed (`--exclude`), and the documented-rule view from an adjudication that reclassifies named technical stops (`--adjudication`).

## Labels, fixed in advance

Computed by `labels()` in [analyze.py](analyze.py) (tested), for the sentence arm (`defined-go`) against the defined arm, from the all-pairs comparison:
- **Sound-plan gain:** `replicated` if the paired difference in sound plans judged `GO` favours the sentence arm at p < 0.05; `reversed` if it favours the defined arm at p < 0.05; otherwise `not replicated`.
- **Evidence-gap cost:** `confirmed` if the paired difference in evidence-gap twins judged `GO_WITH_CHANGES` favours the defined arm at p < 0.05; `reversed (the sentence arm is better)` if it favours the sentence arm at p < 0.05; otherwise `not detected`.
- **Defect twins:** `lost` if 3 or more matched units were `NO_GO` under the defined arm and are not under the sentence arm; otherwise `held`.
- **Skill-style against the sentence arm**, on evidence-gap `GO_WITH_CHANGES` and on sound-plan `GO` separately: `skill-style better`, `sentence arm better` or `no significant difference`, at p < 0.05.

The labels are descriptive and not claims of equivalence: with 32 matched evidence-gap units per pair of arms, "not detected" is weak evidence of no cost. All four hypotheses of the corpus preregistration are reported, with the opposite outcome admissible for each. No pass threshold is claimed.

## Human reading, fixed in advance

Read in full and classified by whether the report names the planted gap or defect, and what it does with it: (1) **every evidence-gap twin that any arm judged `GO`** (the false-clean risk), (2) **every defect twin without `NO_GO`**, (3) **every sound plan with `NO_GO`**, (4) a sample of up to ten sound plans that the skill-style arm judged `GO_WITH_CHANGES` and the sentence arm judged `GO`, to see what drove the hedging, (5) a sample of up to ten correct evidence-gap twins from each arm. Counts are reported by class and the coverage is stated. The reader is the corpus author, who has seen the scores; the previous runs' readings had the same limit.

## Stops, interruptions and adjudication

The driver records any platform safety interruption as `SAFETY_INTERRUPTED` and any non-requested served model as `MODEL_MISMATCH`; both are stops, never verdicts, and the strict verifier checks that none was recorded as a verdict. An adjudication file is written **before any metric is computed**, naming each stop and any reclassification, as in the earlier runs; the as-run result is the headline and the documented-rule view sits beside it. A run that halts on three consecutive stops is not rerun; the owner decides whether to continue with the identical command.

## Exclusions and corrections

As in the corpus preregistration: the headline is the all-pairs result; a pair may be reported as invalid only on an adjudicator's reading of the packet text alone, written before any adjusted figure is computed. Nothing frozen (packets, oracle, rubric, arm prompts, scorer behaviour for existing keys, this file) is edited after a run; a flaw found afterwards means a new version, and no run is re-scored retroactively.

## What results can claim

For one model, route, binary and prompt set on this corpus hash, under the limits in the corpus preregistration (Claude authors and auditors; evidence gaps with no absorbing fallback; short plan notes; nothing about the skill's citation check or adjudication step, Gemini, or real repositories). The sentence was designed on v2, so a gain on v3 is out-of-sample for the sentence's wording; the corpus designer still knew the question.

## Running

`run_pilot_claude.py --arm ARM --corpus benchmarks/counterfactual-pairs/v3 --run-manifest benchmarks/counterfactual-pairs/v3-run/manifest.json ...`, then `verify_run.py` with the same two arguments, `score.py --corpus ...v3` for the skill-style ledger, and `v3-run/analyze.py --corpus ...v3 --rubric ...v3/rubric.json --arm skill=... --arm defined=... --arm defined-go=...`. The gated runbook is [HANDOFF.md](HANDOFF.md).
