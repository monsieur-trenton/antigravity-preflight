## Review

**The plan breaks its own rule. A routine timeout can charge a customer twice.**

The plan establishes these facts:

1. The processor deduplicates only on idempotency key. A key it hasn't seen always produces a fresh charge.
2. A timeout can happen *after* the processor has accepted and charged.
3. The worker retries after timeouts even when the outcome is unknown.
4. The worker generates a **new random UUID on every attempt**, including retries.

Together these produce a double charge:

- Attempt 1 (key A) reaches the processor and the charge succeeds, but the response times out.
- The worker retries with key B. The processor has never seen B, so it charges again.
- The customer is now charged twice for the same order. With up to 3 retries, they could be charged up to 4 times.

This isn't an edge case. It is the normal failure mode the retry logic exists to handle. Because each attempt uses a fresh key, the processor's idempotency guarantee never applies.

**Required change:** use a single idempotency key per order and reuse it on every attempt for that order. Either derive it from the order ID or generate it once and store it with the order before the first attempt. Every attempt finishes within 10 minutes, well inside the processor's 24-hour window. So a retry after an ambiguous timeout will either return the original result or perform the one and only charge, never a second one. With this change, the deliberate retry-on-unknown behavior becomes safe and still meets the goal of not leaving orders unpaid.

**Secondary notes (not blocking once the above is fixed):**
- Persist the key durably before the first submission, so that a worker crash or restart mid-retry reuses the same key instead of minting a new one.
- If anything outside this retry loop could later resubmit an order, such as a manual retry or a reconciliation job, it must use the same key. Otherwise it should reconcile against the processor rather than charge blindly, especially after 24 hours.

VERDICT: NO_GO