# Preregistration (DRAFT, not frozen): counterfactual-pair corpus v4, reviewer arms

**Status: draft for the owner's review.** Nothing in this file is binding until it is frozen: the reviewer files, drivers, run manifest and this text are pinned by hash after the missing tooling (end of file) exists, and before any reviewer arm has produced an observation on this corpus. No model has been run on the test corpus as a reviewer. The only model calls on it so far are its authoring (Gemini 3.8 Flash High) and its blind audits (Claude Opus 5.5), recorded in [../test-authoring/](../test-authoring/README.md), [../test-audit/](../test-audit/README.md) and [../test-audit-revision/](../test-audit-revision/README.md).

## Question

v1 to v3 measured reviewers on short single-source plans written by Claude. They left three things open, which v4 is built to address:
1. whether the result holds on cases **written by a different model** (Gemini 3.8 Flash High) from the reviewer's own family;
2. whether a reviewer notices a **fact that is missing** (an omitted precondition) as well as one that is stated and wrong, and a defect that only shows when a **second source** (a reference excerpt) is read against the plan;
3. whether the skill's review contract changes verdicts compared with a plain request, on Gemini, which is the skill's target reviewer.

## Corpus (sealed; facts from the committed record)

71 pairs, 166 cases, manifest `2d13d47576d404154171126410dfbe31e076c194ebd561693479e332851b4b25` ([sealed-manifest-final.json](../test-audit-revision/sealed-manifest-final.json)). Each pair is a sound plan and a twin that differs by one edit; 12 pairs also have an equivalent rewording (wording B) of both members. The case text is sealed: no session that edits this repository reads it, and the repository holds hashes, abstract counts and redacted ledgers only.

| | Pairs |
| --- | --- |
| Defect twins (correct verdict `NO_GO`) | 47: 19 cross-source (plan against reference excerpt), 20 single-source, 8 decoy (`open_item_becomes_decisive`) |
| Gap twins (correct verdict `GO_WITH_CHANGES`) | 24: 18 omitted unknown (a precondition never mentioned), 6 absorbed (`open_item_absorbed`: an open item the plan's own text absorbs) |
| Sound members (correct verdict `GO`) | 71 (+12 reworded) |

Families, pairs kept of 8 authored (7 for some): contract_clause 8, open_item_becomes_decisive 8, config_limit 7, budget_arithmetic 7, ordering_dependency 7, omitted_measurement 6, omitted_propagation_window 6, scope_authority 6, omitted_access_check 6, open_item_absorbed 6, **policy_rule 4**. Family-level statements about `policy_rule` rest on four pairs and are labelled so.

**Disclosed limits of the corpus** (they bound any claim):
- It was **filtered by a Claude auditor**: a pair stays only if Claude Opus 5.5 recovered its intended class blind. First-pass agreement was 60 of 80; 71 of 71 agree after one rewrite and dropping nine. The Claude arms are the arms most likely to be flattered by this.
- **No human has read a pair blind.** The owner's spot check was not done; agent readings of the dev sample are recorded as not verifiably blind.
- Gemini 3.8 Flash High wrote the cases and is a reviewer arm. Claude audited and is a reviewer arm. Neither separation is clean.
- Short synthetic plans of 25 to 80 lines are a narrow proxy for real change review.

## Arms

| Arm | Reviewer | Request | Trials |
| --- | --- | --- | --- |
| G-skill | Gemini 3.8 Flash High, native `flash-high` route, effort high | `skill` | 1 |
| G-bare | same route and runtime | `bare`, inside the runtime's fixed `preflight-inline` persona (see [README](README.md)) | 1 |
| C-skill | Claude Opus 5.5, Claude CLI, tools disabled, effort high | `skill` | 2 |
| C-skill-go | same | `skill-go` | 2 |

Per trial every arm sees all 166 cases once, in one frozen random order, one tool-free turn per case, **no retries, repairs or fallbacks**. Cases of a pair are submitted independently (no shared session or context). Model, effort, runtime, CLI or `agy` binary, host, request hashes and the run manifest are pinned and stamped on every ledger row; the Gemini served model is not attested (recorded as unavailable). Arms run on one machine, paced in small alternating blocks (next section), so the comparison is concurrent. The optional repeat of G-skill and G-bare (trial 2) on the 24 pairs whose SHA-256 of `pair id + "|v4-repeat"` is smallest (58 cases for the test split as drawn, wording-B members included when their pair is drawn; four blocks, listed in the schedule) is run only if the first trial leaves a result within sampling noise of a stated threshold, and only after the owner approves it.

**Cost and time (estimates from v3):** Gemini about 3 minutes per case, so about 8 to 10 hours per arm; Claude about $0.04 per case, so about $12 to $15 per arm-pair of trials, about $25 to $30 for both Claude arms. Every live call is owner-gated and the run is split into small blocks (next section).

## Pacing (small blocks, one process at a time)

The first draft said "one sitting". That is withdrawn: a Gemini trial is about 9 hours and the session window is 5, and the host is shared with the owner's other work, so the run is paced in small blocks.

- **Block = a set of pairs, 6 pairs (12 to 18 cases, 14 on average) by default.** About 40 minutes of Gemini time or about 10 minutes of Claude time per block; 12 blocks per trial (11 of 6 pairs and one of 5). Both members of a pair (and its rewording) are in the same block, so every matched comparison is made within one block. The assignment is a function of the committed seed and the pair ids (pairs ordered by kind, then by seeded hash, dealt round-robin so every block mixes the kinds), the case order inside a block is the corpus's frozen submission order, and both are written into `run/schedule-test.json`, rebuilt from public inputs and checked against the sealed manifest's pins, and pinned by the run manifest.
- **Alternation.** Blocks are run in a fixed order that alternates arms (G-skill, G-bare, then the next block, and so on; for Claude, C-skill, C-skill-go, with trial 2 after trial 1). A schedule that stops early therefore leaves the arms equally far along and the comparison concurrent; a day, load or version effect hits arms alike. A finished arm is never compared with an unfinished one: the analysis uses only blocks completed in every arm being compared, and says how many.
- **One process at a time.** No parallel runs, no concurrent Gemini and Claude blocks, `nice` and `ionice` at low priority, and a block starts only when the host load is below the threshold the host qualification already needs (about 1.5). The owner starts each block, and may run it whenever the machine is idle. A block is one command with a case cap, stops at a case boundary, and is resume-safe: a recorded case is never rerun and an interrupted case is logged as a stop, not retried.
- **Total time is unchanged**: about 18 hours of Gemini (24 block-runs: 12 blocks × 2 arms) and about 4 of Claude (48 block-runs: 12 blocks × 2 arms × 2 trials), which can be spread over days or weeks. What changes is that no single run needs more than the window or the machine for an hour.
- **Measure first.** Before the first block of the test split, a short rehearsal records the seconds per case, child CPU time, peak child memory and load of each route (`run_v4.py status`, from the block log); if a block bogs down the host, the block size is cut before the freeze and the schedule rebuilt (`schedule.py --pairs-per-block`).
- **A rehearsal on the dev corpus** (public text, 23 pairs) may run any number of blocks before the freeze to test the tooling; its outputs are never evidence and no reviewer file is tuned on them without the change being recorded here.
- **Tooling:** [run/](../run/HANDOFF.md) holds the block driver, the wrapper and the skill [`v4-benchmark-blocks`](../../../../.claude/skills/v4-benchmark-blocks/SKILL.md) that lets an orchestrating agent run one authorized block at a time; guards are checked between cases (`--max-minutes`, `--max-cases`, `--max-load`, the STOP file, three stops in a row, a spend cap).
- **Early stopping.** The owner may stop after any completed block set. Hypotheses are then analysed on the completed blocks, and the analysis states how many blocks and cases that is. No block is added or dropped after seeing results.
- **How the analysis uses partial runs.** Each arm and trial is scored on its own completed blocks (a block is complete when every case has a ledger row, a stop included). A comparison uses only blocks complete in both arms (and, within a route, in every trial being matched), matched units and an exact two-sided sign test. A comparison across routes matches trial 1 of the Claude arm to Gemini's only trial, on cases. Subgroup tables (omitted against absorbed gap twins; cross-source against single-source defect twins) are rates with Wilson intervals, not tests.

## Outcome definitions

Verdict mapping for every arm: `GO` = `NO_BLOCKERS_FOUND`, `GO_WITH_CHANGES` = `CHANGES_RECOMMENDED`, `NO_GO` = `BLOCKERS_FOUND`. The unit is a **pair id with its wording** (83 matched units per trial: 71 plus 12 rewordings). Counts with Wilson 95% intervals per arm and trial; paired comparisons between arms on matched (pair, wording, trial) units with an exact two-sided sign test; no multiple-comparison correction, and every hypothesis below is reported whichever way it falls. The scorer is [`score_v4.py`](../score_v4.py), which reproduces the v1 to v3 scores.

**Three primary rates** (per arm; the bare arms use verdict only):
1. sound plans judged `GO`;
2. defect twins judged `NO_GO`;
3. gap twins judged `GO_WITH_CHANGES`.

**Summary:** strict pair discrimination (sound `GO` and twin correct), and ordered discrimination (twin judged strictly more severely than its sound member; for a gap twin, not `NO_GO`), with the known limit that a reviewer that hedges on sound plans cannot score on gap pairs under the strict metric.

**Secondary:** hedged and blocked sound plans; gap twins `NO_GO` (overclaimed) and `GO` (waved through); all of the above by kind (cross-source, single-source, decoy, omitted, absorbed) and by family; **decoy discipline** (decoy and absorbed members: false-blocker rate on the sound member and the absorbed twin); for the skill arms, decisive-line citation (a finding's cited source and line, checked against that source) and S02 citation on cross-source twins; mechanism judgments (below); wording-B consistency (A and B verdicts agree); verdict repeatability between trials; stops, apart from semantic errors. **Gate, must be zero:** unsupported VERIFIED findings (a VERIFIED finding whose quotation is not on the line it cites, in the source it names). The gate applies to the skill arms only.

**Mechanism judgments.** There is no human reader. For observations where a twin's verdict is correct, a reader model that sees only the oracle's decisive-fact description and the report text, arm label stripped and order shuffled, rules `MECHANISM_NAMED`, `NOT_NAMED` or `WRONG_MECHANISM`. `mechanism.py` builds the items: every twin whose verdict is the right one in trial 1 of every arm, and every twin whose verdict differs between trials of the same arm; the reader sees the oracle's decisive-fact text and one report, never the arm, route, trial or case. It is a model reading (Claude Opus 5.5, so not independent of the Claude arms) and is reported as such; it feeds no headline rate.

## Hypotheses, stated against the final class counts (analysed two-sided; the opposite outcome is reportable)

Predictions come from the v3 results ([Claude](../../results/v3-claude-opus-5-5-high/README.md), [Gemini](../../results/v3-gemini-flash-high/README.md), [skill-go](../../results/v3-skill-go-opus-5-5-high/README.md)) and are therefore informed guesses, not blind ones.

1. **Omission is harder than a stated gap, for Gemini.** G-skill judges omitted-unknown twins (18 pairs) `GO_WITH_CHANGES` less often than absorbed twins (6 pairs, where the gap is stated in the plan), and less often than it did on v3's stated gaps (32 of 32). Reported as the two rates with Wilson intervals; the six absorbed pairs are too few for a test, so that comparison is descriptive.
2. **Cross-source defects are harder than single-source ones.** For each arm the share of cross-source defect twins judged `NO_GO` is lower than for single-source defect twins (19 against 20 pairs). A difference smaller than the interval is reported as none.
3. **Claude overclaims gap twins more than Gemini.** C-skill judges more gap twins `NO_GO` than G-skill (v3: 8 of 32 against 0 of 32).
4. **The optional-suggestions sentence trades hedging for overclaiming on Claude, again.** C-skill-go judges more sound plans `GO` and fewer gap twins `GO_WITH_CHANGES` than C-skill, with more gap twins `NO_GO` (v3: 63 against 35 of 64 sound plans; 18 against 25 of 32 gap twins; 14 against 7 overclaimed, p = 0.039). A replication on a new corpus, not a new claim.
5. **Skill-style against bare on Gemini: no direction predicted.** Strict pair discrimination of G-skill against G-bare is compared two-sided; a difference is attributed to the contract only with the persona caveat above. If G-bare turns out to be unfaithful (offline check) the arm is dropped.
6. **Claude against Gemini on strict discrimination: no direction predicted, and not interpretable alone.** If C-skill exceeds G-skill, the auditor's filter is a competing explanation that this design cannot separate.

No pass threshold and no general accuracy rate is claimed; with 83 units per trial the intervals are wide and are shown.

## Reading procedure and adjudication

- Reports are read by the scorer first; no outcome is changed by hand. The headline is the all-pairs result and nothing replaces it.
- **Written before any metric is computed:** an adjudication file listing observations the reviewer excludes or relabels, with its reason. A pair may be reported as invalid (alongside, never instead of, the headline) only if an adjudicator reading the case text confirms a flaw in the sound member that the reviewers' reports identify and that is checkable from the text. Because the case text is sealed, that adjudicator is a separate session the owner starts, which returns a verdict and a redacted reason; the repository session does not read the text.
- Technical stops (`UNPARSEABLE_REPORT`, `SAFETY_INTERRUPTED`, `MODEL_MISMATCH`, runtime stops) are recorded, never replaced and never counted as verdicts; a stopped case is not run again.
- One parsing tolerance, fixed here: a FINDING line field written `[S02:5]` is read as `S02:5` and the row is marked. Any other deviation from the report format is an `UNPARSEABLE_REPORT` stop.
- Packets, oracle, scorer and rubric are not edited after a run. A flaw found afterwards needs a new corpus version; nothing is re-scored retroactively.

## What results can claim

A result is for one model, route, prompt and this corpus hash; trials of a case are not independent samples. The Claude arms run on the CLI route, which is not the skill's qualified containment. Nothing here concerns the skill's mechanical citation check or adjudication step beyond the VERIFIED-quotation gate, real repositories, or other models. The corpus is Gemini-written and Claude-filtered, sealed and unread by a human; claims are limited accordingly.

## Tooling (written, tested offline; nothing run on the test corpus)

All in [../run/](../run/HANDOFF.md), tested by `run/test_run_v4.py` with a stub Claude binary and a stub native runtime on the public dev corpus:
1. `run_v4.py`: the block driver for both routes (multi-source requests from `review/review_requests.py`; the Gemini packet lists the same sources for every arm and only the prompt file, which the runtime sends byte for byte, differs between arms); `blocks.sh`; the skill `v4-benchmark-blocks`.
2. The Gemini bare-arm faithfulness check is by construction and by the verifier: the runtime's user message is exactly the packet's prompt file (`cli_review.py` writes it as the one `user` frame), the verifier compares the packet prompt and the frame size against the request rebuilt from the pinned files, and the persona file is the same for every arm. What it cannot remove is the persona itself.
3. `build_run_manifest.py`, `schedule.py` (including the hash-drawn repeat subset), `verify_v4.py`, `analyze_v4.py`, `mechanism.py`.

**Still required before the freeze:** the final text of this file; a rehearsal on the dev corpus with each route verified clean; the host measurement; the run manifest written from the final files (`build_run_manifest.py --split test --write`); the owner's approvals (below). Items that did not exist when this draft was first written (driver, wrapper, manifest, verifier, analysis, schedule, repeat subset) now do.

## Decisions for the owner

- Budget as in "Cost and time", or a smaller first stage (for example Claude first, Gemini after).
- Whether the Gemini repeat subset is pre-approved or decided after trial 1.
- Whether the mechanism reading by a Claude model is enough, or a separate non-Claude reader is wanted.
- Whether to run the dev rehearsal now (a few cases per route, owner-gated) so the skill is exercised end to end before the freeze.
