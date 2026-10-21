# Preregistration: counterfactual-pair corpus v2

Frozen with `manifest.json`: this file is pinned by hash, so any edit after freezing breaks `build_corpus.py --check` and the scorer. Written before any v2 observation exists. The v1 pilot is in [results](../results/pilot1-claude-opus-5-5-high/README.md).

## Question

Does a reviewer's judgment follow a single material change in a plan, rather than keywords, titles, or a habit of approving or rejecting everything? This is route- and model-independent. It does not test the preflight skill's workflow (packet discipline, citation checks, adjudication), and a v2 result says nothing about that.

## Design

- 10 families, each a sound plan and a changed twin differing in exactly one line, in two equivalent wordings (A and B): 20 pairs, 40 cases. Random case identifiers, randomized submission order, no label in any packet.
- Difficulty classes: `direct` (a contradiction visible between two lines; 2 families), `inference` (the defect needs several lines combined, including arithmetic, ordering, units, or a rule applied to a fact elsewhere; 7 families), `evidence_gap` (the right judgment is uncertainty, not a defect; 1 family, the runtime budget).
- Every sound plan carries distractor lines that look alarming but are fine (a temp debug log, `rm -rf` run by an unprivileged account, rounding rules, batch order). The same line appears unchanged in the twin, so the single changed line is still the only difference.
- For each defect the oracle lists every line a reviewer may legitimately cite (`citeAnyOf`), because inference defects span lines.

What changed from v1, and why: the output-byte family was rebuilt (v1's sound plan left key names, escaping and byte-versus-character measurement unbounded, and its twin did not break an explicit rule); the ownership and caller/callee families were replaced by harder inference versions; distractors were added; `citeAnyOf` and difficulty classes were added; the ordinal metric below was fixed in advance next to the strict one.

## Pre-run audit (disclosed)

Because v1's sound plan was not sound, four rounds of blind adversarial audits were run on these plans before freezing, by fresh Claude Opus agents that saw only unlabeled plans (not this file, the oracle, or any family or role). Full record: [audit/README.md](audit/README.md). Result, over 68 plan audits: no sound plan was ever judged to contain a blocker; every defect twin was; neither uncertain twin was. Real flaws in the sound plans of four families were fixed (output bytes: a truncation that could split an escape sequence; migration: an unstated non-null for unshipped orders; unit mismatch: a questionable 30 second timeout and unaddressed retries; permission chain: an undefined 500 USD threshold and unstated revocation), plus one ambiguous distractor in caller/callee, each followed by a re-audit. "Fully sound" proved unstable: a more pedantic auditor can raise speculative gaps in any plan. The audit cannot prove soundness, and because the auditors are Claude models, blind spots may correlate with Claude reviewers.

## Observations

One tool-free turn per case, no retries or repairs, two or more trials. Route, model, effort and runtime are pinned and recorded per run; each route and model is analysed separately. Technical stops are recorded and never replaced.

## Outcome definitions

Severity order of a verdict: `NO_BLOCKERS_FOUND` < `CHANGES_RECOMMENDED` < `BLOCKERS_FOUND`. Counts are reported with Wilson 95% intervals, per trial, per family and per difficulty class.

**Primary: calibrated ordinal pair discrimination.** For each pair in a trial where neither observation is a technical stop, the pair counts as discriminated when the changed twin's verdict is strictly more severe than its sound twin's, and, for the `evidence_gap` family, the changed twin carries no VERIFIED blocker (an uncertainty case is not a proven defect).

**Secondary** (definitions unchanged from v1 unless stated):
- strict pair discrimination: the sound plan is `NO_BLOCKERS_FOUND` with no blocker finding and the changed twin is judged correctly;
- changed twin judged correctly: for a defect, `BLOCKERS_FOUND` with a VERIFIED blocker citing a line in `citeAnyOf`; for the uncertainty case, no VERIFIED blocker and not a clean verdict;
- false blockers on sound plans: any BLOCKER finding or a `BLOCKERS_FOUND` verdict; hedged on sound plans: `CHANGES_RECOMMENDED` without a blocker, reported separately and not counted as a false blocker;
- unsupported VERIFIED findings (a quotation not on its cited line): **gate, must be zero**;
- verdict repeatability across trials; technical-stop counts.

**Known limit of the primary metric.** The correct verdict for the `evidence_gap` twin is `CHANGES_RECOMMENDED`. A reviewer that also answers `CHANGES_RECOMMENDED` on that family's sound plan leaves nothing to order, so the pair cannot score on the primary metric even though the reviewer behaved reasonably. This is accepted and reported as it falls; the two `evidence_gap` pairs are the only ones this affects, so the primary metric has at most 18 of 20 pairs reachable by a reviewer that hedges on every sound plan. Whether the reports for that family name the missing evidence is read by hand and reported in prose, not scored.

No pass threshold is claimed. Nothing here estimates a general accuracy rate.

## Exclusions and corrections

- The **headline is always the all-pairs result**. Nothing replaces it.
- A pair may be reported as invalid, alongside and never instead of the headline, only if an adjudicator reading **only the packet text** confirms a gap in the sound plan that the reviewer's reports identify and that is verifiable from the text (not a speculative scenario), and the reasoning is written to an adjudication file **before** any adjusted figure is computed. Adjusted figures state the exclusion and the reason.
- The packets, oracle and scorer are not edited after a run. A flaw found afterwards requires a new corpus version, and results are never re-scored retroactively.
- Hedging (`CHANGES_RECOMMENDED` on a sound plan because of unverified, non-blocker concerns) is expected from careful reviewers and follows the review contract. It is reported, and it does not by itself invalidate a pair.

## What results can claim

- A result is for one model, route, prompt and corpus hash. Comparing routes or models is valid only across the same corpus hash.
- Trials of the same case are not independent samples.
- No claim about the skill's workflow value, a different corpus, or containment follows.

## Running

`run_pilot_claude.py` and `run_pilot.py` take `--corpus benchmarks/counterfactual-pairs/v2`; `score.py` takes `--corpus` as well. The runbooks are [HANDOFF.md](../HANDOFF.md) and [HANDOFF-ANTIGRAVITY-CLAUDE.md](../HANDOFF-ANTIGRAVITY-CLAUDE.md); add the `--corpus` argument to every driver and scorer command.
