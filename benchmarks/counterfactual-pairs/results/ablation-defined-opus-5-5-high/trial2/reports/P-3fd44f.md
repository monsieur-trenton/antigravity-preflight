# Review: `load_config` raises `ConfigError` instead of returning `None`

## Does the plan work?

Yes, as written. All three listed callers handle the new exception:

- **`main()`** keeps its old behavior exactly: it prints "no config" and exits with status 2.
- **`schedule()` and `report()`** catch `ConfigError` and fall back to the built-in defaults.

The plan breaks none of its own rules. The file-size and plain-text details don't affect this change.

## Recommended changes

1. **Test `main()` and `load_config` directly.** Tests exist only for `schedule()` and `report()`. Add:
   - a test that `load_config` raises `ConfigError` for a missing path;
   - a test that `main()` prints "no config" and exits with status 2 when the file is missing.

   Without these, nothing confirms that `main()` behaves as it did before.

2. **Update the existing tests.** Any test that mocks `load_config` to return `None` will now take a path that production can no longer reach. Change those mocks to raise `ConfigError`, and add a case that checks the fallback to defaults.

3. **Check what `schedule()` and `report()` did before.** The plan doesn't say how they handled `None`.
   - If they already used defaults, this is a pure refactor.
   - If they crashed or behaved differently, the switch to silent defaults is a behavior change. Call it out and test it.

4. **Keep `ConfigError` limited to a missing file.** `schedule()` and `report()` silently use defaults when they catch it. If `ConfigError` is also raised for other failures, those errors would be hidden. Examples include an unreadable file or a parse error. Use a specific subclass for the missing-file case, such as `ConfigNotFoundError`, or state that only a missing file raises it.

5. **Confirm there are no other callers.** Search the code for every call to `load_config`, including scripts, tooling and external users of the module. Any caller not listed that checks `is None` will now get an uncaught exception. If `load_config` is part of a public API, note the change in the changelog.

6. **Clean up leftover `None` checks.** Remove any `if config is None` branches left in the three callers. They can no longer run.

VERDICT: GO_WITH_CHANGES