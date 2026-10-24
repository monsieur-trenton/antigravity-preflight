## Review

**Does the plan meet its rule ("no customer may be charged twice for the same order")?**

Yes. The key question is whether a retry after an ambiguous timeout can cause a second charge:

1. **Stable key.** The idempotency key is the order's UUID. It is generated once at placement, persisted with the order, and reused unchanged on every attempt. All attempts for an order therefore carry the same key.
2. **Within the dedupe window.** All attempts finish within 10 minutes, well inside the processor's 24-hour window. Any retry reaches the processor while the original key is still remembered.
3. **Ambiguous timeouts are covered.** If a timed-out attempt actually went through, the retry carries a key the processor has seen. It returns the original result and does not charge again. If the attempt never landed, the retry produces the single charge.
4. **Retrying despite unknown outcomes is safe.** Given points 1–3, retrying on timeout is correct and avoids leaving orders unpaid. The retry count is bounded at 3 further attempts.

Every path yields at most one charge per order, so the plan satisfies its rule as written.

**Optional hardening (not required):**
- Confirm how the processor handles a retry that arrives while the original request is still in flight. Some processors return a "request in progress" error instead of the original result. The worker should treat that as retryable or pending, not as a failure.
- Make sure the UUID is persisted before the first submission. The plan implies this, since the UUID is created at placement. Also make sure no other code path, such as a manual "retry payment" admin action, generates a new key for the same order.
- Record the final processor result against the order so a later reconciliation can find orders whose attempts all timed out.

None of these are needed for the plan to work.

VERDICT: GO