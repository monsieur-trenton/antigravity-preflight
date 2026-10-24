# Review: Checkout capture retry plan

The plan meets its stated rule that a capture must never take effect more than once.

## Why the plan holds

**1. Duplicate risk is acknowledged and covered.**
The plan accepts that a timed-out attempt may already have charged the card, so a resend can arrive for a capture that succeeded. That is the right failure model, and the idempotency key handles it.

**2. The key is stable.**
The key is a UUID created once when the order is made and never replaced. So the first attempt and all 5 resends carry the same key. The common mistake of generating a new key per attempt is ruled out.

**3. Server-side collapsing is both tested and contractual.**
- In staging, 1,000 captures sent 6 times each produced exactly 1,000 charges. Six sends is the plan's maximum (1 original plus 5 resends).
- The payments team has confirmed this as the endpoint's documented contract, so the plan doesn't depend on behaviour that might change.

**4. No hidden retries.**
Retrying inside the HTTP library is turned off. That leaves the plan's 5 resends as the only repeats, so the attempt count really is bounded at 6.

**5. The retry window is short.**
Backoff waits are 200, 400, 800, 1,600 and 3,200 ms, about 6.2 s plus the per-attempt timeouts. That is well within any realistic retention period for idempotency keys.

## Optional suggestions (not required)

- **Jitter:** add random jitter to the backoff so many clients don't resend in lockstep during an outage.
- **Stop on 4xx:** make sure the client doesn't retry on 4xx responses (for example, a card decline). The plan already only retries on timeouts and 5xx, so this just confirms the code matches.
- **In-progress responses:** if the endpoint can answer "a request with this key is still processing" (often 409 or 425), decide whether the client should wait and retry or poll for the result.
- **Exhausted retries:** after the final failed attempt, the charge status is unknown. Mark the order for reconciliation, for example by looking up the charge by its key, rather than treating it as failed and letting the customer re-order.

None of these is needed for the plan to work as written.

VERDICT: GO