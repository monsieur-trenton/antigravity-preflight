The claim holds. No line in the plan verifies parent hash population before execution or prevents or recovers from null-induced corruption.

- **S01:5** states the requirement (zero null parent hashes across all 640,000 entries) and the consequence (permanent B-tree corruption). It establishes no check.
- **Checks that look related but are not:**
  - S01:13 verifies the migration binary's checksum, not the index entries.
  - S01:9 checks free disk space.
  - S01:15 checks for open connections.
  - S01:17 sets synchronous writes for crash consistency, which does not address null values.
- **Checks after execution:**
  - S01:22 validates only the version 4 superblock header.
  - S01:24 monitors daemon initialization logs.
  - S01:25–26 run a smoke test of cache reads and writes.
  
  None of these inspects parent hashes or the integrity of the B-tree directory. All come after the in-place upgrade at S01:19, when the damage S01:5 calls permanent would already be done.
- **No recovery path:** The plan has no snapshot, backup, schema constraint, background check or rollback step. The upgrade is in-place (S01:19). Replication to standby instances (S01:33) is only checked afterwards and is not presented as a recovery path.

AUDIT-BEGIN
CLAIM_HOLDS: YES
CONTRADICTING_LINES: none
AUDIT-END