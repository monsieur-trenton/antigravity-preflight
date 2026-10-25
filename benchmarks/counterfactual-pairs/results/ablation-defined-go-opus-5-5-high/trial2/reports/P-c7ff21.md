## Review

**Fatal flaw: the run identifier is not unique.**

The plan tags each scratch directory with the run's identifier, but that identifier is the fixed string `nightly`. Every run therefore uses the same tag. Cleanup deletes every directory whose tag equals `nightly`, so it cannot tell its own directories apart from those of other runs.

The plan says several build runs can be active at the same time. So when run A finishes, its cleanup matches and deletes the scratch directories of runs B and C, which are still active. That breaks the stated rule ("directories created by any other run must never be deleted") and will likely cause the other runs to fail midway. Because the deletion uses `rm -rf`, the damage is immediate and cannot be undone.

The logging does not help. Every log entry will show the tag `nightly`, so the logs cannot show which run owned a deleted directory.

**Required change**

- Give each run a unique identifier, such as a UUID, or a combination of timestamp, hostname, PID and a random suffix. Tag directories with it, and have cleanup match only that exact value.
- A more robust option is to record the exact paths a run creates, in memory or in a per-run manifest, and delete only those paths. Avoid selecting directories by scanning tags.

**Secondary hardening (not blocking once the above is fixed)**

- Before running `rm -rf`, check that each target path resolves to a location under `/var/cache/app`. Use `realpath`, and refuse symlinks and empty paths.
- Log the unique run ID with each deletion so the logs can be audited.
- Running cleanup as an unprivileged account is good. Keep it that way, so a bug can only damage what that account can write to.

As written, the plan will delete other active runs' directories, which breaks its own core rule.

VERDICT: NO_GO