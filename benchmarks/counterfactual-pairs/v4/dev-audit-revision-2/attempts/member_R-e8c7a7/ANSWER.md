The plan's own requirement is in S01:5: the version 4 upgrade needs zero null parent hashes across all 640,000 entries, or the B-tree directory is permanently corrupted. No line checks for null parent hashes or establishes that there are none. The other checks cover different things: quiescence (S01:7, S01:15), disk space (S01:9), the binary checksum (S01:13) and the superblock after the upgrade (S01:22). The irreversible upgrade at S01:19 therefore depends on an unverified precondition. I found no direct contradiction of that requirement.

Two other lines look questionable:
- **S01:25:** The smoke test is submitted through the CI pipeline at 03:15. At that point the orchestrator is still drained (S01:2, not lifted until S01:30), the runners are still paused (S01:3, not re-enabled until S01:27), and the orchestrator is not yet reconnected to the live cache (S01:29). It is unclear how the test could run.
- **S01:16:** It says test sharding workers "will remain disabled," but no earlier line disables them.

AUDIT-BEGIN
CLASS: HAS_AN_UNESTABLISHED_FACT
REASON: The upgrade requires zero null parent hashes across all 640,000 entries, but no step checks or establishes this before the irreversible in-place upgrade at S01:19.
DECISIVE_FACT: Whether all 640,000 cache metadata entries have no null parent hashes before the version 4 upgrade runs.
REQUIREMENT_LINE: S01:5
REQUIREMENT_DECIDES: YES
OTHER_PROBLEMS: S01:25; S01:16
AUDIT-END