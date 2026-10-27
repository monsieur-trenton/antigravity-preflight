# Dev audit, third round: N-102a76 and N-9cc72c

7 calls (4 members, 2 pairs, 1 claim check) to Claude Opus 5.5 through the Claude CLI on the two pairs rewritten a second time, against the rebuilt [dev corpus](../dev/) (manifest `e965c0b8…fae881`), run by the owner's orchestrator at commit `5627208` on 2026-10-27: no stops, $0.35, every call served `claude-opus-5-5`. Same auditor and caveats as [round one](../dev-audit/README.md). [audit-report-combined.json](audit-report-combined.json) reads the three rounds' ledgers in order, so each pair is read from its latest answers and the others from round one.

## Result

- **N-9cc72c passes.** Sound plan recovered as sound ("the only unconfirmed value belongs to the checkpoint coordinator, which S01:28 explicitly places out of scope"), twin recovered as a defect, the right plan chosen, one edit. The auditor lists lines 16 and 17 as "other problems" in both members; they are the lines I flagged in the authoring write-up (the existing threshold of eight thousand writes against "unconfirmed"), a person's read, not a fault.
- **N-102a76's twin is recovered** as an unestablished fact and the right plan is chosen with one edit, and the author's claim holds. **Its sound plan is not sound.** The auditor says the smoke test is submitted "through the CI pipeline" at 03:15 (line 27) while the orchestrator is drained to all new submissions until 03:26 (line 32) and the runners are paused until 03:20 (line 29), so the step cannot run as written. I checked the three lines: it is right. This is a third kind of slip in filler: a step ordered against a dependency, after a duration mismatch in the first rewrite and the stale scan in the original.

Whole dev corpus after this round: 7 pairs pass, 16 pass with lines to read, 1 review (N-102a76); class recovered for 47 of 48 members; first-pass agreement 23 of 24 pairs.

## N-102a76 dropped; the dev corpus is settled

N-102a76 failed three times on a second fault in a filler line of its sound plan (the stale scan of the original, the four-hour window that closes after five, the smoke test submitted through a drained orchestrator); the twin was recovered correctly each time. **The owner decided on 2026-10-27 to drop it** rather than author it a fourth time ([dev-drops.json](../dev-drops.json)). The dev corpus is [../dev](../dev/) with **23 pairs and 46 cases** (manifest `1e89ac9d…82975`): 7 omitted-precondition, 8 cross-source, 8 scope.

On the final corpus, read from each pair's latest answers ([audit-report-final-dev.json](audit-report-final-dev.json)): 7 pairs pass and 16 pass with lines for a person to read; none is sent to review; class recovered for 46 of 46 members; first-pass agreement is 23 of 23 pairs. **That figure is the agreement after rewriting or dropping the pairs that disagreed, not a first-pass rate**: the first pass, before any rewriting, agreed on 14 of 24 pairs against the original oracle and on 20 of 24 against the reclassified one. Four pairs needed a second authoring, two of those a third, and one was then dropped.

What this says about authoring at scale, for the test split: of 24 pairs written once, 4 carried a real second fault in the sound plan; of the 4 rewrites, 2 carried a new slip (arithmetic or sequencing errors in filler lines, which I had read and missed); of the 2 rewritten again, 1 carried another. A test split of 80 pairs should be planned for roughly the same fraction, with the audit's review decisions rewritten or dropped, and the dropped pairs reported.

## The owner's spot check

A second sample of six pairs, disjoint from the six of the agent reading and drawn with `audit_report.py spot --corpus ../dev --exclude N-c42f85,N-8fbc5c,N-d0d08d,N-3f18f1,N-e889b3,N-90d970 --fraction 0.25`, goes to the owner without the key or any audit answer. The index (which plan is the twin) is not committed until the owner has answered.
