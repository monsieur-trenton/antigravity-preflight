**Rationale**

The plan contradicts itself on retention, and that is a blocker.

- **The requirement:** Line 1 requires point-in-time restore to any moment from 14 days ago up to 5 minutes ago.
- **What that needs:** Lines 3 and 4 say a restore starts from the latest base backup before the target time. With weekly base backups, reaching 14 days back can need a base backup up to 21 days old plus all WAL written after it.
- **The conflict:** Line 5 keeps base backups and WAL for only 7 days, and the lifecycle job deletes anything older. Nothing older than 7 days survives. So every target between about 7 and 14 days back cannot be restored, which is half of the required window.
- **The rehearsal:** The monthly rehearsal on line 8 targets 13 to 14 days back. Under line 5 that data will already be deleted, so the rehearsal would fail. This follows directly from line 5 and is not a separate finding.

The other lines are consistent:

- **Recovery point:** WAL is archived within 60 seconds (line 2), which meets the 5-minute recovery point.
- **Deletion safeguards:** The lifecycle job only deletes objects past the retention limit (line 6), and the database hosts write to a separate account where they cannot overwrite or delete (line 7). Neither creates a conflict. The problem is the 7-day limit itself, not the deletion controls.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | 5 | Base backups and archived WAL are both retained for 7 days, and a nightly lifecycle job deletes anything older.