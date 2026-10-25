# Review: Nightly Batch Plan

## Timing

| Stage | Typical | Max observed (30 runs) |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total (sequential)** | **52 min** | **60 min** |

Against the 75-minute deadline:
- **Typical headroom:** 23 min (about 31%)
- **Headroom if every stage hits its observed max:** 15 min (20%)

The timing looks reasonable today. The stages are measured rather than estimated, and even the pessimistic sum fits with room to spare.

## Concerns

1. **Thirty runs is not a true worst case.** The observed maxima only cover about a month of normal behavior. They likely miss month-end or quarter-end volume, upstream delays, slow storage, or a node under contention. One long-tail event could take most of the 15-minute margin.

2. **The plan says nothing about growth.** If data volume grows, durations will drift upward. There is no trend tracking, so the margin could disappear before anyone notices.

3. **Overhead between and around stages is not counted.** The 52 and 60 minute figures cover the stages alone. Scheduler start latency, handoff gaps, environment setup and teardown all count against the 75 minutes but are not measured.

4. **An overrun loses the whole day's data with no recovery.** This is the biggest issue. The plan has no checkpointing, no stage-level restart, no way to rerun later, and no retention of intermediate outputs. So a slow export at minute 74 throws away a successful import and transform.

5. **Alerting may fail exactly when it is needed.** The summary email is sent "when the batch ends." If the run is killed at the deadline, it never reaches its normal end, so the email may never be sent. The worst failure would then be silent. Also, an email to an alias is a weak signal for data loss.

## Recommended changes

- **Alert from outside the job.** A watchdog or the scheduler should fire on kill, timeout, or non-zero exit, and also when the success email doesn't arrive by the expected time. Page on-call for data loss instead of only emailing.
- **Add early-warning thresholds.** For example, alert if the cumulative time after stage 2 exceeds about 50 minutes, or if the total exceeds about 65 minutes. This gives a chance to act before the kill.
- **Make the work recoverable.** Persist each stage's output so a failed or killed run can resume from the last completed stage, or be replayed in a later window. Losing data permanently should not be the default outcome.
- **Track durations over time.** Record per-stage and total runtimes, review the p95 and p99 regularly, and set a policy such as "re-plan if p99 total exceeds 65 minutes."
- **Measure end-to-end wall time,** including scheduler and inter-stage overhead, not just the stage durations.
- **Check peak-volume periods** (month-end and similar) or run a load test at projected volume to confirm the margin holds.

## Summary

The timing works with a reasonable margin based on measured data. However, the consequence of a failure is severe (permanent data loss), and the alert may not fire in that exact case. Recovery and alerting should be fixed before relying on this plan.

VERDICT: GO_WITH_CHANGES