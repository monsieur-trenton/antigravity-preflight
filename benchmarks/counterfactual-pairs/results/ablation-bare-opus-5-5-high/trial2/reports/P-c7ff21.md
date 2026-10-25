# Review: Scratch Directory Cleanup Plan

## Blocking issue: the run identifier is not unique

The plan's safety depends on one assumption: **a tag identifies exactly one run.** Here every run uses the fixed string `nightly` as its identifier, so the assumption fails.

With several runs active at once:

1. Run A and Run B both tag their directories `nightly`.
2. Run A finishes first and deletes every directory tagged `nightly`.
3. That includes Run B's directories, which B may still be using.

This directly breaks the project rule that directories created by any other run must never be deleted. It is not an edge case. It happens whenever runs overlap, which the plan says they will. Possible results include corrupted builds, failures in the run that is still going, and silently wrong artifacts.

The logging doesn't help. Every entry will show `nightly`, so the logs can't tell you which run deleted which directory or whose directory it was.

## Required changes

1. **Use a unique per-run identifier.** For example, a UUID, or a combination of hostname, PID, start timestamp and random suffix. Generate it once at run start and never reuse it.
2. **Delete from a manifest, not by searching for tags.** When a run creates a directory (preferably with `mktemp -d /var/cache/app/scratch.XXXXXX`), it should append the path to a manifest the run owns. Cleanup should delete only paths in that manifest. This scopes deletion to what the run actually created, rather than to anything that happens to carry a matching tag.
3. **Verify before deleting.** For each entry, confirm that:
   - the path is still a directory and not a symlink,
   - it is under `/var/cache/app/`,
   - its tag still matches this run's unique ID.
   
   Skip and log anything that fails these checks.
4. **Harden the `rm -rf` call.** Use `rm -rf --one-file-system -- "$path"`. Quote the path and fail closed if it is empty or unset, so an empty variable can never expand to `/var/cache/app` or worse. Consider `set -u`.
5. **Handle crashed runs separately.** Runs killed before cleanup will leave orphaned directories. Deal with them through a separate reaper that removes a directory only when its owning run is provably dead (for example, an expired lease or heartbeat file). Do not let the normal cleanup path broaden its matching to catch them.
6. **Make the logs useful.** Log the unique run ID, the path, the outcome (deleted, skipped, or failed) and the reason for any skip.

## Minor notes

- Running as an unprivileged service account is good. Note, though, that all runs probably share that account, so filesystem permissions give no isolation between runs. Correctness depends entirely on the identifier and manifest logic above.
- Use `trap` or an equivalent so cleanup also runs when a run exits with an error.

## Summary

The overall design (tag, scoped cleanup, unprivileged account, logging) is reasonable. The fix is also simple. However, as written, the plan is guaranteed to delete other runs' directories whenever runs overlap, which violates the core project rule. It should not go ahead until unique run IDs and manifest-based deletion are in place.

VERDICT: NO_GO