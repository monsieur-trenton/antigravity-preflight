**Rationale**

The snapshot contains one blocker, and its own lines prove it.

- **Retention is too short (line 5).** Line 1 requires point-in-time restore back to 14 days. Line 3 says a restore starts from the latest base backup before the target time and replays WAL forward from it. Line 4 adds that, with weekly base backups, a 14-day-back restore can need a base backup up to 21 days old plus all WAL written after it. Line 5 keeps base backups and archived WAL for only 7 days, and a nightly job deletes anything older. So only about the last 7 days are recoverable, at best, and the 14-day objective in line 1 cannot be met. Because the conflict follows directly from lines 1, 3, 4 and 5, this is a VERIFIED blocker. The fix is to retain at least 21 days of base backups and WAL, or to take base backups more often.
- **The rehearsal would currently fail (line 8).** Every monthly rehearsal targets 13 to 14 days back, which is outside the data line 5 keeps. These rehearsals would therefore expose the gap, but they also never test recent points.
- **No conflict between lines 6 and 7.** The lifecycle job holds delete permission (line 6), while the database hosts cannot overwrite or delete (line 7). These apply to different principals, and the deletion rule is limited by age, so the lines do not contradict each other.
- **The 5-minute target is consistent with archiving.** WAL is archived within 60 seconds (line 2), which fits the 5-minute recovery point in line 1.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | 5 | Base backups and archived WAL are both retained for 7 days, and a nightly lifecycle job deletes anything older.
FINDING: NOTE | VERIFIED | 8 | Each month a restore to a randomly chosen point between 13 and 14 days back is rehearsed on a scratch instance.