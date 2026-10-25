# Plan Review: Snapshot S01 (orders PostgreSQL PITR)

**Rationale**

The snapshot contains a blocker that its own text supports.

- **Blocker (retention is too short).** Line 1 requires recovery to any moment up to 14 days back. Line 3 says recovery starts from the most recent base backup before the target moment. Line 4 says a 14-day target may therefore need a base backup up to 21 days old, plus all WAL since then. Line 5 deletes both base backups and archived WAL after 7 days. Under that rule, no target older than about 7 days can be recovered. The plan cannot meet its own objective. This is VERIFIED from lines 1, 3, 4 and 5. Retention needs to be at least 21 days for base backups and for the WAL that follows them.
- **Risk (the drill will fail).** Line 8's monthly drill targets 13 to 14 days back. Under line 5's retention, the data for those targets will already have been deleted. So the drill will fail as written. It also never tests the recent end of the window (5 minutes back). This is VERIFIED as a consequence of the text.
- **Note (WAL timing assumption).** Line 2 says segments land within 60 seconds of being written. The snapshot does not say whether segment switching (for example, an archive timeout) makes sure a segment is actually completed within 5 minutes during low write activity. Without that, the 5-minute limit in line 1 may not hold. The snapshot does not let me check this, so it is CANNOT_CHECK.
- **No defect found in lines 6 and 7.** Line 6 limits deletion to objects past the retention age. Line 7 makes database host access add-only in a separate account. Both are consistent with the rest of the plan.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | 5 | Retention is 7 days for base backups and archived WAL alike, with anything past that age removed by a nightly lifecycle job.
FINDING: RISK | VERIFIED | 8 | A monthly drill recovers a scratch instance to a random moment 13 to 14 days in the past.
FINDING: NOTE | CANNOT_CHECK | 2 | WAL is shipped to the archive continuously, with every segment landing within 60 seconds of being written, alongside a full base backup each Sunday at 02:00 UTC.