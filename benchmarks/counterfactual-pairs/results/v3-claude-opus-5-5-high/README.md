# Held-out corpus v3 on Claude Opus 5.5: skill-style, defined verdicts, and the optional-suggestions sentence

Six runs (three arms, two trials each) of the frozen 64-case corpus v3 ([../../v3/README.md](../../v3/README.md)) through [run_pilot_claude.py](../../run_pilot_claude.py), as [the run preregistration](../../v3-run/PREREGISTRATION.md) fixes it: the `skill` arm (the skill-style prompt and numbered packet with a structured report), the `defined` arm (a plain request plus five lines defining the verdicts) and the `defined-go` arm (the defined arm plus one sentence saying optional suggestions that only make a working plan more robust are not changes it needs). **One model, one route (the Claude CLI, tools disabled, not the qualified native containment), one corpus written and audited by Claude, two non-independent trials per arm. Nothing here is a general accuracy rate.**

![Corpus v3: verdict mix for four reviewers](../../../../docs/figures/v3-four-reviewers.svg)

## What was found, in five sentences

On this held-out corpus the sentence **replicated its gain on sound plans** (64 of 64 judged `GO`, against 23 of 64 for the defined arm and 34 of 64 for the skill-style arm) and **kept every defect twin blocked** (32 of 32 in all three arms), but **the evidence-gap cost it showed on v2 did not appear in the form preregistered**: the sentence arm judged 10 of 32 evidence-gap twins `GO_WITH_CHANGES` against the defined arm's 6 (not significant, p = 0.29), because both arms mostly judged them `NO_GO` (21 and 26 of 32), and only one observation of 32 was waved through as `GO`. The skill-style arm is the best of the three at the evidence-gap twin (24 of 32 `GO_WITH_CHANGES`, 8 overclaimed as blockers, none waved through) but hedged 30 of 64 sound plans, so on the strict pair metric the sentence arm is ahead (42 of 64 against 26 of 64 and 12 of 64). The dominant failure on the Claude route is therefore not missing the gap but **ruling a correctly named gap a blocker**: every one of the nine overclaims I read named the unestablished fact and asked for the same measurement the correct reports asked for, and differed only in the verdict. No arm produced a technical stop or a safety interruption, and no sound plan was ever judged `NO_GO`.

## Run identity and integrity

| | |
| --- | --- |
| Route | `claude-cli`, tools disabled, one `claude -p` turn per case from an empty directory, zero retries |
| Model | `claude-opus-5-5` (requested and **served**, in all 384 CLI outputs), effort `high` |
| CLI | Claude Code 2.1.306, binary SHA-256 `520bc6c1…0cfe` (the binary of every earlier arm) |
| Corpus / run manifest | v3 `1ad68528…4202` / `3751f9ac…2f6a`, stamped on every ledger row; arm manifests bare `35d7ea8d…`, defined `60f92686…`, defined-go `b628683f…` |
| Run commit | `dba5b6a7a4374fb11455192bbfd0cfece5cdb85e` (the head of this branch when the run was prepared) |
| Host | `john-laptop`, Linux Mint 22.3, kernel 7.0.0-38 |
| Order and times | the preregistered order, one sitting, 2026-10-23 22:03 to 2026-10-24 00:00 PDT (6 runs of 17 to 22 minutes) |
| Cost | **$13.72** in total (skill $4.81, defined $4.70, defined-go $4.21); the largest single case $0.066 against the $5 cap, which never bound. Above the brief's estimate of about $10 (range $9 to $13) |
| Technical stops | 0 of 384; zero safety interruptions, permission denials and error flags; one turn each |
| Evidence | per arm and trial: `responses.jsonl`, `reports/<case>.md` (unmodified), `outputs/<case>.json` (the CLI result), `requests/<case>.txt`; [verify.json](skill/verify.json) per arm; [adjudication.json](adjudication.json) (written before any metric); [score-skill.json](score-skill.json); [analysis.json](analysis.json); [analysis-gemini-vs-claude-skill.json](analysis-gemini-vs-claude-skill.json); [human-reading.json](human-reading.json); [orchestrator-identity.txt](orchestrator-identity.txt) |

**Checked by me, independently of the orchestrator**, with the committed `verify_run.py` on each arm's returned working directory (both trials) against corpus v3 and the run manifest: 64 rows per trial in the frozen order, every saved request equal to what the frozen prompt and corpus produce, every report hash equal to its ledger row, the stamp and run-manifest hash on every row, every served model the requested one, no stop. Each arm: `failures: []`. The orchestrator did not commit, push or edit anything, and its identity record names the manifest hashes that the repository holds.

## The three primary rates, as run

Wilson 95% intervals; the two trials of a case are not independent, so the intervals are narrower than the truth. All 384 observations have a verdict.

| Rate | `skill` | `defined` | `defined-go` |
| --- | --- | --- | --- |
| Sound plans judged `GO` (64) | 34 (0.411–0.648) | 23 (0.253–0.482) | **64** (0.943–1.000) |
| Defect twins judged `NO_GO` (32) | 32 (0.893–1.000) | 32 | 32 |
| Evidence-gap twins judged `GO_WITH_CHANGES` (32) | **24** (0.579–0.867) | 6 (0.089–0.353) | 10 (0.180–0.486) |
| Strict pair discrimination (sound plan `GO` **and** twin right) (64) | 26 (0.295–0.529) | 12 (0.111–0.300) | **42** (0.534–0.761) |
| Ordered pair discrimination (64) | 39 | 34 | **42** |
| Sound plans hedged / blocked | 30 / 0 | 41 / 0 | 0 / 0 |
| Evidence-gap twins overclaimed (`NO_GO`) / waved through (`GO`) | 8 / 0 | 26 / 0 | 21 / 1 |
| Gap named but dismissed (of the `GO` twins) | 0 of 0 | 0 of 0 | 1 of 1 |
| Verdict follows the finding | 32/32 | 32/32 | 32/32 |
| Verdict identical across trials (64 cases) | 58 | 55 | 60 |
| Cost | $4.81 | $4.70 | $4.21 |

For the skill-style ledger, the finding-level score (`score.py --corpus v3`): strict pairs 14/32 and 13/32, false blockers 0 of 32 in each trial, hedged sound plans 15 and 15 of 32, changed twins right 29/32 and 28/32, **unsupported VERIFIED findings 0 and 0** (the preregistered gate).

Paired comparisons on matched (case, trial) units, exact two-sided sign test (units that favour the first arm only, the second only; p):
- `defined` against `defined-go`: sound plans `GO` 0 / 41, p < 0.0001; defect twins 0 / 0; evidence-gap `GO_WITH_CHANGES` 2 / 6, p = 0.29; strict 1 / 31, p < 0.0001; ordered 1 / 9, p = 0.022.
- `skill` against `defined-go`: sound plans `GO` 0 / 30, p < 0.0001; evidence-gap `GO_WITH_CHANGES` 15 / 1, p = 0.0005; strict 4 / 20, p = 0.0015; ordered 4 / 7, p = 0.55.
- `skill` against `defined`: sound plans `GO` 16 / 5, p = 0.027; evidence-gap `GO_WITH_CHANGES` 18 / 0, p < 0.0001; strict 16 / 2, p = 0.0013; ordered 5 / 0, p = 0.0625.

Per family, every defect twin was blocked in every arm and trial. The sentence arm judged all four sound plans `GO` in every family; the skill-style arm hedged every sound plan of `cert_rotation`, `credential_logging`, `payload_limit`, `rollback_window`, `storage_access` and `unique_constraint` and three of four of `backup_window`. The evidence-gap twins the sentence arm judged correctly came from `storage_access` (3 of 4, and the one `GO`), `unique_constraint` and `capacity_headroom` (3 each) and `rate_limit_quota` (1); it judged no `payload_limit`, `rollback_window`, `retry_idempotent` or `upgrade_compat` twin correctly (all 16 observations were `NO_GO`).

## Preregistered labels and hypotheses

Labels (`labels()` in [analyze.py](../../v3-run/analyze.py), fixed in advance): **sound-plan gain: replicated**; **evidence-gap cost: not detected**; **defect twins: held**; skill-style against the sentence arm: **skill-style better** on evidence-gap `GO_WITH_CHANGES`, **sentence arm better** on sound-plan `GO`. The "not detected" label is the preregistered one and is weak evidence (32 matched units); read with the table, it hides that the sentence arm is not good at the evidence-gap twin either, only differently bad from v2.

1. **The sentence arm judges more sound plans `GO` than the defined arm: supported** (64 against 23).
2. **It judges defect twins `NO_GO` as often: supported** (32 of 32 each).
3. **It judges fewer evidence-gap twins `GO_WITH_CHANGES` than the defined arm: not supported** (10 against 6, the opposite direction, p = 0.29). The v2 cost, three of four runtime-budget twins waved through, appears in v3 as one `GO` of 32. The preregistration's reading, that v2's plan had an absorbing fallback and v3's do not, is consistent with this but one observation cannot separate it from chance; the larger effect is the overclaim to `NO_GO` in both arms.
4. **The skill-style arm judges evidence-gap twins `GO_WITH_CHANGES` at least as often as either other arm and sound plans `GO` less often than the sentence arm: supported** (24 against 6 and 10; 34 against 64).

## Human reading, as preregistered

By the corpus author, after the scores ([human-reading.json](human-reading.json) has the cases and the rules).

- **The one evidence-gap twin judged `GO`** (`defined-go`, trial 2, `storage_access` A): the report names the unverified write access as the "main risk", describes the cost of failure, recommends a test, an alert and a fallback, and then calls them "optional, but cheap and worth doing" and "steps that make the plan more robust": the v2 mechanism, one observation of 32. The same case under the same arm was `GO_WITH_CHANGES` in trial 1.
- **No defect twin lacked `NO_GO` and no sound plan was `NO_GO`.**
- **Ten sound plans the skill-style arm hedged and the sentence arm judged `GO`** (one per hedged family): no blocker and no invented evidence; every hedge is a RISK or NOTE about what the plan does not prove. Several are defensible residual gaps (an unevidenced "single code path" claim, a 1 KB write test against a 30 GB write, a missed weekly backup against the retention margin); some are speculation beyond the text. The skill-style prompt invites an inventory of what is unproven, and this reviewer provides one.
- **26 correct evidence-gap twins** (10 skill-style, 6 defined, 10 defined-go): every one named the unestablished fact, tied it to the plan's stated requirement and the cost of being wrong, said it is a risk and not a proven defect, and asked for a measurement or confirmation.
- **Nine overclaimed twins** (beyond the preregistration; three per arm): the reviewer names the gap correctly and then rules it a blocker. The skill-style reports write "I am not claiming the callers will break" and then "the blocker is narrower: the plan ships against a requirement it admits is unverified", with a VERIFIED or UNVERIFIED BLOCKER on the line that states the gap. The verdict-only reports add mechanisms the text does not state (a column drop that rewrites 400 GB, lock queues) and conclude the plan should not ship. Each asks for the same check as the correct reports; the verdict is the only difference. These are not unsupported VERIFIED findings in the preregistered sense (the cited line does say what is quoted), which is why the gate is zero beside them.

## Beside the Gemini run

The same corpus, one trial pair each, the Gemini 3.8 Flash High native route ([results](../v3-gemini-flash-high/README.md)) against the Claude skill-style arm, matched on (case, trial) units: sound plans `GO` 27 units to 0 (p < 0.0001), evidence-gap `GO_WITH_CHANGES` 8 to 0 (p = 0.0078), defect twins 0 to 0, strict pairs 35 to 0. **This is a difference between two routes as run, not between models**: different CLI, different wrapper and report format, different days, a different served-model guarantee (Claude's served model is attested, Gemini's is not). The Gemini reports were short; the Claude reports are long and list what the plan does not prove, which is where its hedges and overclaims come from.

## What this does and does not show

- **Supported:** on a held-out corpus the one-sentence arm keeps sound plans clean and defects blocked (the gain and the hold replicate); the skill-style arm discriminates the evidence-gap twin better than either plain-request arm; none of the three prompts lets a stated unknown through at more than 1 observation in 32, and none blocks a sound plan.
- **Not supported:** that the sentence "costs" the evidence-gap twin on this corpus by waving it through. The Claude reviewer's failure on a stated unknown is to call it a blocker, in the skill-style arm too (8 of 32), and the sentence does not repair that.
- **Not shown:** that any of this transfers to the skill's real workflow (packets, citation check, adjudication), to Gemini under these prompts, or to unknowns that the plan does not write down: in all eight evidence-gap families the twin states the unknown in one sentence, so the corpus tests what a reviewer does with a stated unknown. Claude wrote and audited the corpus, and the sentence was designed on v2 by the same author.
- **Caveats:** one model; the Claude CLI is configuration isolation, not the qualified containment; two trials of the same cases; the defined arms use a plain request and the verdict-only metric, the skill-style arm a structured report, so "arm" differences are prompt-bundle differences, not one sentence apart except for `defined` against `defined-go`; cost and wall time above the estimate.

## Next, if wanted

1. **Run the skill-style prompt plus the sentence** (or the defined-verdict definition without the sentence) on the Claude route, to ask whether a verdict-calibration line can cut the 8 overclaimed twins and the 30 hedged sound plans without the `GO` cost: this is the question these three arms point at, and none of them answers it. (Since run: see the [skill-go results](../v3-skill-go-opus-5-5-high/README.md).)
2. **A corpus where the unknown is not written down** and where a premise from outside the snapshot decides, since both reviewers have now hit the ceiling or the stated-unknown limit of v3.
3. **Benchmarks A and F in the [benchmark plan](../../../../docs/benchmark-plan.md)**: this measures verdict calibration of a reviewer on a snapshot, not what the workflow gives an independent reviewer.
