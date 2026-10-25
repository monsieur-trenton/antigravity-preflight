# Review: Point-in-Time Recovery Plan for the Orders Database

## Blocking issue: retention is too short for the stated 14-day window

The plan's own numbers contradict each other:

- **Requirement:** recover to any moment from 14 days ago up to 5 minutes ago.
- **Dependency, as the plan says:** with weekly base backups, reaching 14 days back may need a base backup up to **21 days old**, plus every WAL segment since then.
- **Retention:** 7 days for both base backups and archived WAL. The nightly lifecycle job deletes anything older.

So at most about 7 days of base backups and WAL exist at any time. Worse, just before Sunday's backup, the oldest base backup is nearly 7 days old. Recovery is only guaranteed back to roughly the age of the oldest retained base backup, with continuous WAL from it. Every target from about 7 to 14 days ago is unrecoverable, and so are some targets under 7 days old.

**The monthly drill will fail every time.** It picks a moment 13 to 14 days back, and no base backup or WAL from that period survives.

**Required change:** set retention to at least 21 days for base backups and archived WAL, plus a margin for schedule slip or a failed Sunday backup (e.g., 22–28 days). Alternatively, take base backups more often and size retention as *requirement window + backup interval + margin*. The lifecycle rule must use the same value. The rule that it "selects nothing younger than the retention limit" is only safe once that limit is correct.

## Parts that work

- **5-minute recovery point:** WAL landing within 60 seconds fits within the 5-minute target.
- **Bucket isolation:** a separate account with add-only rights for database hosts is a good defense against ransomware and accidental deletion.
- **Drill design:** testing near the far edge of the window is the right choice. It is exactly why the drill would catch this defect.

## Optional robustness suggestions (not required)

- Set `archive_timeout` (e.g., 60s) so segments are completed and shipped on time during low traffic. "Within 60 seconds of being written" otherwise depends on segments filling up.
- Alert on gaps in WAL continuity and on failed or missing Sunday base backups. One missed backup pushes the dependency window to 28 days.
- Consider object lock or versioning on the bucket to protect against the lifecycle job itself.

VERDICT: NO_GO