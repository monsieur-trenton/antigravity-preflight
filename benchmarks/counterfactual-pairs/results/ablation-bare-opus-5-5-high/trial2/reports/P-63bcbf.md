# Review: Client Timeout and Retry Plan

## Critical: the timeout is 5 ms, not 5 seconds

Client library X measures its timeout in **milliseconds**, so `timeout=5` means **5 ms**, not 5 seconds.

The upstream's p99 is 800 ms and its documented maximum is 2 s, so almost every call will time out. Even the fastest responses are unlikely to arrive within 5 ms once you count network round-trip and TLS.

The retry policy makes this worse:
- **Each logical request fails 4 times** (1 attempt + 3 retries), so nearly all requests fail.
- **Upstream load is roughly 4× normal.** Many requests may still be processed server-side after the client gives up, so the upstream does the work and the client throws it away. That is wasted capacity and could cause cascading overload.
- **Error rates and alerts will be misleading.** It will look like the upstream is failing when the bug is in our client configuration.

**Fix:** `timeout=5000`. Better still, use a named constant or duration type, such as `timeout=Duration.ofSeconds(5)` or `TIMEOUT_MS = 5_000`, if the library allows it. Add a code comment or test that asserts the unit so this can't happen again.

## Secondary recommendations (after the fix)

1. **Consider a tighter timeout.** 5 s is 2.5× the documented maximum. Something like 2.5–3 s still covers the documented ceiling with headroom and frees threads sooner when the upstream is unhealthy.

2. **Bound worst-case latency.** With a 5 s timeout, 4 attempts, and exponential backoff, one logical call can take well over 20 s. Decide whether callers can tolerate that. If not, add an overall deadline across all retries.

3. **Protect the thread pool.** During an upstream outage, all 16 threads can sit in 5 s timeouts and retry loops, so throughput collapses to about 16 / (4 × 5 s) ≈ 0.8 req/s and the queue backs up. Consider:
   - a circuit breaker or retry budget, for example capping retries at about 10% of traffic,
   - **jitter** on the exponential backoff, to avoid synchronized retry storms across 16 threads (and across instances),
   - a bounded work queue with load shedding.

4. **Clarify what the timeout covers.** Check whether X's `timeout` applies to connect, read, or the whole request. If only one, set the others explicitly.

5. **Verify idempotency end-to-end.** The plan says timed-out calls are idempotent. Confirm the upstream really deduplicates, or that the operation is naturally idempotent, because a timed-out request may still have succeeded on the server.

## Summary

The design is reasonable, but as written the timeout is three orders of magnitude too small. Nearly every call would fail, and the retries would quadruple the load on the upstream. The plan should not ship in its current form. The fix is simple, but it is a blocking defect, and the retry and pool safeguards above should be added at the same time.

VERDICT: NO_GO