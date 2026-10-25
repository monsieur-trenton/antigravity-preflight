# Preregistration: the skill-style prompt plus the optional-suggestions sentence, on corpus v3

Frozen with `manifest.json`: this file is pinned by hash, and the manifest names the exact corpus v3 manifest, the arm's own manifest (which pins the sentence and the skill-style system prompt) and the skill-style system prompt. Written before any observation of this arm exists. The corpus design and its general limits are in the [corpus preregistration](../v3/PREREGISTRATION.md); the three arms already run on v3 are in the [v3 run preregistration](../v3-run/PREREGISTRATION.md) and [their results](../results/v3-claude-opus-5-5-high/README.md).

## Provenance, stated plainly

This arm was designed **after** the three v3 arms were run and read. Two of their findings motivate it: the skill-style arm hedged 30 of 64 sound plans (judged `CHANGES_RECOMMENDED`), and the sentence arm (`defined-go`) judged all 64 sound plans `GO`. So the question below was chosen with that result in hand, **corpus v3 is no longer held out for it**, and a gain here is a test of a stated prediction on a corpus already seen for related arms, not out-of-sample evidence. The sentence itself was written against corpus v2 (for the plain-request arms) and is changed here only in vocabulary (the verdict `GO` becomes the skill-style assessment `NO_BLOCKERS_FOUND`). Which prompt carries the sentence, where it sits and its wording are fixed below and checked by a test; nothing about them is adjusted after a run.

## Question

Does adding the one sentence to the skill-style prompt (a) cut the hedging of sound plans, (b) keep the defect twins blocked, (c) keep the evidence-gap twins at `GO_WITH_CHANGES` rather than waving them through, and (d) reduce the overclaiming of evidence-gap twins as blockers (8 of 32 in the skill-style arm)? The earlier arms leave this open: the sentence arm used a plain request with defined verdicts and overclaimed 21 of 32 gap twins, so its result does not carry over to the skill-style prompt.

## The arm

`skill-go`: the skill-style request of pilots 1 and 2 and of the `skill` arm (the frozen corpus prompt, the numbered snapshot, the fixed question and the machine-summary block, the same system prompt and strict parser), **with exactly one line added immediately after the corpus prompt and before the snapshot**:

> Optional suggestions that only make a working plan more robust are not changes it needs; if that is all you have, the assessment is NO_BLOCKERS_FOUND.

[`ablation/skill-go/skill-go-sentence.txt`](../ablation/skill-go/skill-go-sentence.txt) holds the line, pinned by [`ablation/skill-go/manifest.json`](../ablation/skill-go/manifest.json) together with the skill-style system prompt hash. The driver and verifier refuse the arm without a run manifest and check every saved request byte for byte against `skill`'s request plus that one line. The report format, the `FINDING` lines, the strict parser and the finding-level score are those of the `skill` arm, so the arm is scored with `score.py --corpus v3` (the unsupported-`VERIFIED` gate must be zero).

## Conditions

Identical to the v3 run: route `claude-cli`; model `claude-opus-5-5`; effort `high`; Claude Code 2.1.306; the binary `/home/john/.local/bin/claude` (SHA-256 `520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe`); tool-free safe mode; one turn per case; no retries; per-case cap `--max-budget-usd 5.0`; two trials; corpus `benchmarks/counterfactual-pairs/v3`; a fresh working directory per arm.

**Runs.** Run 1 and run 4 are the arm under test; runs 2 and 3 are an optional **concurrent control** (the unchanged `skill` arm again), so that the comparison does not rest on a day-old ledger. In this order:

| Run | Trial | Arm | Required |
| --- | --- | --- | --- |
| 1 | 1 | `skill-go` | yes |
| 2 | 1 | `skill` (control) | optional |
| 3 | 2 | `skill` (control) | optional |
| 4 | 2 | `skill-go` | yes |

The owner decides whether the control runs. Without it the comparison is against the `skill` ledgers of 2026-10-23 and carries day-to-day drift as an uncontrolled difference; that is stated in the results. **Expected cost and time** (an estimate from the earlier skill-style runs, not a bound): about $2.4 and 17 to 22 minutes per run; about $5 for the two required runs and $10 with the control.

## Metrics and comparisons

As in the v3 run preregistration, computed by [analyze.py](analyze.py) (which wraps the v3 analysis and adds the labels below) and `score.py --corpus v3` for the finding-level score: the three primary rates (sound plans `GO`, defect twins `NO_GO`, evidence-gap twins `GO_WITH_CHANGES`), strict and ordered pairs, sound plans hedged and blocked, evidence-gap twins judged `NO_GO` (overclaimed) and `GO` (waved through), gap named but dismissed, verdict follows finding, a per-family table, and for every pair of arms present a paired comparison on matched (case, trial) units with an exact two-sided sign test. Wilson 95% intervals; the two trials of a case are not independent. Stops are removed from denominators, never counted as verdicts.

**Primary comparison:** `skill-go` against the concurrent `skill` control if it was run, otherwise against the earlier `skill` ledgers. Whichever it is, the other, when it exists, is reported beside it. `skill-go` is also compared with the earlier `defined-go` ledgers.

## Labels, fixed in advance

Computed by `labels()` in [analyze.py](analyze.py) (tested), for `skill-go` against the primary `skill` comparison, from the all-pairs run:
- **Sound-plan hedging:** `reduced` if the paired difference in sound plans judged `GO` favours `skill-go` at p < 0.05; `increased` if it favours `skill` at p < 0.05; otherwise `not detected`.
- **Defect twins:** `lost` if 3 or more matched units were `NO_GO` under `skill` and are not under `skill-go`; otherwise `held`.
- **Evidence-gap twins:** `skill-go better`, `skill better` or `no significant difference` on `GO_WITH_CHANGES` at p < 0.05; and **waved through**: `waves gaps through` if `skill-go` judged 3 or more evidence-gap twins `GO` (the v2 sentence arm did so for 3 of 4), otherwise `does not wave gaps through`.
- **Overclaiming:** `reduced` if the paired difference in evidence-gap twins judged `NO_GO` favours `skill-go` (fewer) at p < 0.05, `increased` if it favours `skill`, otherwise `not detected`.
- **Against the plain-request sentence arm (`defined-go`)**, on evidence-gap `GO_WITH_CHANGES` and on sound-plan `GO` separately: `skill-go better`, `defined-go better` or `no significant difference`, at p < 0.05.

The labels are descriptive; with 32 matched evidence-gap units, `not detected` is weak evidence of no effect. No pass threshold is claimed.

## Hypotheses, stated before any `skill-go` observation (two-sided; the opposite outcome is reportable)

1. `skill-go` judges more sound plans `GO` than `skill` (the sentence stops the hedging). Prediction: a large gain, since the plain-request sentence arm judged 64 of 64 `GO`.
2. `skill-go` blocks defect twins as often as `skill` (32 of 32 in every arm so far).
3. `skill-go` judges fewer evidence-gap twins `GO_WITH_CHANGES` than `skill`: the detection cost that v2 showed for the sentence reappears, here as `GO`. This is the main risk, because the skill-style reports mark gaps as `RISK` findings that the sentence may recast as optional.
4. `skill-go` judges fewer evidence-gap twins `NO_GO` than `skill`. No prediction: the sentence says nothing about gaps that deserve a change, and the plain-request sentence arm overclaimed more than the skill-style arm.

## Human reading, fixed in advance

Read in full and classified by whether the report names the planted gap or defect, and what it does with it: (1) **every evidence-gap twin `skill-go` judged `GO`** (the false-clean risk), (2) **every defect twin without `NO_GO`**, (3) **every sound plan with `NO_GO`**, (4) a sample of up to ten sound plans `skill-go` still judged `CHANGES_RECOMMENDED` (what is left of the hedging), (5) a sample of up to ten evidence-gap twins `skill-go` judged `NO_GO` (what the overclaim says now) and (6) a sample of up to ten it judged correctly. Counts by class; coverage stated. The reader is the corpus author, who has seen the scores and designed the arm.

## Stops, interruptions and adjudication

As in the v3 run: `SAFETY_INTERRUPTED` and `MODEL_MISMATCH` are stops, never verdicts; an adjudication file naming each stop and any reclassification is written **before any metric**; the as-run result is the headline. A run that halts on three consecutive stops is not rerun; the owner decides whether to continue with the identical command and `--max-consecutive-stops 99`.

## What results can claim

For one model, route, binary and prompt on this corpus hash, under the limits in the corpus preregistration (Claude authors and auditors; stated evidence gaps with no absorbing fallback; short plan notes) and the provenance above: corpus v3 has been seen for this question. Nothing about the skill's citation check or adjudication step, Gemini (the sentence has not been tried on the native route), or real repositories. A different wording or position of the sentence is a different arm.

## Running

`run_pilot_claude.py --arm skill-go --corpus benchmarks/counterfactual-pairs/v3 --run-manifest benchmarks/counterfactual-pairs/v3-run-skill-go/manifest.json ...` (and `--arm skill` with the same manifest for the control), then `verify_run.py` with the same two arguments, `score.py --corpus ...v3` for each skill-style ledger, and `v3-run-skill-go/analyze.py`. The gated runbook is [HANDOFF.md](HANDOFF.md).
