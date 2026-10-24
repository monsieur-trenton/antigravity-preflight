## Review

**The idempotency key strategy breaks the no-double-charge rule.**

The processor only deduplicates requests whose key it has already seen. Because the worker generates a new random UUID on every attempt, each retry looks like a new request and produces a new charge.

This happens in a normal case, not a rare one:

1. Attempt 1 is sent with key `A`. The processor accepts it and charges the customer, but the response times out.
2. The plan says a timeout doesn't mean failure, and the worker retries anyway when the outcome is unknown.
3. Attempt 2 is sent with key `B`. The processor has never seen `B`, so it charges again.

The customer is now charged twice for the same order. With up to 3 retries, they could be charged as many as 4 times.

**Required change:** Generate the idempotency key once per order, not once per attempt. Either derive it from the order ID or generate it once and persist it with the order before the first attempt. Reuse that same key on every retry.

The timing then works in your favor. All attempts finish within 10 minutes, well inside the processor's 24-hour deduplication window. A retry after a timed-out success will get back the original result instead of creating a second charge.

**Other parts of the plan are sound once the key is fixed:**
- Retrying on unknown outcomes is a reasonable choice and becomes safe with a stable key.
- Bounded retries with backoff are fine.

**Optional hardening (not required):**
- Persist the key before the first send, so a worker crash and restart still reuses it.
- Make sure no other code path, such as a manual "retry payment" action, can start a new key for the same order.

VERDICT: NO_GO