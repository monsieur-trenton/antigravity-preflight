# Review: Address Backfill Geocoding Plan

## What checks out

- **Throughput and duration.** 4 workers × 1.25 req/s = 5 req/s. 240,000 ÷ 5 = 48,000 s, which is about 13.3 hours.
- **Combined peak rate.** 5 req/s from the job plus 3 req/s from signup is 8 req/s.
- **Daily volume.** The job sends at most 240,000 requests in total, because nothing is retried. Signup has peaked at 50,000 per day. Even if the 13.3-hour run spans two calendar days, no single day can exceed 290,000.
- **Bounded request count.** Not retrying within the run keeps the job's total fixed at 240,000.

## The blocking problem

The plan's central rule is that the account must never exceed its rate limits. The plan cannot show that it meets this rule, because it has no figure for those limits. They have not been confirmed with the provider.

The plan carefully calculates its own load: 8 req/s at peak and 290,000 per day. But there is nothing to compare those numbers against. Whether the plan is safe depends entirely on a number nobody has looked up.

If the real limit is, say, 5 req/s or 100,000 per day, the account gets suspended. That suspension also breaks live address lookups at signup, which is the exact outcome the rule exists to prevent. Since the cost of being wrong is an outage on the signup path, the plan is not safe to run as written.

**Required change:** Get the account's actual limits from the provider, in writing or from the account dashboard, before the run. Cover every limit window that applies, such as:
- per second
- per minute or burst
- per day
- per month

Then confirm that 8 req/s and 290,000 per day fit within those limits with a clear margin. Reduce the worker count or the per-worker rate if they don't.

## Related gaps to address alongside it

1. **Signup traffic is a past peak, not a cap.** Nothing limits signup to 3 req/s or 50,000 per day. A traffic spike during the 13.3-hour run could push combined load above the 8 req/s the plan budgets for. Either leave headroom below the real limit or have the job back off when signup traffic rises.
2. **Other limit windows.** Providers often enforce per-minute burst limits or monthly quotas. A month with this run plus normal signup traffic is roughly 240,000 + 30 × 50,000 ≈ 1.74 million requests. That should be checked against any monthly cap.
3. **Four separate limiters.** Each process enforces 1.25 req/s on its own. That works only if exactly 4 workers ever run. A shared limiter, or a guard against extra workers starting (for example, after a restart), would make the 5 req/s ceiling a real guarantee.
4. **Stopping on rate-limit responses.** If the provider returns 429 or quota warnings, the job should halt or slow down rather than keep sending.

Items 1–4 make the plan more robust. The missing limit figure is what blocks it: without it, the plan cannot show that it obeys its own rule, and the risk is suspension of the account that signup depends on.

VERDICT: NO_GO