**Rationale**

Line 2 sets the rule that the 14 existing callers must behave exactly as they do today. The snapshot's own text supports that rule being met:

- **Caller behaviour (line 4):** all 14 callers were run against version 3.0 using last month's full recorded inputs. Those inputs are stated to cover every date format the callers pass, and the outputs matched version 2.8 byte for byte. This directly addresses the irreversible-invoice risk described on line 3.
- **Runtime (line 5):** version 3.0 needs runtime 11 or later, and every billing host already runs runtime 12.
- **Archived reporting tool (line 6):** it keeps its own pinned copy of 2.8, is not one of the 14 callers, and is not redeployed. It therefore falls outside the rule and is unaffected.
- **Timing (line 7):** the 14:00 deploy comes before the 02:00 invoice run, which leaves time to notice problems.

None of the lines contradict each other, and no required evidence is missing.

Two additions would make the plan more robust but are not required:

- a stated rollback step before 02:00
- a check that last month's input values, not just its formats, include edge cases such as month-end dates

Neither is needed for the plan as written to meet its own rule, so I have not raised either as a finding.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: NO_BLOCKERS_FOUND