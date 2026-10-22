## Review

**Does the change hold together?** Yes. All three known callers of `load_config()` are updated to handle the new exception:

- **`schedule()` and `report()`** catch `ConfigError` and fall back to the built-in defaults.
- **`main()`** catches `ConfigError`, prints "no config" and exits with status 2. This explicitly matches its old behaviour on `None`.

No caller is left expecting `None`, so nothing breaks as written.

**Gaps worth closing:**

1. **`main()` has no test.** It is the only caller whose behaviour the plan promises to preserve, and it is the one without coverage. Add a test that runs `main()` with a missing config and checks two things: "no config" is printed and the exit status is 2.

2. **`load_config()` has no test.** Add one test that a missing file raises `ConfigError`, and one that a present file still loads correctly.

3. **Existing tests may now give false passes.** Tests for `schedule()` and `report()` that mock `load_config` to return `None` for the missing-config case no longer test the real path. Change those mocks to raise `ConfigError`.

4. **Behaviour change in `schedule()` and `report()` is not stated.** The plan says what they do now (use defaults). It does not say what they did before with `None`. Confirm the defaults behaviour is unchanged, or call out the change explicitly.

5. **Old `None` checks become dead code.** Remove any `if cfg is None` branches left in the three callers.

6. **Other callers may exist.** Grep the codebase for every call to `load_config`. If it is a public or importable API, external code that checks for `None` will break silently and needs a changelog note.

7. **Scope of `ConfigError` is undefined.** The plan only covers a missing file. Decide whether unreadable files and permission errors also raise `ConfigError`, or still raise `OSError`, and whether callers should handle those cases.

The file being plain text under 10 KB does not affect this change.

**Conclusion:** The plan works as written. The test gaps, especially for `main()`'s exit code, should be fixed before merging.

VERDICT: GO_WITH_CHANGES