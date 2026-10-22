# Plan Review: Order Discount Export

The plan is internally consistent and matches the schema. I found nothing that would make it fail or break one of its own rules.

## Checks against the stated rules

- **Missing discount exported as 0.** The schema says a missing discount means none applies, so 0 is the right value. An explicit 0 and a missing field mean the same thing, so merging them loses nothing.
- **Explicit null exported unchanged as null.** This keeps the "not known" meaning instead of turning it into 0. That is the main way such exports go wrong, and the plan avoids it.
- **Downstream totals skip null discounts and flag those records.** This follows from preserving null. Unknown values are kept out of the sums, so they cannot quietly distort them, and the flag makes the gap visible rather than silent.
- **Rounding to the nearest cent, ties to even.** This rule is fully specified and needs no change. It only applies to actual numbers; null passes through untouched, as it should.
- **Batches of 500 in any order.** Mapping each record (missing → 0, null → null) depends only on that record, so batch order has no effect. Summing totals and flagging records are also order-independent operations.

## Optional suggestions (not needed for correctness)

1. **Parse fields so that missing and null stay distinct.** Some JSON or ORM layers return `None` for both a missing key and an explicit null. To be safe, read the discount with a check for whether the key exists, and add a test case for each of the three states (absent, null, number).
2. **Use decimal arithmetic for money.** Binary floating point can produce values that should be exact halves but come out slightly off, so ties-to-even never triggers. Floating-point sums can also differ slightly depending on order. Decimal types avoid both problems and keep the "order does not matter" claim strictly true.
3. **Say where rounding happens.** Rounding each record before summing can give a different total than rounding only the final sum. Either choice works, but documenting it keeps the export and the downstream totals consistent.

VERDICT: GO