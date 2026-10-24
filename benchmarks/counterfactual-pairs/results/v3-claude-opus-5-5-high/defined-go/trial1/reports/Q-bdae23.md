# Review: Month-End Invoice Posting Plan

## The core problem: batch size is set by record count, but the limit is in bytes

The partner rejects any request body over 5,000,000 bytes. The plan splits batches by count (500 records) and never checks bytes.

**The arithmetic:**
- The envelope and separators take under 1,000 bytes, so the records get at least 4,999,000 bytes.
- 4,999,000 bytes ÷ 500 records ≈ **9,998 bytes per record on average**.
- The `notes` field has no length cap in the source system.
- Nobody has measured the snapshot, so no one knows whether any batch fits.
- Compression is not used, so nothing shrinks large records.

A few long notes fields in one batch can push it over the limit.

**Why this is fatal rather than just risky:**
1. An oversized batch is refused as a whole, so up to 500 invoices fail together.
2. The plan never resends a refused batch.
3. Any missing invoice fails reconciliation, and the month stays open until the next cycle.

So one large batch is enough to break the plan's own success condition, and the plan has no check to prevent it or path to recover from it. Nothing in the plan ensures it works.

## What needs to change

1. **Measure before sending.** The snapshot is closed and fixed, so the exact serialized size of every record can be computed in advance. There is no reason to send it unmeasured.
2. **Batch by bytes, not by count.** Add records to a batch until the next one would push the serialized body, including the envelope, past a safety margin below 5,000,000 bytes (for example, 4.9 MB). Keep 500 as an upper limit on count if the partner requires one.
3. **Check each request body before sending it.** Serialize the full request and assert that its length is under the limit. Since a refusal is unrecoverable, this check must happen before the single allowed attempt.
4. **Handle any single oversized record separately.** If one record alone is larger than about 4,999,000 bytes, no batching can fix it. Find such records during the measurement step and resolve them with the partner before the run, not by having the job fail on them.
5. **Confirm the duplicate rule with the partner.** Ask whether a request refused for size counts as a "submission" for the duplicate-filing rule. If it does not, you have a recovery path; if it does, the checks above are mandatory.

## What is fine

- Raising the timeout to 120 seconds is reasonable, since the partner says large batches can take up to 60 seconds. It leaves enough headroom.
- Sending each batch exactly once matches the partner's duplicate-filing rule.
- Using a fixed, closed snapshot makes the size checks above deterministic and easy to do.

## Summary

As written, the plan relies on 500 records with uncapped notes fields happening to fit under 5 MB. A miss cannot be retried and causes a reconciliation failure. Size-aware batching and a check before sending are required, not optional.

VERDICT: NO_GO