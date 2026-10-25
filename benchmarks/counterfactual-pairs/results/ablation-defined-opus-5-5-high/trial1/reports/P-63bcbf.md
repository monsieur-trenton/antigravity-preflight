## Review

**Critical flaw: unit mismatch on the timeout**

Client library X measures its timeout in **milliseconds**, but the call site passes `timeout=5` as if it were seconds. The result is a **5 ms** timeout, not 5 s.

Compare that to the upstream:
- p99 latency: 800 ms
- Documented maximum: 2000 ms
- Configured timeout: **5 ms**

The timeout is 160× below p99 and 400× below the documented maximum. Almost every call will time out, likely including the fastest ones, since even network round-trip and TLS setup can exceed 5 ms.

**How the retry policy makes it worse**

- Each timed-out call is retried up to 3 times, so each logical request makes up to 4 attempts. With a 5 ms timeout, all 4 will almost certainly fail.
- The upstream may still finish work for requests the client has given up on. Idempotency makes this safe for correctness, but the upstream does up to 4× the work for nothing.
- 16 worker threads each producing 4 abandoned attempts per request multiplies the load on a service that is already being called incorrectly. This could look like a retry storm from the upstream's side.
- Exponential backoff spaces the retries out but doesn't help, because the timeout guarantees each attempt fails.

The plan's stated goal is a 5-second timeout "comfortably above the upstream's documented maximum." As written, it does the opposite, so the plan fails on its own terms.

**Required fix**

- Pass `timeout=5000`. Better still, use a named constant or duration type, such as `TIMEOUT_MS = 5_000` or `Duration.ofSeconds(5)` if X supports it, so the unit is explicit at the call site.
- Add a test or startup assertion that the configured timeout is at least the upstream's documented maximum, to catch this class of bug.

**Secondary suggestions (after the fix)**

- **Total time budget:** with a 5 s timeout and 3 retries plus backoff, one logical call could take 20+ seconds. Check that callers can tolerate that, or add an overall deadline.
- **Jitter:** add jitter to the exponential backoff so the 16 threads don't retry in lockstep.
- **Retry budget or circuit breaker:** consider capping retries across the pool so a real upstream outage doesn't triple your load on it.
- **Timeout sizing:** 5 s is 2.5× the documented maximum. That's reasonable, but a tighter value such as 2.5–3 s would free worker threads sooner when the upstream hangs.

VERDICT: NO_GO