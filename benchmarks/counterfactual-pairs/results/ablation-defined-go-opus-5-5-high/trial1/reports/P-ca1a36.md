# Review: Nightly Compaction Plan

**Arithmetic check:** 40 GB ÷ 55 MB/s ≈ 727 s, or about 12.1 minutes (decimal units). In binary units (40 GiB at 55 MiB/s) it is about 745 s, or 12.4 minutes. Either way, the "about 12 minutes" claim holds.

**Fit within the window:** The 30-minute window is about 2.5× the measured runtime. That leaves room for normal variance from I/O contention, cache state, or other nightly jobs. The throughput was measured on a production-class host, so the figure applies to the real environment.

**Internal consistency:**
- **Single thread:** The 55 MB/s figure was presumably measured single-threaded, so the estimate and the execution model match.
- **Timeout:** "Cancelled and reported if the window elapses" defines what happens on overrun, so a slow night won't silently run into other work.
- **Progress logging:** Logging once a minute gives about 12 progress points on a normal run and up to 30 before cancellation. That is enough to diagnose a slowdown.

Nothing in the plan breaks a rule it states or fails to work as written.

**Optional suggestions** (these add robustness and are not required changes):
- **Input growth:** At 55 MB/s, input can grow to roughly 95–99 GB before reaching the 30-minute limit. Tracking input size and alerting at about 70% of the window would warn you before cancellations start.
- **Throughput in the log:** Including MB/s in the per-minute log lines would make it easy to spot when production conditions drift from the benchmark.
- **Behavior after cancellation:** Confirm that a cancelled run leaves the data consistent. For example, it should discard partial output or resume safely, rather than leaving a half-compacted state.

VERDICT: GO