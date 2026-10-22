# Review

**Units check:** Client library X measures timeouts in milliseconds, so `timeout=5000` is 5 seconds, which is what the plan intends. There is no unit mismatch.

**Timeout vs. upstream behavior:** 5 s is 2.5× the documented 2 s maximum and over 6× the 800 ms p99. Healthy calls won't be cut off, and genuinely stuck calls are still bounded. This satisfies the plan's own goal of staying comfortably above the upstream maximum.

**Retries:** The call is idempotent, so retrying after a timeout is safe even if the first attempt actually completed upstream. Three retries with exponential backoff is a standard, reasonable policy.

**Concurrency:** 16 workers is a modest pool, and nothing stated implies it violates a limit.

**Optional robustness notes (not required changes):**
- **Worst-case blocking time:** One logical call can hold a worker for about 20 s (4 attempts × 5 s) plus backoff. If the upstream degrades, all 16 threads could be tied up for that long. An overall deadline or retry budget across attempts would cap this.
- **Jitter:** Adding jitter to the backoff avoids synchronized retry bursts from 16 threads hitting a recovering upstream at once.
- **Retry amplification:** Up to 4× load during an upstream incident. A circuit breaker or retry budget would limit this.

None of these are needed for the plan to work as stated. They only make a working plan more robust.

VERDICT: GO