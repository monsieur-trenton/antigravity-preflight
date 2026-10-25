# Review: Orders PostgreSQL PITR Backup Plan

**The plan cannot meet its own 14-day recovery requirement.** Its retention setting deletes the backups that requirement depends on.

## Blocking issue: retention is shorter than the recovery window

The plan states two things that conflict:

1. Reaching a point 14 days back can require a base backup **up to 21 days old**, plus all WAL written after it.
2. Base backups and archived WAL are **retained for only 7 days**, and a nightly job deletes anything older.

With 7-day retention, at most one or two base backups exist at any moment, and none is older than 7 days. WAL older than 7 days is also gone. So any restore target more than about 7 days back has no base backup before it and no WAL to replay. Roughly half the promised window, from 7 to 14 days ago, cannot be restored.

**Fix:** retain base backups for at least 21 days, or more precisely recovery window plus one backup interval, with a margin. Also retain all WAL from the oldest kept base backup onward. In practice:

- Keep at least 4 weekly base backups (22 to 28 days).
- Make WAL expiry depend on the oldest retained base backup, not on a fixed age. A fixed-age rule can break the replay chain.
- Alternatively, take base backups more often (for example nightly). This reduces how much history you must keep: about 15 days for a 14-day window with daily backups.

## The rehearsal would expose the failure

The monthly rehearsal targets a point 13 to 14 days back. Under the current retention, every rehearsal would fail. That is a useful check, but it means the plan, as designed, guarantees a failed rehearsal rather than a working restore capability.

## Recommended improvements (once retention is fixed)

- **Gaps in the WAL chain:** WAL is archived "within 60 seconds of being written," but PostgreSQL archives a segment only once it is complete. Set `archive_timeout` (for example 60s) so quiet periods still produce archived segments. Also alert on `pg_stat_archiver` failures and on gaps in the archive. The 5-minute recovery point depends on this.
- **Expiry should reflect dependencies:** the lifecycle rule should never delete a base backup or WAL that a retained restore point still needs. Purely age-based rules are fragile here. Tools like pgBackRest or WAL-G manage expiry by dependency natively.
- **Lifecycle job permissions:** separating the backup account and blocking overwrites and deletes from the database hosts is good. The lifecycle job is now the only deletion path, so restrict and audit its credentials. Consider object lock with a retention period equal to the required window, so a misconfigured rule cannot delete needed data.
- **Rehearsal coverage:** also test a recent point (around 5 to 10 minutes ago) to confirm the recovery-point claim. Record restore duration so you have a measured recovery time.
- **Monitoring:** alert if the newest base backup is more than 7 days old, or if the oldest retained backup no longer covers 14 days.

## Summary

The architecture is sound: weekly base backups, continuous WAL archiving, a separate write-once account, and regular rehearsals. However, the 7-day retention directly contradicts the 21-day lookback the plan itself says it needs. As written, restores beyond about 7 days, including every planned rehearsal, will fail.

VERDICT: NO_GO