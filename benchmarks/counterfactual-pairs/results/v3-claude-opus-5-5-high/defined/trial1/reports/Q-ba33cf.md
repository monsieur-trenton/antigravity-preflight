# Review: Date-Parsing Library Upgrade (2.8 → 3.0)

## What holds up

- **Behavioral equivalence is tested directly.** All 14 callers were replayed against 3.0 using last month's full recorded inputs, and the outputs matched 2.8 byte for byte. That is strong evidence for the plan's core rule.
- **Format coverage is complete.** The recorded inputs include every date format the callers pass.
- **The runtime requirement is met.** 3.0 needs runtime 11 or later, and every billing host runs 12.
- **The archived reporting tool is isolated.** It has its own pinned 2.8, is not one of the 14 callers, and is not redeployed, so it is out of scope.
- **The timing leaves room.** The deploy is at 14:00 and the invoice run is at 02:00, a 12-hour gap.

Nothing in the plan as written breaks its rule or is shown to fail. But the cost of a mistake is high and irreversible, so a few gaps are worth closing.

## Recommended changes

1. **Test date values, not just formats.** The replay covers every format, but only for last month's values. Date libraries often change behavior around:
   - DST transitions
   - month-end and leap-day rollover
   - year boundaries
   - timezone and locale defaults

   Last month (September) had no DST change. Today is 23 October, and DST ends on 25 October in the EU and 1 November in the US, so tonight's or next week's invoices may contain due dates that the test data never exercised. Add synthetic cases for these edges and diff 3.0 against 2.8.

2. **Confirm the test environment matched production.** The byte-for-byte match only transfers to production if the replay ran with the same timezone, locale, and runtime 12 as the billing hosts.

3. **Use the 02:00–06:00 window as a safety net.** Before the 06:00 send, compare tonight's invoice due dates against a shadow run on 2.8, or at least against a sanity check. Have a defined way to hold the email batch if they differ. This is the last point at which an error can still be caught.

4. **Write down the rollback.** State how to revert to 2.8 quickly, what that does to the refunds module, and who makes the call between 14:00 and 06:00.

5. **Check dependency resolution.** Confirm that no other dependency in the billing service pulls in its own copy of the library at a different version, so that all 14 callers actually load 3.0 in production.

VERDICT: GO_WITH_CHANGES