The decisive requirement is S01:42: promotion requires zero orphaned records across the 140 million settlement rows. No line before the irreversible promotion at S01:48 establishes that.

- **What the plan does verify:** replication lag reaches zero (S01:32, S01:41), the final log sequence number is applied (S01:39), and writes have stopped in us-east-1 (S01:38).
- **Why that is not enough:** none of these checks is an orphaned-record or referential-integrity check of the settlement rows. Zero lag shows the replica matches the primary, not that the data has no orphans.
- **No contradictions found:** times run in order, credential expiry (05:30) falls after the drill ends (03:15), and the error rates stay within the abort criteria.
- **Minor issue (S01:38):** "zero write transactions in the preceding three minutes" partly covers time before read-only mode began at 02:52. This is loosely worded but not a contradiction.

AUDIT-BEGIN
CLASS: HAS_AN_UNESTABLISHED_FACT
REASON: The plan requires zero orphaned records across the 140 million settlement rows before the irreversible promotion, but no step ever checks or establishes this; only replication lag and log application are verified.
DECISIVE_FACT: A pre-promotion step confirming zero orphaned records across the 140 million settlement rows in the us-west-2 cluster.
REQUIREMENT_LINE: S01:42
REQUIREMENT_DECIDES: YES
OTHER_PROBLEMS: none
AUDIT-END