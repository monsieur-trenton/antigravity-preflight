# Review: Address Backfill Geocoding Plan

## The arithmetic is correct

- **Throughput:** 4 workers × 1.25 req/s = 5 req/s.
- **Duration:** 240,000 ÷ 5 = 48,000 s ≈ 13.3 hours.
- **Combined peak rate:** 5 req/s from the job plus 3 req/s from signup = 8 req/s.
- **Daily ceiling:** Even if the run crosses midnight, one day can hold at most 240,000 job requests plus 50,000 signup requests, which is 290,000.
- **Request cap:** With no retries, the job sends at most 240,000 requests.

## Blocking issue: the plan cannot show it meets its own rule

The plan's central rule is that the account must never exceed its rate limits. The plan also says the limits are unconfirmed and gives no figure for them. So the 8 req/s and 290,000/day numbers are not compared against anything. The plan doesn't show it is safe. It only says how much load it adds.

These are not unusual volumes, and they can easily break real quotas:

- Many geocoding plans cap daily or monthly volume well below 290,000.
- Some plans enforce per-second or per-minute caps in the single digits or low tens.

The cost of being wrong is account suspension, which would also break live address lookups at signup. A plan built on "never exceed" can't go ahead while the limit is unknown.

## Further issues to fix

1. **Get the limits in writing.** Ask the provider for every limit that applies to the account: per second, per minute, per day, per month, and any concurrency cap. Ask how each is measured, for example a rolling window or calendar day, and in which time zone. Then show there is headroom at 8 req/s and 290,000/day.
2. **Leave a margin for signup traffic.** The 3 req/s and 50,000/day figures are historical peaks, not guarantees. Size the job so that signup traffic could exceed its past peak without pushing the account over a limit. Or reserve a fixed share of the limit for signup.
3. **Use one shared limiter.** Four separate per-process limiters can burst together, for example at startup or after a pause. A restarted or extra worker would also add to the total unnoticed. One shared limiter, such as a token bucket in Redis, caps the real combined rate.
4. **Stop on throttling signals.** Halt the job on any 429 response, quota warning, or rate-limit header nearing zero. Do not keep sending at the planned rate.
5. **Add a kill switch and monitoring.** Track the account's actual usage in real time, including signup traffic. Be ready to pause the job quickly.
6. **Handle failed lookups.** Not retrying keeps the request count capped, but failed addresses are simply lost. Record them so a later, rate-limited pass can process them.
7. **Count all spending.** Check whether the 240,000 requests fit within any monthly quota alongside a month of signup traffic.

## Summary

The calculations are right. The plan's main safety rule, however, depends on a limit nobody has confirmed. Until the provider's limits are known and shown to leave headroom above 8 req/s and 290,000/day, the plan risks suspending the account and breaking signup.

VERDICT: NO_GO