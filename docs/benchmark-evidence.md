# Benchmark evidence: what has been measured, how, and what it does not show

This is the full narrative behind the summary table in the [README](../README.md#evidence-at-a-glance). Every number comes from a committed ledger, a preregistered analysis and an adjudication written before the metrics; each section links its write-up, which is the authority. The design of the benchmarks is in the [benchmark plan](benchmark-plan.md).

## How to read it

- **Two kinds of evidence, never mixed.** The deterministic gates (hashes, source coverage, exact-quotation checks) are tested offline with no model calls. The reviewer's judgments are measured live, on counterfactual pairs: a sound plan and a twin that changes one line.
- **What a live result is.** One model as requested and configured (the Gemini served model is not attested), one route, a corpus written and audited by Claude, two trials of the same cases. Intervals are Wilson 95%; the two trials are not independent samples. None of it is a general accuracy rate.
- **What has not been measured.** Whether the workflow lowers the burden on a separate independent reviewer (benchmarks A and F in the plan): the headline claim, still untested. Real repositories, long messy plans, unknowns that the plan does not state, and defects that need a premise from outside the snapshot.
- **Known limits of the design.** In every evidence-gap family of corpus v3 the plan states the unknown in one explicit sentence, so the corpus tests what a reviewer does with a stated unknown. Both Claude and Gemini reached a ceiling on parts of it. Several arms (the defined arm, the sentence arms) were designed after earlier results were read, and each write-up says which corpus is held out for which question. The human readings were done by the side that built the corpora and arms. Claude-route runs use CLI configuration for isolation, not the qualified native containment, and say nothing about Gemini.

## The write-ups, in the order they were run

![Offline evidence: 45 utility checks, 50 citation scenarios, 13 of 13 injected faults stopped, 1,464 Argon controls, zero provider calls](figures/offline-evidence.svg)

All figures above come from deterministic offline checks. They show the gates behave as specified; they say nothing yet about how well the model reviews. That claim needs the live trials in the [benchmark plan](benchmark-plan.md).

![Fault injection matrix: 13 of 13 mechanical faults stopped, 2 semantic faults pass through to manual premise checking, 4 checks not exercised](figures/fault-gate-matrix.svg)

![Reviewer verdicts for each sound plan and its changed twin](figures/pilot1-verdict-matrix.svg)

That figure is a small pilot on the `claude-cli` route (Claude Opus 5.5), not a Gemini or workflow result: no false blockers and no fabricated citations, with one corpus family found to be flawed in adjudication. Read the [full write-up](../benchmarks/counterfactual-pairs/results/pilot1-claude-opus-5-5-high/README.md) before quoting it.

![Reviewer verdicts on corpus v2](figures/pilot2-verdict-matrix.svg)

Pilot 2 repeated this on the preregistered, harder [corpus v2](../benchmarks/counterfactual-pairs/v2/README.md) (same model, route and prompt): the preregistered ordinal metric was 20/20 in both trials, no sound plan was ever blocked, and no citation was fabricated. The honest reading is that the corpus has reached its ceiling for this reviewer, and that sound plans were hedged 40% of the time. [Write-up](../benchmarks/counterfactual-pairs/results/pilot2-v2-claude-opus-5-5-high/README.md).

![Bare prompt against skill-style prompt on corpus v2](figures/ablation-bare-vs-skill.svg)

The preregistered ablation ran the same 40 plans with a bare prompt. On the verdict-only metric the skill-style arm ordered 40 of 40 pairs and the bare arm 21 of 37, yet the bare reviewer **found and named the defect in all 15 of the twins it missed**, then ended `GO_WITH_CHANGES`; neither arm blocked a sound plan. So this shows the verdict line carried the signal in one arm and not the other, not that the bundle improved defect detection. [Write-up](../benchmarks/counterfactual-pairs/results/ablation-bare-opus-5-5-high/README.md).

![Three arms on corpus v2: skill-style, bare, and bare with defined verdicts](figures/ablation-three-arms.svg)

A third arm added **five lines saying what each verdict means** to the bare prompt and nothing else. That moved it from 21 of 37 to 35 of 39 pairs ordered (12 units for the defined arm, none against, p = 0.0005); all 35 of its defect twins that produced a verdict received `NO_GO`, and no sound plan was blocked. By the preregistered rule it **partly closes the gap**: the 4 units still favouring the skill-style arm are all in one documented family, and the defined arm still hedges sound plans (clean 8 of 40, against 24 of 40 for the skill-style arm). So most of the earlier verdict gap was verdict calibration, not detection. One safety interruption again hit an `output_bytes` plan. [Write-up](../benchmarks/counterfactual-pairs/results/ablation-defined-opus-5-5-high/README.md).

![Four arms on corpus v2: the optional-suggestions sentence](figures/ablation-four-arms.svg)

A fourth arm added **one sentence** (optional suggestions that only make a working plan more robust are not changes the plan needs, so `GO` if that is all). It made **all 40 sound plans clean** (the defined arm: 8; skill-style: 24) and kept all 36 defect twins blocked, but **3 of the 4 uncertainty-twin observations**, all in the runtime-budget family where an unmeasured risk deserves a flagged change, were judged `GO`. The preregistered label is **"costs detection"**. The sentence was written after the defined result, on the same corpus, so this checks the mechanism and is not out-of-sample evidence; the cost rests on four observations and needs a held-out corpus. [Write-up](../benchmarks/counterfactual-pairs/results/ablation-defined-go-opus-5-5-high/README.md).

![The same 24 plans on two reviewer routes](figures/pilot-routes-comparison.svg)

The same frozen corpus v1 has also run on **Gemini 3.8 Flash High through the qualified native route**, the skill's target. After a documented re-read of four format stops (the reviewer wrote the snapshot label `S01:3` where a digit was asked), it discriminated 8 of 12 pairs in both trials against Claude's 9 and 8 of 12, blocked no sound plan, hedged none (Claude hedged 7 of 24), invented no evidence, and matched Claude's 20 of 20 on the ordinal reading of the five valid families; its one systematic difference is writing a RISK instead of a blocker on both required-coverage twins. It is about 10 to 15 times slower, and its served model is requested, not attested. [Write-up](../benchmarks/counterfactual-pairs/results/pilot-flash-high/README.md).

![Gemini 3.8 Flash High on the held-out corpus v3](figures/v3-gemini-verdicts.svg)

On the held-out [corpus v3](../benchmarks/counterfactual-pairs/v3/README.md) (64 cases, eight evidence-gap families with no absorbing fallback), preregistered and run in two trials on the same route, Gemini 3.8 Flash High judged **61 of 63 sound plans Clean, blocked all 32 defect-twin observations and flagged all 32 evidence-gap-twin observations as Changes recommended**, with no false blocker, no waved-through gap and zero unsupported VERIFIED findings; the only misses are two non-blocking hedges on sound plans, and one observation was a runtime stop, excluded and not rerun. It was no weaker on the five inference families than on the three direct ones. This is a ceiling result: in every evidence-gap family the plan states the unknown in one sentence, and the corpus shares its author's blind spots, so it shows the reviewer reads a stated unknown as a risk and cannot rank it against a stronger reviewer or show how it behaves when the unknown is not written down. The served model is requested, not attested. [Write-up](../benchmarks/counterfactual-pairs/results/v3-gemini-flash-high/README.md).

![Corpus v3: verdict mix for five reviewers](figures/v3-four-reviewers.svg)

The same held-out corpus on **Claude Opus 5.5** (three prompt arms, six runs, no stops, $13.72) gave a different picture. The one-sentence arm **replicated its gain on sound plans** (64 of 64 `GO`, against 23 for the defined arm and 34 for the skill-style arm) and **kept every defect twin blocked** in all three arms, but the evidence-gap twin was mostly **ruled a blocker rather than missed**: 8 of 32 in the skill-style arm, 26 in the defined arm and 21 in the sentence arm, which waved through 1. The skill-style arm is the best of the three on the evidence-gap twin (24 of 32 `GO_WITH_CHANGES`) but hedged 30 of 64 sound plans. On matched units the Gemini run was ahead of the Claude skill-style arm on sound plans and on evidence-gap twins; that is a difference between two routes as run (different CLI, wrapper, report format and day), not between models. [Write-up](../benchmarks/counterfactual-pairs/results/v3-claude-opus-5-5-high/README.md).

Adding the same sentence to the **skill-style prompt** (designed after those results, so v3 is not held out for it; four runs with a concurrent control) **cured the hedging** (63 of 64 sound plans `GO` against 35 of 64) and kept every defect twin blocked, and waved no evidence-gap twin through (0 of 32). The cost appeared as more overclaiming instead: 14 of 32 gap twins were judged `NO_GO` against 7 in the control (p = 0.039), each naming the gap correctly and asking for the same check. It is the best Claude arm on the strict pair metric (49 of 64 against 28 for the control), still behind the Gemini run's 32 of 32 on the gap twins. [Write-up](../benchmarks/counterfactual-pairs/results/v3-skill-go-opus-5-5-high/README.md).

The amber rows in the fault matrix are documented limits: a verbatim quotation can still misstate its source, so Codex must check each finding's premise. See the [fault-injection harness](../benchmarks/fault-injection/README.md).

