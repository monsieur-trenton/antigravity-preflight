# Review: Capture Retry Plan

## Does the plan meet its own rule?

Yes. The rule is that a capture must never take effect more than once. The plan meets it:

- **The risk is acknowledged.** The plan states that a timeout can hide a capture that succeeded, so it doesn't assume a timeout means failure.
- **The key is stable.** One UUID is created when the order is made, never replaced, and sent on every attempt for that order.
- **The server deduplicates.** Collapsing repeats with the same key is the payments team's documented contract, and the staging test confirms it (1,000 orders × 6 submissions = 1,000 charges).
- **There are no hidden retries.** Retries inside the HTTP library are off, so the 5 resends are the only repeats.
- **The number of attempts is bounded.** That is 6 attempts in total, with waits of 200, 400, 800, 1,600 and 3,200 ms, about 6.2 s of waiting plus the timeouts.

None of these steps can produce a second charge.

## Recommended changes

1. **Decide what happens when all retries fail.** After the 5th failed resend, the outcome is unknown: the card may or may not have been charged. The plan doesn't cover this case. If it's left undefined, someone may later retry by hand, or the order may be re-created with a new key, and either could double-charge. Mark the order as "capture pending/unknown" and reconcile it by asking the payments service for the status under the same key. Never generate a new key for that order.

2. **Check that same-key requests arriving at the same time are handled.** A resend can reach the server while the original is still being processed. The staging test doesn't say whether its 6 submissions overlapped in time. Confirm with the payments team that the contract covers this case, whether by locking, returning a 409 "in progress" response, or similar. Also decide how the client handles that response; it probably should not count as success or as a terminal failure.

3. **Make sure the key is stored before the first call.** "Generated once when the order is made" should mean the key is saved with the order. Otherwise a client crash or restart would produce a new key for the same order.

4. **Add jitter to the backoff.** Without it, many clients that failed together during an outage will retry at the same moments.

5. **Set an overall deadline and ask how long keys are kept.** Cap the total time across all attempts, including timeouts, and confirm the server keeps keys longer than any retry or reconciliation could take.

6. **Smaller points:**
   - Keep the request body identical on every attempt; many APIs reject a reused key with a different payload.
   - Don't retry 4xx responses.
   - Log the key with every attempt so problems can be traced.

## Conclusion

The plan prevents duplicate charges as written. The changes above, especially defining the outcome after retries are exhausted and confirming that overlapping same-key requests are handled, close the operational gaps around it.

VERDICT: GO_WITH_CHANGES