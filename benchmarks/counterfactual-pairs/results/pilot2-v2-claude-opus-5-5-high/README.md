# Pilot 2: corpus v2, Claude Opus 5.5 through the Claude CLI

Two trials of the preregistered 40-case [corpus v2](../../v2/README.md), run through [run_pilot_claude.py](../../run_pilot_claude.py) as set out in the [v2 handoff brief](../../v2/HANDOFF.md). **This is the `claude-cli` route and a Claude model. It says nothing about Gemini, the skill's qualified runtimes, or the value of the preflight workflow** (benchmarks A and F in the [benchmark plan](../../../../docs/benchmark-plan.md)). Nothing here is a general accuracy rate.

![Reviewer verdicts for each sound plan and its changed twin on corpus v2](../../../../docs/figures/pilot2-verdict-matrix.svg)

## Run identity and integrity

| | |
| --- | --- |
| Route / model / effort | `claude-cli` / `claude-opus-5-5` / `high`, the same as [pilot 1](../pilot1-claude-opus-5-5-high/README.md) |
| Claude Code version | 2.1.306, the same as pilot 1 |
| Served model | `claude-opus-5-5` in all 80 observations, as reported by the CLI |
| Trials | 2, 40 cases each, one tool-free turn per case, no retries |
| Cost / time | $2.14 in total ($1.24 and $0.90); about 12 s per case |
| Technical stops | 0 of 80 |
| Corpus | v2, manifest SHA-256 `79facc8a…b6316b`, preregistration pinned in it |
| Evidence | [trial1](trial1/), [trial2](trial2/) (ledger and unmodified reports), [score.json](score.json), [adjudication.json](adjudication.json), [verify.json](verify.json) |

[verify_run.py](../../verify_run.py), rerun on the returned working directory, reports **0 failures**: every saved request is byte-identical to what the frozen corpus and committed driver produce, every ledger report hash matches its saved report, every report equals the CLI's result field, and the stamp and served model match. Cost and wall times were also recomputed independently. The run's commit was not recorded; it is inferred from those byte matches.

## Preregistered results

The metrics, the exclusion rule and the known limits were fixed in the [preregistration](../../v2/PREREGISTRATION.md) before any v2 observation existed. Wilson 95% intervals; the two trials are not independent samples.

| | Trial 1 | Trial 2 |
| --- | --- | --- |
| **Primary: calibrated ordinal pair discrimination** (changed twin judged strictly more severely than its sound twin) | **20/20** (0.84–1.00) | **20/20** (0.84–1.00) |
| Strict pair discrimination (sound plan fully clean as well) | 13/20 (0.43–0.82) | 11/20 (0.34–0.74) |
| Changed twins judged correctly (mechanism cited at a legitimate line) | 20/20 | 20/20 |
| False blockers on sound plans | 0/20 (0.00–0.16) | 0/20 (0.00–0.16) |
| Hedged on sound plans (`CHANGES_RECOMMENDED`, no blocker) | 7/20 | 9/20 |
| Unsupported VERIFIED findings (gate: zero) | 0 | 0 |
| Verdict identical across trials | 38/40 (0.84–0.99) | |

By difficulty class, the primary metric was 4/4 (direct), 14/14 (inference) and 2/2 (evidence gap) in each trial. The only two verdicts that differed between trials were hedges on sound plans.

## Adjudication

All 16 hedged sound-plan reports were read in full, along with 16 of the 20 trial 1 twin reports; the trial 2 twin reports were checked by keyword only (every one of 36 defect-twin reports names its mechanism, and all four uncertainty-twin reports derive the same 22 MB/s requirement and carry no verified blocker). Judgments are by one reader, the benchmark's author, after seeing the scores. The reasoning is in [adjudication.json](adjudication.json), written before any adjusted figure was computed.

**What the reviewer got right.**
- The mechanisms were correct and reasoned from the text: 52 minutes against a 45-minute deadline (and 60 at the maximum); the pre-write assertion that detects an overflow but does not prevent the release abort; the support-lead group justifying a scope that revocation never removes; the unit trap `timeout=5` read as 5 ms. It also cleared the planted traps in the sound plans (`timeout=5000` is 5 s; separate UUIDs keep concurrent cleanups apart).
- The uncertainty twin was handled as uncertainty in all four observations: it derived the required rate as an inference, invented no measured throughput, and kept the finding at a RISK.
- The rebuilt output-byte family, the one that failed in pilot 1, was cleared in all four sound observations and blocked in all four twin observations. That supports the pilot 1 conclusion that its failure was the corpus, not the reviewer, though it does not prove it.

**What hedging was.** Sixteen of 40 sound-plan observations (40%) got `CHANGES_RECOMMENDED`, none a blocker. The hedges were mostly claims stated without evidence (a complete caller list, how a token issuer works, idempotency) and hypothetical failures (leaked tokens, symlink races, thread-pool exhaustion), which is what the [review contract](../../../../skills/antigravity-preflight/references/review-contract.md) asks for. Five families drew no hedge at all.

**One pair qualified as invalid under the preregistered rule.** In both wordings of caller/callee the sound plan says unit tests cover `schedule()` and `report()` but not `main()`, the one caller whose changed handling sets the exit status. That is visible from lines 4 and 6 alone, and all four sound-plan reports said so. The other hedges did not qualify: they rest on unsupported premises, hypotheticals or outside knowledge. Adjusted figures, shown beside the all-pairs result and never instead of it:

| | Trial 1 | Trial 2 |
| --- | --- | --- |
| Primary, excluding caller/callee | 18/18 (0.82–1.00) | 18/18 (0.82–1.00) |
| Strict, excluding caller/callee | 13/18 (0.49–0.88) | 11/18 (0.39–0.80) |
| Hedged on sound plans, excluding caller/callee | 5/18 | 7/18 |

The exclusion changes nothing about the headline: the primary metric is 20/20 either way.

## What this does and does not show

- For this model, prompt and route, on these ten families, the reviewer judged the changed twin more severely than its sound twin in every pair-observation, never blocked a sound plan, and never fabricated a citation. That is route- and model-specific and rests on 20 pairs with intervals reaching down to 0.84.
- **The corpus has hit its ceiling for this reviewer.** A perfect primary score means the corpus no longer separates this model and prompt from "perfect". It cannot tell a strong reviewer from a stronger one, and every difference it can still show is in calibration (hedging), not in detection.
- A few reports guess where the planted defect would be ("the likely trap is a unit mismatch"), so some success may reflect recognising the genre of plan as well as reading it. This cannot be separated here.
- Corpus weaknesses found by the reviewer, for a v3: the migration plan names a column `shipped_at` and adds NOT NULL to it, which invites a design objection that is not in the text; the caller/callee sound plan's test line leaves `main()` uncovered.
- Nothing about the skill's own claims: whether packet discipline, citation checks and adjudication beat a bare prompt, or reduce what reaches an independent reviewer.
- Nothing about Gemini. Comparing a Gemini result with this one is valid only on the same corpus hash.

## Next, if wanted

1. **Use the corpus where it can still discriminate.** The same 40 cases on a smaller model (a cheap run) or a bare-prompt arm would show whether the ceiling is the corpus or the reviewer. This is also the shortest route to the ablation arm, which tests the skill's own claim.
2. **Corpus v3** for a stronger reviewer: defects that need longer chains of inference, distractors that are close to defects, plans where the sound version is subtler, and the two weaknesses above fixed.
3. **The same corpus on a qualified Gemini route**, for a like-for-like comparison.
