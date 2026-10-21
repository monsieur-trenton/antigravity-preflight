**Rationale**

There is one blocker, and the snapshot's own text proves it.

- **Lines 2 and 3 conflict.** Line 2 gives the schema two different meanings: a missing discount means "none applies," and an explicit null means "not known." Line 3 exports both as `0`. That loses the "unknown" state at export time.
- **Line 4 can never work.** Downstream totals are supposed to leave out null-discount records and flag them for review. Because the export already turned nulls into `0`, no null ever reaches the totals. Records with an unknown discount are counted as having no discount and are never flagged. The text alone establishes this, so it is VERIFIED.
- **Line 5 is not a defect.** Rounding ties to the even digit is a valid choice, and nothing else in the snapshot contradicts it.
- **Line 6 is not a defect either.** The claim that batch order does not matter has no supporting evidence. But it does not conflict with any other line, and missing evidence is not a proven defect.

To fix this, export an explicit null as null or as a distinct marker, and keep `0` only for a missing discount.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | 3 | A missing discount and an explicit null are both exported as 0.