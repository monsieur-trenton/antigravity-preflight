# Review: Order Export Plan

## Critical issue: explicit null is collapsed into 0

The plan says the schema gives a missing discount and a null discount different meanings:

- **Missing** means no discount applies, so the value is 0.
- **Explicit null** means the discount is unknown.

The export then writes both as `0`. That throws away the difference the schema defines, and it breaks the downstream rule:

- Downstream totals are supposed to **leave out null-discount records and flag them for review**.
- After the export, no record ever reaches downstream with a null discount. Every unknown discount arrives as a confident `0`.
- So records that should be excluded and flagged are **silently included in totals**, with an assumed discount of zero. Revenue or net totals will be overstated wherever a real discount existed but wasn't known. The review queue also stays empty, so nothing alerts anyone to the problem.

This is not a robustness gap. The plan contradicts the rules it states, so it will produce wrong totals.

**Required change:** Keep null as null, or as some other unambiguous "unknown" marker, all the way through the export. Map only a *missing* discount to `0`. Make sure the output format can actually carry a null (for example, the CSV/JSON encoding and the column type are nullable).

## Other points (not blocking)

- **Rounding:** Rounding half to even at the cent is fine as stated. Say *where* it happens. Rounding each record before summing can give a different total than summing first and rounding once. Also use decimal or integer-cent arithmetic rather than binary floats, so that ties are real ties.
- **Batches of 500 in any order:** This is fine as long as each record is handled independently and totals are aggregated with exact (decimal) arithmetic. With exact arithmetic, the order of summation can't change the result.

## Summary

The export erases the null/missing distinction, so the downstream rule to exclude and flag null discounts can never fire. Unknown discounts get counted as zero.

VERDICT: NO_GO