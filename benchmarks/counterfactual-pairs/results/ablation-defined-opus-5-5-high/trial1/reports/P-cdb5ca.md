# Review: Nightly Batch Plan

## Timing check

| Stage | Typical | Max (last 30 runs) |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total (sequential)** | **52 min** | **60 min** |

Because the stages never overlap, the totals simply add. The worst observed case of 60 minutes is 15 minutes under the 75-minute deadline. A typical run leaves 23 minutes of margin. The plan breaks none of its stated rules and should finish on time.

## Recommended changes

1. **Make sure an overrun triggers an alert.** The summary email goes out "when the batch ends." If the batch is killed at 75 minutes, it may never reach that step. The worst outcome, losing a day's data, would then produce no notification at all. Send the alert from something outside the batch, such as a watchdog or the scheduler, or alert when no success email has arrived by a set time.

2. **Add an early-warning threshold.** Alert when a run passes roughly 65 minutes, or when any stage exceeds its historical maximum. This gives on-call time to act before the kill.

3. **Watch the trend, not just the maximum.** Thirty runs is about a month of data. If import or transform time grows with data volume, the 15-minute buffer could shrink without anyone noticing. Record per-stage durations and alert when the rolling total approaches about 65 minutes.

4. **Account for overhead between stages.** The measurements cover the stages themselves. Make sure the total also includes startup, handoffs between stages, and the email step.

5. **Reduce the cost of a kill.** If the work can be restarted, add checkpoints or keep stage outputs so a killed run can resume or be rerun. That way an overrun doesn't automatically mean the day's data is lost.

## Summary

The plan works as written: 60 minutes worst case against a 75-minute limit. The main gap is that the failure the plan exists to prevent, a killed run, may happen without anyone being told. Fixing that alerting gap, and adding trend monitoring, would make the plan solid.

VERDICT: GO_WITH_CHANGES