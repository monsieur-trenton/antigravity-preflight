# Plan Review: Order Export (Discount Handling)

## Blocking issue: null and missing discounts are merged

The plan breaks the schema's meaning and the downstream contract.

- **Schema:** a missing discount means *none applies* (effectively 0). An explicit `null` means *unknown*.
- **Export:** both become `0`.
- **Downstream:** totals are expected to exclude null-discount records and flag them for review.

Because the export turns every `null` into `0`, downstream never receives a null. As a result:

1. Records with unknown discounts are **silently included in totals as zero discount**. Totals may be overstated, by the amount of whatever discounts actually applied.
2. **No records are ever flagged for review.** The safeguard does nothing, and nobody will notice, because the output looks valid.
3. The information is **lost for good** at export. Downstream cannot recover it.

**Required change:**
- Export a missing discount as `0`.
- Export an explicit `null` as `null`, or another explicit "unknown" marker that downstream recognizes.
- Add a test with all three cases (missing, `null`, and a real value). Confirm that downstream excludes and flags only the `null` case.

## Non-blocking points to clarify

- **Rounding rule.** Round-half-to-even is a valid choice. The plan should still specify:
  - **Where rounding happens:** per line, per discount, or only on final totals. Each gives different sums.
  - **That money uses decimal or integer-cent arithmetic, not binary floats.** With floats, ties like `x.xx5` often aren't exact ties, so half-even won't behave as intended.
  - **That downstream uses the same rule**, so reconciliations match.
- **Order of batches.** "Order doesn't matter" holds only if aggregation is commutative and exact. That is true with decimal or integer cents. With floats, summation order can change results. Also confirm that no step relies on sequence, such as running totals or "latest record wins" deduplication.
- **Batch retries and idempotency.** State what happens when a batch of 500 fails partway or is retried. Records must not be duplicated or dropped across batches. The final partial batch should also be handled explicitly.

## Summary

The batching and rounding approach is basically sound, apart from the details above. The null-to-0 mapping, however, is a correctness bug. It silently corrupts totals and disables the review process. Fix that mapping and add tests for it before proceeding.

VERDICT: GO_WITH_CHANGES