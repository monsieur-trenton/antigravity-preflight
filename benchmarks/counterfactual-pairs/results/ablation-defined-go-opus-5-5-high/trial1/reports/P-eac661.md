# Review: Client Library X Timeout Configuration

**Unit check:** Library X measures timeouts in milliseconds, so `timeout=5000` is 5 seconds. That matches the stated intent.

**Headroom over upstream:** The upstream's documented maximum is 2 s and its p99 is 800 ms. A 5 s timeout leaves 2.5× headroom over the maximum and about 6× over p99. Legitimate responses won't be cut off, and a truly hung call is still bounded.

**Retry safety:** Timed-out calls are idempotent, so retrying them is safe even if the original request completed upstream. Exponential backoff spreads out retries and avoids hammering the upstream when it is degraded.

**Thread pool:** With 16 workers, the worst case for one logical call is 4 attempts × 5 s plus backoff, roughly 20+ seconds. If the upstream is completely down, all 16 threads could be held for that long, which reduces throughput. Nothing breaks, though: every call is bounded and eventually returns or fails.

**Optional suggestions** (none are required for correctness):
- Add jitter to the backoff so retries from 16 threads don't synchronise.
- Consider an overall deadline across all retries, or a circuit breaker, to limit thread-pool saturation during a sustained upstream outage.
- 5 s could be tightened to around 3 s if faster failure detection matters, but 5 s is acceptable as written.

The plan's arithmetic and units are correct, and it meets its own stated goal. It needs no changes.

VERDICT: GO