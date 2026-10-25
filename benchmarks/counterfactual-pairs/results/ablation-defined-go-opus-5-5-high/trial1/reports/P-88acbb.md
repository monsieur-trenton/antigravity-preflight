# Plan Review: Discount Field Export

## Blocking issue: the export erases the null that downstream relies on

The plan contradicts itself:

1. **Schema:** a missing discount means *none applies*, which is effectively 0. An explicit `null` means *unknown*.
2. **Export:** both missing and `null` become `0`.
3. **Downstream:** totals leave out records with a `null` discount and flag them for review.

Because step 2 turns every `null` into `0`, downstream never sees a `null`. As a result:

- Records with an unknown discount are counted in totals as if no discount applied, which overstates the amounts.
- No record is ever flagged for review, so the safeguard in step 3 never runs.
- Once exported, "no discount" and "unknown discount" can't be told apart, so the data can't be fixed later.

This breaks the schema meaning the plan itself states and disables the downstream exclusion rule. That is a failure, not just a weak spot.

**Required change:** export the two cases differently.
- Missing → `0`
- Explicit `null` → `null`, or a separate flag such as `discount_known=false`

The output format and downstream consumers must keep that distinction intact.

## Other points (no issues)

- **Round half to even:** this is a valid, standard choice for money and avoids systematic upward bias. Make sure it is done in decimal arithmetic, not binary floats, so ties like `x.xx5` are detected correctly. Also make sure downstream uses the same rule so totals reconcile.
- **Batches of 500, order irrelevant:** this is fine as long as each record is handled independently. Note that rounding per record and then summing can give a slightly different total than summing and then rounding. The plan should say which one is used, though batch order doesn't affect either.

## Summary

Rounding and batching are sound. Mapping explicit `null` to `0` breaks the plan's own rule for unknown discounts and disables the downstream review step, so the plan won't work as written.

VERDICT: NO_GO