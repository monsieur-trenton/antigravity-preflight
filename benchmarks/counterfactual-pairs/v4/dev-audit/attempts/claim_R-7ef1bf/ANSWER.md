The claim holds: no line checks the 140 million settlement rows for orphaned records before the promotion.

- **S01:42 states the requirement but does not check it.** It says promotion "requires zero orphaned records across the 140 million settlement rows." Nothing in the plan carries out that requirement.
- **The replication checks do not cover orphans.** S01:14, S01:22, S01:26, S01:32, S01:39 and S01:41 confirm lag and log-sequence application. Zero lag only shows the replica matches the primary. If the primary already holds orphaned rows, a perfect replica holds them too.
- **The snapshot does not cover them either.** S01:47 takes a storage snapshot, which preserves state but does not inspect it. The promotion in S01:48 is called irreversible. The snapshot also does not stop the downstream corruption, because S01:55 starts settlement reconciliation jobs against the newly promoted primary without any validation in between.
- **Pausing consumers does not cover them.** S01:44 stops reconciliation consumers before the promotion. That only delays reconciliation, and S01:53 and S01:55 restart it.
- **No other line runs a query, constraint validation or dry run** on the settlement data. There is no S02.

AUDIT-BEGIN
CLAIM_HOLDS: YES
CONTRADICTING_LINES: none
AUDIT-END