# Plan Review: Address Backfill Against the Vendor Geocoding API

## Does the rate ceiling hold?

**Worst-case combined rate:** 8 workers × 5 requests per one-second window = **40 requests per second**. The contracted ceiling is 50, so the worst case leaves 10 requests per second (20%) of headroom.

The plan closes off the usual ways this kind of setup goes over the limit:

| Risk | How the plan handles it | Result |
|---|---|---|
| Retry storms | HTTP 500 retries use the same per-worker limiter allowance as first attempts | Retries can't raise a worker above 5 per second |
| Worker count growing (autoscaling, restarts that overlap) | Exactly 8 workers, fixed for the whole run | The 8 × 5 bound is stable |
| Other services sharing the key | No other service or job uses the key during the run | The whole 50 per second budget belongs to the backfill |
| No coordination between workers | Not needed: each worker's local cap times the worker count stays under the ceiling | Safe without a shared limiter |
| Fixed-window boundary bursts | The limiter caps requests in *any* one-second window, not per calendar second | No 2× burst where two windows meet |

Since the worst case (40) is below the ceiling (50) under the stated conditions, the requirement is met.

## Throughput (for planning)

3,200,000 rows ÷ 40 per second ≈ 80,000 seconds ≈ **22 hours** at full rate, and longer once retries and latency are included. That is acceptable, but the run will overlap live checkout traffic, which makes avoiding a suspension even more important. The plan already protects against that.

## Optional hardening (not required)

These go beyond what the plan needs to be correct:

- **Retries for other failure types:** make sure timeouts, connection resets, and any 429 responses also go through the limiter. The plan only names HTTP 500. A timed-out request may still have reached the vendor.
- **Arrival bunching:** network jitter can make requests that leave evenly spaced arrive close together. The 20% headroom covers normal jitter.
- **Stop on 429:** if the vendor ever returns 429, halt all workers instead of backing off and retrying.
- **Make the assumptions hold in practice:** pin the worker count in deployment config so overlapping restarts can't briefly run 9 or more workers. Keep the key out of other jobs during the run.

## Conclusion

Under the stated conditions the plan cannot exceed the contracted 50 requests per second. The worst case is 40 per second, and retries are already counted against each worker's limit. No changes are needed.

VERDICT: GO