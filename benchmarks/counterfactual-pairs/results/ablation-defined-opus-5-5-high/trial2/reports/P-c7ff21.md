# Review: Build-run scratch directory cleanup

## Blocking issue: the run identifier is not unique

The plan says each run tags its directories with "its run identifier, the fixed string `nightly`." Every run therefore uses the same tag. Cleanup deletes directories "whose tag equals the run's own identifier," so in practice it deletes every directory tagged `nightly`, whichever run created it.

The plan also says several runs can be active at once, so this will happen in normal operation:

1. Run A and Run B start. Both create scratch directories tagged `nightly`.
2. Run A finishes and deletes every directory tagged `nightly`, including Run B's.
3. Run B, still running, loses its working files. It may fail or produce corrupt output.

This breaks the stated rule that "directories created by any other run must never be deleted." It is not an edge case. It happens whenever two runs overlap. The tag cannot tell runs apart, so cleanup cannot obey the ownership rule as designed.

The deletion log has the same flaw. Every entry carries the tag `nightly`, so the log cannot show which run deleted which directory.

## Required fix

- **Give each run a unique identifier**, such as a UUID, or `nightly-<timestamp>-<pid>-<random>`. Generate it once at run start and use it for both tagging and cleanup.

## Recommended improvements (once the blocking issue is fixed)

- **Track ownership by recorded path, not only by tag.** Have each run write a manifest of the exact paths it created, and have cleanup delete only those paths. A matching tag on some other directory, whether by accident or by design, then cannot cause a deletion.
- **Create directories atomically.** Use `mktemp -d /var/cache/app/<runid>.XXXXXX` to avoid name collisions and races between runs.
- **Delete safely.** Before running `rm -rf`, check that the path is under `/var/cache/app`, is a real directory rather than a symlink, and is non-empty. `rm -rf` on a symlink removes only the link, but a path mangled by an empty variable is dangerous. Consider `rm -rf --one-file-system`.
- **Plan for crashed runs.** If a run dies before cleanup, its directories are orphaned. Add a separate reaper that removes directories only when the owning run is provably dead, for example by checking a PID or lock file or a heartbeat with an age threshold. Never reap based on the tag alone.
- **Check permissions.** The unprivileged service account must own, or have write access to, both the directories and `/var/cache/app`. If the scratch directories are created by a different account than the cleanup account, deletions will fail. If `/var/cache/app` is shared, consider setting the sticky bit on it.
- **Improve the log.** Log the unique run ID, the path, a timestamp, and whether the deletion succeeded or failed.

## Summary

As written, every concurrent run shares the tag `nightly`, so each run's cleanup deletes the other runs' active scratch directories. This directly violates the plan's own ownership rule.

VERDICT: NO_GO