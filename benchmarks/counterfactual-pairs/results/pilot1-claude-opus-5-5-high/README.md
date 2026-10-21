# Pilot 1: counterfactual pairs, Claude Opus 5.5 through the Claude CLI

Two trials of the frozen 24-case corpus ([../../README.md](../../README.md)), run through [run_pilot_claude.py](../../run_pilot_claude.py). **This is the `claude-cli` route and a Claude model. It says nothing about Gemini 3.8 Flash / High, the skill's qualified runtimes, or the value of the preflight workflow itself** (benchmarks A and F in the [benchmark plan](../../../../docs/benchmark-plan.md)). Nothing here is a general accuracy rate.

![Reviewer verdicts for each sound plan and its changed twin](../../../../docs/figures/pilot1-verdict-matrix.svg)

## Run identity

| | |
| --- | --- |
| Route / model / effort | `claude-cli` / `claude-opus-5-5` / `high` |
| Claude Code version | 2.1.306 |
| Served model | `claude-opus-5-5` in all 48 observations, as reported by the CLI |
| Trials | 2, 24 cases each, one tool-free turn per case, no retries |
| Cost / time | $1.14 in total ($0.67 and $0.47); about 11 s per case |
| Technical stops | 0 of 48 |
| Evidence | [trial1](trial1/), [trial2](trial2/), each with the ledger and the unmodified reports; [score.json](score.json) |

**Integrity checks, run on receipt.** For all 48 observations the saved request is byte-identical to what the frozen corpus and the committed driver produce, the ledger's report hash matches the saved report, the report equals the CLI's `result` field, and the system-prompt hash matches. The run's commit was not recorded; it is inferred (95a4fcd) from those matches, which would not detect a driver change that leaves the request and system prompt unchanged.

## Pre-registered score, unchanged

The scorer and its definitions were frozen before the run. Wilson 95% intervals; the two trials are not independent samples.

| | Trial 1 | Trial 2 |
| --- | --- | --- |
| Pairs discriminated (sound plan clean **and** changed twin correct) | 9/12 (0.47–0.91) | 8/12 (0.39–0.86) |
| False blockers on sound plans | 0/12 (0.00–0.24) | 0/12 (0.00–0.24) |
| Changed plans judged correctly | 10/12 (0.55–0.95) | 10/12 (0.55–0.95) |
| Unsupported VERIFIED findings (gate: zero) | 0 | 0 |
| Verdict identical across trials | 23/24 (0.80–0.99) | |

Per family, trial 1 / trial 2 pairs discriminated: absent vs null 2/2, 2/2; ownership 2/2, 2/2; required coverage 2/2, 2/2; runtime budget 2/2, 2/2; caller/callee 1/2, 0/2; output byte limit 0/2, 0/2.

## Adjudication (post hoc, read the reports behind each number)

The two families that scored badly were adjudicated by reading every report. This reading was done after seeing the scores, which is a researcher degree of freedom; the reasons below rest on the packet text, not on the verdicts.

**Output byte limit: the corpus was defective, not the reviewer.** Both the sound plan and its changed twin received `CHANGES_RECOMMENDED` with two UNVERIFIED RISKs, in both wordings and both trials. Reading the reports:
- The sound plan was not sound. Line 4 claims the summary "stays under 1100 bytes" because values are cut to 64 bytes, but nothing bounds key names or JSON overhead, escaping after truncation can grow a value, and line 5's `len(output)` does not say whether it counts bytes or characters. The reviewer named these gaps in all four sound observations. I wrote that plan; it repeats the flaw of the unbounded control in the [exploratory audit](../../../exploratory-plan-audit/README.md), and [testing-next.md](../../../../docs/testing-next.md) said to bound serialization size in the sound plan.
- The changed twin's oracle expected a BLOCKER. The reviewer identified the oracle's mechanism in all four observations (values up to 900 bytes against a 1500-byte cap) and graded it a RISK, because line 5's assertion turns an overflow into a failed step, not an oversized output, and the packet never says a failed step is fatal. That is a defensible reading of the text. The oracle over-read the packet.

So this family measures nothing about the reviewer, and it is excluded from the adjudicated reading below. The scorer and oracle are not edited, so the pre-registered numbers above stand as run.

**Caller/callee: the strict metric penalised appropriate caution.** The changed twin received a VERIFIED BLOCKER on the decisive line in 4 of 4 observations. The sound plan was never blocked, but 3 of 4 observations got `CHANGES_RECOMMENDED` for an UNVERIFIED RISK that "the only caller is `schedule()`" is asserted without evidence. That follows the [review contract](../../../../skills/antigravity-preflight/references/review-contract.md) (missing context is an unverified concern, not a defect), and the scorer's requirement that a sound plan be fully `NO_BLOCKERS_FOUND` was too strict for a design review.

**The other four families.** Mechanisms were correct and cited at the decisive line; I found no invented evidence. In the runtime-budget family the reviewer computed the required rate (about 22 MB/s from 40 GB in 1,800 s), labelled it an inference, invented no measured throughput, and kept the finding at RISK. That is the behaviour the exploratory audit's reviewer lacked. A minor extra remark in one ownership report (the "tag" is undefined) was accurate.

**Adjudicated reading, labelled post hoc.** Counting a pair as discriminated when the changed twin was judged strictly more severely than its sound twin, across the five valid families: **20 of 20 pair-observations**. Under the same reading the output-byte family is 0 of 4, and that family is the corpus defect described above.

## What this does and does not show

- For this model, prompt and route, on these five families, the reviewer followed the changed fact in every pair-observation, produced no false blocker, no fabricated VERIFIED citation, and handled the missing-evidence case as uncertainty rather than a defect.
- **Ceiling effect.** Most changed twins are visible self-contradictions between two lines of the same snapshot. Success there is the easy case. The corpus does not yet include defects that need cross-line inference, distractors in sound plans, or evidence that is subtly insufficient.
- Six families, 12 pairs and two non-independent trials. A five-family adjudicated count chosen after the fact carries selection risk.
- Nothing about the skill's own claims: whether packet discipline, citation checks and adjudication beat a bare prompt, or reduce what reaches an independent reviewer.
- Nothing about Gemini. The same corpus has not been run on a qualified Gemini route.

## The aborted first attempt

[aborted-wrong-model-id](aborted-wrong-model-id/) is preserved as run: three stops with a wrong model id (`opus-5.5`), an API error before any model served, $0, Claude Code 2.1.294. The driver halted on the third consecutive stop as designed. Its stop code read `CLAUDE_ERROR:success` because the driver labelled errors by `subtype`, which the CLI reports as `success` even on an API error; later commits label by `terminal_reason` (here `api_error`). No case from that attempt was reused.

## Next, if wanted

1. **Corpus v2.** Rebuild the output-byte family (bound keys, escaping and byte measurement in the sound plan; make the twin contradict an explicit contract line); add cross-line-inference defects and distractors; report the strict and the ordinal metric side by side, both fixed before the run.
2. **Ablation arm** (benchmark A): the same cases with a bare prompt versus the full packet and adjudication workflow, which tests the skill's own claim.
3. **The same corpus on a qualified Gemini route**, for a like-for-like comparison.
