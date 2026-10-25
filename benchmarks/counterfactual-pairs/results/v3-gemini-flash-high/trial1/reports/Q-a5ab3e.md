### Advisory Review of Snapshot S01

#### Rationale and Answer to Question Q01
Yes, snapshot S01 contains a critical blocker supported directly by its own text.

Line [S01:1] establishes the operational requirement that point-in-time recovery (PITR) for the PostgreSQL database must reach any moment from 14 days ago up to 5 minutes ago. Line [S01:4] correctly notes that because full base backups occur only once per week (each Sunday at 02:00 UTC per [S01:2]), restoring to a point 14 days in the past may require a base backup up to 21 days old along with all WAL segments generated since that backup. Furthermore, line [S01:8] specifies a monthly drill attempting recovery to a moment 13 to 14 days in the past.

However, line [S01:5] defines a retention period of only 7 days for both base backups and archived WAL, with older artifacts purged nightly by a lifecycle job. Because all base backups and WAL segments older than 7 days are deleted, the system cannot recover to any point earlier than 7 days ago. This creates an irreconcilable conflict between the 7-day retention policy in [S01:5] and the 14-day PITR requirement in [S01:1] / [S01:4], ensuring the drill described in [S01:8] will fail.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | 5 | Retention is 7 days for base backups and archived WAL alike, with anything past that age removed by a nightly lifecycle job.
