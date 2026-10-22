# Plan Review: Order Discount Export

## Consistency check

**Missing vs. null discount.** The schema gives two different meanings, and the plan maps each one correctly:

| Input state | Schema meaning | Export | Correct? |
|---|---|---|---|
| Field missing | No discount applies | `0` | Yes. "None applies" is a known zero. |
| Explicit `null` | Discount unknown | `null` | Yes. Unknown stays distinct from zero. |
| Present value | Known discount | value, rounded | Yes |

The key risk is merging these two cases, and the plan avoids it. Exporting missing as `0` is safe because zero is the true value. Keeping `null` unchanged means no unknown value is turned into a false zero.

**Downstream totals.** Excluding null-discount records from totals and flagging them for review matches what null means here. An unknown value can't be summed honestly, and flagging keeps those records from silently disappearing. Missing-discount records export as `0`, so they are correctly included in totals.

**Rounding.** Round-half-to-even to the cent is a standard, well-defined rule for money. It avoids the upward bias of half-up rounding when summing many values. Applying it to `0` is trivial, and it is never applied to `null`, since those records are excluded.

**Batching.** Batches of 500 in any order work because each record's export is a function of that record alone. Totals are sums, which don't depend on order. Flagging is per record, so batch order doesn't affect it either.

I found no contradiction or failure in the plan as written.

## Optional robustness suggestions (not required changes)

- **Use decimal arithmetic, not binary floats.** With floats, half-even ties like `x.xx5` may not be represented exactly, and float sums can vary slightly with batch order. Decimal types keep both the rounding rule and order independence exact.
- **Confirm the serializer keeps explicit nulls.** Some JSON or CSV writers drop null fields or turn them into empty strings or `0`. Either would collapse the distinction the plan depends on.
- **Specify where rounding happens.** Rounding each amount before summing and rounding only the final total can give different results. Stating which one you use avoids confusion between export and downstream.
- **Add tests for the three discount states** (missing, null, present) and for half-even tie cases.

These would make a correct plan sturdier, but the plan doesn't need them to work.

VERDICT: GO