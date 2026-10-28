# Test split authoring: what happened, and what is committed

The Gemini 3.8 Flash High native route wrote the 80 pairs and 12 rewordings of the test split of corpus v4 ([author hand-off](../author/HANDOFF.md)), run by the owner's orchestrator on 2026-10-27 and 2026-10-28 and returned as an archive. **The case text is sealed and is not in this repository: only the ledger, the receipts and the SHA-256 of every file of the built corpus are. One model as requested (served model unattested), one author, one split. Nothing here measures a reviewer.**

## What happened

| | |
| --- | --- |
| Route | `runtime/flash-high`, `gemini-3.8-flash-high` as requested (`servedAttestation: UNAVAILABLE`), `agy` 1.4.1 `16e228cb…f7508`, bound to the v3 Gemini run manifest `d853fee3…01ff5d2` |
| Calls | 109: 97 authoring calls for 80 pairs, 12 rewordings. Per call a median of 255 s (a rewording 283 s), 8.0 hours of call time in all, reports at most 23.5 KB |
| Wording A | all 80 accepted; 71 of the 97 calls were accepted when made |
| Wording B | all 12 rewordings accepted at the first attempt, none failed a check |
| Runtime stops | 4 `UNQUALIFIED_STEP` stops (the `agy` runtime reported an `error_message` event): N-3bf296, N-7f61bb, N-a86988 and N-a91e58, a rate of 4 in 109 calls (against 1 in 128 in the v3 Gemini run); each pair that stopped was authored on a later attempt |
| Failed checks | 22 reports: 13 `RUBRIC_GROUNDED_IN_THE_PLAN`, 3 `NO_ADMISSIONS_OUTSIDE_OPEN_ITEMS`, 3 `ORACLE_REFS_IN_RANGE`, 2 `CITES_SURVIVE_AND_COVER_THE_EDIT`, 2 `LINE_SHAPE` |
| The checks changed during the run | the first batches showed two of my rules were wrong, not the reports: the rubric must be grounded in the plan (three corrections: gap families, then every family needs only one group, which was the main cause of failure), and a cited line that a deletion removes is dropped from the citations instead of failing the report. Nine pairs held a report that failed only the old rule and were accepted by re-applying the corrected checks to the held report, with no further call (`recheck.py`): N-0338d1, N-16fb50, N-2e3b2d, N-9123f1, N-920e4a, N-acf6ba, N-af992a, N-c86ed8, N-d50fec |
| A runtime stop used up an attempt | for N-a91e58 (first attempt failed a check, second lost to a stop) until the rule was changed so that a stop does not count |

The identity record `identity.txt` is written at the host stage and names the commit of that moment (`33e1fcb`); the checker, `author.py` and `run.sh` were corrected during the run (commits `5e0a5f6`, `c12751c`, `1774079`, `4b8b6ef`), so per-row checker versions are not recorded for the batches before the corrections. The held-report re-check should have written `rechecks.jsonl`, which the bundle script did not copy (it does now); it is asked for separately.

## Checked by me, independently of the orchestrator

From the returned archive, with the committed tests recomputing the checkable parts: every author prompt rebuilds byte for byte from the assignment, the family and the domain (and the 12 reword prompts from the accepted reports, checked outside the repository); all report hashes match the ledger; every receipt is clean, unretried and bound to the pinned binary, the four stops named; every accepted wording-A report passes the mechanical checks as they now stand and every accepted rewording passes the reword checks; the nine re-checked pairs' accepted files are byte-identical to their held last report; and **rebuilding the corpus here from the accepted reports gives the manifest SHA-256 `a9ec80f2…f8b3a` that the orchestrator built and is auditing**.

## What is committed

[calls.jsonl](calls.jsonl) (one row per call with the mechanical results, structural details such as line numbers, and the receipt summary), [receipts/](receipts/) (the CLI receipt of every call), [identity.txt](identity.txt), [CAPABILITIES-RESULT.json](CAPABILITIES-RESULT.json), [DUAL-OFFLINE-QUALIFICATION.json](DUAL-OFFLINE-QUALIFICATION.json) and [sealed-manifest.json](sealed-manifest.json): the SHA-256 of every packet and oracle file of the 184-case corpus, of the accepted report of every pair and rewording, and of the assignments, with no text. Not committed, by design: the reports, the prompts, the packets and the oracle.

## Class mix of the test split as built

Wording A twins by kind and class: cross-source 24 defects; omitted unknown 20 gaps; single-source defects 20; decoy pairs 8 defects (`open_item_becomes_decisive`) and 8 gaps (`open_item_absorbed`). That is 52 defect twins and 28 gap twins, not the 44 and 36 the plan first counted, because the owner reclassified the first decoy family as a defect after the dev audit.
