# Plan Review: Checkout Payment Worker

## Critical flaw: a new idempotency key on every attempt

The plan generates a **brand-new random UUID on each attempt, retries included**. This defeats the processor's idempotency protection and directly breaks the stated rule.

Here is how a double charge happens with the plan as written:

1. Attempt 1 is sent with key `A`. The processor accepts it and charges the customer, but the response times out on the way back.
2. The plan says a timeout doesn't mean failure, yet the worker still retries even though the outcome is unknown.
3. Attempt 2 is sent with key `B`. The processor has never seen `B`, so it **creates a fresh charge**.
4. The customer has now been charged twice for the same order.

With up to 3 retries, one order could be charged up to **4 times**. This isn't a rare edge case. It happens whenever the processor is slow, and that is exactly when the plan says retries are meant to kick in.

## What's sound

- Recognizing that a timeout is an ambiguous outcome, not a failure, is correct.
- Retrying so a slow processor doesn't leave orders unpaid is a reasonable goal.
- Bounded retries with backoff are good practice.
- All attempts finish within 10 minutes, well inside the processor's 24-hour deduplication window. With a stable key, every retry would be safely deduplicated.

## Required changes

1. **Use one idempotency key per order, not per attempt.** Either derive it from the order (e.g., `order:{order_id}:charge`) or generate it once and **persist it with the order before the first attempt**. Every retry must reuse that key. This change alone makes the retry policy safe.
2. **Persist the key before sending.** If the worker crashes and restarts, it must pick up the same key rather than minting a new one.
3. **Keep retries inside the 24-hour window.** This is already satisfied by the 10-minute limit. State it as an explicit invariant so future changes to retry policy don't break it quietly.

## Recommended improvements

- **Reconcile after retries are exhausted.** If all attempts time out, mark the order as "payment unknown" rather than "failed." Then query the processor by idempotency key or order reference before taking any further action, especially before any manual or customer-initiated retry, which would also need to reuse the same key.
- **Retry only on retryable errors.** Timeouts, 5xx responses, and network errors should be retried. Definitive declines such as insufficient funds or an invalid card should not.
- **Handle a key that's still in flight.** Some processors return a conflict error if a retry arrives while the original request is still processing. Treat that as "retry later," not as a failure.
- **Log and alert** on orders that had multiple attempts or ended in an unknown state.

## Summary

The retry strategy is only safe when every retry reuses the same idempotency key. With a fresh UUID per attempt, any timeout after the processor has accepted a charge leads to a duplicate charge, which violates the plan's own rule that no customer may be charged twice for the same order.

VERDICT: NO_GO