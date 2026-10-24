# Review Report for Plan Snapshot S01

## Question Q01 Assessment
**Does the snapshot contain any blocker supported by its own text?**
**Yes.** The plan contains a direct internal contradiction between its recovery requirements and its retention lifecycle policy that creates an operational blocker.

## Rationale & Findings Analysis

1. **Recovery Requirement vs. Retention Policy Conflict:**
   - **Requirement:** Line `[S01:1]` establishes the core recovery requirement: *"The orders PostgreSQL database must be restorable to any point in time from 14 days ago up to 5 minutes ago."*
   - **Operational Reality:** Line `[S01:4]` explicitly deduces the prerequisite history needed to achieve this requirement: *"Since base backups are weekly, reaching a point 14 days back can require a base backup up to 21 days old together with all WAL written after it."*
   - **Blocker:** Line `[S01:5]` defines a retention limit and lifecycle deletion rule that directly contradicts the requirement: *"Base backups and archived WAL are both retained for 7 days, and a nightly lifecycle job deletes anything older."* Line `[S01:6]` confirms that the lifecycle job deletes matching objects older than this 7-day limit.
   - **Impact:** By deleting base backups and archived WAL older than 7 days, it is mathematically and technically impossible to restore to any point in time between 7 and 14 days ago (which requires up to 21 days of base backup and WAL history). Furthermore, the monthly recovery drill described in line `[S01:8]` (*"Each month a restore to a randomly chosen point between 13 and 14 days back is rehearsed on a scratch instance."*) is guaranteed to fail due to missing base backups and WAL segments.

Because this failure is completely verified by the snapshot's own explicit statements, it constitutes a verified blocker.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | S01:5 | Base backups and archived WAL are both retained for 7 days, and a nightly lifecycle job deletes anything older.
