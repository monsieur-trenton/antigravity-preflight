# Review: Build Scratch-Directory Cleanup Plan

## Does the plan meet its rule?

The rule is that a run removes only the scratch directories it made itself, never another run's, even when several runs are going at once. The plan meets this rule.

- **Ownership is unambiguous.** Each run gets a new random UUID and tags every directory it makes with that UUID. Two concurrent runs will not share an identifier, so no directory can carry two runs' tags.
- **Selection is exact.** Cleanup deletes only directories whose tag equals the current run's identifier. It doesn't guess ownership from timestamps, name prefixes, process IDs, or "older than N minutes" rules. Those approaches are where concurrent-cleanup schemes usually go wrong.
- **Concurrency is safe.** Run B can't select Run A's directories because the tags never match. It doesn't matter whether A is still running, finishing, or already done.
- **Damage is limited.** Cleanup runs under an unprivileged service account, so a bug in path handling can't reach far outside `/var/cache/app`. It also runs `rm -rf` only on the paths it selected.
- **It can be audited.** Logging each deletion's tag and path makes it easy to check afterward that a run touched only its own directories.

I see nothing in the plan as written that would fail or violate the stated rule.

## Optional robustness suggestions (not required changes)

1. **Orphaned directories after crashes.** If a run dies before its cleanup step, its directories stay behind. No later run will remove them, which is correct under the rule but means they pile up. A separate, deliberate janitor process could handle them, for example by removing directories whose owning run is known to have ended. That process would need its own ownership rule.
2. **Where the tag lives.** Record the tag when the directory is created, ideally in the directory name (e.g. `/var/cache/app/<uuid>-<suffix>`) or in a marker file written at creation. Name-based tags are easiest, because selection is then a plain path match and nothing inside the directory has to be read.
3. **Path sanity check before `rm -rf`.** Confirm that each chosen path is non-empty, resolves to a location under `/var/cache/app`, and is not a symlink. This guards against a bug that produces an empty or unexpected path.
4. **Log before deleting.** Also log failures, so a partial cleanup can be seen.

These would make a working plan sturdier. None of them is needed for the plan to work.

VERDICT: GO