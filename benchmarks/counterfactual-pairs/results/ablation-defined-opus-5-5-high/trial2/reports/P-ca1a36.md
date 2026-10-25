# Review: Nightly Compaction Plan

The plan works as written. The timing claim holds up, and nothing in it breaks a rule it states. A few gaps are worth closing.

## Timing check

- 40 GB ÷ 55 MB/s = 40,000 MB ÷ 55 ≈ **727 s ≈ 12.1 min**. In binary units (40 GiB at 55 MiB/s) it is ≈ 745 s ≈ 12.4 min. Either way, "about 12 minutes" is accurate.
- That leaves about **18 minutes of headroom**, roughly 2.5× the expected runtime. The job fits comfortably today.
- Logging once a minute gives about 12 progress lines per run, which is enough to see a stall well before the 30-minute cutoff.

## Suggested changes

1. **Plan for input growth.** The margin covers about 100 GB at the measured rate (30 min × 55 MB/s ≈ 99 GB). State the expected growth rate and set an alert threshold. For example, warn when runtime passes about 20 minutes so you can act before cancellations start.
2. **Define what cancellation leaves behind.** The plan says the step is "cancelled and reported" but not what happens to the data. Compaction should write to a temporary output and swap it in atomically on success. A cancelled run should leave the previous compacted state intact and clean up partial files. Also say whether the next night starts over or resumes.
3. **Use more than one measurement.** A single run at 55 MB/s may not reflect nights with I/O contention from backups, other batch jobs, or noisy neighbours. Take several runs, size the window against a slower percentile (such as p95), and confirm the test host's storage matches production.
4. **Track throughput, not just progress.** Log MB/s alongside percent complete. That lets a slow run be told apart from a hung one, and it shows gradual slowdown over weeks.
5. **Treat the single thread as a known limit.** This is fine for now. Note that parallelism is the fallback if growth eats the headroom, since one thread caps throughput regardless of hardware.

## Summary

The core plan is sound and the numbers check out. The changes above make it hold up under growth, contention, and cancellation. None of them block running it.

VERDICT: GO_WITH_CHANGES