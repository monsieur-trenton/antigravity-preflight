# Review: Month-End Invoice Batch Posting Plan

## The core problem: batch size is fixed by record count, but the limit is in bytes

The partner refuses any request body over **5,000,000 bytes**. The plan sends **500 records** per batch, with under 1,000 bytes of envelope. For a batch to fit, its records must average no more than about **9,998 bytes** each.

Nothing in the plan ensures that:

- **The notes field has no length cap.** One long note can push a record, and its batch, past the limit.
- **No one has measured the records.** The plan has no evidence that any batch fits.
- **No size check runs before sending.** An oversized batch will only be discovered when the partner rejects it.

The failure path is irrecoverable under the plan's own rules:

1. An oversized batch is refused.
2. The plan forbids resending, because a second submission counts as a duplicate filing.
3. Up to 500 invoices never reach the partner's ledger.
4. Reconciliation fails, and the month stays open until the next cycle.

One oversized batch is enough to break the outcome the plan exists to deliver. And the plan has no safeguard at the one step where a mistake can't be undone.

## What makes this fixable

The snapshot is **closed and fixed**. Every batch's exact size can be computed before anything is sent. The fix is cheap and deterministic.

## Required changes

1. **Batch by bytes, not just count.** Serialize each record exactly as it will be sent (same JSON encoder, UTF-8). Fill each batch until adding the next record would exceed a safe ceiling, such as 4,900,000 bytes after counting the envelope and separators. Keep 500 as an upper bound on record count if the partner requires it.
2. **Run a pre-flight pass over the whole snapshot before sending anything.** Build every batch, compute each body's exact byte length, and abort if any batch exceeds the ceiling. Nothing is sent until all batches pass.
3. **Handle records that can't fit at all.** If a single record serializes to more than about 4,999,000 bytes, no batching will help. Pre-flight should flag it for manual handling, such as truncation agreed with the partner or a separate channel, before the run starts.
4. **Count bytes, not characters.** Notes may contain multi-byte UTF-8 characters, and JSON escaping adds length. Measure the actual encoded body.
5. **Log the size and record IDs of every batch.** If something still goes wrong, you'll know exactly which invoices are missing.

## Smaller points

- **Timeout:** Raising it to 120 seconds against a stated 60-second worst case is reasonable. However, a client timeout leaves the outcome unknown: the partner may have accepted the batch. Under the no-resend rule, the plan should say how a timed-out batch is checked, for example by querying the partner's ledger, rather than leaving it ambiguous.
- **Smaller batches:** Size-based batching will likely mean more, smaller requests. That also lowers the chance of hitting the 60-second response time.

## Conclusion

The plan's correctness depends on an unmeasured, uncapped quantity staying under a hard limit. A single violation causes unrecoverable data loss and a failed reconciliation. That is a design gap, not a polish item.

VERDICT: NO_GO