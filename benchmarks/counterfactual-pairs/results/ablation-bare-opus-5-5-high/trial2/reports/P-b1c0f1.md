# Review: Scratch Directory Cleanup Plan

The core design is sound. Each run gets a fresh random UUID, tags what it creates, and deletes only what matches its own tag. This meets the rule that a run removes only its own directories, even with concurrent runs. A few gaps should be closed before it ships.

## Issues to address

**1. Where and how the tag is stored is unspecified.**
This choice determines whether the ownership check can be trusted.
- **Best:** put the UUID in the directory name, e.g. `/var/cache/app/<run-uuid>/...` or `/var/cache/app/build-<run-uuid>-<n>`. It can't go missing, and selection is a simple exact match.
- **Weaker:** a marker file or xattr inside the directory. It can be absent, corrupted, or edited by anything running as the same service account. If you use one, treat "no readable tag" as "not mine, skip."

**2. Guard against an empty or malformed run ID.**
This is the most dangerous failure mode. If the ID variable is ever empty or unset, a pattern like `rm -rf "/var/cache/app/${RUN_ID}"*` matches everything.
- Before cleanup, validate that the ID is a well-formed UUID and abort if it isn't.
- Match the full ID exactly, never by prefix or loose glob.
- Use `set -u` (or the equivalent) in the cleanup script.

**3. Prefer a manifest over scanning.**
Have the run append each directory it creates to a run-local list, then delete exactly those paths. Before each deletion, re-check the tag. This avoids scanning the shared directory and avoids surprises from other runs' entries.

**4. Path safety with `rm -rf`.**
- Resolve each target and confirm it is a direct child of `/var/cache/app` before deleting. Reject `..`, absolute paths from tag data, and symlinks. Use `rm -rf -- "$path"` with no trailing slash, so a symlinked entry removes only the link.
- Lock down `/var/cache/app`: owned by the service account, not world-writable. Otherwise other local users could plant entries or symlinks.

**5. Cleanup must run on failure paths too.**
"When a run finishes" should include failures, cancellations, and timeouts. Use a `trap ... EXIT` or a `finally` block.

**6. Orphans from crashed runs.**
If a run is killed hard (SIGKILL, node loss), its directories are never removed. Under the rules, no other run may remove them, so they will accumulate. You need an explicitly sanctioned path, such as a separate janitor job documented as an exception to the rule. It would remove a directory only when its tag's run is confirmed dead and the directory is older than a threshold. Otherwise, monitor disk usage and handle orphans manually.

## Minor

- Also log skipped or refused deletions and the reason (bad tag, outside root, symlink). Include the timestamp and the outcome of each `rm`.
- Running as an unprivileged account is good. Keep it that way, and never fall back to sudo or root on permission errors.

## Summary

The ownership model is correct for concurrent runs. The required changes are:
- a defined, robust tag location
- a hard guard against an empty or malformed ID
- path validation before `rm -rf`
- cleanup on all exit paths
- a sanctioned plan for orphaned directories

VERDICT: GO_WITH_CHANGES