### Advisory Review: Snapshot S01

#### Rationale & Answer to Question Q01
**Question Q01 Answer:** Yes, snapshot S01 contains a blocker supported directly by its own text.

**Analysis:**
- **Requirement & Mechanics:** Line `[S01:1]` mandates that the orders database must be restorable to any point in time from 14 days ago up to 5 minutes ago. Line `[S01:4]` explicitly identifies that because full base backups run weekly (`[S01:2]`), restoring to a point 14 days ago can require a base backup up to 21 days old along with all WAL segments written after it.
- **Direct Contradiction / Blocker:** Line `[S01:5]` specifies that both base backups and archived WAL segments are retained for only 7 days, and a nightly lifecycle job deletes anything older. Because all base backups and WAL older than 7 days are deleted, point-in-time recovery (PITR) to any point between 7 and 14 days ago is impossible.
- **Downstream Failure:** As a direct consequence of this retention policy, the monthly disaster recovery rehearsal described in line `[S01:8]` (rehearsing a restore to a point between 13 and 14 days back) cannot succeed.

The retention policy in line `[S01:5]` directly conflicts with lines `[S01:1]`, `[S01:4]`, and `[S01:8]`, representing a verified blocker.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | S01:5 | Base backups and archived WAL are both retained for 7 days, and a nightly lifecycle job deletes anything older.
