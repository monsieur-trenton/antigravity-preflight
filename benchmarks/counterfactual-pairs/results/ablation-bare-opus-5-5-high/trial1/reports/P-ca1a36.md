# Plan Review: Nightly Compaction Step

## Arithmetic check

40 GB ÷ 55 MB/s ≈ 727 s ≈ **12.1 minutes** (decimal units), or ≈ 12.4 min with binary units. The "about 12 minutes" claim holds, giving roughly **2.5× headroom** against the 30-minute window. That margin is comfortable today.

## Strengths

- The throughput is **measured on production-class hardware**, not estimated.
- There is a **hard time bound** with an explicit failure path (cancel and report), so the job can't run unbounded.
- **Per-minute progress logging** gives enough resolution to see a stall or slowdown well before the deadline.
- A **single thread** keeps behavior predictable and avoids contention bugs.

## Gaps and risks

1. **Cancellation safety isn't specified.** This is the most important gap. What state does a cancelled run leave behind? The plan should state that compaction writes to a temporary location and swaps in atomically, or that partial output is discarded. Otherwise a cancel could corrupt or half-replace the data.

2. **Input growth isn't addressed.** At 55 MB/s the window holds about 99 GB. If the input grows, the headroom shrinks. Add an alert or threshold, for example warn when projected runtime exceeds about 60% of the window (around 18 min, or about 60 GB of input).

3. **Single-run measurement.** One 55 MB/s figure doesn't capture variance. Nightly hosts often share I/O with backups, other batch jobs, or noisy neighbors. Measure several runs, or under representative nightly load, and plan around a pessimistic rate.

4. **Behavior after cancellation.** "Reported" should say who gets alerted and what happens next: retry tonight, wait until tomorrow, or fall back to a manual run. Repeated cancellations mean uncompacted data piles up, which makes the next run longer and could cause a cascade of failures.

5. **Optional early abort.** The per-minute progress data could be used to cancel early if the projected finish time is past the window. That would free resources sooner than waiting the full 30 minutes. This is nice to have, not required.

6. **Single thread as a lever.** The single-thread design is fine now. Note it as the first thing to change if headroom becomes tight, assuming the workload is CPU-bound rather than I/O-bound.

## Recommendation

The core timing claim is correct and the margin is healthy. Before approving, the plan should:

- define atomic or rollback-safe cancellation behavior,
- add an input-size or runtime trend alert, and
- define the escalation or retry path after a cancellation.

VERDICT: GO_WITH_CHANGES