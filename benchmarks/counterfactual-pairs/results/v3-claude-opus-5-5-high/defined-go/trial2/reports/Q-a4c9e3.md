# Review: Month-End Invoice Batch Job

## Main issue: nothing keeps a batch under the 5,000,000-byte limit

The plan sizes batches by **record count** (500), but the partner enforces a **byte** limit. Nothing in the plan connects the two.

- **The budget per record is small.** After the envelope overhead (under 1,000 bytes), 500 records must fit in about 4,999,000 bytes. That averages about **9,998 bytes per record**.
- **The size of a record is unbounded.** The free-text `notes` field has no length limit at the source. One record with a pasted email thread, base64 attachment or log dump could push its batch over the limit.
- **Nobody has checked.** Record sizes in the snapshot have not been measured, so whether every batch fits is unknown.
- **A failure cannot be fixed in the same cycle.** An oversized batch is rejected whole, which drops 500 invoices. The plan forbids a resend because the partner would treat it as a duplicate filing. Reconciliation then fails, and the month stays open until the next cycle.

So the plan's success depends on an untested assumption, and if that assumption is wrong, the failure is guaranteed and cannot be recovered. That makes this a defect, not an optional improvement.

## The fix is easy

The snapshot is closed and will not change. That means the exact serialized size of every batch can be known **before anything is sent**. Do one or both of these:

1. **Batch by bytes.** Serialize each record first. Fill each batch until adding the next record would exceed a safe limit, such as 4,900,000 bytes after counting the envelope and separators. Also cap the batch at 500 records if the partner requires that.
2. **Pre-flight check.** Before sending anything, serialize every batch exactly as it will go out. Abort, without sending, if any batch is over the limit. Also flag any single record that is too large to fit in a batch by itself. That record needs a decision, such as truncating its notes by agreement with the partner. Silent truncation is not acceptable.

Either way, the "one request per batch, never resend" rule stays intact, because no request is sent until every request is known to fit.

## Other points (minor)

- **Timeout:** 120 seconds covers the partner's documented 60 seconds with room to spare. That is fine. If a timeout does happen, the batch's status is unknown and it cannot be resent. You need a way to check the partner's ledger, or a manual escalation step, rather than guessing.
- **Per-batch log:** Record batch IDs, record counts, byte sizes and partner responses. This lets you diagnose a reconciliation failure without resubmitting anything.

## Summary

As written, the plan can drop up to 500 invoices with no way to recover them in the same cycle, and it has no protection against that. Measuring the batches or batching by bytes is required before this runs.

VERDICT: NO_GO