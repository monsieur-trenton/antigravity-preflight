# Plan Review: Scratch Directory Cleanup

## Does it meet the stated rule?

**Yes.** The rule is that a run removes only the scratch directories it made. The plan enforces this by ownership tagging:

- Each run gets a **fresh random UUID**, so two concurrent runs will not share an identifier.
- Every directory is tagged with its creator's UUID at creation time.
- Cleanup selects directories **only** by an exact match on its own UUID.

Directories from other runs carry different UUIDs and are never selected. Untagged directories match nothing and are also left alone. Running several builds at once does not break this, because selection depends on ownership, not timing. The logging gives an audit trail that can show the rule was followed.

Nothing in the plan as written causes failure or a rule violation. There are still gaps worth closing.

## Recommended changes

1. **Orphans after crashes.** If a run is killed (SIGKILL, OOM, node loss), its cleanup never runs. Under the rule, no other run may delete those directories, so they pile up forever. Add:
   - A `trap` / `finally` handler so cleanup also runs on normal failures and signals.
   - A separate, explicitly authorized reaper for abandoned directories. For example, it could remove a directory only when it is older than N hours and its run is confirmed dead. This must be documented as a separate, sanctioned process so it doesn't conflict with the per-run rule.

2. **Say where and how the tag is stored.** Possible places are the directory name (e.g. `/var/cache/app/<uuid>-<suffix>`), a marker file inside it, or an xattr. Encoding the UUID in the name, created atomically with `mktemp -d /var/cache/app/<uuid>.XXXXXX`, is simplest. It also avoids a window where a directory exists without its tag.

3. **Guard the `rm -rf` call.** Before each deletion:
   - Resolve the path and confirm it sits directly under `/var/cache/app`.
   - Refuse to proceed if the path is a symlink.
   - Refuse to proceed if the run ID or path is empty, to avoid `rm -rf "/var/cache/app/"`-style accidents.
   - Quote all variables and use `rm -rf -- "$dir"`.

   With one shared service account, the OS gives no protection between runs. The tag check is the only safeguard, so it should be strict.

4. **Avoid check-then-delete races.** Build the list of directories from what this run recorded when it created them (an in-memory or on-disk manifest). Don't build it from a later scan-and-match. That way cleanup never acts on a directory that appeared or changed after creation.

5. **Log failures, not just successes.** If `rm -rf` fails or only partly succeeds (permissions, busy files), log the tag, the path, and the error. Leftovers should be visible.

6. **Optional hardening:** use a per-run parent directory (`/var/cache/app/<uuid>/`). Cleanup then becomes a single guarded removal, and ownership is obvious from the layout.

## Summary

The core design (unique per-run UUID, exact-match cleanup) is correct and satisfies the rule even with concurrent runs. The improvements are about robustness: handling crash orphans without breaking the rule, atomic tagging, defensive guards on `rm -rf`, and failure logging.

VERDICT: GO_WITH_CHANGES