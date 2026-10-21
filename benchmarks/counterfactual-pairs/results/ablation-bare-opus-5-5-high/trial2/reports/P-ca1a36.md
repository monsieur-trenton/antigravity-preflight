# Review: Nightly Compaction Plan

The plan is sound and the numbers hold up. A few gaps should be closed before relying on it.

## The arithmetic checks out

- 40 GB at 55 MB/s is about 727–745 s (decimal vs. binary units), roughly **12–12.5 minutes**.
- That gives about **2.4× headroom** against the 30-minute window.
- At 55 MB/s, the window fits about **99 GB** of input. That is the breach point to track.

## Strengths

- The duration comes from a measurement on production-class hardware, not an estimate.
- There is a hard time bound, and overruns are reported rather than silent.
- Logging progress every minute gives visibility during the run.

## Gaps and recommended changes

1. **Cancellation semantics are unspecified (most important).** What state does a cancelled run leave behind? The plan should state that compaction writes to a temporary output and swaps it in atomically, so a cancelled run leaves the original data intact and readable. It should also say whether the next night restarts from scratch or resumes. If a partial compaction could corrupt or half-replace data, this becomes a blocker.

2. **The measurement may not be representative.** A single 55 MB/s figure doesn't show variance. Confirm it was taken:
   - with a cold page cache,
   - at the actual nightly time slot, alongside whatever else runs then (backups, ETL, snapshots),
   - on realistic data, not data that happens to compact easily.

   If p95 throughput is much lower than 55 MB/s, the headroom shrinks.

3. **No growth tracking.** Record input size and throughput each night. Alert well before the ~99 GB breach point, for example when projected duration passes about 20 minutes. Otherwise the first sign of trouble will be a cancellation.

4. **Make the progress log actionable.** Each per-minute line should include bytes processed, current rate, and an ETA. Alert early when the projected finish exceeds the window, rather than waiting for the cancel.

5. **Define a response to repeated cancellations.** For example, page someone after two consecutive misses, since uncompacted data will accumulate and make each later run longer.

6. **Single thread (minor).** This is fine given the current headroom. Note parallelism or chunked/incremental compaction as the planned fix if growth erodes the margin.

## Summary

The capacity math is solid and the time-boxing is reasonable. The main thing to add is an explicit guarantee that cancellation is safe (atomic swap, originals untouched), plus growth and variance monitoring so the margin doesn't run out unnoticed.

VERDICT: GO_WITH_CHANGES