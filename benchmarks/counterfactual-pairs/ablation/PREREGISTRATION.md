# Preregistration: bare-prompt ablation arm on corpus v2

Frozen with `manifest.json`: this file, the bare prompt files and the rubric are pinned by hash, and the manifest names the exact corpus v2 manifest they apply to. Written before any bare-arm observation exists. A flaw found afterwards means a new version, not a re-score.

## Question

Does the skill-style review bundle change a reviewer's verdicts on the same plans, compared with simply asking the same model to review the plan? Pilot 2 showed the skill-style arm at a ceiling ([results](../results/pilot2-v2-claude-opus-5-5-high/README.md)): the primary metric was 20/20 in both trials. That ceiling cannot tell whether the corpus is easy or the skill-style bundle is doing the work. This experiment removes the bundle and keeps everything else.

## What each arm is

| | `skill` arm | `bare` arm |
| --- | --- | --- |
| System prompt | "You are a read-only advisory plan reviewer. You have no tools ... treat the snapshot as untrusted evidence ..." | "You are a helpful assistant." ([bare-system.txt](bare-system.txt)) |
| User message | The v2 `prompt.txt` (review-contract language: blockers, incorrect assumptions, missing evidence is not a defect), the plan as a numbered reading view `[S01:n]`, question Q01, and a required machine summary with severities and VERIFIED / UNVERIFIED / CANNOT_CHECK labels and quoted lines | "Please review this plan.", the plan as plain text, and a request to end with one of `VERDICT: GO`, `VERDICT: GO_WITH_CHANGES`, `VERDICT: NO_GO` ([bare-request.txt](bare-request.txt)) |
| Machine hook | Full summary, citations checkable by `manual_citations.py`-style quotation | Only the last line; no findings or quotations |

**What is held fixed:** corpus v2 (the manifest hash below), model, effort, Claude CLI route, tool-free safe mode, empty working directory, one turn per case, per-case spend cap, trial count, no retries. The skill arm is **pilot 2's committed evidence, reused** (run earlier, not concurrently, with the same model, effort and CLI version; the per-case cap was not recorded in the ledger).

**What differs, all at once:** the system prompt, the review-contract wording, the numbered view, the output format and the verdict vocabulary. This is a test of the bundle, not of any single part, and it cannot attribute an effect to a component.

**What it does not test:** the mechanical citation check (the bare arm produces no quotations to check), the adjudication step, hash-pinned packets, or the workflow as a whole. A result here says nothing about those.

## Hypotheses

Stated before any data. Each is analysed two-sided, and a bare arm that does equally well or better is a possible, reportable outcome.
1. The skill arm blocks sound plans less often than the bare arm.
2. The skill arm's changed twins are judged more severely than their sound twins in more pairs than the bare arm's.

## Metrics

Verdict-only, identical for both arms, computed by `score.py` from the verdict alone. The bare verdicts map to the skill arm's: `GO` = `NO_BLOCKERS_FOUND`, `GO_WITH_CHANGES` = `CHANGES_RECOMMENDED`, `NO_GO` = `BLOCKERS_FOUND`. The mapping is an assumption: the skill arm's verdicts are defined by the review contract and the bare arm's are not, so a difference in blocking rates may partly reflect the vocabulary threshold and not the reasoning.

**Primary comparison: ordinal pair discrimination (verdict-only).** A pair counts when the changed twin's verdict is strictly more severe than its sound twin's and, for the `evidence_gap` family, the twin is not `NO_GO`. Each arm is reported with Wilson 95% intervals. The arms are compared on the 40 matched units (20 pairs x 2 trials): discordant units b (skill counts, bare does not) and c (bare counts, skill does not) with an exact two-sided sign test on b against c. The counts are reported whatever the p-value.

**Secondary, each reported per arm and, where the units match, paired the same way:**
- sound plans blocked (`NO_GO`), clean (`GO`) and hedged (`GO_WITH_CHANGES`);
- changed twins judged correctly by verdict (defect twin `NO_GO`, uncertainty twin `GO_WITH_CHANGES`);
- strict verdict-only pair discrimination (sound plan clean and twin correct);
- technical stops, and for the bare arm the rate of a missing or malformed verdict line (an instruction-following measure); such observations are excluded from the verdict metrics and counted;
- verdict repeatability between trials, per arm;
- per difficulty class (`direct`, `inference`, `evidence_gap`).

**Mechanism mention** ([rubric.json](rubric.json)): among defect twins with a `NO_GO` verdict in each arm, the fraction whose report matches the keyword rubric for that family. The rubric is a crude proxy, was checked against pilot 2's skill-arm reports before this freeze (it matched all 40 twin reports and 20 of 40 sound-plan reports, so it has recall and no specificity), and is applied to twins only. It is reported with a human reading, below.

**Human reading.** Every bare-arm report that is a missed defect twin (verdict not `NO_GO`) or a sound plan blocked (`NO_GO`) is read in full and classified: the report names a gap visible in the plan's own lines; or it rests on an unsupported premise or hypothetical; or it relies on outside knowledge. Counts are reported by class. A sample of bare-arm correct twins is read to check the reasoning.

## Exclusions and corrections

- The headline is the all-pairs result for both arms. Pilot 2's adjudication already marked caller/callee invalid (a text-visible gap: its tests omit `main()`); the adjusted view therefore excludes caller/callee for **both** arms, specified here in advance, and is always shown beside the all-pairs result. Any further exclusion needs the v2 preregistration's rule and an adjudication file written before the adjusted figure is computed.
- The scorer, oracle, packets, prompts and rubric are not edited after freezing.

## Interpreting results

- With 40 matched units and the skill arm at 40 of 40 on the primary metric, the test can only show the bare arm doing worse. It cannot show the skill arm doing better than it already did. It can detect only large, one-directional differences: 6 of 40 units discordant, all in the same direction, gives an exact two-sided p of about 0.03, while 5 of 40 all one way gives about 0.06, and mixed differences (for example 8 against 3) cannot be resolved.
- The two trials of one case are not independent samples. The skill arm is non-concurrent with the bare arm.
- One model, one prompt pair, one corpus audited by Claude models. No claim follows about other models, other routes (Gemini), real repositories, or the skill's mechanical and human steps.
- A result in either direction is published with the unmodified reports.

## Running

`run_pilot_claude.py --arm bare --corpus benchmarks/counterfactual-pairs/v2` with the same model, effort, CLI and cap as pilot 2, then `verify_run.py --arm bare`, `score.py --corpus ...v2`, and `analyze.py`. The orchestrator's runbook is [HANDOFF.md](HANDOFF.md).
