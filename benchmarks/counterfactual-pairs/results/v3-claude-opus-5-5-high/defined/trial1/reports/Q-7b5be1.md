## Review

**The plan breaks its own rule: a customer can be charged twice for the same order.**

The failure path follows directly from the stated facts:

1. Attempt 1 is sent with key `K1`. The processor accepts it and charges the customer, but the response times out.
2. The worker retries on purpose, even though the outcome is unknown.
3. Attempt 2 uses a **new** random UUID `K2`. The processor has never seen `K2`, so it creates a fresh charge.
4. The customer has now been charged twice for one order. With up to 3 retries, they could be charged up to 4 times.

The idempotency mechanism would prevent this, but generating a new key on every attempt switches it off. Retrying when the outcome is unknown is a reasonable choice only if the retries are idempotent. Here they are not.

### Required changes

- **Use one idempotency key per order, not per attempt.** Generate it once, for example a UUID created with the payment record or a value derived from the order or payment ID. Save it durably before the first submission, and reuse it on every retry. That way a worker restart or crash also resumes with the same key.
- **The timing already fits.** All attempts finish within 10 minutes, well inside the processor's 24-hour deduplication window, so a reused key will always be recognized.
- **Make sure the worker itself can't submit the same order twice.** Two workers, or a re-enqueued job, must not run the same order at the same time with different keys. Store the key on the order or payment row, not in job memory, and use a lock or lease so only one worker handles an order.

### Recommended improvements

- If the processor offers a lookup endpoint, check the outcome of the existing key after the final timeout, before marking the order failed. This avoids leaving an order "unpaid" when it was actually charged.
- If a payment is ever deliberately re-attempted after more than 24 hours, or after a confirmed decline, decide explicitly whether to issue a new key. Do this as a conscious state change, not as a side effect of retrying.
- Log the idempotency key with every attempt so support can reconcile charges.

As written, the plan will produce duplicate charges whenever a timeout happens after the processor has accepted the request. That is exactly the case the plan says it handles.

VERDICT: NO_GO