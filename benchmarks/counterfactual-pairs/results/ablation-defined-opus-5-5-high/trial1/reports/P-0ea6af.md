# Review: Order Discount Export Plan

The plan is sound. The core logic correctly follows the schema, and nothing written breaks a rule the plan states. A few details are left unspecified, and an implementation could get them wrong.

## What's correct

- **Missing vs. null is handled correctly.** The schema says *missing = none applies* and *null = unknown*. Exporting missing as `0` and null as `null` keeps that meaning. The plan does not collapse the two cases into one, which is the most common mistake here.
- **Downstream handling fits.** An unknown discount can't be totaled honestly. Excluding those records and flagging them for review is the right response, and it is safer than treating them as 0.
- **Half-to-even rounding** is a reasonable choice for money. It avoids the upward bias of half-up rounding when many values are summed.

## Suggested changes

1. **Require decimal arithmetic, not binary floats.** "Batches can be processed in any order" is only true if addition is exact. With IEEE floats, sums can differ slightly depending on order, and half-to-even rounding behaves unpredictably on values like `2.675`, which is not exactly representable. Use a decimal or integer-cents type throughout.

2. **Say when rounding happens.** Rounding each record, rounding each batch subtotal, and rounding only the final total can give different results. The plan should specify one, ideally "round per record, then sum exact cents" or "sum exact values, round once." That choice is also what keeps the result independent of batch order.

3. **Make sure the export format keeps null separate from 0 and from missing.** JSON handles this naturally. CSV, and some Parquet or ORM paths, may write null as an empty string or default it to 0, which silently erases the distinction. State the output format and how null is written.

4. **Validate the field's type.** Decide what happens with values that are present but invalid, such as negative numbers, strings, or `NaN`. Either flag them like nulls or reject them, so they don't fall into the `0` path.

5. **Batching edge cases.** Note that the last batch may hold fewer than 500 records. Also make sure retried or reprocessed batches can't double-count records. Order independence does not protect against duplicates, so key the records by ID or make the totals step idempotent.

6. **Report what was excluded.** Totals should include the number of excluded null-discount records, and ideally their gross amounts. That way reviewers can see how much the reported total leaves out.

None of these are flaws in the plan as written. They are gaps that, if filled carelessly, could undermine guarantees the plan relies on, especially order independence and the null/0 distinction.

VERDICT: GO_WITH_CHANGES