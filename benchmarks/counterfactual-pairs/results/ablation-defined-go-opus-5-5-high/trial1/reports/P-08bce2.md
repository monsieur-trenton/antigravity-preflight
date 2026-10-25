# Review: Nightly Compaction Plan

The plan handles overruns safely, but nobody knows whether the job can finish inside its window, and nothing in the plan checks.

## What the plan requires

- 40 GB in 30 minutes means about **22–23 MB/s sustained**, on a single thread, for the whole window.
- Compaction usually reads and writes, so the disk sees roughly twice that, about **45 MB/s combined**.

## Is that achievable?

It might be, but there is no evidence either way:

- **Plausible case:** Sequential I/O on SSD, or even HDD, with light per-record work. 22 MB/s fits comfortably.
- **Tight or failing case:** Single-threaded heavy compression (gzip-class codecs often reach only about 30–60 MB/s per core), random I/O on spinning disks, a busy shared host, or input that grows past 40 GB. Any of these can put the rate at or below what is needed.

Because no throughput has been measured on the target host, the plan's central assumption is unverified. The plan doesn't break its own rules. The cancel-and-report path means an overrun is handled rather than silently harmful. But "cancelled every night" would mean the job never does its work, and nothing in the plan would show that before it happens in production.

## Changes the plan should make

1. **Benchmark on the target host before rollout.** Run compaction on a representative sample, such as 2–4 GB of real data, under realistic nightly load. Record MB/s and confirm a clear margin, ideally at least 1.5–2×, or about 35–45 MB/s.
2. **State what happens on repeated cancellation.** Decide whether a partial or failed compaction leaves data consistent. Decide whether there is a fallback, such as resuming the next night, chunked or incremental compaction, or an alert after N consecutive cancellations.

## Optional improvements

- Use the once-a-minute progress log to project the finish time. Warn or abort early, for example at minute 10, if the projected rate can't finish in time.
- Track input size growth so the 40 GB figure doesn't drift unnoticed.
- If the benchmark shows a tight margin, consider parallelism or a faster codec.

## Summary

Overruns are handled safely and visibly, so the plan works as written. Its feasibility, though, rests on an unmeasured throughput assumption with a modest but unproven margin. Measuring throughput and defining what happens after repeated cancellations are changes the plan should make, not just nice-to-haves.

VERDICT: GO_WITH_CHANGES