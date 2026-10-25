# Review: Order Discount Export Plan

## Blocking issue: null and missing discounts are merged

The schema gives these two cases different meanings:

| Source value | Schema meaning | Planned export | Correct export |
|---|---|---|---|
| field missing | no discount applies | `0` | `0` ✅ |
| explicit `null` | discount unknown | `0` ❌ | `null`, or an explicit "unknown" marker |

The downstream totals step excludes null-discount records and flags them for review. Because the export turns every null into `0`, that step will never see a null, which causes three problems:

- **Wrong totals.** Records with an unknown discount are counted as having no discount. Revenue is overstated wherever a real discount existed but wasn't recorded.
- **The review safeguard stops working.** No records get flagged, so the failure is silent. Downstream can't tell "no discount" from "unknown discount."
- **The loss can't be undone.** Once both cases are `0`, the distinction can't be rebuilt from the export.

**Required change:** map missing to `0` and keep explicit null as null (or a sentinel the downstream step recognizes). Add a test with one record of each kind (missing, null, explicit `0`, non-zero) and check that only the null record is excluded and flagged.

## Non-blocking points to tighten

1. **Rounding implementation.** Round-half-to-even is a reasonable choice. Use a decimal type, not binary floating point, or ties won't be detected correctly. For example, `2.675` is stored as `2.67499…`.
2. **Where rounding happens.** Say whether you round per line, per order, or only on final totals. Rounding per line and then summing gives different results from summing and then rounding. Downstream should know which one it's getting.
3. **"Order doesn't matter" for batches.** This holds only if aggregation is commutative and nothing is rounded per batch. It also needs idempotent handling of retried or duplicated batches, so a re-run batch of 500 isn't counted twice. Say how records are deduplicated, for example by order ID.
4. **Partial last batch and failures.** Confirm that the final batch (fewer than 500 records) is handled, and say what happens to totals if one batch fails partway through.
5. **Validating discount values.** Decide what to do with negative discounts, discounts larger than the order amount, or values that aren't numbers. Flagging them is probably better than coercing them.

## Summary

The structure is sound. However, the null-to-0 mapping directly contradicts both the schema and the downstream design, and it would silently corrupt totals. Fix that mapping and clarify rounding placement and batch idempotency, and the plan is fine to proceed.

VERDICT: GO_WITH_CHANGES