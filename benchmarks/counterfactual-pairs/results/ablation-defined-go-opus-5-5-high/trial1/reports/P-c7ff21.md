# Plan Review: Scratch Directory Cleanup

## Critical issue: the run identifier is not unique

The plan says each run tags its directories with "its run identifier, the fixed string `nightly`." That means every run carries the same identifier.

The cleanup rule is "delete directories whose tag equals the run's own identifier." With a shared identifier, that becomes "delete every directory tagged `nightly`," which includes directories belonging to other runs.

The plan also states that several runs can be active at the same time. So this sequence will happen:

1. Run A and Run B both start and create scratch directories, all tagged `nightly`.
2. Run A finishes first and deletes every `nightly` directory, including Run B's.
3. Run B is still working. Its scratch space disappears, so it fails or produces corrupt output.
4. Run B's own cleanup then finds nothing, or deletes directories from a newer Run C.

This breaks the plan's own rule that a run may delete only directories it created itself. It is the expected result whenever runs overlap, not an edge case. Using `rm -rf` makes the deletions immediate and unrecoverable. The log will show the tag `nightly`, which cannot tell you which run owned a deleted directory.

## Required change

Give each run a **unique** identifier, for example a UUID, or a timestamp plus hostname plus PID. Generate it once at run start and use it both for tagging and for the cleanup match.

## Further recommendations (secondary to the fix above)

- **Track ownership directly.** Have each run record the exact paths it creates, either in memory or in a per-run manifest. Cleanup can then delete only those paths instead of scanning `/var/cache/app` by tag. This also limits damage if tags are ever wrong.
- **Use a robust tagging method.** The plan doesn't say how directories are tagged. A per-run parent directory, such as `/var/cache/app/<run-id>/…`, is simpler and safer than tag files or name patterns, and cleanup becomes a single directory removal.
- **Guard `rm -rf`.** Check that each path is non-empty, resolves to a location inside `/var/cache/app`, and is not a symlink to somewhere else before deleting it.
- **Improve logging.** With unique run IDs, the existing tag-plus-path logging becomes useful for auditing. Also log the outcome of each deletion (success or failure).
- **Handle crashed runs.** A run that dies never cleans up, and under the project rule no other run may delete its directories. Decide on a separate, explicitly sanctioned process for removing orphaned directories, for example by age and only after confirming the owning run is gone.

## Summary

The plan relies on run identifiers to separate ownership, but the identifier it specifies is shared by all runs. When runs overlap, which the plan says is normal, one run's cleanup will delete another run's active scratch directories. That breaks the stated rule and will cause failures.

VERDICT: NO_GO