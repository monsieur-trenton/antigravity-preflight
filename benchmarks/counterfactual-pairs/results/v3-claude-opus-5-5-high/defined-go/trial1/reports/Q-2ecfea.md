# Review: Orders DB Point-in-Time Recovery Plan

## Blocking issue: 7-day retention cannot support a 14-day recovery window

The plan contradicts itself:

- **Requirement:** restore to any point from 14 days ago up to 5 minutes ago.
- **Plan's own analysis:** reaching 14 days back can need a base backup up to **21 days old**, plus all WAL written after it.
- **Retention:** base backups and WAL are both kept for **7 days**, and a nightly job deletes anything older.

With 7-day retention, the oldest base backup available is at most 7 days old. The usable window is therefore roughly 0–7 days, and at worst only the time since the most recent Sunday. Any target between about 7 and 14 days back is unrecoverable, so the plan breaks its main stated requirement.

The monthly rehearsal would also fail every time. It targets 13–14 days back, which lies entirely outside the retained data.

**Required fix:** retain base backups and WAL for at least 21 days, plus a margin for job timing, clock skew, and a missed or failed Sunday backup. A failed Sunday backup pushes the needed base backup to 28 days old. A rule like "keep the newest base backup older than 14 days, plus all WAL from it onward" is more precise, but a flat 22–28+ days for both is simpler and safer.

## Other points (not blocking)

- **5-minute RPO:** WAL is archived within 60 seconds, which meets the requirement. Low-write periods can delay segment switches, so set `archive_timeout` (e.g., 60s) so a partially filled segment still gets archived on time.
- **Bucket protection:** Using a separate account where the database hosts can write but not overwrite or delete is good ransomware and accident protection. The lifecycle job is the only principal that can delete, so its rule is the one thing standing between you and data loss. Consider object lock or versioning with a retention floor at or above the corrected retention period, so a misconfigured rule can't wipe needed backups.
- **Monitoring:** Alert on failed base backups, WAL archive lag or gaps, and the age of the oldest restorable point. That way a coverage hole shows up before the monthly drill.
- **Rehearsal:** Testing the 13–14 day edge is a good choice. Once retention is fixed, occasionally also test recent targets and a target just after a base backup, and record the restore time against your RTO.

## Summary

The architecture is sound, but the 7-day retention makes the 14-day recovery requirement impossible. It must be raised to at least 21 days, and preferably more.

VERDICT: NO_GO