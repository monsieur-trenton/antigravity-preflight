# Review: Upgrading the billing date-parsing library from 2.8 to 3.0

**The rule:** none of the 14 existing callers may behave differently after the upgrade, because a mistake would put wrong due dates on invoices that can't be recalled.

**Does the evidence support the rule?** Yes.
- All 14 callers were run on 3.0 against last month's complete recorded inputs.
- Those inputs include every date format the callers supply.
- The output was byte-for-byte identical to 2.8.
- This is direct evidence across the full input space the callers use, not a sample or spot check.

**Prerequisites:**
- **Runtime:** 3.0 needs runtime 11 or newer. Every billing host already has runtime 12, so no runtime change happens alongside the library change.
- **Archived reporting tool:** it is outside the 14 callers, keeps its own pinned 2.8 copy, and is not redeployed. The upgrade can't affect it, and leaving it alone is correct.
- **New refunds module:** it is the reason for the upgrade, not one of the 14. The no-change rule doesn't apply to it.

**Timing:** shipping with the routine 14:00 deploy leaves about 12 hours before the 02:00 invoice run. A bad deploy would surface well before any invoice is produced or emailed.

**Optional hardening (not required):**
- If any caller's output depends on the current date or time zone (relative dates, local-time conversions), a replay of last month's inputs might not cover tonight's conditions. One example is a daylight-saving transition in the coming days that didn't happen during the recorded month. Quickly confirming that no caller depends on "now", or re-running the comparison with a frozen clock set to tonight, would close this.
- Having a one-step rollback to 2.8 ready before 02:00 is cheap insurance.

Neither is needed for the plan to meet its stated rule. The comparison already covers the 14 callers' complete input set.

VERDICT: GO