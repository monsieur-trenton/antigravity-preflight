# Review: Client Timeout and Retry Plan

## Critical issue: the timeout is 5 ms, not 5 seconds

Client library X measures its timeout in milliseconds, so `timeout=5` gives each attempt **5 ms**. The intent was 5 seconds.

The upstream's p99 is 800 ms, so almost every call will time out. Then the retry policy makes it worse:

- **Every request fails.** Each one makes 4 attempts (1 + 3 retries), and each attempt is abandoned after 5 ms. The caller sees errors on nearly every request.
- **Upstream load roughly quadruples.** When the client gives up, the server usually keeps processing the abandoned request. Each logical call can generate up to 4 real units of work upstream that nobody waits for. With 16 workers looping, this can push load on the upstream to several times normal while delivering no successful results.
- **It looks like an upstream outage.** Dashboards will show 100% timeouts, and on-call may chase the upstream instead of the config.

**Fix:** set the timeout in milliseconds, e.g. `timeout=5000`. A tighter value such as `2500` or `3000` would also work, since it still clears the documented 2 s maximum with margin. Use a named constant or unit-explicit form (e.g. `TIMEOUT_MS = 5_000`) and a comment, so this mistake doesn't come back.

## Secondary issues

1. **Worst-case latency per request is high.** With a correct 5 s timeout, 3 retries, and exponential backoff, one logical call can hold a worker for over 20 seconds. Consider either:
   - an overall deadline across all attempts, or
   - a shorter per-attempt timeout, around 2.5–3 s. Anything past the documented 2 s maximum is already abnormal, so waiting 5 s buys little.
2. **Thread pool exhaustion.** With only 16 workers, a degraded upstream can tie up every thread in long timeout-and-retry cycles. Throughput then falls to near zero and work queues behind them. Bound the queue and/or add a circuit breaker so the client fails fast when the upstream is clearly unhealthy.
3. **Add jitter to the backoff.** Pure exponential backoff across 16 threads that time out together will retry in synchronized waves. Use full or decorrelated jitter.
4. **Consider a retry budget.** Cap retries as a fraction of total traffic (e.g. ≤10–20%) so retries can't multiply load during an incident.
5. **Check what the timeout covers.** Confirm whether X's timeout is connect-only, read/idle, or total request time. If it's per-read, a slow trickling response could exceed the intended bound.
6. **Idempotency.** It's good that timed-out calls are idempotent. Make sure that holds server-side, e.g. via an idempotency key if the operation has side effects, since abandoned attempts may still complete upstream.

## Summary

The plan is sound in structure: idempotent retries, backoff, and a timeout above the documented maximum. But the unit mismatch would make every call fail and multiply upstream load. Fixing it is a one-line change. The secondary items (overall deadline, jitter, circuit breaker or retry budget) are strongly recommended but not blocking.

VERDICT: GO_WITH_CHANGES