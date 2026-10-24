# Review: Address Backfill Geocoding Plan

## Arithmetic checks out

- 4 workers × 1.25 req/s = **5 req/s** for the backfill.
- 240,000 ÷ 5 = 48,000 s ≈ **13.3 hours**.
- Combined peak: 5 + 3 = **8 req/s**.
- Daily worst case: 240,000 + 50,000 = **290,000**. This holds even if the run crosses midnight, because the whole backfill is capped at 240,000.
- With no retries, total backfill volume is capped at 240,000 per run.

## Blocking issue: the plan can't show it follows its own rule

The plan's rule is that the account must **never exceed its rate limits**, because suspension would also take down signup lookups. But the limits haven't been confirmed, and the plan has no figure for them. So the 8 req/s and 290,000/day numbers have nothing to be compared against.

- If the per-second limit is 5 or less, the backfill alone breaks it.
- If the per-second limit is under 8, the backfill and signup together can break it.
- If there is a daily quota under 290,000, a common size for geocoding plans, a single day can break it.
- The limit may also be counted per minute, per month, or by concurrent requests. Any of these could be breached even if the per-second numbers look fine.

The plan also adds the backfill's full load on top of peak signup traffic with no defined headroom. The failure it is meant to prevent, account suspension, would break production signup. As written, the plan has not shown that it meets its stated rule, and with plausible limit values it would break it.

## Other issues to fix

1. **Per-process limiters aren't a global limit.** Four independent limiters each allowing 1.25 req/s can still produce bursts above 5 req/s inside one second, depending on the algorithm and token-bucket burst size. A worker that restarts can also add extra load. Use one shared limiter, such as a Redis token bucket, or set the burst size to 1.
2. **No reaction to the provider's signals.** The job should read any rate-limit or quota headers the provider sends. On HTTP 429 or quota errors it should halt or back off sharply, not keep going.
3. **The 240,000 cap only holds within one run.** If the job crashes and is restarted, or rerun to fill gaps, it can exceed that number unless it skips addresses already geocoded and counts requests across runs.
4. **Past peak signup traffic isn't a guaranteed ceiling.** Add a margin, or schedule the run for off-peak hours.
5. **Failed lookups are never revisited.** Not retrying keeps the volume capped, but it leaves gaps. Record the failures and plan a separate, rate-limited follow-up pass.
6. **Consider separating the backfill from signup.** A separate API key or account for the backfill, if the provider allows it, would mean a mistake in the backfill can't suspend signup lookups.

## To reach GO

Get the real limits from the provider in writing: per second, per minute, per day, per month, and concurrency. Then size the backfill so the backfill plus peak signup traffic stays under each limit with explicit headroom, for example ≤70%. Add a global limiter and a circuit breaker that trips on 429 or quota errors.

VERDICT: NO_GO