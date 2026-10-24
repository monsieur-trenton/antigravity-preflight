# Review: Point-in-Time Recovery Plan for the Orders Database

The plan cannot meet its 14-day recovery target, because its retention period is shorter than the recovery window it has to support.

## Blocking issue: retention is shorter than the recovery window

The plan states two things that conflict:

1. **The requirement.** Recovery must reach any moment from 14 days ago up to 5 minutes ago.
2. **The dependency.** Base backups are weekly. To reach a moment 14 days ago, you may need a base backup up to **21 days old**, plus every WAL segment from that backup forward.

Against that, **retention is 7 days** for both base backups and WAL, and the nightly lifecycle job deletes anything older.

The consequences:

- **Base backups.** At most one or two Sunday backups exist at any time, and none is older than 7 days. Any moment more than about 7 days back has no base backup preceding it.
- **WAL.** Archived WAL older than 7 days is gone. Even if an old base backup survived, the chain from it could not be replayed.
- **Effective window.** Recovery works reliably only to moments after the oldest surviving base backup. That is roughly 0 to 7 days back, depending on the day of the week. It never reaches 14 days.

The monthly drill targets 13–14 days back, so it would fail every time. That at least means the problem would be caught, but the plan as written fails its stated requirement.

## Required changes

- **Raise retention to at least 21 days** for both base backups and archived WAL, ideally with a margin such as 22–28 days. This absorbs a late or failed Sunday backup and lifecycle-job timing. If one Sunday backup fails, you need the one before it, which can be up to 28 days old.
- **Make retention dependency-aware, or keep the two limits in step.** WAL must never be deleted while a retained base backup still needs it. The simplest rule is to delete WAL only when it is older than the oldest base backup you are keeping. Tools like pgBackRest and WAL-G handle this automatically.
- **Alternatively, take base backups more often.** Daily base backups would cut the required retention to about 15 days plus a margin, and would also shorten replay time during recovery.

## Parts that are sound

- **Immutability.** Using a separate account with add-only rights for the database hosts gives good protection against a compromised host or ransomware.
- **Lifecycle scope.** Limiting the lifecycle job to objects older than the retention limit is the right control. It just needs the corrected limit.
- **The drill.** It targets the hardest edge of the window, which is exactly right.
- **The 5-minute recovery point.** Archiving within 60 seconds is consistent with this target.

## Suggestions (not blocking)

- **Archive partial segments on quiet systems.** "Within 60 seconds of being written" only helps once a segment is complete. Set `archive_timeout`, for example to 60 seconds, so a partially filled segment is still archived during low traffic. Without it, the 5-minute recovery point can slip.
- **Monitor the archive.** Alert on `archive_command` failures and archive lag, and on missing or failed Sunday base backups.
- **Strengthen immutability.** Consider object lock or WORM on the bucket, so retention can't be shortened accidentally either.
- **Widen the drill.** Occasionally also test a recent target, and record how long recovery takes.

VERDICT: NO_GO