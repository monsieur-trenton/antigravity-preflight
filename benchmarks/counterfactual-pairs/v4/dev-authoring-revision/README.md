# Dev split, second batch: the four pairs the audit sent back, rewritten

Four calls (N-102a76, N-4aedf1, N-93366f, N-9cc72c) through the same `flash-high` route, in a new root, after the family hazards were revised and the scope families reclassified (see [the audit write-up](../dev-audit/README.md)). Run by the owner's orchestrator at commit `ae2533e` on 2026-10-27 and returned as an archive. **One model as requested (served model unattested), one author. Nothing here measures a reviewer.**

## What happened

- Four calls, four reports, **all accepted at the first attempt**; zero stops, zero retries inside a call, every receipt `REPORT_RECEIVED_PENDING_ADJUDICATION` and bound to the pinned binary. Per call 220, 329, 432 and 286 seconds (21 minutes in all).
- The first offline-qualification attempt of the orchestrator stopped (`OFFLINE_RUN_1_STOPPED`, no model call) at a load average of 9 on 4 cpus; the rerun in a fresh root (`/tmp/v4author-dev3`) after the machine had settled passed. The hand-off now says to wait for the load to settle.
- Checked by me (the committed tests recompute it): the four prompts rebuild with the revised hazards and hash as sent, the reports hash to the ledger and receipts, and each passes the mechanical checks again.
- The accepted reports replace the first batch's four in the dev corpus; the other 20 are untouched. `build_corpus.py --accepted` now takes several directories, a later one replacing the same pair. The rebuilt corpus is [../dev](../dev/) (manifest `a57b84a6…f61c4`); the case ids do not change, so the audit now marks any earlier answer for these four pairs as **stale** (its request hash is not what the corpus now sends) and counts the pair as incomplete until it is re-audited.

## What I read

All 38 and 44 lines of the two omitted-precondition plans, and the requirement, edit, open-item and neighbouring lines of the two scope plans plus every line of the plan that mentions confirmation or approval.

- **N-102a76** now takes a write lock on the catalog (line 6) before the integrity scan (line 7, the deleted line), and nothing writes to it before the irreversible compaction (line 23): the stale-scan flaw is gone. **N-4aedf1** scans the drill target itself after the log replay (lines 5 and 9, the deleted pair), the object the constraint-enforcing script runs on. Neither has a later line that checks foreign keys or referential integrity, so the twin leaves the precondition unestablished. Lines 15 and 23 of N-4aedf1 (bloat analysis, index consistency) are not the precondition.
- **N-93366f** states in line 25 that the retention days and replication of the other three prefixes are fully confirmed, and the only open item is the legal-hold prefix (line 41, "pending signoff until Friday afternoon"), which line 48 puts out of scope; the twin puts it in scope, and the same plan executes the policy that night (go/no-go at 22:15, verification at 22:35), so the twin contradicts its own requirement (line 51) from its own lines. **N-9cc72c** is built the same way: every parameter is confirmed except the secondary checkpoint compaction interval ("pending vendor validation tomorrow afternoon", line 8), and the twin brings that service into tonight's run.
- Both scope plans now carry exactly one open item. Whether the auditor agrees is the re-audit's question.

## Files

[identity.txt](identity.txt), [calls.jsonl](calls.jsonl), [accepted/](accepted/), [prompts/](prompts/), [calls/](calls/) (report, CLI receipt and init record per call), [CAPABILITIES-RESULT.json](CAPABILITIES-RESULT.json), [DUAL-OFFLINE-QUALIFICATION.json](DUAL-OFFLINE-QUALIFICATION.json).
