# Dev split authoring: the Gemini 3.8 Flash High route writes 24 pairs

The first live use of [the authoring tooling](../author/HANDOFF.md): 27 calls (24 pairs, three of them on a second attempt) through the `flash-high` native route, as `SPLIT=dev`, run by the owner's orchestrator and returned as an archive. **One model as requested (the served model is not attested), one author, one split. This is the dev split: it exists to find what is wrong with the tooling and the cases before the test split is written, and nothing here measures a reviewer.**

## What happened

| | |
| --- | --- |
| Route | `runtime/flash-high`, `gemini-3.8-flash-high` as requested (`servedAttestation: UNAVAILABLE`), `agy` 1.4.1 `16e228cb…f7508`, bound to the v3 Gemini run manifest `d853fee3…01ff5d2` |
| Commit | `49b917fe…` (the orchestrator's record, in [identity.txt](identity.txt)) |
| Calls | 27 in two batches (24 on 2026-10-25, 90 minutes; 3 on 2026-10-26, 12 minutes), zero runtime stops, zero retries inside a call, every receipt `REPORT_RECEIVED_PENDING_ADJUDICATION` |
| Time | 6,113 s of call time; per call a median of 230 s, a range of 124 to 312 s (the probe's one call took 153 s) |
| Size | reports of 15.3 KB on average, at most 23.8 KB (the per-call cap is 28,000) |
| First-attempt failures | 3 of 24: two `RUBRIC_GROUNDED_IN_THE_PLAN` (N-8fbc5c, N-ba0d02), one `NO_ADMISSIONS_OUTSIDE_OPEN_ITEMS` (N-f9a801, an admission in a reference line). All three passed on the second attempt. The failed reports are kept under `calls/` |
| Result | all 24 pairs accepted; the built corpus is [../dev/](../dev/) (48 cases) |

**Checked by me, independently of the orchestrator** (the committed tests recompute all of it): every prompt rebuilds byte for byte from the templates, the assignment and the family; every report hashes to its ledger row and its receipt; every receipt is clean, unretried and bound to the pinned binary; every accepted report passes the mechanical checks again; and the dev corpus is reproduced exactly from the accepted reports.

## What I read, and what it shows

Read by me, the author of the tooling, as the plan requires before any test case is written; the owner has not yet read the pairs. For the eight omitted-precondition pairs I read every line of the sound plan. For the cross-source and decoy pairs I read the whole reference excerpt and, from the plan, the requirement, the edit, the open item and their neighbouring lines, not every filler line (those are covered by the program's checks for admissions, meta words and duplicates, not by reading). The blind audit is the second reader.

- **The mechanics work.** The twins are exactly one edit; positions fall in the assigned thirds; the cross-source references run from 9 to 25 entries and carry deliberate near-name traps (`analytics_pipeline_worker` against `analytics_pipeline_workers`, `clearing-settlement-records` against `clearing-settlements-records`, `catalog_product_v3` against `catalog_products_v3`), which is what the family specification asked for. Notes carry realistic names, owners, times and identifiers.
- **Each dev family is one template, eight times.** All eight omitted-precondition requirements read "the irreversible X will corrupt Y if any row has a null Z", with a scan line pair that the twin deletes; all eight schema-state references list entities one per line with a near-name; all eight scope pairs are "component C is (out of / in) scope", "C's setting is pending", "every in-scope component must have approved settings". A reviewer that learns the template on the dev split will do well on that family's test pairs; the test split has 11 families, so this is a caution on the dev split's usefulness for tuning, not on the test design.
- **A cue in the omitted-precondition sound plans.** The word "irreversible" and a corruption consequence sit on the requirement line in all eight, and in the twin nothing follows the requirement that a reviewer would call a check. That makes the gap easy to see, which is the point of an omission case, but it also means the family may sit near a ceiling. The audit and the cheap Claude arm on dev are where that shows.
- **Possible partial fallbacks to watch in the audit.** N-c42f85 verifies the compaction script's exit code and zero dropped rows after the irreversible step; N-a9e9f9 verifies "zero replication lag" before promotion. Neither establishes the deleted precondition, but a careful reader could call them partial.
- **The scope-family twins are close to a contradiction.** In the twin the plan says component C is in scope, says C's setting is pending, and says every in-scope component must have it confirmed before rollout. Nothing says the approval will not arrive in time, so by the specification this is an unestablished fact (`GO_WITH_CHANGES`), but the authors' own mechanism sentences say it "violates the requirement", and a reader may well call it a defect (`NO_GO`). The audit's class question will show which: if it recovers `HAS_A_DEFECT` for these twins, the class in the family specification is wrong or the twin needs the requirement phrased so that approval before rollout remains possible.

## Files

[identity.txt](identity.txt) (commit, hashes, host, the start and end of each batch and the driver summaries), [calls.jsonl](calls.jsonl) (one row per call with the mechanical results), [accepted/](accepted/) (the 24 unmodified reports), [prompts/](prompts/), [calls/](calls/) (every report, including the three failed ones, with CLI receipt and init record), [CAPABILITIES-RESULT.json](CAPABILITIES-RESULT.json), [DUAL-OFFLINE-QUALIFICATION.json](DUAL-OFFLINE-QUALIFICATION.json). The orchestrator did not commit or push.
