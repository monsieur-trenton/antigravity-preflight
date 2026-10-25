# Plan Review: Order Discount Export

## Blocking issue: null and missing discounts become indistinguishable

The schema gives the discount field three states:

| Source state | Schema meaning | Exported as |
|---|---|---|
| Missing | No discount applies | `0` |
| Explicit `null` | Discount is unknown | `0` |
| A number | That discount | the number |

The export maps both missing and `null` to `0`. Missing → `0` is correct, but `null` → `0` turns "unknown" into "known to be zero."

This breaks the downstream rule. Totals are supposed to leave out records with a null discount and flag them for review, but once the export has run, no nulls remain. So:

- Records with an unknown discount are **counted in totals** as if they had no discount, which can overstate revenue or net amounts.
- **Nothing is flagged for review**, so the error never surfaces.
- The failure is silent. The output looks valid, so tests that only check the format or the totals pipeline will pass.

**Required fix:** Keep `null` as `null` in the export, or add an explicit flag such as `discount_known: false`. Map only a missing field to `0`. Make sure the serializer and any intermediate typed structures can represent null. For example, a non-nullable decimal column or a struct with a default of 0 would reintroduce the bug.

## Other points (non-blocking)

1. **Rounding with ties to even** works, but say where it is applied: on each record, or on aggregates after summing raw values. Rounding each record and then summing can give a different total than summing and then rounding. Pick one and document it. Also confirm that amounts use a decimal type and not binary floating point. Otherwise values like `2.675` won't round as you expect, regardless of the tie rule.
2. **Order-independent batching of 500** is fine as long as no step depends on order. This holds for rounding each record, and for summing exact decimals. It does not strictly hold for floating-point accumulation, which is another reason to use decimals. Also make sure the review flags and exclusions are collected across all batches, and that a failed or retried batch can't double-count records or drop flagged ones.
3. **Tests:** Add fixtures for all three discount states, and assert that `null` reaches downstream, is excluded from totals, and is flagged.

## Summary

The plan collapses `null` into `0` and so prevents the downstream rule it describes from ever applying. Unknown discounts would be silently treated as zero and never reviewed. This has to change before the plan can proceed.

VERDICT: NO_GO