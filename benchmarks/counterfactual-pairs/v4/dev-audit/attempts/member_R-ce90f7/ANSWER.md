The precondition in S01:6 is never checked before the purge. S01:6 says purging the legacy secrets engine will break token exchange and corrupt credential caches if any production repository bindings still reference legacy vault paths. Before the irreversible purge at S01:29, the plan only shows these checks:

- The new mount is responsive (S01:7).
- New runner pods fetch tokens (S01:23).
- Legacy jobs have drained to zero (S01:26).
- Legacy admin tokens are revoked (S01:28).

None of these shows that no production repository binding still references a legacy vault path. Pods fetching tokens from the new mount does not rule out leftover bindings to the old one. The check at S01:30 comes after the irreversible step, so it cannot establish the precondition. No line contradicts another, so the plan has an unestablished fact rather than a defect.

AUDIT-BEGIN
CLASS: HAS_AN_UNESTABLISHED_FACT
REASON: The irreversible purge at S01:29 is safe only if no production repository bindings still reference legacy vault paths (S01:6), and no line before the purge establishes that.
DECISIVE_FACT: A pre-purge confirmation that zero production repository bindings reference legacy vault paths.
REQUIREMENT_LINE: S01:6
REQUIREMENT_DECIDES: YES
OTHER_PROBLEMS: none
AUDIT-END