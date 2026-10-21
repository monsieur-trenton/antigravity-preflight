# Review: Order Discount Export Plan

The core semantics are sound. Exporting missing as `0` and explicit `null` as `null` matches the schema: "none applies" maps to zero, and "unknown" is preserved instead of being guessed. Excluding and flagging null-discount records downstream follows from that. There are no logical contradictions, but a few details need to be pinned down before implementation.

## Issues to address

1. **Missing vs. null must survive parsing.** Many parsers and accessors treat the two the same. Python's `dict.get("discount")` returns `None` for both, and some ORMs or deserializers turn absent fields into null. The plan should require an explicit presence check, such as `"discount" in record`, and include a test case for each of the three states: absent, `null`, and a value.

2. **The output format must be able to represent null.** JSON can. CSV and some columnar formats cannot reliably tell null apart from an empty string. Name the export format, and if it is CSV, define the null encoding and confirm that downstream consumers read it the same way.

3. **Say where rounding happens.**
   - Round per line, per order, or only on final totals? Each gives different results.
   - Use decimal or integer-cent arithmetic, not binary floats. With floats, ties like `x.xx5` are often not exact ties, so half-to-even rounding behaves unpredictably.
   - Check that downstream systems use the same rounding mode, or totals will drift.

4. **"Order does not matter" depends on point 3.** Float summation is not associative, so batch order can change totals in the last digit. With decimal or integer cents, the claim holds.

5. **Report what was excluded.** Totals that silently drop null-discount records can mislead. Report the count and possibly the gross amount of excluded or flagged records next to each total.

6. **Batch retry and idempotency.** If a batch of 500 fails partway or is retried, records could be duplicated or double-flagged. State whether batches are atomic and whether reprocessing is safe.

7. **Value validation (minor).** Define handling for negative discounts, discounts larger than the order amount, and non-numeric values. Reject them, flag them, or pass them through?

## Summary

The null and missing handling is correct and well reasoned. The changes needed are specification gaps, mainly parsing fidelity, serialization format, and where and how rounding happens. None of them requires redesigning the plan.

VERDICT: GO_WITH_CHANGES