# Review: Month-End Invoice Batch Job

## Main issue: nothing keeps a request under the 5,000,000-byte limit

The plan batches by **record count** (500), but the partner's limit is on **bytes**. Nothing connects the two:

- The `notes` field has **no length limit** at the source.
- The record sizes in the snapshot have **never been measured**, so the largest record is unknown.
- 500 records plus under 1,000 bytes of envelope stay under the limit only if the records **average under about 9,998 bytes**. A few records with long pasted notes, such as email threads or logs, could exceed that. A single record over about 5 MB could never be sent in any batch.

Errors here can't be undone:

- An oversized request is **rejected as a whole**, so all 500 invoices are lost, not just the large one.
- The job **never resends**, by design, because of the duplicate-filing rule.
- Any missing invoice **fails reconciliation** and keeps the month open until the next cycle.

So the plan doesn't merely carry some risk. It has no mechanism to meet a hard constraint, and if it misses, the damage is permanent. Its correctness depends on data nobody has looked at. That makes it NO_GO as written.

## Required changes

1. **Batch by serialized byte size, not record count.** Serialize each record first. Add records to a batch while `envelope + separators + sum(record bytes)` stays below a safety threshold, for example 4,900,000 bytes. You can keep 500 as an upper bound on count if the partner requires it.
2. **Measure the snapshot before sending anything.** The snapshot is closed and immutable, so you can do this as a dry run. Compute every record's serialized size, the maximum, and each planned batch's total. If any planned request exceeds the threshold, abort before sending. Since you only get one attempt, every check has to happen first.
3. **Decide what happens to a record that can't fit alone.** If any single record (plus envelope) exceeds the limit, the job can't send it. Detect this in the dry run and escalate before month-end. Options include agreeing a truncation or attachment approach with the partner, or a manual filing. Don't let the job discover it at send time.
4. **Measure the exact bytes you send.** Use the length of the final UTF-8 encoded body. Character counts are wrong when notes contain non-ASCII text, and JSON escaping of quotes, newlines, and control characters makes the body larger than the raw text.

## Smaller points

- **Timeouts are ambiguous outcomes.** Raising the timeout to 120 s against a documented 60 s maximum is reasonable. But if a request still times out, you won't know whether the partner recorded it, and you can't resend. Define a procedure for this case, such as querying the partner's ledger or status endpoint for that batch before any manual action. Also log the batch contents and IDs so you can reconcile by hand.
- **Record batch membership.** Persist which invoice IDs went in which request and what response each got. Any failure is then confined to a known set of invoices for manual follow-up.
- If the partner supports a per-batch idempotency key or status lookup, it's worth asking about. It would make the "never resend" rule less brittle.

## Summary

The timeout change is fine. The core sending logic ignores the one hard limit the partner enforces, on data with no size bound, under a one-shot rule where failure can't be recovered. Switch to byte-based batching with a pre-send dry-run check of the closed snapshot, and plan for records too large to send.

VERDICT: NO_GO