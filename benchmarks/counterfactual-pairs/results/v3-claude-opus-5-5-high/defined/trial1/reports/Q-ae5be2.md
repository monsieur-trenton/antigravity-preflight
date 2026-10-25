# Review: Checkout Payment Worker Retry and Idempotency Plan

## The no-double-charge rule holds

- **The key is stable.** The order UUID is generated once at order placement, saved with the order, and reused unchanged on every attempt. All attempts for an order carry the same key.
- **The timing fits.** All attempts finish within 10 minutes, well inside the processor's 24-hour deduplication window. Any retry reaches the processor while it still remembers the key.
- **Unknown outcomes are safe to retry.** If a timed-out attempt was actually accepted, the retry gets the original result back and no second charge happens. This is why retrying after an ambiguous timeout is correct.
- **Concurrent workers are safe too.** If two worker instances pick up the same order, they send the same key, so only one charge can result.

The plan does what it claims: a slow processor won't leave orders unpaid, and a customer can't be charged twice for an order. Nothing here causes the plan to fail or break its rule.

## Gaps worth fixing

1. **Retrying a failure the processor recorded does nothing.** The processor replays the original result for any key it has seen. If it recorded a failure (a decline, or an internal error tied to the key), every retry with the same key returns that same failure. The plan says failed submissions get up to 3 more attempts, but those attempts only help when the processor never recorded the request (timeouts, connection errors, some 5xx responses). The plan should:
   - stop retrying on definitive failures like declines and invalid cards;
   - decide how to recover from a recorded transient failure. This needs a deliberate new payment attempt, and it is only safe once the first charge is confirmed not to exist.

2. **There is no defined end state when retries run out.** After the last retry times out, the outcome is still unknown. The order should not be marked "failed" and silently re-queued. If someone or something resubmits after 24 hours with the same key, the processor treats it as new, and a double charge becomes possible. The plan should add:
   - an "unknown" or "pending reconciliation" status;
   - a lookup against the processor (by key or charge ID) to settle the real outcome;
   - an alert for orders that stay unresolved.

3. **Any resubmission should be checked against the 24-hour window.** Manual retries, replays from a dead-letter queue, or a re-run after an outage should first confirm with the processor whether a charge already exists. The worker must not rely on the key alone once more than 24 hours have passed since the first attempt.

4. **Minor points:**
   - Add jitter to the backoff.
   - Log the idempotency key and each attempt's outcome so reconciliation is possible.
   - Make sure the worker records a replayed success as "paid" when it arrives on a retry.

## Conclusion

The core design is sound and meets the stated rule. The changes above are about handling failures and the end of the retry window, not about fixing a double-charge bug in the plan as written.

VERDICT: GO_WITH_CHANGES