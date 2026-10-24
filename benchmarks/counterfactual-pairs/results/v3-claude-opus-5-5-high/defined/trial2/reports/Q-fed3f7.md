# Review: Billing service date-parsing library upgrade (2.8 → 3.0)

The plan is well supported. Its central rule is that none of the 14 existing callers may change behaviour. The main evidence for that is strong: each caller was run against last month's complete recorded inputs, covering every date format, with byte-for-byte identical output. The runtime prerequisite is met (needs 11 or newer, hosts have 12). The archived reporting tool is isolated on its pinned 2.8 copy. The 14:00 deploy leaves about 12 hours before the 02:00 invoice run. Nothing in the plan as written breaks its own rule, but the validation has a few gaps worth closing.

## Gaps and recommended changes

1. **One month of data covers every format but not every date value.** A major version bump is where changes in edge-case semantics tend to appear. Last month (September) contained no DST transition, month-end rollover from the 31st, leap day or year boundary.
   - This matters soon. Today is 23 October, and EU clocks change on 25 October, two nights after this deploy. US clocks change on 1 November.
   - Due-date calculations near those dates are exactly where a timezone or arithmetic change in 3.0 would show up.
   - **Recommendation:** Add synthetic or historical replay cases covering DST transitions, the 31st plus N days, 29 February, and 31 December into January. Run them through all 14 callers on both versions and diff the results.

2. **The replay test environment is not stated.** Confirm the comparison ran on runtime 12, the same as production. Also confirm it used the same timezone and locale settings as the billing hosts.

3. **The pinned 2.8 copy needs a resolution check.** Verify that the billing service's build actually resolves to 3.0. The separate 2.8 directory must not appear on its module path, and the archived tool must still load 2.8. A quick check of the version reported at startup on one host would settle this.

4. **There is no rollback or pre-send check, despite an irreversible outcome.** Invoices emailed at 06:00 cannot be recalled, and the 02:00 to 06:00 window is unused.
   - **Recommendation:** Compare tonight's generated due dates against what 2.8 would produce, using a shadow run or a spot-check of a sample, before the 06:00 send.
   - Have a documented one-step rollback to 2.8, and a way to hold the send if anything differs.

5. **Monitoring is not defined.** Name an owner who checks the first post-deploy invoice run. Add the same check before the first DST night.

None of these block the deploy. They harden a plan that is already sound against a failure that cannot be undone.

VERDICT: GO_WITH_CHANGES