# Plan Review: Order Discount Export

## What holds up

**The discount semantics are consistent from end to end.**

| Source state | Schema meaning | Exported as | Downstream handling |
|---|---|---|---|
| Field missing | No discount applies | `0` | Included in totals |
| Explicit `null` | Discount unknown | `null` | Excluded from totals, flagged |
| Value present | Known discount | Value | Included in totals |

- Mapping "missing" to `0` matches the schema's "none applies" meaning.
- Keeping `null` as `null` preserves "unknown." Converting it to `0` would silently assert something the data doesn't say.
- Downstream exclusion and flagging is the right response to unknown values. It doesn't bias totals by guessing.
- No step contradicts another, and no rule the plan states gets broken.

**Round-half-to-even is a sound choice for money.** It avoids the upward drift that round-half-up causes when many values are summed.

**Order-independent batches of 500 are fine.** Sums are commutative, and nothing in the plan depends on processing order.

## Recommended improvements

1. **Specify how the distinction survives serialization.** The plan relies on `missing` and `null` staying distinct at both ends.
   - The reader must keep "key absent" separate from "key present with null." Many JSON libraries, ORMs and dataclass defaults merge the two.
   - The output format must be able to represent `null` separately from `0`. In CSV, an empty cell is ambiguous, so define an explicit null marker or use JSON.
   - Add tests for all three cases: absent, `null`, and a numeric value.

2. **Say when rounding happens.** Rounding each record and then summing can give a different total than summing unrounded values and rounding once. Pick one approach and document it.
   - Also require decimal or integer-cent arithmetic, not binary floats. Otherwise ties like `x.xx5` may never reach the rounding step as exact ties, and the half-even rule won't apply as intended.

3. **Make batches idempotent.** Order independence doesn't cover retries or partial failures. Make sure a batch that is re-run doesn't double-count records or double-flag nulls.

4. **Decide what gets flagged.** Say whether the review flag is set per record or per batch, and where it is reported. That way, excluded records stay visible in the totals output.

None of these block the plan, but items 1 and 2 are where implementations most often drift from what the plan intends.

VERDICT: GO_WITH_CHANGES