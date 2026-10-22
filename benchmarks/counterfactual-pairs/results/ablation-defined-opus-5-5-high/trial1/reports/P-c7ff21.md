# Plan Review: Scratch Directory Cleanup for Concurrent Build Runs

## Blocking issue: the run identifier is not unique

The plan tags each directory with "its run identifier, the fixed string `nightly`." Every run therefore gets the same tag. Cleanup deletes every directory whose tag equals the run's own identifier, so it matches every directory tagged `nightly`, no matter which run created it.

The plan also says several runs can be active at once. So:

1. Run A and Run B start. Both create scratch directories tagged `nightly`.
2. Run A finishes first and deletes all `nightly` directories, including Run B's.
3. Run B, still working, loses its scratch space and fails or produces corrupt output. More importantly, the rule "directories created by any other run must never be deleted" has been broken.

This is not an edge case. It happens whenever two runs overlap, which the plan says is expected. The plan as written breaks a rule it states.

## Required fix

The selection rule has to identify the directories this run created, not a label every run shares. Options, from most to least robust:

- **One parent directory per run (preferred).** At startup, create a run directory with `mktemp -d /var/cache/app/run.XXXXXXXX`, put all scratch directories under it, and delete only that one path at the end. No tag matching or scanning is needed. Uniqueness is guaranteed atomically by the filesystem.
- **Manifest of created paths.** Record each directory's path in a per-run manifest as it is created, and delete only the listed paths. Ownership becomes something you recorded, not something you inferred.
- **Unique run ID in the tag.** If tags must stay, use a value that really is unique per run, such as a UUID or `nightly-<timestamp>-<pid>-<random>`. A schedule name like "nightly" is not an identity. Overlapping or retried nightly runs still collide.

## Other improvements

These matter less than the blocking issue, but they are worth doing once it is fixed:

- **Constrain what `rm -rf` can touch.** Before deleting, resolve the path and check that it is a real directory, not a symlink, and sits under `/var/cache/app`. Use `rm -rf -- "$path"` with quoting so an empty or odd value can't widen the deletion. Running as an unprivileged account limits damage but doesn't stop it from deleting other runs' files, since those are owned by the same account.
- **Make tags tamper-resistant if you keep them.** A tag stored somewhere writable, such as a marker file, can be copied or overwritten. A manifest or parent directory held by the run avoids this.
- **Clean up after crashes.** If a run dies before cleanup, its directories are orphaned. With unique IDs, a separate reaper can safely remove directories whose owning run is confirmed dead, for example by checking a stale lockfile or heartbeat. The reaper should not be the per-run cleanup.
- **Improve logging.** Log the run ID, path, timestamp, and result, including failures. Logging "nightly" alone can't show which run deleted what, which is exactly what you'd need to diagnose this bug.

## Summary

Cleanup selects directories by a tag that every run shares. With concurrent runs, one run's cleanup deletes other active runs' directories, which directly breaks the project rule. Give each run a unique identity, ideally its own `mktemp -d` parent directory, before this plan goes ahead.

VERDICT: NO_GO