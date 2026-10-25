# Review: Nightly Compaction Plan

## The core problem: feasibility is unknown

The plan requires a throughput it has never measured.

- **Required rate:** 40 GB ÷ 1,800 s ≈ **22 MB/s sustained**, with no margin.
- **I/O load is higher than that.** Compaction reads and writes, so the disk sees about **44 MB/s combined**, plus any seeks.
- **Single thread:** the whole job depends on one core keeping up for the full 30 minutes.

22 MB/s single-threaded is achievable on most modern hardware, so the plan **may well work**. It may also miss the window every night if the host has slow or shared storage, CPU-heavy compaction (compression or checksumming), or competing nightly jobs. Today we cannot tell which.

## Why this isn't NO_GO

None of the plan's stated rules is broken. If the window elapses, the step is cancelled and reported, which is the defined failure behavior. The plan can work as written; it just carries risk that hasn't been quantified.

## Recommended changes

1. **Benchmark on the target host before go-live.** Run a representative compaction (e.g., 2–4 GB) at the scheduled time of night. Aim for at least **~1.5× headroom**, about 33 MB/s, so the job fits even if the input grows or the host is busy.
2. **Make cancellation safe.** State what happens to partial output when the job is cancelled. Writes should be atomic (temp file + rename) or checkpointed, so a cancelled run never leaves corrupted or half-swapped data.
3. **Allow resume or incremental progress.** If the job is cut off at 25 minutes, the next night should not start from zero. Otherwise one slow night can turn into permanent failure.
4. **Make the minute log useful.** Each line should include bytes processed, current rate, and projected finish time. Alert early, for example at 10 minutes, if the projected finish exceeds the window. Don't wait for the hard cancel.
5. **Plan for input growth.** Track input size over time and set a threshold that triggers review, such as 45 GB or a projected window use above 75%.
6. **Keep parallelism as a fallback.** If the benchmark comes in marginal, decide in advance whether splitting the input across threads is an option.

## Summary

The structure is sound: a bounded window, defined cancel-and-report behavior, and periodic progress logging. The gap is that the 30-minute window and the 40 GB input have never been checked against each other on the real host. Measure throughput, make partial runs safe and resumable, and make the progress log forecast completion.

VERDICT: GO_WITH_CHANGES