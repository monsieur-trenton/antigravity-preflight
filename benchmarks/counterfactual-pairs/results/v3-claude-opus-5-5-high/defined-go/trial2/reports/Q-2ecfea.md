# Review: Orders DB Point-in-Time Recovery Plan

## Blocking issue: retention is too short for the 14-day window

The plan states its own requirement for this, then sets retention below it:

- **Requirement:** restore to any point up to 14 days ago.
- **Plan's own analysis:** with weekly base backups, a 14-day-back target can need a base backup up to **21 days old**, plus all WAL written since.
- **Retention:** base backups and WAL are kept for **7 days**, and the nightly job deletes anything older.

So at any moment the oldest base backup is at most 7 days old, and WAL older than 7 days is gone. Points older than about 7 days cannot be restored. That is roughly half the required window. The plan as written fails its stated objective.

The monthly rehearsal targets 13–14 days back, so it should fail every time. That at least means the gap would be caught. But the plan gives no sign this was expected, and a failing rehearsal does not fix the design.

**Required fix:** retain base backups and WAL for at least 21 days, plus a margin of a day or two for a late or failed Sunday backup. For example:

- Keep base backups for at least 22 days, or keep the last 4 weekly base backups.
- Keep WAL back to the start of the oldest retained base backup, not on a fixed age.
- Make the lifecycle rule depend on the backup chain. It should never delete WAL needed by a base backup that is still retained, and never delete the last base backup that falls before the 14-day boundary.

Shortening the base-backup interval is another option. Daily base backups would need about 15 days of retention, though WAL must still reach back to the oldest needed base backup.

## Parts that work

- **5-minute recovery point:** WAL is archived within 60 seconds, so this target is met. In practice this depends on `archive_timeout` (or a WAL streaming tool) forcing segment switches during low write activity. The "within 60 seconds of being written" wording suggests this is handled. Confirm it is set.
- **Protection from compromised database hosts:** a separate account with write-only, no-overwrite, no-delete access is a sound design. Limiting the lifecycle job's deletes to objects past retention is also good. Once retention is corrected, check that the job's rule is updated with it, so it can't quietly delete objects that are still needed.
- **Rehearsal:** testing a restore near the hardest point of the window is the right target. Consider also checking that the WAL chain has no gaps, and alerting if the Sunday base backup is missing.

## Summary

The design is mostly sound, but the 7-day retention cannot support the 14-day recovery window, and the plan's own 21-day analysis shows this. As written, the plan cannot meet its main requirement.

VERDICT: NO_GO