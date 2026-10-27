# Dev audit, second round: the four rewritten pairs

14 calls to Claude Opus 5.5 through the Claude CLI on the four pairs rewritten after the first audit (N-102a76, N-4aedf1, N-93366f, N-9cc72c), against the rebuilt [dev corpus](../dev/) (manifest `a57b84a6…f61c4`), run by the owner's orchestrator at commit `48e5e14` on 2026-10-27: 8 members, 4 pairs, 2 claim checks; $0.76 and about 3 minutes; every call served `claude-opus-5-5`. **Same auditor, same caveats as [the first round](../dev-audit/README.md): one model of the family that also serves as a reviewer arm, an opinion that a person settles where it disagrees with the oracle.**

[audit-report-combined.json](audit-report-combined.json) is `audit_report.py report` on the first round's ledger followed by this one, so the four pairs are read from the new answers and the other 20 from the old ones (answers to a request the corpus no longer sends are marked stale and ignored).

## Result

| Pair | Round 2 | Reading |
| --- | --- | --- |
| N-4aedf1 (precondition, restore drill) | pass with lines to read | Sound plan recovered as sound, twin as an unestablished fact, the right plan chosen, one edit, the author's claim holds |
| N-93366f (scope, object-storage retention) | pass with lines to read | Sound plan recovered as sound, **twin recovered as a defect**, as the reclassified oracle says |
| N-102a76 (precondition, CI routing) | review | The sound plan is called a defect for a **real inconsistency in a filler line**: line 1 opens a "four-hour" window at 01:00 UTC and line 38 closes it at 06:00 UTC, five hours later |
| N-9cc72c (scope, warehouse load) | incomplete | The sound plan is called a defect for a **real contradiction in a filler line**: line 21 runs the load "across forty threads" against the "confirmed concurrency limit of sixteen" in line 17; the auditor therefore also answered `BOTH` on which plan needs a change. One answer (the twin alone) could not be parsed (`OTHER_PROBLEMS` carried an annotation) and is recorded as a stop, not repaired |

Combined with the 20 unchanged pairs: 7 pass, 15 pass with lines to read, 1 review, 1 incomplete; class recovered for 45 of 47 members that have a clean answer, first-pass agreement 22 of 23 pairs with all answers.

## What it shows

- **The revised hazards did what they were written for.** The stale-scan flaw of N-102a76, the wrong-object scan of N-4aedf1 and the second open items of N-93366f and N-9cc72c are gone; the auditor no longer reports any of them.
- **The remaining faults are a different kind: arithmetic slips in filler lines** (a duration against its start and end time, a thread count against a stated limit). I read both plans before the audit and missed both; the auditor found them. The mechanical checks cannot see them, and they matter, because a reviewer that reads such a line correctly will block a plan that is meant to be sound. This is a limit of the author, not of the design, and the audit is what catches it.
- **The two faulty pairs are re-authored** (owner's earlier decision on flawed pairs), with one more rule in the author template: before answering, check every number that appears twice or bounds another, and make it agree everywhere. Template hash and `run.sh` pin are updated; the 22 other pairs are not touched.
