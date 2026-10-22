# Review: `load_config` raising `ConfigError` on a missing file

**Caller coverage.** The plan names three callers: `schedule()`, `report()` and `main()`. Each one gets a handler, so none of them will hit an unhandled `ConfigError`.

**Behavior preservation.**
- `main()` keeps its observable behavior: it prints "no config" and exits with status 2, as it did when it received `None`.
- `schedule()` and `report()` fall back to the built-in defaults. This is the sensible reading of what a `None` config meant for them. If either one previously did something else with `None`, such as skipping work, its behavior would change. The plan implies defaults, so I take that as the intended baseline.

**Scope.** The file being plain text and under 10 KB doesn't affect the change. There is no streaming or partial-read concern, and a missing file stays a clean, single failure.

**Tests.** `schedule()` and `report()` have unit tests, so regressions in the fallback path should show up.

## Optional suggestions

None of these are required.

- **Add a test for `main()`'s exit path.** It should assert the "no config" output and exit status 2. This is the one caller whose contract is user-visible and has no test.
- **Add a test for `load_config` itself.** It should assert that a missing path raises `ConfigError`.
- **Check whether existing tests return `None`.** If the current `schedule()` and `report()` tests stub `load_config` to return `None` for the defaults case, update them to raise `ConfigError` instead. Otherwise they keep passing while testing a path that no longer exists.
- **Keep `ConfigError` specific to "file missing."** If it is ever raised for malformed content too, `schedule()` and `report()` would silently use defaults on a broken config instead of surfacing it. A subclass such as `ConfigNotFoundError`, or a narrow catch, would prevent that.

The plan works as stated: every caller is handled and the existing behavior is preserved.

VERDICT: GO