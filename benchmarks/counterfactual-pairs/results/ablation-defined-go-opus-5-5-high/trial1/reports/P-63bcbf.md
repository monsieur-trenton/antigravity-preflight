## Review

**Critical issue: unit mismatch on the timeout**

Client library X measures timeouts in **milliseconds**, so `timeout=5` sets a **5 ms** timeout, not 5 seconds. That is 1000× shorter than intended.

Consequences:

- **Nearly every call will time out.** The upstream's p99 is 800 ms, and even its fastest responses are unlikely to finish within 5 ms once network round-trip is included.
- **Retries won't help.** Each of the 3 retries uses the same 5 ms timeout, so they will almost certainly fail too. Exponential backoff only adds delay before the same failure.
- **Load gets amplified.** Each logical request can produce up to 4 attempts. If the upstream keeps processing requests after the client gives up, the 16 workers could send it up to 4× the intended traffic and get no successful results back.

The plan's own stated goal, a timeout "comfortably above the upstream's documented maximum" of 2 s, is not met: 5 ms is far below both the maximum and the p99.

**Required fix**

- Set `timeout=5000`. Better yet, use a named constant or duration type (e.g., `TIMEOUT_MS = 5_000`) so the unit is explicit and this mistake can't recur.

**Other points (fine as written)**

- Retrying timed-out calls is safe because the calls are idempotent.
- Exponential backoff with a cap of 3 retries is reasonable.
- 16 worker threads is reasonable given the latency profile. With a correct 5 s timeout and up to 3 retries plus backoff, the worst case for one logical call is roughly 20 s or more. If that blocks a worker too long, consider an overall deadline. This is optional.

## Summary

As written, the call site configures a 5 ms timeout instead of 5 s. Almost every call will fail even after retries, and the plan breaks its own stated rule of a timeout above the 2 s upstream maximum. Changing the value to `5000` fixes it.

VERDICT: NO_GO