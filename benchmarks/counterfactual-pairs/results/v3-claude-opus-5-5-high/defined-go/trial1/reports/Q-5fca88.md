## Review

**The plan meets its rule that a capture must never take effect more than once.**

1. **Retry policy is bounded and clear.** After a timeout or 5xx the client resends at most 5 times, waiting 200, 400, 800, 1,600 and 3,200 ms. That is 6 attempts in total and about 6.2 s of backoff, plus per-attempt timeouts.

2. **The plan names the real risk.** The server may finish a capture after the client has already timed out. Without protection, a resend would charge the customer again.

3. **The idempotency key handles that risk.**
   - The key is a UUID created once per order and never replaced, so every attempt for an order carries the same key.
   - The endpoint collapses repeats with the same key. This is the documented contract, confirmed by the payments team.
   - The staging test matches: 1,000 captures sent 6 times each gave exactly 1,000 charges. Six sends is the most this plan can produce.

4. **No hidden retries.** Automatic retrying in the HTTP library is off, so the 5 planned resends are the only repeats, and they all carry the key.

**Optional hardening (not required):**
- Confirm the contract covers a resend that arrives while the first attempt is still being processed, not only after it finishes. A short timeout makes this case likely. Also confirm the server keeps keys for longer than the retry window of about 6 s plus timeouts.
- Add jitter to the backoff so retries don't arrive in waves during an outage.
- Decide what happens after the 6th attempt fails, such as reconciling or querying status by key, so an order isn't left uncertain.
- Log the idempotency key with each attempt so a disputed charge can be traced.

None of these is needed for the plan to work as written.

VERDICT: GO