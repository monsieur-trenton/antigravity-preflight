# Review: Address Backfill Rate-Limit Plan

**The plan stays under the limit.**

- **Combined ceiling:** 8 workers × 5 requests per second = **40 requests per second**. The contract allows 50, so there is about 20% headroom.
- **Window semantics match:** each limiter caps "any one-second window," the same rule the vendor enforces. No worker can send a burst at a window boundary, so no worker sends more than 5 in any one-second span. Without coordination, the most all 8 can send in any one-second span is 40.
- **Retries are covered:** HTTP 500 retries use the same limiter allowance, so a retry storm cannot push any worker above 5.
- **No hidden traffic:** the worker count is fixed at 8, and no other service uses the key during the run. Nothing outside the plan adds load.

**Throughput check:** 3.2M rows at 40 requests per second is about 80,000 seconds, or roughly 22 hours. If every row needs one request, that is long but workable. Retries will add some time.

**Optional points, not required:**

1. **Network jitter.** The limiter counts when requests are sent, but the vendor counts when they arrive. Delays on the network could bunch arrivals somewhat. The 10 requests per second of headroom covers realistic jitter, so this is not a real risk.
2. **Back off on 429 or rate-limit warnings,** if the vendor sends them. This is a safety net in case a config change ever raises the worker count or per-worker cap.
3. **Lock the configuration.** Assert at startup that the worker count is 8 and the cap is 5. This stops someone from "speeding things up" mid-run. The plan already says the count won't change, so this only guards against later edits.

None of these are needed for the plan to meet its stated requirement. As written, it cannot exceed 50 requests in any one-second window.

VERDICT: GO