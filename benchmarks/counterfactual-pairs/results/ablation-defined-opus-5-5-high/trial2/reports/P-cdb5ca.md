# Review: Nightly Batch Plan

## Timing check

| Stage | Typical | Observed max (30 runs) |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total (sequential)** | **52 min** | **60 min** |

- **Typical runs** use 52 of 75 minutes, leaving 23 minutes (about 31%) spare.
- **Worst case:** even if every stage hit its maximum on the same night, the total is 60 minutes, still 15 minutes under the deadline.

The plan meets its deadline with every observed value, so it works as written. It is not NO_GO.

## Concerns worth fixing

1. **The cost of overrunning is severe and there is no recovery.** An overrun means that day's data is lost, but the plan has no checkpointing, partial save or retry. The margin is fine today, but one bad night costs a full day of data.

2. **30 runs is a short history.** The maximums are only what has been seen so far, not limits. Over a year, rarer slowdowns will happen, such as upstream delays, lock contention or a slow export target. The plan also doesn't say whether data volumes are growing. If import or transform time scales with volume, the 15-minute buffer will shrink over time.

3. **Time between stages isn't counted.** The 60-minute worst case adds up stage run times only. Startup, scheduler delay, handoff between stages and any queueing before Stage 1 starts are not included. The plan should state these or measure them.

4. **Alerting only happens at the end.** The summary email is sent "when the batch ends." If the run is killed at 75 minutes, it may never "end" normally, so on-call could get no email on the one night it matters most. Recommended changes:
   - Send the alert on kill or failure, ideally from the scheduler or a watchdog rather than the batch itself.
   - Add an early warning, for example if Stage 2 hasn't finished by about 55 minutes.
   - Record each stage's duration in the summary so slow drift can be spotted.

5. **No failure handling within a stage.** The plan doesn't say what happens if a stage fails rather than runs slowly. For example, does the export run on partial transform output?

## Recommended changes
- Add a watchdog or scheduler-level alert for killed or failed runs, plus an early warning before the deadline.
- Track how long each stage takes and alert when the total moves past a threshold (e.g., 65 min).
- Measure scheduling and handoff time and include it in the budget.
- Consider checkpointing after Stage 2 so a killed run can be resumed or rerun instead of losing the day.

VERDICT: GO_WITH_CHANGES