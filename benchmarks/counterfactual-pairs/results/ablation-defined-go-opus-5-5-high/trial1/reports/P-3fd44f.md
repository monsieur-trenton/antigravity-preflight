## Review

**Caller coverage is complete.** The plan names all three callers of `load_config()`: `schedule()`, `report()` and `main()`. Each one handles the new exception:

- **`schedule()` and `report()`** catch `ConfigError` and fall back to the built-in defaults. This replaces the old handling of a `None` return.
- **`main()`** catches `ConfigError`, prints "no config" and exits with status 2. That matches its previous behaviour when it got `None`, so the user sees the same CLI result.

No caller is left with an uncaught exception, and none is left checking for a `None` that will no longer arrive. The change is self-consistent.

**Other details are consistent.** The config file is plain text and under 10 KB, so reading it raises no performance or encoding concerns. This change doesn't touch those properties either way.

**Optional suggestions** (these add robustness, not required fixes):

1. **Add tests for the new paths.**
   - A test that `load_config()` raises `ConfigError` on a missing file.
   - Tests that `schedule()` and `report()` fall back to defaults when `ConfigError` is raised. Existing tests that mock `load_config` to return `None` would no longer exercise the real failure path.
   - A test for `main()`'s exit status 2 and its "no config" message, which currently has no stated coverage.
2. **Scope the exception precisely.** Make sure `ConfigError` is raised only for a missing file, unless you intend otherwise. Other errors, such as permission denied or a path that is a directory, then keep their current behaviour and don't silently fall back to defaults.
3. **Remove the dead `None` checks.** Once the exception path is in place, delete any leftover `if config is None` checks in the callers.

None of these are needed for the plan to work as stated.

VERDICT: GO