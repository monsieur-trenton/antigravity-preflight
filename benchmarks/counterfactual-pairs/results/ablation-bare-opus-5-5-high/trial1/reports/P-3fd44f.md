## Review

The plan is mostly sound. Raising `ConfigError` is clearer than returning `None`, and every listed caller handles the new exception. Before merging, close the gaps below, mostly around preserving behavior and test coverage.

**1. Confirm the caller list is complete.**
The plan names `schedule()`, `report()` and `main()`. Any other caller will get an uncaught exception where it used to get `None`. Before merging:
- Search the codebase for all references to `load_config`, including scripts, plugins and any indirect calls.
- Check whether `load_config` is part of a public API that external code may call. If it is, this is a breaking change and needs a changelog entry or deprecation note.

**2. Check that `schedule()` and `report()` really used defaults before.**
The plan says they now use the built-in defaults when they catch `ConfigError`. It doesn't say what they did when they received `None`. Possible cases:
- If they already fell back to defaults on `None`, behavior is preserved and this is a pure refactor.
- If they crashed, skipped work or logged a warning, falling back to defaults silently changes behavior. That change should be made on purpose and noted.
- If they used to log something like "using defaults", keep that log.

**3. Define what `ConfigError` covers.**
The plan only mentions a missing file. Decide whether unreadable files (permission denied), decode errors or malformed content also raise `ConfigError`, and confirm each case is what you want:
- If they do, `schedule()` and `report()` will silently use defaults on a corrupt config. That is probably wrong, since a broken config should usually be reported.
- If they don't, those errors will propagate, which may also differ from the old behavior.

Consider a subclass such as `ConfigNotFoundError`, or narrow the catches so only "missing" triggers the defaults.

**4. Tests.**
- Existing tests for `schedule()` and `report()` that mock `load_config` to return `None` must be changed to raise `ConfigError`. Otherwise they will pass while testing a path that no longer exists.
- Add tests for `load_config` itself: it should raise when the file is missing and return the config when the file is present.
- `main()` has no test. Add one that checks a missing config prints "no config" and exits with status 2. Also check it prints to the same stream (stdout or stderr) as before.

**5. Minor points.**
- The plain-text, under-10 KB detail doesn't affect this change.
- Make sure `ConfigError` is defined somewhere all three callers can import it without circular imports.
- If `main()` loads the config and `schedule()` or `report()` also call `load_config`, check whether the double load is intended.

## Summary
The design is fine. The required changes are: verify the caller list is complete, confirm what `schedule()` and `report()` did with `None`, decide which failures `ConfigError` covers, update the mocks in the existing tests, and add tests for `main()` and `load_config`.

VERDICT: GO_WITH_CHANGES