# Plan Review: Timeout and Retry Configuration for Client Library X

**The plan works as written, but the retry design has gaps worth fixing.**

## Unit check: passes

- Library X takes timeouts in milliseconds, so `timeout=5000` is 5 seconds, as intended.
- 5 s is 2.5× the documented 2 s maximum and about 6× the 800 ms p99. Healthy calls should never hit the timeout.
- Nothing in the plan contradicts itself or breaks a rule it states.

## Recommended changes

1. **Bound the total time per logical call.** "Retried up to 3 times" means up to 4 attempts. In the worst case that is 4 × 5 s = 20 s, plus backoff (roughly 1 + 2 + 4 s with a 1 s base), so about 27 s with a worker blocked. Add an overall deadline, for example 10–12 s, that stops retries once it is exceeded.

2. **Watch for pool exhaustion when the upstream is slow.** If the upstream starts timing out, each of the 16 threads can be stuck for about 27 s on one call. Throughput then drops to about 0.6 calls/s and work queues up behind it. Consider:
   - a circuit breaker, or a retry budget such as capping retries at about 10–20% of requests, so retries stop amplifying load on a struggling upstream;
   - a bounded queue in front of the pool, with load shedding when it fills.

3. **Add jitter to the exponential backoff.** Without it, the 16 threads that time out together will retry together, causing synchronized load spikes.

4. **Consider a tighter timeout.** Since the documented maximum is 2 s, a timeout of about 2.5–3 s still leaves margin. It also detects failures faster and roughly halves worst-case thread occupancy. 5 s is defensible, but the extra headroom costs pool capacity during incidents.

5. **Clarify what the timeout covers.** Check whether library X's timeout applies to connect, read, or the whole request. If it is per-read or per-socket-operation, a slow streaming response could exceed 5 s in total. Check whether total time can be bounded separately.

6. **Retry only on errors that can succeed on retry.** Retry on timeouts, 5xx, and 429 (respecting `Retry-After`). Don't retry other 4xx errors.

VERDICT: GO_WITH_CHANGES