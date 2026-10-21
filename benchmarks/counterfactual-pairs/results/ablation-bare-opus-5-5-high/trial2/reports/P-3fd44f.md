# Review: `load_config` raises `ConfigError` instead of returning `None`

The change itself is reasonable. Raising an exception is clearer than returning a sentinel, and the plan names a handler for each caller it lists. A few gaps should be closed before merging.

## What looks good
- **`main()` keeps its behavior.** It still exits with status 2, and the plan explicitly ties this to the old `None` behavior.
- **Each listed caller has an explicit handler.** No call path is left to crash on the new exception.
- **The config file's size and format don't matter here.** Plain text under 10 KB has no bearing on the error-handling change.

## Issues and requested changes

1. **Confirm the caller list is complete.** The plan names three callers. Before switching from a return value to an exception, grep the whole codebase for `load_config`, including scripts, CLI tools and plugins. If it's a public or importable function, check external consumers too. Any caller you miss that did `if cfg is None:` will now crash with an uncaught `ConfigError`.

2. **Check whether `schedule()` and `report()` change behavior.** The plan says they "now" fall back to defaults, but it doesn't say what they did with `None` before.
   - If they already used defaults, say so. This is then a pure refactor.
   - If they did something else (failed, skipped, logged), the switch to silent defaults is a behavior change. It needs its own justification, and probably a log or warning line so a missing config doesn't go unnoticed.

3. **Define exactly when `ConfigError` is raised.**
   - Is it only for a missing file (`FileNotFoundError`)?
   - What about permission errors, a path that is a directory, decode errors, or a malformed file?
   - Did `load_config` previously return `None` in any non-missing case, such as an empty file? If so, those paths need the same treatment.
   - If `ConfigError` covers more than "missing," the `schedule()` and `report()` handlers will silently use defaults for a broken config. That is probably not what you want. Consider catching only the missing-file case, or a subclass like `ConfigNotFoundError`.

4. **Add tests for the new behavior.** Existing `schedule()` and `report()` tests don't show the change works.
   - A unit test that `load_config` raises `ConfigError` for a missing path.
   - Tests that `schedule()` and `report()` fall back to defaults when `ConfigError` is raised.
   - A test for `main()`, which currently has none: missing config gives "no config" and exit code 2. This is the path you most want to stay exactly the same.
   - Update any existing tests that assert `load_config(...) is None`.

5. **Match the old output exactly in `main()`.** Confirm "no config" goes to the same stream as before (stdout or stderr) with the same text. Scripts or CI may depend on it.

6. **Clean up the old code.** Remove leftover `is None` checks in the callers so the old path doesn't linger as dead code. Preserve the original cause, e.g. `raise ConfigError(...) from e`, so debugging still shows the underlying `OSError`.

## Summary
The design is sound. The main risks are callers outside the listed three, an unclear scope for `ConfigError` (which could silently swallow broken configs), and no test coverage for `main()` or the new error paths. Fix those and this is ready to merge.

VERDICT: GO_WITH_CHANGES