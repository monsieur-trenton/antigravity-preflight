# Review: Checkout Capture Retry Plan

**The plan meets its stated rule: a capture never takes effect more than once.**

## Why it holds

1. **Retrying is safe, not just likely safe.** The plan correctly names the dangerous case: the server may have charged the card before the client's timeout fires. That is the case that causes double charges. The plan doesn't try to avoid it. Instead, it makes it harmless: every attempt carries the same idempotency key, and the server collapses repeats.

2. **The key can't drift.** The key is a UUID created once when the order is made and never replaced. A resend can't get a fresh key, which would defeat deduplication.

3. **The dedupe guarantee comes from the server.** Deduplication is the payments team's documented contract, not just behaviour seen in testing. The staging run backs it up exactly. It sent 6 submissions per capture, which is the original call plus all 5 resends. Those 6,000 requests produced exactly 1,000 charges.

4. **No hidden extra requests.** The HTTP library's automatic retries are off. So the request count is limited to 1 + 5, the volume the staging test covered. This also prevents retries stacking on top of retries.

5. **The retry policy is bounded and sensible.** The client retries only on timeouts and 5xx responses, where the outcome is unknown or the error is transient. It waits 200, 400, 800, 1600 and 3200 ms, about 6.2 s of waiting plus the per-attempt timeouts. That window is far shorter than any realistic idempotency-key retention period.

## Optional notes (not needed for correctness)

- **Jitter:** adding random variation to the backoff would spread out retries if many clients fail at once. This affects load, not duplicate charges.
- **After all 5 resends fail:** the outcome is unknown, so the order should be reconciled, for example by looking up the capture by its key, rather than marked as failed. Any later retry must reuse the same key. The plan already requires this, because the key is never replaced.

Neither point is a flaw in the plan as written, and neither threatens the no-double-capture rule.

VERDICT: GO