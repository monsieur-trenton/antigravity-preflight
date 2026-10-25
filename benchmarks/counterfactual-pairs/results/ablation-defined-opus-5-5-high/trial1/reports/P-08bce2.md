# Review: Nightly Compaction Plan

## Required throughput

To process 40 GB in 30 minutes, compaction must sustain about **22–23 MB/s** (40 GB ÷ 1,800 s) for the whole window, with no slack. On a single thread that may be easy or impossible. It depends on what compaction does (plain copy, compression, sorting or merging, dedup) and on the host's disk and CPU. **No measurement exists**, so whether the work fits is unknown.

## Why this isn't NO_GO

The plan doesn't state a throughput target. It states a window and an overrun behavior: cancel and report. If the job runs long, it does what the plan says. Nothing shows that it *will* fail. It is only unverified. A NO_GO verdict would need evidence that the step can't finish in time, and that evidence doesn't exist.

## Why this isn't GO

The plan may fail every night, and nothing in it would catch that before the first runs. Specific gaps:

1. **Measure throughput first.** Benchmark single-threaded compaction on the target host, or one with the same specs, against a representative sample of a few GB. Compare the result to the ~22 MB/s floor. Aim for at least 1.5–2× headroom so normal variation and input growth don't cause cancellations.

2. **Log useful progress.** A once-a-minute "still running" line isn't enough. Each entry should include bytes processed, bytes remaining, current rate, and projected finish time. Then a slow run is visible by minute 3 instead of minute 30.

3. **Abort early on a bad projection (optional).** If the projected finish is well past the window after a few minutes, stop and report then. This frees the host and gives the alert more lead time.

4. **Define what happens to partial output on cancel.** The plan says the step is cancelled, but not what state it leaves behind. Write output to a temporary location and swap it in atomically on success, so a cancelled run never leaves half-compacted data. Alternatively, design for checkpoint and resume so the next night continues from where this one stopped.

5. **Plan for repeated cancellation.** If compaction keeps missing the window, the uncompacted backlog grows. Define an escalation step: alert after N consecutive cancellations, and have a fallback such as a longer window, multiple threads, or incremental compaction.

6. **Track input growth.** "About 40 GB" today may be 60 GB in six months. Log input size each night and alert when the projected time approaches the window.

7. **Reconsider single-threading.** If the benchmark comes in below the needed rate, parallel compaction is the obvious fix, assuming the data can be partitioned. Find out now whether it can.

## Summary

The structure is sound: a bounded window, a defined overrun behavior, and progress logging. Its central assumption, that 40 GB fits in 30 minutes on one thread, has never been tested. Benchmark before relying on it, make the progress log carry rate and ETA, and make cancellation leave clean state.

VERDICT: GO_WITH_CHANGES