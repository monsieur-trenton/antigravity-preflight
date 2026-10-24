# Review: Month-End Invoice Batch Submission

## The blocking problem: nothing keeps a batch under 5,000,000 bytes

The plan sets batches by **record count** (500), but the partner's limit is on **bytes**. These facts combine badly:

- **Each record's size is unbounded.** The free-text notes field has no length limit at the source.
- **No record's size is known.** The snapshot's serialized sizes have never been measured.
- **The margin is small.** With under 1,000 bytes of envelope, 500 records must average under about 9,998 bytes each. One record with a long note, such as a pasted email thread or an embedded document, could push its batch over.
- **The payload is uncompressed,** so nothing shrinks it.

If a batch goes over, the plan has no way to recover:

1. The partner rejects the **whole** request, so all 500 invoices are lost, not just the large one.
2. The job **never resends**, and a manual resend would count as a duplicate filing.
3. Any missing invoice makes **reconciliation fail**, and the month stays open until the next cycle.

The plan therefore has no step that prevents the failure, no way to detect it beforehand, and no recovery afterwards. Whether this month's data happens to fit is unknown. That is a gap in the design, not an edge case.

## Required changes

The snapshot is closed and will not change, so the risk can be removed before anything is sent.

- **Measure first.** Before sending, serialize every record in the snapshot exactly as it will be sent (same JSON encoding and escaping). Record the largest record size and each planned batch's total size. If any batch plus envelope reaches 5,000,000 bytes, stop before sending anything.
- **Batch by bytes as well as count.** Build each batch until adding the next record would go over a byte budget. Use a safe margin, such as 4.5 MB including the envelope. Keep 500 as an upper limit on count if the partner requires it.
- **Handle a single oversized record.** If one record alone exceeds the budget, the job must stop and flag it before submitting anything. It must not send a batch it knows will be rejected. Agree with the partner beforehand how such a record is handled, for example truncating notes or filing it separately.
- **Run the check before any request.** Partial submission is also unrecoverable under the no-resend rule, so the whole snapshot should pass validation before the first batch goes out.

## Smaller points

- **Timeout:** Raising it to 120 seconds, double the documented 60-second maximum, is reasonable. Also decide what a timeout means. Because the job cannot resend, a timed-out request has an **unknown** outcome. It should be confirmed with the partner, for example through a status query, rather than assumed to have failed or succeeded. This is a robustness gap rather than the main blocker, but it comes from the same no-resend rule.
- **Byte counting:** Measure the bytes actually sent (UTF-8 encoded, after escaping), not character counts. Notes containing non-ASCII text or many escaped characters will be larger in bytes than in characters.

## Summary

The plan sends fixed-count batches of records with unbounded, unmeasured sizes to an endpoint with a hard byte limit. Any rejection cannot be resent and causes reconciliation to fail. Because the snapshot is static, measuring it and batching by size before sending would fix this cheaply. Without those steps, the plan cannot be relied on to meet the outcome it requires.

VERDICT: NO_GO