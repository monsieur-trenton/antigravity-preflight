## Review

**Critical issue: the timeout unit is wrong.**

The plan says client library X measures its timeout in **milliseconds**, but the call site passes `timeout=5` intending **5 seconds**. That actually sets a **5 ms** timeout.

Here is how that plays out against the upstream's numbers:

| Value | Intended | Actual |
|---|---|---|
| Configured timeout | 5,000 ms | **5 ms** |
| Upstream p99 | 800 ms | 800 ms |
| Upstream documented max | 2,000 ms | 2,000 ms |

A 5 ms timeout is about 160× below the p99 and 400× below the documented maximum. Almost every call will time out, which breaks the plan's own stated goal of a timeout "comfortably above the upstream's documented maximum."

**Knock-on effects:**

1. **Retries make it worse.** Each logical call becomes 4 attempts (1 + 3 retries), and nearly all of them will time out. So you get close to 100% failure plus 4× the request volume.
2. **Load on the upstream.** A client-side timeout doesn't cancel server-side work. The upstream will still process each abandoned request. With 16 workers each sending 4 attempts per logical call, the upstream sees roughly 64 in-flight-equivalent requests whose results are all thrown away.
3. **Idempotency helps, but only partly.** Because the call is idempotent, retries are safe for correctness. They are not safe for capacity.

**Required fix:**
- Set `timeout=5000`. Better still, use a named constant or a unit-explicit value, such as `timeout=timedelta(seconds=5)` or `TIMEOUT_MS = 5_000`, so the unit can't be misread again.

**Secondary suggestions (not blocking once the unit is fixed):**
- Add jitter to the exponential backoff so 16 workers don't retry in lockstep.
- Check the worst-case time per logical call: 4 × 5 s plus the backoff delays. Make sure that fits within any caller or request deadline. Consider an overall deadline or retry budget.
- Consider a lower timeout, around 2.5–3 s. With a 2 s documented maximum, 5 s mostly holds a worker thread longer when the upstream is unhealthy.
- Add a circuit breaker or retry budget so a degraded upstream doesn't get hit with 4× traffic from all 16 workers.

## Conclusion

As written, the plan sets a 5 ms timeout. Effectively every call will fail, which contradicts the plan's stated intent. This is a correctness failure, not just something to improve.

VERDICT: NO_GO