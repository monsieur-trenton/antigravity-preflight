# Review: Nightly Compaction Plan

## Summary

The plan has sound guardrails: a bounded window, cancel-and-report, and periodic progress logging. But its central question is unanswered. Nobody knows whether a single thread can finish 40 GB in 30 minutes on this host. Until that is measured, the plan may fail every night.

## The core math

- 40 GB in 1,800 s requires about **22 MB/s sustained, end to end**.
- Compaction usually reads the input and writes the output, often with decoding, merging and re-encoding in between. Effective I/O is therefore about 2× the input, roughly 45 MB/s or more, while one core also does the CPU work.
- That target is plausible on local NVMe with lightweight compaction. It is risky on network storage, spinning disks, shared or noisy hosts, or with heavy compression or sorting. Today we cannot tell which case applies.

## Issues

1. **No throughput measurement (blocking).** Benchmark single-thread compaction on the target host, or an identical one, using production-shaped data. Measure at both the typical nightly time and the worst-case time. Require at least 1.5–2× headroom, meaning roughly 35–45 MB/s or more of input throughput.

2. **Cancellation semantics are undefined.** If the step is cancelled at minute 30:
   - Is partial output discarded, or kept in a valid state?
   - Is the original data guaranteed intact? Writes should go to a temporary location and be swapped in atomically.
   - Does the next run start over? If so, a job that needs 35 minutes will fail every night and never make progress. Consider checkpointing or resumable or incremental compaction so cancelled work is not wasted.

3. **No growth margin.** "About 40 GB" is today's size. State the expected growth rate and the input size at which the window breaks. Add an alert well before that point, for example when a run takes more than 70% of the window.

4. **Single thread is an unexplained constraint.** If it is deliberate, for example to limit impact on other nightly jobs, document why. If not, parallelism is the most obvious fallback if the benchmark falls short.

5. **Logging is not monitoring.** A per-minute progress log helps diagnosis, but it should also record bytes processed, rate and projected finish time. Repeated cancellations should page or alert someone, not just produce a report entry. Define what happens operationally after N consecutive failures.

6. **Contention in the window.** Identify other jobs (backups, ETL, other compactions) that share disk, network or CPU during the window. A benchmark on an idle host will overstate real throughput.

## Required changes before go-live

- Measure throughput on the target host under realistic load, and confirm at least 1.5× headroom against 22 MB/s.
- Define cancellation behavior: original data stays safe, no corrupt partial output, and ideally resumable progress.
- Add duration and rate trend alerting with a threshold below the hard cutoff, plus escalation for repeated cancellations.
- Document the growth assumption and the input size at which the design must change, such as parallelism, a longer window, or incremental compaction.

The design is reasonable. It is not proven to fit its window, and its failure mode needs to be safe and non-repeating.

VERDICT: GO_WITH_CHANGES