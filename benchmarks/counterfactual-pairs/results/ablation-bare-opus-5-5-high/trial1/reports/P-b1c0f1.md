# Plan Review: Scratch Directory Cleanup in `/var/cache/app`

## Summary

The core design is sound. Tagging each directory with a per-run random UUID and deleting only matching tags directly enforces the rule that a run removes only its own directories, even with concurrent runs. Using an unprivileged account and logging each deletion are also good choices. A few gaps should be closed before implementation.

## What works

- **Ownership model fits the rule.** A fresh random UUID per run makes accidental tag matches between concurrent runs practically impossible.
- **Least privilege.** An unprivileged account limits the damage if path selection goes wrong.
- **Auditability.** Logging the tag and path for each deletion supports later investigation.

## Issues and recommended changes

1. **How tags are stored and read is unspecified.** This matters most.
   - If the tag is a file inside the directory, cleanup must read it safely. It should not follow symlinks (use `O_NOFOLLOW`), and it should skip anything that is not a real directory.
   - Any directory with a missing, unreadable, or malformed tag must be skipped, never deleted.
   - **Better option:** have each run keep its own list of the exact paths it created, held in memory or in a run-private file. Cleanup then deletes only paths on that list, after confirming the tag still matches. This avoids scanning shared space and trusting whatever is there.
   - **Even simpler:** give each run one parent directory, `/var/cache/app/<uuid>/`, and create all scratch directories under it. Cleanup then removes one path that the run created itself.

2. **Directory names must be unique and created atomically.** Create directories with `mkdtemp` or `mkdir` with an exclusive, unique name, not a fixed or predictable one. Otherwise two runs could collide on the same path, and one run's tag could end up on a directory the other run is using. Write the tag immediately after creation. A directory that is briefly untagged is acceptable only because untagged directories are skipped (see item 1).

3. **The gap between checking and deleting.** Between reading a tag and calling `rm -rf`, the path could in theory be replaced, for example by a symlink.
   - Resolve the path once and check that it is a real directory (`lstat`, not a symlink) inside `/var/cache/app`.
   - Pass the full absolute path with no trailing slash.
   - Use `rm -rf --one-file-system --` so a path cannot be read as an option and deletion stays on one filesystem.
   - Never build the path from an empty or unset variable. Fail closed if the path is empty or equals `/var/cache/app` itself.

4. **Crashed or killed runs leave orphans.** If a run dies before cleanup, its directories carry a UUID that no future run will ever match, so they accumulate forever.
   - Under the stated rule, other runs must not remove them, so this needs a separate, explicitly approved process.
   - For example, an operator-run or scheduled reaper could remove directories whose owning run is confirmed finished (tracked in a run registry) or that are older than a conservative age limit.
   - Document this as a deliberate exception or as a separate owner.
   - Also run cleanup in a `finally`/`trap` handler so normal failures still clean up.

5. **UUID quality.** State that the UUID is a v4 UUID from a cryptographically secure random source, not a time-based or seeded one.

6. **Logging details.**
   - Also log the run ID, the timestamp, and whether `rm` succeeded.
   - Log skipped directories and the reason, such as a tag mismatch, a missing tag, or a symlink.
   - Make deletion failures visible rather than silently ignored.

7. **Permissions on `/var/cache/app`.** If every run uses the same service account, any run can technically delete any directory. The rule is then enforced by the code, not by the operating system. That is acceptable if the build code is trusted, but say so explicitly. Make sure no other account can write to `/var/cache/app`, so outside processes cannot plant or alter tags.

## Bottom line

The approach is right. Before implementation:

- Specify tag storage and fail-closed handling.
- Make directory names unique and created atomically, or use a per-run parent directory.
- Harden the `rm -rf` call.
- Define a separate, approved path for cleaning up orphaned directories.

VERDICT: GO_WITH_CHANGES