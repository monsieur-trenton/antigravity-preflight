# Review: Orders PostgreSQL Point-in-Time Recovery Plan

**The 7-day retention cannot support the 14-day recovery requirement.** The plan states the problem itself and then sets retention too short to cover it.

## Blocking issue: retention is too short

- **The plan's own math:** reaching a point 14 days back can require a base backup up to 21 days old, plus all WAL written after it.
- **The retention setting:** base backups and WAL are kept for only 7 days, and the nightly lifecycle job deletes anything older.
- **The result:** you can restore to roughly 7 days back at most, and sometimes less (see below). Every target between about 7 and 14 days back is unrecoverable, so the plan breaks the requirement it states.
- **The rehearsal will fail every time.** It targets 13 to 14 days back, and by then the needed base backup and WAL have already been deleted. The rehearsal is a good control and will surface the problem quickly. As written, though, every rehearsal fails.

## Secondary issue: gaps even inside 7 days

With weekly base backups and 7-day retention, the oldest base backup is deleted around the time the next one is taken.

- If Sunday's backup runs long, fails, or finishes after the lifecycle job runs, there can be a window with no usable base backup for older points.
- At other times, the recoverable window shrinks to just the time since the most recent Sunday backup.

## Required fix

- **Retain base backups for at least 21 days, plus a safety margin.** For example, use 22 to 28 days, or "keep the last 4 base backups."
- **Retain all WAL from the oldest retained base backup onward.** Better still, tie WAL deletion to the oldest retained base backup rather than to a fixed age, so WAL is never deleted while a backup that needs it still exists.
- **Make lifecycle deletion conditional on a newer base backup existing.** The job should only remove a base backup once a newer one has completed successfully and been verified. That way a failed Sunday backup doesn't trigger deletion of the only usable one.

## Smaller improvements

- **Confirm the 5-minute recovery point.** WAL segments are only archived when they fill or are switched. Set `archive_timeout` (for example, 60s) so segments are archived on a schedule even when write volume is low. Also monitor archive lag and failures with `pg_stat_archiver` and alert on them.
- **Check WAL continuity.** Run an automated check that the archived WAL sequence has no gaps from each retained base backup onward.
- **Tighten the lifecycle job's permissions.** Scope its delete permission to backup and WAL prefixes only. Consider bucket versioning or object lock with a retention period of at least 21 days, so a buggy rule can't delete required data.
- **Broaden the rehearsal.** Occasionally test other points in the window, such as just after a base backup and 5 minutes ago. Record the restore duration as well, so you also validate how long recovery takes.

## What's good

- The bucket is in a separate account and the database hosts cannot overwrite or delete objects. That is good protection against ransomware or a compromised host.
- WAL is archived continuously, and monthly restore rehearsals are already in place.

VERDICT: NO_GO