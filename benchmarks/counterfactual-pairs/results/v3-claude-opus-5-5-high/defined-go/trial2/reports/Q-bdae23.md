# Review: Month-End Invoice Batch Posting Plan

## The blocking issue: batch size is capped by record count, but the limit is in bytes

The partner refuses any request body over **5,000,000 bytes**. The plan splits batches by **record count (500)**, not by size.

- With under 1,000 bytes of envelope and separators, 500 records must average under roughly **9,998 bytes** each.
- Every record has a **notes field with no length cap**.
- **Nobody has measured** the serialized records, so the largest record size is unknown. Nothing in the plan keeps a 500-record batch under the limit.

On its own this would be a risk to manage. The plan's other rules make it a failure with no recovery:

1. A refused batch is **never sent again**, because the partner treats a resubmission as a duplicate filing.
2. If **any** invoice is missing, reconciliation fails and the month stays open until the next cycle.

So one oversized batch causes up to 500 invoices to be missing for good this cycle, and the month cannot close. The plan has no step that detects this before sending. Its success depends entirely on an assumption nobody has checked.

## This is cheap to fix

The input is a **closed, fixed snapshot**, so its size is fully knowable before anything is sent. Either of these fixes would close the gap:

- **Pre-flight measurement:** serialize every batch and check each one against 5,000,000 bytes minus envelope overhead, with a safety margin, before sending anything. Abort or re-split if any batch is too large.
- **Byte-based packing (better):** build batches from serialized size, with a byte budget of about 4.9 MB and at most 500 records. A single record that cannot fit in any request should stop the run before submission. It needs manual handling, not a refused request.

Either way, the check must run before the **first** request. The plan cannot rely on refusals to signal problems, because a refusal is already unrecoverable.

## Other points

- **Timeout:** raising it from 30 s to 120 s comfortably covers the partner's stated maximum of 60 s. This is fine.
- **Ambiguous outcomes (suggestion):** with a no-resend rule, a timeout or dropped connection leaves you unsure whether the partner accepted the batch. It would help to define how that case is checked with the partner, for example by querying the ledger, rather than resending.
- **Byte counting:** measure size as UTF-8 encoded bytes of the exact body sent, not as character counts. Non-ASCII text in notes makes these differ.

## Conclusion

As written, the plan has no safeguard against exceeding the 5 MB limit. Its input has an uncapped field of unmeasured size, and its own rules make any refusal unrecoverable. A size check on the fixed snapshot, or byte-based batching, is a required change.

VERDICT: NO_GO