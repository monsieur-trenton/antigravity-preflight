# Review: Orders DB Point-in-Time Recovery Plan

## Blocking issue: retention is too short for the stated recovery window

The plan states its own requirement: reaching a moment 14 days back may need a base backup up to **21 days old**, plus all WAL since that backup. Retention is **7 days** for both base backups and WAL, so the lifecycle job deletes that data long before it is needed.

The real recovery window is worse than 7 days. It shrinks over the week:

- **Sunday, just after 02:00 UTC:** the new backup has just finished. The previous one is about 7 days old and due for deletion. You can reach nearly 7 days back.
- **Saturday:** the newest backup is about 6 days old. Its predecessor is about 13 days old and was deleted days ago. You can reach only about **6 days** back.
- **Sunday, just before 02:00:** the window drops to roughly **0 to 7 days**, depending on exactly when the nightly job ran.

Anything earlier than the oldest surviving base backup cannot be recovered. This is far from the 14 days the plan promises.

**The monthly drill will fail every time.** Its targets are 13 to 14 days back, and there is never a base backup that old. The drill is designed well, because it would catch exactly this problem. But as written, the plan cannot pass its own test.

## Required changes

1. **Keep base backups for at least 21 days, plus a margin.** The margin should cover backup run time, the timing of the nightly job, and one missed or failed weekly backup. 28 to 35 days is reasonable. Without allowing for a failed backup, a single bad Sunday breaks the 14-day guarantee.
2. **Keep WAL back to the start of the oldest base backup you keep.** Base backups are useless without the WAL from their start point onward. The simplest approach is to give WAL the same or longer retention. A better approach is to delete WAL by reference to the oldest retained backup's start LSN, rather than by age alone.
3. **Only delete a backup once a newer one is confirmed usable.** Never let the job remove the oldest base backup unless enough newer backups exist and have been verified to cover the 14-day window.

## Recommended improvements

- **Check the 5-minute recovery point.** WAL lands within 60 seconds of a segment being *completed*. A segment is only completed when it fills up or a switch is forced. On a quiet database, a partly filled segment could hold recent commits for longer than 5 minutes. Set `archive_timeout` (for example, 60 seconds), or stream WAL with `pg_receivewal`, so the 5-minute target holds at low traffic.
- **Monitor archiving.** Alert on `pg_stat_archiver` failures and on archive lag. Alert if the weekly base backup is missing or late.
- **Know the earliest valid target for each backup.** A base backup can only be restored to points after its end-of-backup position, not its 02:00 start.
- **Widen the drill.** Sometimes target about 5 minutes ago, and sometimes target a point just after a Sunday backup. This tests both ends of the window. Record pass/fail and alert on failure.
- **Restrict the lifecycle job.** Isolation is good as designed: hosts can only add objects and the bucket is in its own account. But the lifecycle job's delete permission is the remaining risk. Consider object lock or versioning with a minimum hold equal to the new retention, so a mistaken rule cannot delete data that is still needed.

## Summary

The architecture is sound: continuous WAL archiving, weekly base backups, a separate account, add-only access from hosts, and a regular drill. However, the 7-day retention contradicts the 14-day recovery requirement and the plan's own 21-day reasoning. As written, it will fail both its recovery goal and its drill.

VERDICT: NO_GO