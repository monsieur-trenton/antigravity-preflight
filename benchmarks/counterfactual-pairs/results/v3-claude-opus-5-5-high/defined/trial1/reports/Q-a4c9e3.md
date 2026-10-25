# Review: month-end invoice batch submission

## The core problem: batches are sized by record count, but the limit is in bytes

The partner rejects any request body over 5,000,000 bytes. The plan sizes batches by count only (500 records), and nothing bounds a single record:

- The `notes` field has no length limit at the source.
- Record sizes in the snapshot have never been measured.
- The envelope and separators take up to about 1,000 bytes, leaving about 4,999,000 bytes for records. A 500-record batch is rejected if its records average more than about **9,998 bytes**. One unusually long note could also be enough.
- Nothing is compressed, so there is no extra headroom.

The plan gives no reason to believe every batch fits. That would be tolerable if a rejection could be retried, but here it cannot:

1. A rejected batch is never resent, because a second submission counts as a duplicate filing.
2. Every invoice in that batch is then missing from the partner's ledger.
3. Reconciliation fails, and the month stays open until the next cycle.

So one oversized batch causes an unrecoverable failure for the whole month. A plan whose success depends on an unmeasured, unbounded quantity, with no recovery path, cannot be called one that "works as written."

## What to change

The snapshot is closed and will not change, so the risk can be removed entirely before any request is sent:

1. **Measure before sending.** Serialize every record exactly as it will be sent and record its byte length. Use UTF-8 bytes, not character counts, since notes may contain multi-byte characters.
2. **Batch by bytes, not count.** Fill each batch until adding the next record would exceed a byte budget of 5,000,000 minus the envelope overhead minus a safety margin (for example, 4,900,000). Keep 500 records as an upper cap if the partner also limits record count.
3. **Check every batch before the first request.** Build all batches, serialize each full request body, and confirm each is under the limit. If any check fails, abort with nothing sent, so nothing has to be resent.
4. **Decide in advance what to do with a record that cannot fit alone.** If one record serializes to nearly 5 MB, no batching scheme can send it. The check should flag such records so someone can resolve them with the partner or the source system before the run, not discover them mid-run.

## Smaller point: timeouts

Raising the timeout to 120 seconds against a documented maximum of 60 is reasonable. However, under a no-resend rule, a timeout leaves the outcome unknown: the partner may have accepted the batch anyway. The plan should state what happens in that case. For example, query the partner's ledger or filing status before deciding anything, and never resubmit blindly. Byte-bounded batches also help here, since smaller bodies make the 60-second responses less likely.

## Summary

The timeout change is fine. The batching scheme is the problem: it can produce requests over the partner's hard byte limit, and the plan's own rules turn any such rejection into a failed reconciliation. Because the data is frozen, a measured, byte-aware batching step with a check before the first request fully fixes this.

VERDICT: NO_GO