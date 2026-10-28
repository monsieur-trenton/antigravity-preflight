# Blind audit of the test corpus

268 calls to Claude Opus 5.5 through the Claude CLI on the 184-case sealed test corpus (manifest `a9ec80f2…f8b3a`, the one rebuilt from the authoring bundle), run by the owner's orchestrator at commit `4b8b6ef` on 2026-10-28: $14.80, no safety stops, every call served `claude-opus-5-5`. Same auditor and caveats as [the dev audit](../dev-audit/README.md): one model of the family that also serves as a reviewer arm, an opinion that a person settles where it disagrees with the oracle. **The case text is sealed: the ledgers here are redacted (each free-text answer field replaced by its SHA-256), no attempt directory is committed, and I (the repository session) have not read the plans or the auditor's sentences; a subagent read the sentences and reported abstract categories only.**

## Files

- [audit-answers-redacted.jsonl](audit-answers-redacted.jsonl): the ledger as run. Six member answers were recorded as technical stops (`UNPARSEABLE_ANSWER:BAD_REFS`: commentary in parentheses after a reference).
- [audit-answers-lenient-redacted.jsonl](audit-answers-lenient-redacted.jsonl): those six re-read under the one stated relaxation of `reparse_lenient.py` (held answer hash-checked, parenthetical commentary dropped, nothing else). They replace the same calls in the report.
- [audit-report.json](audit-report.json): the ledgers read against the oracle. [audit-report-claim-rule-v1.json](audit-report-claim-rule-v1.json): the same with the claim rule as first written (see below).

## Result

| | Pairs |
| --- | --- |
| Pass | 14 |
| Pass, with lines for a person to read | 46 |
| Sent to review | **20** |

Class recovered for 145 of 160 members; first-pass agreement **60 of 80 pairs** (0.75, Wilson 0.65 to 0.83). Dev's first pass was 14 of 24 against the original oracle and 20 of 24 against the reclassified one. By family, pairs sent to review: contract_clause 0 of 8, budget_arithmetic 0 of 7, omitted_access_check 1 of 6, open_item_becomes_decisive 1 of 8, scope_authority 1 of 6, config_limit 2 of 8, omitted_measurement 2 of 7, omitted_propagation_window 2 of 7, ordering_dependency 3 of 7, open_item_absorbed 4 of 8, policy_rule 4 of 8.

**The claim rule was changed after the first look at these results, and the change is disclosed.** For a twin made by deleting lines, the author's "nothing in the plan bounds or makes up for it" claim was first counted as contradicted whenever the auditor named any line. The subagent's abstract report showed that in most of those cases (8 of the pairs) the line named was the requirement line, which states what the plan must achieve and so always "implies" the missing fact. The report now counts a contradiction only if the auditor names some other line, and records "rejected on the requirement line only" as a flag. That moves 6 pairs from review to pass-with-read (26 to 20 reviews, 54 to 60 agreeing); the first version is kept as `audit-report-claim-rule-v1.json`.

## What the 20 are, in abstract (subagent's report, categories without content)

- **Sound plans that are not sound, with a checkable reason, the larger group:** a stated number, duration or threshold violating a stated limit (3 pairs); a calendar inconsistency such as a weekday label wrong for its date (2); a role or authority problem such as two titles for one person or a task assigned to a role with no granted authority (3); a consumed item that no earlier line creates or confirms (4, three of them in `ordering_dependency`); a second fact the requirement needs also unestablished (3). The auditor is likely right in these; the dev audit found the same kinds.
- **Likely auditor overreach or arguable:** a conditional limit whose condition is unestablished although the values fit on either reading (1); a stated open item treated as a defect with no credit for a fallback (1); "not one edit" for a single inserted line that does not fully repair the plan (2); past-run evidence judged insufficient as current verification (1).
- **A twin that may not be defective:** two pairs where an abort or discard mechanism makes the missing measurement non-essential, so the auditor calls the twin sound (`omitted_measurement`).
- **One real "not one edit":** a difference that spans two inserted lines (`omitted_propagation_window`).
- **Systematic patterns:** `ordering_dependency` (a used item has no earlier creating or confirming line, in all 3 reviews); `policy_rule` (3 of 4 sound plans really defective via a number or a title); `open_item_absorbed` (a fallback that depends on the same unconfirmed fact, or an open item read as a defect); `omitted_measurement` (an abort path that makes the measurement unnecessary).

## Decision

The 20 are re-authored once, with hazards added to the families where the pattern is systematic (and one more clause in the author template: a weekday label must agree with its date), and re-audited; a pair that is still sent back is dropped and reported, as in dev. The list is [../test-rewrite-list.json](../test-rewrite-list.json). Four of the 20 have a rewording (N-0a7387, N-c86ed8, N-e154ea, N-f41ebe), which must be redone after their wording A. The prompts of the first test batches are rebuilt by the tests from the copies of the template and the families that they ran with ([../test-authoring/tooling-as-run/](../test-authoring/tooling-as-run/)).
