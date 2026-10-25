# Plan Review: Payment Worker Retries with Idempotency Keys

The plan satisfies its rule that no customer is charged twice for the same order. It works as written. A few gaps are worth fixing.

## Why the no-double-charge rule holds

- **The key is stable.** The order UUID is generated once at placement, stored with the order, and reused unchanged on every attempt. All attempts for an order therefore carry the same key.
- **Retries stay inside the dedup window.** Every attempt finishes within 10 minutes, well inside the processor's 24-hour window. Any retry reaches the processor while it still remembers the key.
- **Unknown outcomes are safe to retry.** If a timed-out attempt actually succeeded, the retry returns the original result with no second charge. If it never arrived, the retry produces the first and only charge. Retrying through ambiguity is the correct design here, not a risk.

## Suggested changes

1. **Separate definitive failures from transient ones.** The plan retries "timed-out or failed" submissions. If the processor recorded a decline or validation error under the key, every retry with that key just replays the same failure. Retry only timeouts, connection errors and 5xx/transient responses. Mark hard declines as failed straight away and surface them so the customer can act.

2. **Plan for exhausted retries.** After the 3 further attempts, a final timeout leaves the outcome unknown. Do not mark the order "unpaid" or "failed." Put it in a "payment pending/unknown" state and reconcile it before the 24-hour window ends. You can query the processor by key or replay the same key. Manual replays or retriggers after 24 hours would create a fresh charge.

3. **Guard any path that could change the key.** The guarantee depends entirely on the UUID never changing. Re-created orders, cloned carts, migrations, or a "retry payment" button that makes a new order record would all bypass deduplication. State explicitly that the charge key is always the original order's stored UUID.

4. **Handle concurrent in-flight duplicates.** Some processors reject a second request with the same key while the first is still processing, often with a 409. Treat that response as "in progress, check later," not as a failure. Consider a per-order lock or lease so two workers don't process the same order at once.

5. **Confirm the processor binds parameters to the key.** Check what happens if a retry carries a different amount for the same key. The worker should send identical payloads on every attempt, built from the stored order rather than recomputed.

None of these changes are needed to meet the stated rule. They improve correctness of order state, customer experience and robustness at the edges.

VERDICT: GO_WITH_CHANGES