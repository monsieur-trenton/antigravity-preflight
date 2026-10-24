# Review: Address Backfill Rate-Limit Plan

## Does the plan stay under the ceiling?

Yes. The arithmetic holds:

- **Per worker:** at most 5 requests in any one-second window, and this is enforced by the worker's own limiter.
- **Fleet:** exactly 8 workers, and that number is fixed for the run. So the combined rate is at most 8 × 5 = **40 requests in any one-second window**.
- **Contract ceiling:** 50 requests per second. That leaves 10 requests per second (20%) of headroom.

The usual ways this kind of plan goes wrong are each handled by a stated premise:

1. **Retry amplification.** Retries after HTTP 500 draw from the same limiter allowance as first attempts. A burst of 500s therefore cannot push a worker above 5 per second. It only delays its progress.
2. **Fleet growth.** The worker count is fixed at 8, so the 40-per-second bound cannot quietly increase during the run.
3. **Other traffic on the key.** No other service or job uses the key during the backfill, so the backfill's 40 per second is the key's total load.
4. **Window alignment.** The limit is "any one-second window," i.e. a sliding window. That means a worker cannot send 5 at the end of one second and 5 more at the start of the next. Because each worker is capped in every one-second interval, the sum is capped at 40 in every one-second interval too. This holds wherever the vendor's window falls.

The workers don't need to coordinate, because the per-worker caps add up to less than the ceiling.

## Optional hardening (not required)

- **Network jitter.** The limiter controls when requests are sent. The vendor counts when they arrive. Variable latency could, in theory, bunch one worker's requests into a narrower window at the vendor's end. The 10-per-second headroom absorbs ordinary jitter. If you want a firmer margin, you could lower the per-worker cap to 4, at the cost of throughput.
- **Backoff on 500s.** Retries can't break the limit, but adding exponential backoff with jitter would avoid hammering a struggling vendor. It would also help 429s or rate-limit headers get noticed early.
- **Kill switch.** Watch for 429s or other rate-limit warnings from the vendor, and halt the backfill automatically if any appear. This protects checkout if one of the premises turns out to be wrong in practice.
- **Throughput expectation.** At 40 requests per second, 3.2 million rows take about 80,000 seconds, roughly **22 hours** plus retry time. Plan the schedule with that in mind.

None of these are needed for the plan to meet its stated requirement.

VERDICT: GO