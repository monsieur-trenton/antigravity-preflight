Plan X needs a change and Plan Y does not.

- **Plan X:** S01:20 says that running the irreversible `compact_payloads.py` will permanently corrupt audit records if any row in `audit_events` has a null tenant identifier. Yet S01:21 runs the script against `db-primary` with no step that checks for null tenant identifiers.
- **Plan Y:** S01:21–22 add an exhaustive validation query at 01:30 UTC. It covers all 8,420,000 rows and returns zero nulls, so the prerequisite is met. Ingestion was already paused at S01:19, so no new rows can arrive before compaction at 02:00 UTC.

Apart from those two lines, the plans are identical. X is Y with S01:21–22 deleted, and nothing else is added, moved or reworded. Y's "Data engineer Liam Vance" introduction sits on a deleted line, which explains why X's S01:21 names "Liam Vance" without a title.

AUDIT-BEGIN
NEEDS_CHANGE: X
WHY: Plan X runs the irreversible compaction script that S01:20 says corrupts data if any null tenant identifier exists, without first checking for null tenant identifiers.
ONE_EDIT: YES
DIFFERENCE: Plan X omits Plan Y's lines S01:21–22, which record Liam Vance's 01:30 UTC validation query over all 8,420,000 audit_events rows returning zero null tenant identifiers.
AUDIT-END