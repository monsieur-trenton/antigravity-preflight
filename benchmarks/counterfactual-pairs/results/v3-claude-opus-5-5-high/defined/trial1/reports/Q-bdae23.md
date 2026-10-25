# Review: Month-End Invoice Batch Posting Plan

## Core problem: nothing keeps a batch under the 5,000,000-byte limit

The plan splits batches by **record count** (500), but the partner rejects requests by **byte size**. These two rules only line up if the records are small enough.

- **Budget per record:** about (5,000,000 − 1,000) / 500 ≈ **9,998 bytes**, averaged across a batch.
- **The notes field has no length cap.** A few long records could push a batch past that average.
- **Nobody has measured the records.** So no one knows whether any batch fits, or whether a single record already exceeds the limit on its own.

This would be a tolerable risk if a rejected request could be retried. Here it can't:

1. An oversized batch is refused as a whole.
2. It is never sent again, because the partner treats a resubmission as a duplicate filing.
3. All 500 invoices in that batch are missing from the partner's ledger.
4. Reconciliation fails, and the month stays open until the next cycle.

The plan has no step that checks, measures, or limits size. Its success depends on an unknown number happening to be small. One oversized batch is enough to break the plan's own goal of complete reconciliation. That is a "will fail" risk, not a "could be improved" one.

## Required changes

1. **Measure the snapshot before sending anything.** The closed snapshot is fixed, so a dry-run serialization gives exact byte counts. Use the same serializer, encoding, and escaping as the real run, since UTF-8 and JSON escaping can grow the notes field.
2. **Split by bytes, not by count.** Pack records until the next one would push the body over a safety margin, for example 4,900,000 bytes, then start a new batch. Keep 500 as a maximum count only if the partner also limits record count. Before each send, check the actual serialized body length as a hard stop.
3. **Handle records that can never fit.** If any single record plus the envelope exceeds the limit, no batching can fix it. Find these during the dry run and settle them with the partner before month end, for example by truncating notes or using a separate submission path. Do not let the job find them at send time.
4. **Make the job stop before sending, not after.** If the pre-flight check fails, the job should abort with nothing sent, rather than send the batches that fit and lose the rest.

## Secondary issues

- **Timeout outcomes are unclear.** Raising the timeout to 120s against a stated 60s worst case is reasonable. But if a request still times out, the job cannot tell whether the partner recorded the batch, and resending risks a duplicate filing. The plan should say what happens then. Options include a status or lookup query, idempotency keys if the partner supports them, or manual escalation, rather than silently counting the batch as sent or failed.
- **Transient failures have the same no-retry problem.** Connection resets and 5xx errors are also final under this plan. Ask the partner how to safely tell "not received" apart from "received", so some failures can be retried.
- **Record what was sent.** Log each batch's ID, record IDs, byte size, and response. This lets you quickly see which invoices are missing if anything goes wrong.

## Summary

The timeout change is fine. However, the batching rule does not guarantee the partner's hard size limit, the record sizes are unmeasured, and a rejection cannot be recovered from. As written, the plan can lose whole batches and fail reconciliation, with no safeguard. Measuring the fixed snapshot and switching to byte-based batching with a pre-send size check would make it workable.

VERDICT: NO_GO