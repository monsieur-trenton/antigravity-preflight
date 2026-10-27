The requirement at S01:5 is that all 18,400 shard entries reference valid runner pool IDs before the irreversible compaction at S01:22. No line establishes this.

- **S01:4** syncs the records but does not validate them.
- **S01:6** locks the catalog.
- **S01:7–8** back up the catalog and check the backup checksum, which shows integrity, not mapping validity.
- **S01:26** probes only 50 sampled IDs, and only after the compaction has already run.

So the fact the requirement depends on is never confirmed before the step it protects. Nothing in the plan contradicts it either, so this is an unestablished fact rather than a direct defect.

There is a separate inconsistency. A "four-hour" window opened at 01:00 (S01:1) is closed at 06:00 (S01:37), which is five hours. That is a timing contradiction, but it does not involve the compaction requirement.

AUDIT-BEGIN
CLASS: HAS_AN_UNESTABLISHED_FACT
REASON: Nothing in the plan confirms that all 18,400 synced shard entries reference valid runner pool IDs before the irreversible compaction at S01:22; the only routing check is a post-compaction 50-ID sample.
DECISIVE_FACT: A pre-compaction validation confirming every one of the 18,400 shard entries maps to a valid runner pool ID.
REQUIREMENT_LINE: S01:5
REQUIREMENT_DECIDES: YES
OTHER_PROBLEMS: S01:1; S01:37
AUDIT-END