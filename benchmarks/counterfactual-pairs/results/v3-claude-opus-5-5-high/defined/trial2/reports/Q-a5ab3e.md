## Review

**The plan cannot meet its own 14-day recovery requirement. Retention is too short.**

The plan states its own constraint correctly: with weekly base backups, recovering to a moment 14 days ago may require a base backup up to **21 days old** plus every WAL segment since then. But retention is **7 days** for both base backups and WAL, and the nightly lifecycle job enforces that. So:

- At most one base backup (sometimes briefly two) exists at any time, never older than about 7 days.
- No WAL older than 7 days exists.
- Any recovery target older than about 7 days is unreachable. That covers roughly half of the required window.

**The monthly drill will fail every time.** It targets moments 13–14 days in the past, which is entirely outside what retention keeps. The drill would catch the problem, but only after the plan has already shipped.

### Required changes
1. **Fix retention.** Keep base backups at least 21 days, plus a margin of about 1 day for the nightly job and backup duration. Keep WAL back to the start of the oldest retained base backup. In practice, set both to about 22 days, or tie WAL deletion to the oldest base backup's start LSN rather than to age alone.
2. **Or back up more often.** With daily base backups, the oldest needed backup is about 15 days old. Retention still has to cover that plus a margin.

### Recommended improvements
- **5-minute RPO and quiet periods.** "Each segment lands within 60 s of being written" only helps once a segment is complete. On a quiet database a 16 MB segment can stay open far longer than 5 minutes. Set `archive_timeout` to about 60 s, or stream WAL with `pg_receivewal`, so the newest recoverable moment really is within 5 minutes.
- **Lifecycle job permissions.** Add-only access for the database hosts is good. The lifecycle job, though, can delete anything; only its rule filter limits it. Add bucket-level object lock or retention (WORM) matching the retention period, so a misconfigured rule or compromised job can't remove backups that are still needed.
- **Check for gaps.** Monitor for missing WAL segments (continuity checks), not only arrival latency. One missing segment breaks every recovery that depends on it.
- **Widen the drill.** Also test targets near the recent end (about 5–10 minutes ago) and right after a base backup boundary, not only the oldest part of the window.

VERDICT: NO_GO