## Review

**The schedule cannot meet the deadline.** The stages run one after another with no overlap, so total runtime is the sum of the three stages:

| Stage | Typical | Max observed |
|---|---|---|
| 1 – Import | 22 min | 25 min |
| 2 – Transform | 18 min | 21 min |
| 3 – Export | 12 min | 14 min |
| **Total** | **52 min** | **60 min** |

The hard deadline is **45 minutes**. A typical run already overruns it by 7 minutes, and a worst-case run by 15. These are measured figures from 30 runs, so this is the expected outcome, not an edge case. The batch will be killed every night, and every night's data will be lost.

The summary email will also not be sent, because the kill happens before "the batch ends." On-call would get no signal that anything failed.

**What would need to change (any one of these, sized to the gap):**
- **Overlap or parallelize stages.** For example, stream or chunk the data so transform starts on imported batches while import continues, and export likewise. The 52-minute sequential total has to come down by at least 7 minutes, and by 15 or more to cover the worst case with margin.
- **Speed up the stages.** Import is the largest stage and the obvious first target. Combined savings must be at least 15 minutes to cover observed maximums.
- **Relax the constraint.** Get the deadline raised to at least about 60 minutes plus a safety margin, or split the work across two windows.
- **Make failure non-destructive.** Checkpoint after each stage so a killed run can resume instead of losing the day's data. This doesn't fix the timing, but it removes the catastrophic consequence.
- **Alert on failure, not just on completion.** Have a watchdog or the scheduler send an alert when the job is killed, so a timeout isn't silent.

Because the plan as written fails on every run, it needs a structural change, not refinement.

VERDICT: NO_GO