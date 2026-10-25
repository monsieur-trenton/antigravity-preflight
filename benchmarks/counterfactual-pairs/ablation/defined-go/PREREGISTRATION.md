# Preregistration: defined verdicts plus one sentence on optional suggestions (fourth arm)

Frozen with `manifest.json`: this file and the request file are pinned by hash, the bare system prompt and the rubric are pinned as borrowed files, and the manifest names the exact corpus v2 manifest. Written before any observation of this arm exists. A flaw found afterwards means a new version, not a re-score.

## How this arm came about, and what that does to its evidence

The [defined-verdicts arm](../defined/PREREGISTRATION.md) was run first and [partly closed the gap](../../results/ablation-defined-opus-5-5-high/README.md): defect twins were blocked correctly (35 of 35 with a verdict), but sound plans were hedged as often as in the bare arm (clean 8 of 40, against 24 of 40 for the skill-style arm). Sound-plan reports I read in that run (five from trial 1: two migration plans, ownership/authorization, permission chain, caller/callee) said things like "the plan is correct ... these are improvements, not blockers", then ended `GO_WITH_CHANGES`. The definition of `GO` ("needs no changes") is hard to meet when a reviewer can always suggest something, and `GO_WITH_CHANGES` ("should be improved") invites any suggestion.

**The sentence below was written after seeing that result, by the person who wrote the corpus, to fix the observed failure on this corpus.** A positive result is therefore partly expected and is not independent validation. It can show that the mechanism is what it appears to be (the remaining sound-plan gap is also vocabulary); it cannot show that the sentence generalizes. A held-out test needs a corpus the sentence was not written against.

## Question

**Does one added sentence, saying that optional suggestions that only make a working plan more robust are not changes the plan needs, make the reviewer judge sound plans clean, without losing the defect twins?**

## What the arm is

| | `defined` arm (run) | `defined-go` arm (this experiment) |
| --- | --- | --- |
| System prompt | "You are a helpful assistant." | identical ([bare-system.txt](../bare-system.txt), borrowed by hash) |
| User message | "Please review this plan.", the plan as plain text, the five-line definition block, a request to end with a `VERDICT:` line | identical, plus one sentence directly after the definitions |

The only difference is this sentence ([defined-go-request.txt](defined-go-request.txt)), a test checks that nothing else changed:

```
Optional suggestions that only make a working plan more robust are not changes it needs; if that is all you have, the verdict is GO.
```

**What is held fixed:** corpus v2 (the pinned manifest hash), model, effort, Claude CLI route, tool-free safe mode, empty working directory, one turn per case, trial count, no retries, the verdict-line parser and the verdict-only scoring. The comparison arms (`defined`, skill-style, bare) are committed evidence, all run earlier and not concurrently.

**What the sentence is, and is not.** It does not change the three definitions, so it sits beside "GO_WITH_CHANGES: the plan works as written but should be improved". How the reviewer reconciles "should be improved" with "optional suggestions are not changes it needs" is part of what is tested, and a possible limit: a cleaner design would reword the definition, but that would be more than one change and could not be attributed. The sentence does not mention evidence, severities, quotations or labelled findings, and does not number the plan.

**Risk the sentence adds.** A reviewer told that optional suggestions do not matter could also wave through a real defect or an uncertain plan as "optional". That is why the detection guard below exists and why every false `GO` on a changed twin will be read.

## Hypotheses

Stated before any data, analysed two-sided; the opposite outcome is reportable.
1. The `defined-go` arm judges more sound plans clean than the `defined` arm. This is the vocabulary hypothesis for sound plans.
2. It does so without lowering the share of defect twins that receive `NO_GO`.
3. It is closer to the skill-style arm on sound-plan cleanliness than the `defined` arm is.

## Metrics

Verdict-only, identical for every arm, computed by `score.py` and `analyze.py` as before: `GO` = `NO_BLOCKERS_FOUND`, `GO_WITH_CHANGES` = `CHANGES_RECOMMENDED`, `NO_GO` = `BLOCKERS_FOUND`. Wilson 95% intervals; paired comparisons on matched (pair, trial) units with an exact two-sided sign test. Two analyses, each with the second arm being `defined-go`: against `defined`, and against the skill-style arm.

**Primary: sound plans judged clean (`GO`)**, paired against `defined` on matched sound-plan units.

**Detection guard: defect twins receiving `NO_GO`** and, more generally, changed twins judged correctly (`NO_GO` for a defect twin, `GO_WITH_CHANGES` for an uncertainty twin), paired against `defined`. The outcome label names a loss if three or more matched units lose the correct verdict.

**Secondary:**
- Strict pair discrimination (sound twin `GO` and changed twin correct), the metric that was far below the skill-style arm (24 of 40 against 7 of 39); and the primary ordinal pair discrimination (35 of 39 for `defined`, 40 of 40 skill-style).
- Sound plans blocked, hedged and clean; verdict follows finding; verdict repeatability; technical stops; each as the all-pairs headline, and as pre-specified views excluding `caller_callee` (adjudicated in pilot 2 as having a text-visible gap in its sound plan, so a `GO` there is arguably wrong) and excluding `output_bytes` (see Interruptions).

## Human reading

Read in full and classified before conclusions are drawn:
1. **Every changed twin that received `GO`** (a false clean, the new risk): does the report name the planted mechanism and dismiss it as optional, or miss it?
2. **Every defect twin without `NO_GO`**, and **every sound plan with `NO_GO`**, as in the `defined` arm.
3. **A sample of sound plans that were hedged in the `defined` arm and are clean here**, to see whether real, text-visible gaps were waved through, and a sample of sound plans that are still `GO_WITH_CHANGES`, to see what the reviewer treats as a needed change.
Counts are reported by class and the reading coverage is stated. As before the reader is the corpus author, who has seen the scores.

## Interruptions

The same platform interruption seen in the bare and `defined` arms is likely (1 of 80 in the `defined` arm, the same `output_bytes` case). The driver records any safety interruption as `SAFETY_INTERRUPTED` and any non-requested served model as `MODEL_MISMATCH`; both are stops, never verdicts. Results are reported for all pairs and, as a pre-specified view, excluding `output_bytes`.

## Reading the outcome

Descriptive labels, fixed in advance, applied to the all-pairs primary comparisons, in this order (the first that applies is used). They are not claims of equivalence: with about 40 matched units, "no significant difference" is weak evidence of equality. The function that applies them is `fourth_arm_label` in [analyze.py](../analyze.py), tested.
- **Costs detection:** three or more matched units where `defined` judged the changed twin correctly and `defined-go` did not. A cleaner sound-plan result does not rescue this label.
- **Worse on sound plans:** `defined` beats `defined-go` on sound-plan cleanliness at p < 0.05.
- **Closes the sound-plan gap:** `defined-go` beats `defined` on sound-plan cleanliness (p < 0.05) and no more than 5 units favour the skill-style arm over `defined-go` on sound-plan cleanliness. The 5 is arbitrary and written down before the data; two unrelated 50-percent reviewers disagree on many units, so it is not a test of equality.
- **Partly closes the sound-plan gap:** the first part holds (p < 0.05) but more than 5 units still favour the skill-style arm.
- **Does not close the sound-plan gap:** `defined-go` does not beat `defined` at p < 0.05.

## Exclusions and corrections

The headline is the all-pairs result. Adjusted views are shown beside it, never instead of it: `caller_callee` and `output_bytes` exclusions as above, and any adjudication-named reclassification as a second view. Any further exclusion needs the v2 preregistration's rule and an adjudication file written before the adjusted figure is computed. The scorer, oracle, packets, prompts and rubric are not edited after freezing.

## Limits

About 40 matched units, two trials of one case that are not independent, one model, one corpus audited by Claude models. The sentence was chosen after seeing the `defined` results on this same corpus (above), so an improvement here is not an out-of-sample result. The comparison arms were run earlier and not concurrently. Nothing here concerns Gemini, other routes, real repositories, or the skill's citation check and adjudication step. If the sentence works, what is learned is that the three-verdict scale needs a definition of when `GO` applies, not that this wording is the right one.

## Running

`run_pilot_claude.py --arm defined-go --corpus benchmarks/counterfactual-pairs/v2` with the same model, effort, CLI and binary as the earlier arms, then `verify_run.py --arm defined-go`, `score.py --corpus ...v2`, and `ablation/analyze.py` twice (`defined` then `defined-go`, and `skill` then `defined-go`). The runbook is [HANDOFF.md](HANDOFF.md).
