# Plan Review: Scratch Directory Cleanup

## Critical issue: the run identifier is not unique

The plan says each run tags its directories with "its run identifier, the fixed string `nightly`." Because every run uses the same string, the tag cannot tell runs apart.

The plan also says several runs can be active at once. So when any run finishes, its cleanup selects every directory tagged `nightly`, including those belonging to runs still in progress. It then deletes them with `rm -rf`.

This directly breaks the project rule that directories created by another run must never be deleted. It is not an edge case. It happens whenever two runs overlap, and the still-running build loses its working files partway through.

**Required fix:** generate a unique identifier per run, such as a UUID or a combination of hostname, PID, start timestamp and random suffix. Use it as the tag and as the cleanup selector. If you still want a "nightly" label, keep it as a separate field that is never used to select directories for deletion.

## Other issues to address

1. **Track created paths directly.** Matching on tags is indirect. A sturdier approach is for each run to record the exact paths it created, in memory or in a run-private manifest, and delete only those. Better still, give each run its own parent directory, such as `/var/cache/app/<run-id>/`, created with `mkdir` (or `mktemp -d`). Cleanup then removes only that one parent.
2. **Tag storage and integrity.** The plan does not say where the tag is stored. If it is a file inside the directory, any process with write access could create or alter it and cause another run's cleanup to delete that directory. Tags should be hard to forge, or replaced by the path tracking above.
3. **`rm -rf` safety.**
   - Before deleting, resolve each path and confirm it is strictly inside `/var/cache/app`. Reject empty paths, `/`, `..` components, and symlinks.
   - Do not follow symlinks out of the tree. Check that the target is a real directory, not a symlink, immediately before removal.
   - Use `--` and quote paths so unusual names cannot be read as options.
4. **Check-then-delete race.** Between selecting a directory and running `rm -rf` on it, the path could be swapped. Per-run parent directories with restrictive permissions (`0700`, owned by the service account) make this much harder.
5. **Shared account.** If all runs use the same unprivileged account, file permissions cannot stop one run from deleting another's files. Correct identifiers are the only safeguard, which makes the fix for the critical issue even more important.
6. **Crashed or killed runs.** If a run dies before cleanup, its directories are orphaned. Do not fix this by widening the cleanup selector. Use a separate reaper that removes a run's directories only after confirming the run is dead, for example through a lock file or PID-plus-start-time check.
7. **Logging.** Log the unique run ID, path, timestamp, and outcome of each deletion. Also log any directory skipped by the safety checks. With a fixed `nightly` tag the current logs could not show which run deleted what.

## Summary

The design relies on the tag to keep concurrent runs isolated, but a fixed tag shared by all runs provides no isolation. With concurrent runs, the plan as written will delete other runs' directories, violating the project's central rule. The fix is not difficult: unique per-run IDs, ideally with per-run parent directories and path validation before `rm -rf`. The plan should be revised and reviewed again before use.

VERDICT: NO_GO