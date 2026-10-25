# Review: Address Backfill Geocoding Plan

## What checks out

- **Throughput:** 4 workers × 1.25 req/s = 5 req/s. 240,000 ÷ 5 = 48,000 s, or about 13.3 hours.
- **Combined peak rate:** 5 req/s from the backfill plus 3 req/s peak from signup gives 8 req/s.
- **Daily volume:** 240,000 + 50,000 = 290,000. Even if the run spans midnight, no single calendar day can exceed this.
- **Request cap:** With no retries, the backfill sends at most 240,000 requests.

## The blocking problem

The plan's main rule is that the account must never exceed its rate limits. The reason is serious: a suspension would also stop live address lookups at signup. But the plan admits that the actual limits are unconfirmed and gives no figure for them.

Every number above only matters when compared against a limit, and that limit is missing. We have no way of knowing whether 8 req/s or 290,000 per day is safely under the limit, close to it, or over it. Typical geocoding tiers range from a few requests per second to hundreds, and from a few thousand to millions of requests per day. A limit of 5 req/s or 250,000 per day would put the account into suspension, and nothing in the plan rules that out.

So the plan does not show that it satisfies its own rule. The worst case is losing signup functionality, so this has to be fixed before the job runs.

## Required changes

1. **Confirm the account's limits with the provider in writing.** This includes:
   - per-second limits
   - per-minute limits
   - daily or monthly quotas
   - any concurrency limits
   - whether the limits are per account or per key

   Then record the figures in the plan and show that 8 req/s and 290,000 per day sit below each limit with margin.

2. **Size the backfill against the confirmed limits.** If the headroom is thin, lower the per-worker rate or spread the run over more days. Signup's 3 req/s and 50,000 per day are historical peaks, not caps, so they could be exceeded.

## Recommended, not blocking once limits are confirmed

- **Use a separate API key or sub-account for the backfill, if the provider supports it.** Then a mistake in the backfill cannot suspend signup lookups.
- **Use one shared limiter instead of four independent per-process limiters.** Independent token buckets can line up their bursts, which matters if the provider enforces limits over short windows.
- **Stop the job automatically on the first 429 or quota warning.** Without this, the job keeps sending requests into a limit it has already hit.
- **Schedule the run off-peak** to keep away from signup's peak hours.

VERDICT: NO_GO