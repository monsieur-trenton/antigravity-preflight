Plan X needs a change and Plan Y does not, because X drops the only step that checks the safety condition the plan itself sets.

- **The condition:** Line S01:5 in both plans says all 18,400 shard entries must reference valid runner pool IDs before the irreversible compaction runs. Otherwise routing metadata is corrupted and CI halts.
- **Plan Y meets it:** At S01:7 (02:00 UTC), Elena Rostova runs a referential integrity scan and confirms zero unmapped runner pool IDs. This happens after the write lock (01:45) and well before the irreversible compaction (S01:23, 04:30).
- **Plan X does not:** It contains no such scan. Nothing between the lock and the compaction (S01:22) checks the shard entries. The later synthetic probes (S01:26) sample only 50 IDs and run after the irreversible step, so they cannot stand in for the scan.
- **One edit:** Every other line of X matches Y word for word, with only the numbering shifted. X is therefore Y with exactly one line deleted.
- **Shared quirk:** Both plans call the window "four-hour" but run it from 01:00 to 06:00 UTC. Since this is identical in both, it does not separate them.

AUDIT-BEGIN
NEEDS_CHANGE: X
WHY: Plan X runs the irreversible dispatch table compaction without first checking that all 18,400 shard entries reference valid runner pool IDs, which S01:5 requires.
ONE_EDIT: YES
DIFFERENCE: Plan Y has an extra line (Y S01:7) where Elena Rostova runs a referential integrity scan at 02:00 UTC confirming zero unmapped runner pool IDs, and Plan X deletes that line and is otherwise identical.
AUDIT-END