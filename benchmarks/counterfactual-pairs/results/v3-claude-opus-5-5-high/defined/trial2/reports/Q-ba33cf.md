# Review: Date-Parsing Library Upgrade (2.8 → 3.0)

The plan is sound, and nothing in it fails or breaks the stated rule. Because invoice errors can't be recalled, a few gaps are worth closing before the 14:00 deploy.

## What holds up

- **Behavioral equivalence is well tested.** All 14 callers were replayed against 3.0 using a full month of recorded inputs covering every date format. The outputs matched 2.8 byte for byte. This is strong evidence that the rule will hold.
- **Runtime is compatible.** 3.0 needs runtime 11 or later, and every billing host runs 12.
- **The archived reporting tool is isolated.** It has its own pinned copy of 2.8 in a separate directory, isn't one of the 14 callers, and isn't redeployed. The upgrade doesn't touch it.
- **The timing leaves room.** About 12 hours separate the deploy from the 02:00 invoice run, and another 4 hours separate the run from the 06:00 email.

## Gaps worth closing

1. **The tests covered formats, not every input value.** Last month's data was September (30 days, no clock changes). Tonight's due dates may fall in late October or early November, when the clocks change: EU on 25 Oct and US on 1 Nov 2026. They may also hit month-end rollovers that September didn't exercise. Major library versions often change bundled timezone data or how ambiguous and nonexistent local times are handled.
   - *Fix:* add synthetic cases for the DST transitions, 31-day month-ends, and the year-end and leap-day cases due dates can reach. Run them against both versions.

2. **Nothing catches a bad result between 02:00 and 06:00.** If something slips through, nothing stops the emails.
   - *Fix:* compute tonight's due dates with both 2.8 and 3.0 and compare them before the 06:00 send. Alternatively, run a dry-run comparison against tonight's real inputs after the deploy and before 02:00. Either way, block or alert on any difference.

3. **There is no rollback step.** State who reverts to 2.8, how they do it, and the deadline: before 02:00, or at the latest before 06:00.

4. **Transitive dependencies may have shifted.** Check that the lockfile diff contains only the date library. Its transitive dependencies, such as a timezone-data package, should be pinned the same way they were in the replay test, so the tested build matches the deployed build.

None of these show that the plan will fail. They add margin to an evidence base that is already good, for an operation where mistakes can't be undone.

VERDICT: GO_WITH_CHANGES