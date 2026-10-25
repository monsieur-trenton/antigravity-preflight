# Benchmark v4: plan (draft for the owner's decisions)

Status: **a plan with the owner's three decisions recorded (below), not yet a preregistration.** Nothing here is frozen, no case exists, and no model has been called. It turns the limits of [corpus v3 and its runs](benchmark-evidence.md) into a design, and ends with the decisions the owner must make before any case is written. When they are made, the design below becomes a preregistration pinned by a manifest, as for v2 and v3.

## What v3 could not tell us

| Limit of v3 | Why it matters | What v4 changes |
| --- | --- | --- |
| Every evidence gap is **stated** in one sentence of the plan | It tests what a reviewer does with a written unknown, not whether it notices a missing one | Gaps by **omission**: the plan never mentions the fact; the sound twin contains it |
| One snapshot of 7 or 8 lines | Real plans are long, mixed and mostly irrelevant to the one decisive fact | Plans of 25 to 120 lines with realistic noise |
| Every defect is derivable from the snapshot's own lines | The Gemini v1 pilot's one systematic miss needed a premise from outside the text | **Multi-source packets**: the decisive premise lives in a second named source (a spec, a config, a contract) |
| Sound plans carry no tempting gap | A reviewer that hedges everything passes a hedge-friendly metric, and one that blocks every stated unknown passes the other | **Decoy gaps**: sound plans with a plausible but non-binding gap |
| Written and audited by Claude, then arms designed after reading results | Shared blind spots; every arm was tuned on a corpus already seen | Cross-family authors and auditors; a **dev split** for any tuning and a **sealed test split** touched once |
| Both reviewers at or near a ceiling | A 100% result cannot separate good from very good | Harder cases, more of them, and a target where the Gemini reviewer is not at the top |
| Measures verdict calibration only | The headline claim (less independent-review burden) is untested | A separate phase for benchmarks G and F (below) |

## Design

**Case structure.** As before: a sound plan and a twin that changes one fact, two wordings, random ids, a hidden oracle, SHA-256 manifest, preregistered metrics. New kinds of pair, each a family with several instances:

1. **Omitted unknown** (verdict `CHANGES_RECOMMENDED`): the sound plan states the decisive evidence; the twin drops the sentence and nothing replaces it.
2. **Cross-source defect** (`BLOCKERS_FOUND`): the plan is consistent on its own; a second source (a pinned config, API contract or policy excerpt) contradicts one line. The packet names both sources, so source-coverage and quotation checks apply to the second one too.
3. **Direct and inferred defects** as in v3, in longer plans, to keep a bridge to the earlier numbers.
4. **Decoys**: sound plans with a stated, non-binding gap (the reviewer should note it at most as a `NOTE`); twins where the same gap becomes decisive.

Each family has a written specification of what makes the twin a defect or a gap and what the oracle's decisive line, accepted citation lines and mechanism are. Case sizes and noise are varied on purpose; no case is shorter than 25 lines.

**Splits and sealing.** About 20% of families are the **dev split**, used for any prompt or tooling work and for choosing arms. The remaining families are the **test split**, committed only as hashes (the manifest, not the packets) until the arms and their preregistration are frozen, then unsealed and run **once**. A prompt change after the test split is unsealed is a different arm on a new corpus, never a rerun.

**Independence.** Cases are written by a different model family from the reviewers under test and audited blind by a second family, plus an owner spot check of at least a fifth of the cases, with the class (sound, defect, gap) hidden. The corpus author and the person who reads the results are not the person who designed the arms; if that cannot be arranged, the readings are done by a model blind to arm identity and the limit is stated.

**Arms, preregistered before the test split is unsealed.**

| Arm | Reviewer | Why |
| --- | --- | --- |
| Skill-style | Gemini 3.8 Flash High, native | The skill's target; the first Gemini run on anything but a stated-unknown corpus |
| Bare | Gemini 3.8 Flash High, native, plain request in the same runtime | Benchmark A on the target model: does the skill's packet and contract beat just asking? Never run on Gemini |
| Skill-style | Claude Opus 5.5, CLI | The cross-route comparison already seen on v3 |
| Skill + sentence | Claude Opus 5.5, CLI | The only prompt variant with a prediction already on record; included as a fixed arm, not tuned further |

Nothing else is added after the dev split closes. Anything tuned on dev (a calibrated verdict line, a different sentence) enters as one preregistered arm, named before the test split is unsealed.

**Metrics.** The three primary rates of v3 (sound plans `GO`, defect twins `NO_GO`, gap twins `GO_WITH_CHANGES`), strict and ordered pairs, hedged, overclaimed and waved-through counts, per-family Wilson intervals, exact paired sign tests, and two new ones: **finding-level mechanism** (a blind reader checks that a blocker names the planted mechanism and cites an accepted line, on all defect twins that were blocked) and **decoy discipline** (decoy sound plans judged `GO`). Zero unsupported `VERIFIED` findings stays a gate.

**Size and power.** Test split: 80 pairs (160 cases), roughly 20 omitted-unknown, 24 cross-source, 20 direct and inferred defects, 16 decoys. That gives Wilson intervals of roughly ±7 points on a rate near 90%, and a paired sign test on 80 matched units that detects a difference of about 15 points when most discordant units fall one way. Dev split: about 24 pairs (48 cases).

## Estimated cost and time (an estimate from the v3 runs, not a bound)

| Run | Cases | Cost / time |
| --- | --- | --- |
| Claude skill-style, 2 trials, test split | 160 × 2 | about $11 and 1.5 hours |
| Claude skill + sentence, 2 trials | 160 × 2 | about $11 |
| Gemini skill-style, 1 trial, test split | 160 | about 9 hours |
| Gemini bare, 1 trial | 160 | about 6 to 9 hours (shorter prompts, same turn length) |
| Gemini second trial of both arms on a 48-case subset | 2 × 48 | about 5 hours |
| Dev split, any arm | 48 | $2 on Claude, about 2.5 hours on Gemini |

Authoring and audit add model cost and, for a cross-family author through the native route, orchestrator hours. The Gemini route takes about 195 s per case on average (v3: 12,500 s for 64 cases), so Gemini time is the binding cost. All live calls remain owner-gated with zero retries.

## Phases and gates

0. **Decisions** (below) and this plan's approval.
1. **Specification.** Family specs, the case schema and the scoring additions (mechanism check, decoy metric), with tests. Gate: the new scorer reproduces the committed v3 scores exactly.
2. **Dev split.** Author, audit, freeze. Run the cheap Claude arm to find broken cases (a twin no reviewer can distinguish, a sound plan every reviewer blocks) and fix or drop them before the test split is built. Report what was dropped.
3. **Test split.** Author and audit blind; commit hashes only. Gate: audit agreement on class at least as high as v3's, and the owner's spot check clean.
4. **Preregistration and tooling.** Freeze the arms, prompts, metrics, hypotheses and reading procedure; add the Gemini bare-arm wrapper and the multi-source packet support to the native driver (a new wrapper, `run_pilot.py` stays unchanged); manifests and tests as for v3. Gate: dry runs and the full offline suite.
5. **Unseal and run**, in the order the preregistration fixes, with concurrent controls where an arm is compared with a day-old ledger.
6. **Adjudicate, score, read, write up**, with the arm designer not the reader, and publish with the limits.

**Separate track, after phase 3 and not blocking it: benchmarks G and F.** G mines real artifacts with later-confirmed defects: the repository's own review history (the two reconciliation documents in `docs/reviews/` record about 25 real findings on reviewed releases in the larger one, though few pre-fix commits survive), and public bug-fix commits dated after the reviewers' knowledge cutoffs to limit contamination; the open questions are licensing, how many items survive a clean ground-truth check, and whether 30 items are enough to say anything. F runs a fixed independent reviewer on candidates with and without preflight's findings applied, on real work items, counting blockers surviving to the independent review; it needs an owner-supplied set of real tasks, so it is the only part that cannot be done alone.

## Risks

- **Corpus is again at a ceiling or a floor.** Mitigation: the dev split exists to find it, and cases that no arm can separate are dropped before the test split is built, with the drop reported.
- **Cross-family authoring is slow.** A Gemini author needs orchestrator hours; a fallback is a Claude author with a Gemini and owner audit, stated as a weaker independence.
- **Multi-source packets change the skill's own gates** (coverage, quotation lines per source). That is intended, but it means the scorer and parser need source-aware citations, which the v3 line-number field cannot express.
- **Bare Gemini arm on the native route.** The runtime embeds a packet and a fixed question; a faithful bare arm may need a wrapper that changes less than it seems to. It is tested offline first, and if it cannot be made faithful the arm is dropped and said so.
- **Real-data track yields too few items.** Then it is reported as a pilot, not a benchmark.

## Decisions made (2026-10-25)

1. **Scope: synthetic corpus first** (phases 0 to 6). Benchmarks G and F stay a separate track after phase 3.
2. **Authors: Gemini writes the cases, Claude audits them blind**, with the owner's spot check of at least a fifth. The reviewers under test then include Gemini 3.8 Flash High, so the plan must keep authoring and review apart: a different model or effort from the Flash reviewer where the owner has one (Gemini 4 Argon / High is the qualified candidate), and a statement of how close the two are if only Flash is available. Claude, the auditor, is also a reviewer arm; the audit is blind to class and the audit prompt is not the review prompt.
3. **Budget: one Gemini trial per arm on the test split** (about 9 hours per arm) **and two Claude trials** (about $22 for both Claude arms), with a Gemini repeat only on a 48-case subset (about 5 hours more) if the first trial leaves a result within noise of a threshold.

## First actions, in order

1. **Probe Gemini authoring** (no cases yet; the hand-off is drafted in [benchmarks/counterfactual-pairs/v4/probe](../benchmarks/counterfactual-pairs/v4/probe/PROBE.md) and has not been run). Authoring is not what the native runtime was qualified for: it is a tool-free reviewer with a fixed question and a machine-summary parser. Run one family specification through it as the prompt and read the output by hand, to decide whether the existing `cli_review.py` can be used as a plain generator (taking the saved report text) or whether a thin wrapper is needed. Owner-gated; one family; no retries.
2. **Write the family specifications** (the four kinds above, about a dozen families in all, a fifth of them dev), each with the twin's definition, decisive-line rule, accepted citation lines and mechanism, and one worked example written by me as a format reference, not as a case.
3. **Extend the scorer and schema** for multi-source packets and the two new metrics; the gate is that it reproduces the committed v3 scores exactly.
4. **Write the authoring brief and the audit brief** as hand-offs, in the style of `v3-run-gemini/HANDOFF.md` (where to find things, rules, a gated helper script).

Each step is a small commit on a branch from `main`; none changes a frozen file.
