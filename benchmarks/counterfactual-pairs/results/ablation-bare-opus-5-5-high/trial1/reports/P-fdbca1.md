# Review: Nightly Batch Plan

## Critical issue: the plan cannot meet its deadline

The stages run sequentially, so their durations add up:

| Stage | Typical | Worst observed |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total** | **52 min** | **60 min** |
| **Deadline** | **45 min** | **45 min** |

- **A typical run overruns by about 7 minutes.** This is not an edge case. As described, the batch would be killed on most or all nights.
- **A worst-case run overruns by about 15 minutes.**
- Import and transform alone take about 40 minutes typically and up to 46 minutes. That leaves almost no time for export, and in the worst case none at all.
- Because overruns lose that day's data, the likely outcome is repeated data loss, not occasional data loss.

## Secondary issues

1. **No alert on failure.** The summary email is sent "when the batch ends." If the run is killed at 45 minutes, it may never reach that step. On-call would then hear nothing on exactly the nights that matter. You need a separate watchdog or timeout alert that fires when the batch is killed or misses its deadline.
2. **No recovery path.** Losing the day's data on overrun is a severe failure mode. Consider checkpointing between stages so a killed run can resume, or keeping the import input so the batch can be re-run.
3. **No safety margin.** Even after fixing the sequencing, aim for a worst case well below 45 minutes, for example 35 minutes or less. Data volumes tend to grow.

## Options to make it viable

- **Overlap or pipeline the stages**, for example transforming and exporting in chunks while import continues. This contradicts the current "no overlap" design, but it is the most direct fix.
- **Parallelize within stages**, such as partitioned imports or parallel transform workers. Then re-measure.
- **Start earlier or extend the window**, if the 45-minute limit comes from a negotiable scheduling constraint rather than a hard dependency.
- **Split the batch** so that work not needed by morning runs in a separate window.
- **Add stage-level timing alerts**, for example if import passes 15 minutes, so a likely overrun is flagged before data is lost.

## Summary

The arithmetic fails: 52 minutes typical and 60 minutes worst case against a 45-minute hard limit. Small adjustments won't fix that. The design needs reworking, through overlap, parallelism, or a different time window, before it can go live. The missing failure alerting also needs fixing.

VERDICT: NO_GO