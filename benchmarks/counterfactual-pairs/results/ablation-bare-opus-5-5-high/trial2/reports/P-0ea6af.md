# Plan Review: Order Discount Export

## Summary

The plan is internally consistent. It keeps the schema's distinction between "missing" and "null," and the downstream handling matches that meaning. I found no logical errors. A few implementation details should be pinned down, because they are common sources of silent bugs.

## What's correct

- **Missing → 0.** The schema says a missing discount means none applies, so 0 is the right value.
- **Null → null.** The schema says null means unknown. Passing it through unchanged keeps that information, and avoids the classic mistake of coercing unknown to 0.
- **Downstream handling.** Totals leave out null-discount records and flag them for review. This follows from "unknown" and prevents totals that look precise but are wrong.
- **Round half to even.** This is a reasonable choice for money and avoids systematic upward bias across many records.
- **Order-independent batches.** This holds, given the per-record logic described and the notes below.

## Points to make explicit (not blockers)

1. **Detecting missing vs. null.** The export must use a check that tells "key absent" apart from "key present with null." Examples are `"discount" in record` rather than `record.get("discount")`, or `Option`/`undefined` vs. `null`. Many JSON libraries, ORMs and dataclass/struct decoders merge the two by default. Add a test for each case.
2. **Explicit zero.** Confirm that an explicit `discount: 0` passes through as 0. It should not be treated as missing or as falsy-null.
3. **Decimal arithmetic.** Use a decimal or integer-cents type, not binary floats. Half-to-even rounding on floats misbehaves on ties like 2.675. Float summation is also not associative, which would quietly undermine the claim that order doesn't matter.
4. **Where rounding happens.** State whether rounding is applied per record before summing, or only to final totals. Either works, but the results differ, and downstream consumers should know which one is used.
5. **Review flags.** Specify where flagged records go, such as a separate list, a column or a log. Excluding records from totals without a durable record of the exclusions makes the totals hard to audit.
6. **Partial-batch failures.** Batches are order-independent, but say what happens if one batch fails: retry, skip, or abort. Also confirm that retries can't double-count records or flags.

## Verdict rationale

The core data semantics are correct and the design is sound. The items above are clarifications and tests to add during implementation. They don't change the plan's approach.

VERDICT: GO