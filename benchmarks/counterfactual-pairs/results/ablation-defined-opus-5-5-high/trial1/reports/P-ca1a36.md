# Review: Nightly Compaction Plan

## Does the timing hold?

Yes. 40 GB at 55 MB/s is about 727 s (decimal units) or about 745 s (binary units). Either way that's roughly 12 minutes, so the stated figure is correct. Against a 30-minute window, that leaves about 2.5× headroom. The measurement was taken on a production-class host, so the baseline is credible. Nothing in the plan as written fails or contradicts its own rules.

## Gaps worth addressing

1. **Data growth isn't accounted for.** At 55 MB/s, the window is exhausted at about 99 GB. The plan should state the input's growth rate and the date it's projected to cross a safe threshold, say 70–80 GB. Otherwise the current headroom will quietly shrink until a nightly run is cancelled.

2. **The throughput figure looks like a single measurement.** Nightly conditions can differ from the test: concurrent backups, noisy neighbours, cold caches, or degraded disks. Record p50/p95 duration across several real runs rather than relying on one number.

3. **Cancellation behaviour is unspecified.** "Cancelled and reported" doesn't say what state the data is left in. The plan should confirm that:
   - a cancelled run leaves the original input intact, using write-to-temp-then-atomic-swap or equivalent,
   - partial output is cleaned up, and
   - the next night's run starts cleanly rather than compounding the backlog.

4. **There's no early warning before a hard failure.** The once-a-minute progress log can drive this cheaply. Alert if projected completion exceeds, for example, 20 minutes, or if the rate drops well below 55 MB/s. That way you learn about trouble before the cancellation does.

5. **The single-thread limit needs a fallback.** Single-threaded is fine today. Note whether compaction could be parallelised or sharded if growth demands it, so the response to point 1 is already planned.

6. **Minor: state units explicitly.** Say whether you mean GB or GiB and MB or MiB. It changes the margin only slightly, but it avoids confusion in future capacity maths.

## Summary

The plan is sound for current data volumes. The main improvements are planning for growth and defining safe cancellation semantics, so the time limit degrades gracefully instead of becoming a surprise.

VERDICT: GO_WITH_CHANGES