# Review: date-parsing library upgrade (2.8 → 3.0)

The plan needs no changes. Its one rule is that the 14 existing callers must behave exactly as they do today, and the plan backs that rule with direct evidence:

- **Caller behaviour:** All 14 callers were replayed against 3.0 using last month's full recorded inputs. Those inputs cover every date format the callers pass, and the outputs matched 2.8 byte for byte. This tests the rule directly.
- **Runtime compatibility:** 3.0 needs runtime 11 or later, and every billing host runs runtime 12.
- **Archived reporting tool:** It keeps its own pinned copy of 2.8 in a separate directory and isn't redeployed, so the upgrade can't affect it. It also isn't one of the 14 callers, so the rule doesn't cover it.
- **Timing:** The 14:00 deploy leaves 12 hours before the 02:00 invoice run. That is time to deploy, check and roll back if needed, and invoices aren't emailed until 06:00.
- **Refunds module:** It gets the fix it needs.

## Optional suggestions (not required)

- **Date values that last month didn't include:** The replay covers every format, but some behaviour depends on the date itself. Last month's data won't include the upcoming daylight-saving change (late October or early November), month-end in a 31-day month, or year-end. A few synthetic cases for these would make the test more thorough.
- **Rollback:** Write down how to revert to 2.8 and confirm it fits in the 14:00 to 02:00 window.
- **Night-of check:** After the first invoice run on 3.0, spot-check due dates before 06:00, while there is still time to hold the emails.

VERDICT: GO