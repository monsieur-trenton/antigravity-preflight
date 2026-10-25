# Review: Scratch Directory Cleanup Plan

## Does it meet the stated rule?

Yes. The rule is that a run may remove only the scratch directories it made itself. The plan meets it:

- **Each run has its own ID.** Every run gets a fresh random UUID, so concurrent runs have different identifiers. A collision between two v4 UUIDs is negligible in practice.
- **Every directory is tagged at creation.** The tag is the ID of the run that created it.
- **Cleanup matches exactly.** It deletes only directories whose tag equals the run's own ID, so a directory from another run, finished or still running, never matches.
- **The account is unprivileged.** This limits the damage if something goes wrong.
- **Deletions are logged.** Logging each tag and path gives an audit trail for checking the rule after the fact.

Concurrency doesn't break the plan, because selection uses a per-run identity rather than timing or location.

## Recommended improvements

1. **Specify where the tag lives and how it's matched.** The plan should say whether the tag is part of the directory name, a marker file inside, or an extended attribute. Matching must be an exact full-string comparison, never prefix, substring or glob. A marker file inside the directory should be written when the directory is created, before anything else uses it.

2. **Refuse to clean up with an empty or malformed run ID.** If the ID variable is unset, an empty-string match could select untagged directories. Check that the ID is a well-formed UUID before cleanup starts.

3. **Validate each path before calling `rm -rf`:**
   - Resolve it to a canonical path and confirm it is a direct child of `/var/cache/app`.
   - Reject symlinks, because the chosen entry itself should be a real directory.
   - Call `rm -rf -- "$path"` with quoting and `--`, and never add a trailing slash.

4. **Narrow the window between checking and deleting.** If the tag is checked and the path is deleted later, the path could be swapped in between. This is unlikely between cooperating builds, but it's cheap to prevent. Two options:
   - Rename the directory to a run-unique "deleting" name first, then delete it.
   - Hold a handle on the directory while deleting.

5. **Handle runs that crash.** A run that dies before cleanup leaves orphaned directories, and no run may delete them under the current rule. Add a separate, explicitly authorized reaper. It should remove a directory only when its owning run is confirmed dead, for example by a heartbeat or lock-file check, and never merely because the directory looks old.

6. **Run cleanup on failure too.** Use a `trap`, a `finally` block, or the CI system's always-run step, so failed builds also clean up after themselves.

7. **Log enough to debug.** Also log the run ID doing the cleanup, a timestamp, and the result of each `rm`. Log the skipped and failed entries as well as the deleted ones.

## Summary

The plan is sound as written and doesn't violate its rule. The changes above make it robust against edge cases: an empty ID, loose matching, symlinks, crashed runs and failed builds.

VERDICT: GO_WITH_CHANGES