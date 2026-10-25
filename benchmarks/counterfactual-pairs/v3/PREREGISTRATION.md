# Preregistration: counterfactual-pair corpus v3

Frozen with `manifest.json`: this file, the family texts, the keyword rubric and the audit records are pinned by hash, so any edit after freezing breaks `build_corpus.py --check` and the scorer. Written before any v3 observation by a reviewer arm exists. The only model calls on v3 so far are its authoring and its blind audits ([audit/README.md](audit/README.md)).

## Why v3 exists

The [v2 runs](../results/ablation-defined-go-opus-5-5-high/README.md) found that a five-line definition of the verdicts and one added sentence about optional suggestions made a plain prompt's verdicts follow its findings, but that the sentence also made 3 of 4 evidence-gap observations come out `GO`. Two problems limit what v2 can say:
1. **It was used to tune.** The defined arm and the sentence were written with v2's results in view. An improvement on v2 is a check of a mechanism, not an out-of-sample result.
2. **Its evidence-gap evidence is thin and contestable.** One family, four observations, and the plan's own cancel-and-report rule let a reader argue that `GO` was right (the reports said so). The oracle's `UNCERTAIN` label for that twin was a judgment, not something two independent readers had agreed on.

v3 is the held-out answer to both: new domains, new wording, eight evidence-gap families instead of one, each checked by independent readers.

## Design

- **16 families, 64 cases.** Each family is a sound plan and a changed twin that differ in exactly one line, in two wordings A and B that keep every number, unit and identifier and differ in phrasing on every line (a test checks it). Random case ids (`Q-xxxxxx`, disjoint from v2's `P-` ids), randomized submission order, no label in any packet, reviewer prompt byte-identical to v1 and v2.
- **8 defect families** (the twin's changed line makes the plan, as written, fail or break a rule it states, derivable from its own lines): 3 `direct` (a visible contradiction between two lines) and 5 `inference` (several lines, arithmetic or ordering).
- **8 evidence-gap families** (class `UNCERTAIN`, difficulty `evidence_gap`): the plan states a requirement and a consequence if it is missed; the sound plan states the decisive fact as measured, tested or confirmed with comfortable margin; the twin's single changed line says plainly that the fact has not been measured, tested or confirmed. **Nothing in either version makes a miss harmless or self-correcting** (no fallback, retry, alert, rollback or override that absorbs it). The correct verdict is `CHANGES_RECOMMENDED`: not `BLOCKERS_FOUND`, because nothing shows the plan failing, and not `NO_BLOCKERS_FOUND`, because a stated requirement rests on an unestablished fact.
- Every sound plan carries one or two distractor lines that look alarming but are fine by the plan's own text (a scary command run safely, an explained odd setting), repeated unchanged in the twin.
- Families: defect: cache key and tenant isolation, lock order, rate-limit arithmetic, idempotency key per retry, certificate rotation order, feature-flag default, backup retention against restore window, credential logging; evidence gap: batch capacity against a hard window, upgrade compatibility of existing callers, retry safety against idempotency, third-party rate limit, unique constraint against existing data, rollback duration, payload size against a hard limit, storage write permission.

## Authorship and audit (disclosed)

Four independent model authors wrote the families from [audit/author-brief.txt](audit/author-brief.txt), without seeing any arm, result or the added sentence. Two blind gap audits (32 plans each) and two blind classification audits (each classified all 64 plans as `FAILS`, `UNESTABLISHED` or `ESTABLISHED` from definitions that do not say which plan is expected to be which) were run before freezing. Results: both classifiers matched the intended class on 64 of 64 plans; no sound plan was flagged for a blocker or an unestablished fact; every defect twin was flagged for a blocker; every evidence-gap twin was flagged for its unestablished fact and none for a blocker. No text was edited. Full record, method and its limits: [audit/README.md](audit/README.md). **The authors and auditors are Claude models; the specification and themes were mine, written after v2's results and knowing the sentence.** Independent authorship is therefore partial, and v3 is held-out in the sense that no v3 plan was written, selected or changed in view of any arm's output on v3, not in the sense that the question was unknown to its designer.

## Observations

One tool-free turn per case, no retries or repairs, two or more trials. Route, model, effort and runtime are pinned and recorded per run. Technical stops, including any `SAFETY_INTERRUPTED` and `MODEL_MISMATCH` stop, are recorded and never replaced or counted as verdicts. The arms to be compared (the defined arm, the defined arm plus the optional-suggestions sentence, and the skill-style arm, with the bare arm optional), their order, trial count and spend cap are fixed in a **run preregistration written after this corpus is frozen and before any run**, which pins the arm manifests and this corpus's manifest hash. Arms are meant to run in one sitting on one machine with one binary, with arm order within a trial set in advance, so the comparison is concurrent rather than across days. The existing arm manifests bind each arm to corpus v2, so running v3 needs tooling that does not exist yet; that tooling is written, tested and committed before the run preregistration.

## Outcome definitions

Verdict mapping for every arm: `GO` = `NO_BLOCKERS_FOUND`, `GO_WITH_CHANGES` = `CHANGES_RECOMMENDED`, `NO_GO` = `BLOCKERS_FOUND`. Counts with Wilson 95% intervals, per trial, per family and per difficulty class; paired comparisons between arms on matched (case, trial) units with an exact two-sided sign test. All metrics below are verdict-only, so they mean the same for every arm.

**Three primary rates** (each reported for each arm, and paired between arms):
1. **Sound plans judged `GO`** (the sentence's intended effect).
2. **Defect twins judged `NO_GO`** (what the sentence must not lose).
3. **Evidence-gap twins judged `GO_WITH_CHANGES`** (neither `GO` nor `NO_GO`; the cost the sentence showed on v2, and the metric v3 is built to measure: 8 families x 2 wordings x 2 trials = 32 units per arm).

**One summary: strict pair discrimination**, the sound plan is `GO` and the changed twin has its correct verdict (`NO_GO` for a defect, `GO_WITH_CHANGES` for an evidence gap). Pair ordering (the changed twin judged strictly more severely than its sound twin; for an evidence gap, not `NO_GO`) is reported beside it, with its known limit: a reviewer that hedges on a sound plan cannot score on an evidence-gap pair.

**Secondary:** sound plans blocked (`NO_GO`) and hedged (`GO_WITH_CHANGES`); evidence-gap twins judged `NO_GO` (overclaiming) and `GO` (waved through); **gap named but dismissed**, among evidence-gap twins judged `GO`, the share whose report matches the family's keyword rubric (the report names the unestablished fact and the verdict ignores it; recall only, with the rubric's caveat, and read by hand on a sample); verdict follows finding on defect twins; verdict repeatability between trials; technical stops; each by family. For the skill-style arm the finding-level metrics (VERIFIED findings with an exact quotation) are also reported, for that arm only. Unsupported VERIFIED findings: **gate, must be zero**, as in v2.

## Hypotheses, stated before any v3 data (analysed two-sided; the opposite outcome is reportable)

1. The sentence arm judges more sound plans `GO` than the defined arm (a replication on a held-out corpus).
2. The sentence arm judges defect twins `NO_GO` as often as the defined arm.
3. **The sentence arm judges fewer evidence-gap twins `GO_WITH_CHANGES` than the defined arm.** v2 showed this on 4 observations in one family. v3 can show it is general (several families), or confined to plans with an absorbing fallback (v2's runtime-budget plan had one; v3's have none, so no cost here would point to that explanation), or absent.
4. The skill-style arm judges evidence-gap twins `GO_WITH_CHANGES` at least as often as either other arm, and sound plans `GO` less often than the sentence arm.

No pass threshold is claimed and nothing here estimates a general accuracy rate. The labels that summarise the run are fixed in the run preregistration.

## Exclusions and corrections

- The **headline is always the all-pairs result**; nothing replaces it. Pre-specified sensitivity views: excluding any family named in an adjudication written before the adjusted figure is computed.
- A pair may be reported as invalid, alongside and never instead of the headline, only if an adjudicator reading **only the packet text** confirms a gap in the sound plan that the reviewers' reports identify and that is verifiable from the text, with the reasoning written to an adjudication file before any adjusted figure is computed (the v2 rule).
- The packets, oracle, rubric and scorer are not edited after a run. A flaw found afterwards requires a new corpus version, and results are never re-scored retroactively.

## What results can claim

- A result is for one model, route, prompt and this corpus hash. Trials of the same case are not independent samples.
- v3 covers evidence gaps **with no absorbing fallback**. Plans whose own rules make a miss harmless (v2's runtime-budget plan) are not in it, so the sentence's behaviour on those is not measured here.
- Short plan notes are a narrow proxy for review of real changes. Nothing here concerns the skill's mechanical citation check or adjudication step, Gemini routes, or real repositories.
- The keyword rubric (`rubric.json`) is a recall-only proxy for "the report names the mechanism or gap"; it was written from the families' answer keys and validated against the authors' own sample reports before any observation exists.

## Running

`build_corpus.py --check` regenerates the packets, oracle and manifest from `families.json` and compares. `run_pilot_claude.py`, `verify_run.py` and `score.py` take `--corpus benchmarks/counterfactual-pairs/v3` for the skill-style arm today. The arms that borrow the v2-bound manifests need the run tooling and run preregistration described above.
