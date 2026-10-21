# Review: Nightly Batch Plan

## Timing

| Stage | Typical | Max (30 runs) |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total** | **52 min** | **60 min** |

- **Typical case:** 52 of 75 minutes, leaving 23 minutes (31%) of headroom.
- **Worst observed case:** Even if all three stages hit their maximum on the same night, the total is 60 minutes, leaving 15 minutes (20%) of headroom.

The schedule fits the deadline with a reasonable margin. Timing does not block this plan.

## Risks

1. **A kill would go unnoticed.** The summary email is sent "when the batch ends." If the job is killed at 75 minutes, it probably never reaches that step. The one failure that loses data would then produce no email. Someone could notice only by realizing a message is missing, which people rarely do.

2. **Overrun means total data loss, with no recovery path.** The plan has no checkpointing, no retry, and no way to rerun a day. If Stage 3 fails at minute 58, all the work from Stages 1 and 2 is lost.

3. **Thirty runs is a short history.** The maximums cover about a month. They miss rarer events such as month-end or quarter-end volume spikes, upstream delays, and resource contention.

4. **No trend tracking.** If data volume grows, the 15-minute buffer will shrink gradually. Nothing in the plan would warn anyone before the deadline is breached.

5. **Unaccounted overhead.** The figures appear to be stage run times only. Startup, gaps between stages, and the email step are not measured. These are probably small, but they come out of the same 75 minutes.

## Recommended Changes

1. **Alert on failure and timeout, not only on completion.** Use a watchdog or the scheduler's failure hook to email or page on-call if the job is killed, fails, or hasn't finished by a set time. A dead-man's-switch style check works well here.
2. **Add an early warning threshold.** Alert if total run time passes about 65 minutes, or if any stage exceeds its historical maximum.
3. **Track run times over time.** Record per-stage durations and review the trend, especially before known high-volume periods.
4. **Make lost days recoverable.** Persist each stage's output so a failed run can resume from the last completed stage, or at least allow a manual rerun of a missed day outside the window.
5. **Measure end-to-end time,** including overhead, rather than adding up stage times.

## Summary

The timing works, with a 15-minute worst-case margin. The main gaps are observability and recovery. The most serious one is that a killed run likely sends no notification, which turns the costliest failure into a silent one. These are inexpensive fixes and should be made before relying on this plan.

VERDICT: GO_WITH_CHANGES