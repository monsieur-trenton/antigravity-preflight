# Preregistration: bare prompt with defined verdicts (third arm)

Frozen with `manifest.json`: this file and the request file are pinned by hash, the bare system prompt and the rubric are pinned as borrowed files, and the manifest names the exact corpus v2 manifest. Written before any observation of this arm exists. A flaw found afterwards means a new version, not a re-score.

## Question

The [bare-arm ablation](../../results/ablation-bare-opus-5-5-high/README.md) found a large verdict-only gap between the skill-style arm (40 of 40 pairs ordered) and the bare arm (21 of 37), while the preregistered human reading showed the bare reviewer had found and named the planted defect in all 15 twins it missed, then ended `GO_WITH_CHANGES`. The explanation that fits is that the bare prompt gives the three verdicts no meaning and no link to the findings. This arm tests that explanation directly: **does defining the verdicts, and nothing else, close the gap?**

## What the arm is

| | `bare` arm (run) | `defined` arm (this experiment) |
| --- | --- | --- |
| System prompt | "You are a helpful assistant." | identical ([bare-system.txt](../bare-system.txt), borrowed by hash) |
| User message | "Please review this plan.", the plan as plain text, a request to end with a `VERDICT:` line | identical, plus one block that says what each verdict means |

The only difference is this block, inserted before the final-line instruction ([defined-request.txt](defined-request.txt)):

```
Verdicts mean this:
GO: the plan needs no changes.
GO_WITH_CHANGES: the plan works as written but should be improved.
NO_GO: the plan as written will fail or break a rule it states.
```

**What is held fixed:** corpus v2 (the pinned manifest hash), model, effort, Claude CLI route, tool-free safe mode, empty working directory, one turn per case, trial count, no retries, the verdict-line parser, and the verdict-only scoring. The comparison arms are the committed bare-arm and pilot 2 evidence, both run earlier and not concurrently.

**What the block is, and is not.** `NO_GO` here is close to the review contract's idea of a blocker (a plan that fails or breaks a rule it states). That closeness is the hypothesis. The block does **not** say that missing evidence is not a defect, does not ask for severities, evidence labels or quotations, does not number the plan, and does not change the system prompt. The skill-style arm still differs in all of those, and in tying its verdict structurally to labelled findings.

**What a result can and cannot show.** If the gap closes, defined verdicts are *sufficient* for verdict calibration in this design; that does not show they are *necessary*, because the skill-style arm differs in other ways too. If the gap does not close, something else in the bundle is doing the work, and this experiment cannot say what.

## Hypotheses

Stated before any data, analysed two-sided; the opposite outcome is reportable.
1. The `defined` arm orders more pairs than the `bare` arm. This is the vocabulary hypothesis.
2. The `defined` arm is closer to the skill-style arm than the `bare` arm is.

## Metrics

Verdict-only, identical for every arm, computed by `score.py` and `analyze.py` exactly as in the [bare-arm preregistration](../PREREGISTRATION.md): `GO` = `NO_BLOCKERS_FOUND`, `GO_WITH_CHANGES` = `CHANGES_RECOMMENDED`, `NO_GO` = `BLOCKERS_FOUND`.

**Primary: ordinal pair discrimination** (changed twin judged strictly more severely than its sound twin; for the `evidence_gap` family the twin must not be `NO_GO`), with Wilson 95% intervals. Two paired comparisons on matched (pair, trial) units, each with an exact two-sided sign test: `defined` against `bare`, and `defined` against the skill-style arm.

**Verdict follows finding (new).** Among defect twins that produced a verdict and whose report matches the family's keyword rubric (the same [rubric](../rubric.json)), the share that received `NO_GO`. In the bare arm every defect twin's report matched the rubric, so this measures directly whether the verdict follows the finding. It has recall but no specificity (the rubric also matches many sound-plan reports), which is why it is only used on defect twins and read alongside the human reading.

**Secondary:** sound plans blocked, clean and hedged; defect twins judged correctly by verdict; strict verdict-only pair discrimination; technical stops; verdict repeatability between trials; each per difficulty class and, as pre-specified views, excluding `caller_callee` (adjudicated in pilot 2 as having a text-visible gap in its sound plan) and excluding `output_bytes` (see Interruptions).

**Human reading.** Every `defined`-arm defect twin that did not receive `NO_GO`, and **every sound plan that received `NO_GO`** (defining `NO_GO` could create false blockers, so these now matter), is read in full and classified: the report names a gap visible in the plan's own lines; or rests on an unsupported premise or hypothetical; or relies on outside knowledge. A sample of correct twins is read for reasoning. Counts are reported by class, and the reading coverage is stated.

## Interruptions

In the bare arm, 4 of the 8 `output_bytes` observations were interrupted by the platform ([details](../../results/ablation-bare-opus-5-5-high/README.md)); the cause is unknown and this arm is also a bare-style prompt, so the same loss is likely. The driver now records any safety interruption as a named stop (`SAFETY_INTERRUPTED`) and any non-requested served model as `MODEL_MISMATCH`; both are stops, never verdicts. The primary result is reported for all pairs **and**, as a pre-specified view, excluding `output_bytes`. Conclusions are stated only as far as they hold in both.

## Reading the outcome

Descriptive labels, fixed in advance, applied to the primary paired comparisons on all pairs. They are not claims of equivalence: with about 40 matched units, "no significant difference" is weak evidence of equality.
- **Closes the gap:** `defined` beats `bare` (sign test p < 0.05) and no more than 3 units favour the skill-style arm over `defined`.
- **Partly closes it:** `defined` beats `bare` (p < 0.05) but more than 3 units still favour the skill-style arm.
- **Does not close it:** `defined` does not beat `bare` at p < 0.05.
- **Worse:** `bare` beats `defined` at p < 0.05.

## Exclusions and corrections

The headline is the all-pairs result. Adjusted views are shown beside it, never instead of it: `caller_callee` and `output_bytes` exclusions as above, and any adjudication-named reclassification as a second view. Any further exclusion needs the v2 preregistration's rule and an adjudication file written before the adjusted figure is computed. The scorer, oracle, packets, prompts and rubric are not edited after freezing.

## Limits

About 40 matched units, two trials of one case that are not independent, one model and one corpus audited by Claude models. The wording of the definitions was chosen by the author, who knows the corpus, and is close to what the skill's contract means by a blocker; a differently worded definition could behave differently. Nothing here concerns Gemini, other routes, real repositories, or the skill's citation check and adjudication step.

## Running

`run_pilot_claude.py --arm defined --corpus benchmarks/counterfactual-pairs/v2` with the same model, effort, CLI and binary as the bare arm, then `verify_run.py --arm defined`, `score.py --corpus ...v2`, and `ablation/analyze.py` twice (`defined` against `bare`, and `defined` against the skill-style arm). The runbook is [HANDOFF.md](HANDOFF.md).
