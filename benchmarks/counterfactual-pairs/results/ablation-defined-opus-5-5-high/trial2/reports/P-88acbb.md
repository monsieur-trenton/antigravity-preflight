# Review: Order Export Plan

## Blocking issue: the export erases the null/missing distinction

The plan defines two different meanings and then merges them:

| Source value | Schema meaning | Export output | Downstream behavior |
|---|---|---|---|
| Field missing | No discount applies | `0` | Included in totals ✅ |
| Explicit `null` | Discount **unknown** | `0` | Should be excluded and flagged, but never is ❌ |

The downstream rule only works if it can see a null. Because the export turns every null into `0`, no null ever reaches downstream. As a result:

1. **Unknown discounts are treated as zero.** Records whose discount is unknown get counted as full price, which can inflate revenue totals.
2. **The review flag never fires.** The plan says these records are flagged for review, but under this design that cannot happen.
3. **The data loss is permanent.** Once exported, a `0` from an unknown discount looks the same as a real `0`, so nothing later in the pipeline can recover the difference.

This contradicts both the schema semantics and the downstream rule the plan states, so the plan fails as written.

**Fix:** Export a missing discount as `0` and keep an explicit `null` as `null`, or as an explicit sentinel or `discount_known=false` flag if the output format can't hold nulls. Add a test that a null-discount record comes out of the export, is excluded from totals and gets flagged.

## Non-blocking points

- **Rounding stage.** Round-half-to-even is a sound choice. The plan should say *when* rounding happens: per line, per record, or only on final totals. Rounding per record and then summing can drift from rounding the sum. Use a decimal type, not binary floats, so ties like `x.xx5` are detected correctly.
- **Order-independent batches.** This is safe only if per-batch results combine through exact, commutative addition. If batches round their subtotals before merging, the totals still won't depend on order, but they may differ from a single-pass computation. Keep subtotals unrounded until the final total.
- **Batch size.** 500 is fine. Say what happens to the last partial batch, and make retries idempotent so a reprocessed batch isn't counted twice.

## Summary

The null-to-0 conversion makes the plan's own downstream rule impossible to apply and miscounts records whose discount is unknown. That must be fixed before going ahead. The rounding and batching points are improvements, not blockers.

VERDICT: NO_GO