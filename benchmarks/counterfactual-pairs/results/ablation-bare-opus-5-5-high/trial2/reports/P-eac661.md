# Review

**The core concern checks out: the units are correct.** Library X measures the timeout in milliseconds, so `timeout=5000` is 5 seconds, as intended. That is 2.5× the upstream's documented 2 s maximum and over 6× its p99, so legitimate slow responses won't be cut off. Retrying is safe because the operation is idempotent.

The rest of the plan is reasonable but leaves out some failure-mode details.

**1. Worst-case latency per logical call is unbounded in practice.**
With 1 initial attempt plus 3 retries at 5 s each, one call can take about **20 s plus backoff** (say 1 + 2 + 4 s, giving roughly 27 s). Check that the callers above this layer can tolerate that. If they have their own deadline, add an **overall deadline** across all attempts so retries stop when the caller has already given up.

**2. Retries amplify load on a struggling upstream.**
If the upstream degrades, timeouts can turn each request into 4 attempts, quadrupling load on a service that is already slow. Consider:
- adding **jitter** to the exponential backoff, so 16 threads that failed together don't retry in lockstep
- adding a **retry budget or circuit breaker**, so retries stop once failures are widespread rather than isolated.

**3. Thread pool saturation.**
With 16 threads and up to about 27 s per call during an upstream incident, throughput can fall to roughly 0.6 calls/s, and work queues up behind the pool. Decide whether the queue is bounded and what happens when it fills: reject, shed load, or block the producer. A circuit breaker (item 2) also helps here.

**4. Confirm what "timeout" covers in library X.**
Many clients separate connect, read, and total timeouts. If `timeout` sets only one of them, a hung connect or a slowly trickling response could exceed 5 s. Verify that it caps the whole request, or set each timeout explicitly.

**5. Optional tuning.**
5 s is generous given the documented 2 s maximum. A timeout around 2.5–3 s would still cover legitimate responses and would cut the worst case and pool-hold time roughly in half. This is a judgment call, not a defect.

**Summary:** The timeout value and units are correct, and retrying is safe. Before shipping, add jitter, an overall deadline or retry budget, and confirm what the timeout covers, so that a slow upstream doesn't tie up the worker pool.

VERDICT: GO_WITH_CHANGES