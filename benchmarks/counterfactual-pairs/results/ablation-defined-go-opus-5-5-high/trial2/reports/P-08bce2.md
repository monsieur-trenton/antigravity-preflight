# Review: Nightly Compaction Plan

**Required throughput.** 40 GB in 30 minutes needs about **22 MB/s** sustained (about 23–24 MB/s if "GB" means GiB). Single-threaded compaction can usually reach that on typical server storage, but no one has measured it on the target host, so it is unconfirmed.

**Is there a defined path for every outcome?**
- **Finishes in time:** the step completes normally.
- **Runs past the window:** it is cancelled and reported. That is a stated, handled outcome, not a silent failure or a broken rule.
- **During the run:** the log entry every minute shows progress and makes stalls visible.

Nothing in the plan is shown to fail, and it breaks none of its own rules. The unmeasured throughput is a risk, but the cancel-and-report rule already contains it. So the plan works as written.

**Optional suggestions (robustness only, not required):**
1. **Benchmark first.** Time a compaction of a few GB on the target host before relying on the window. You want headroom well above 22 MB/s, ideally 1.5× or more, to cover I/O contention at night.
2. **Make cancellation safe.** Confirm that a cancelled run leaves the data consistent and either keeps partial progress or rolls back cleanly. If every run restarts from zero and the job is too slow, compaction would never finish. The report would show this, but it is worth knowing ahead of time.
3. **Warn early.** Log a projected completion time each minute (bytes done ÷ elapsed time) and warn as soon as the projection exceeds 30 minutes, rather than only reporting at cancellation.
4. **Plan for growth.** If the input grows, the required rate grows with it. A note on when to revisit the window or add parallelism would help.

VERDICT: GO