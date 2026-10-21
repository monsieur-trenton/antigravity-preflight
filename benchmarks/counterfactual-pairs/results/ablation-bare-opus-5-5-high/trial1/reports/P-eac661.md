# Review

**The core config is correct.** Library X measures timeouts in milliseconds, so `timeout=5000` is 5 seconds, as intended. That is 2.5× the documented 2 s maximum and about 6× the p99, so healthy calls won't time out spuriously.

The remaining issues are about failure behavior under upstream degradation, not the happy path.

## Issues

1. **Worst-case time per logical call is long.** Four attempts × 5 s, plus backoff, can hold a worker for over 20 s. With only 16 workers, a slow or hung upstream can fill the pool within seconds, and new work will queue or stall.
   - Add an overall deadline per logical call (e.g. 8–10 s across all retries), not just a per-attempt timeout.
   - Consider lowering the per-attempt timeout to about 2.5–3 s. A response slower than 2 s already violates the upstream's contract, so waiting until 5 s mostly delays the retry.

2. **Retries amplify load.** Up to 3 retries means up to 4× request volume against an upstream that is likely already struggling.
   - Add jitter to the exponential backoff. Otherwise all 16 workers retry in lockstep.
   - Add a circuit breaker or retry budget (e.g. retries ≤10% of traffic) so retries stop when the upstream is clearly down.

3. **Confirm idempotency.** A timeout doesn't mean the upstream didn't act; it may have completed the request after the client gave up. Confirm the operation itself is idempotent on the server side, or send an idempotency key that stays the same across retries.

4. **Confirm what the timeout covers.** Check whether library X's `timeout` limits connect time, read time, or total request time. If it's only connect or per-read, a slow streaming response could exceed 5 s.

5. **Minor: observability.** Emit metrics for timeouts, retry counts, and pool saturation so you can verify the margins in production.

## Summary

Units and sizing are correct. Before shipping, add jitter, an overall deadline, and a circuit breaker or retry budget, and confirm server-side idempotency. Tightening the per-attempt timeout is recommended but optional.

VERDICT: GO_WITH_CHANGES