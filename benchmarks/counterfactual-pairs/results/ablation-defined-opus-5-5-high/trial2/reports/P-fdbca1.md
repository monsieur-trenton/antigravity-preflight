# Review: Nightly Batch Plan

## The core problem: the stages don't fit in the window

The stages run one after another, so their durations add up:

| Stage | Typical | Worst observed |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total** | **52 min** | **60 min** |
| **Deadline** | **45 min** | **45 min** |

A **typical** run takes about 52 minutes, which is **7 minutes over** the 45-minute limit. The worst observed run takes about 60 minutes, which is **15 minutes over**.

These figures come from 30 measured runs, so this is not a rare-case risk. On a normal night the batch will be killed partway through export and that day's data will be lost. Import and transform alone take 40 minutes typically and up to 46 minutes, so even those two stages together can exceed the deadline before export starts.

The plan also has no buffer. There is no allowance for retries, startup and teardown time, or the summary email.

## Secondary issues

1. **Unclear email on failure.** The plan says the email is sent "when the batch ends." A killed run may not end cleanly, so on-call may never be told that data was lost. A watchdog or an external alert should fire if the job is killed or no summary arrives by a set time.
2. **No failure handling.** There is no checkpointing, partial-commit, or rerun strategy. A kill means total loss for the day.
3. **No trend monitoring.** Durations near the limits should trigger a warning before they become failures.

## Options to make it work

You would need to save at least 7 minutes typically and 15+ minutes in the worst case, plus a safety margin:

- **Overlap or pipeline the stages.** For example, stream records from import into transform. This contradicts the plan's statement that stages do not overlap, so the design would have to change.
- **Speed up individual stages.** Parallelize import, optimize transform, or add capacity.
- **Move work out of the window.** Do incremental imports during the day, or pre-stage the data.
- **Change the constraint.** Extend the window, or make the kill save completed stages so the next run can resume.

Aim for a worst-case total of about 40 minutes or less, which leaves at least 5 minutes of headroom.

## Conclusion

The plan breaks its own stated rule. Even typical stage times add up to more than the hard 45-minute deadline, so it will regularly overrun, get killed, and lose data. Improvements alone won't fix this; the schedule needs to be redesigned.

VERDICT: NO_GO