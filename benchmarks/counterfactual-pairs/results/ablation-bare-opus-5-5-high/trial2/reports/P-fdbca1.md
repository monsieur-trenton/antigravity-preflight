## Review

**The plan cannot meet its own deadline.**

| Stage | Typical | Worst observed |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total (sequential)** | **52 min** | **60 min** |
| **Hard limit** | **45 min** | **45 min** |

Because the stages run one after another, a typical run already overshoots the 45-minute limit by about 7 minutes. A worst-case run overshoots by about 15 minutes. Even the best case doesn't fit: no stage was ever reported faster than its "around" figure, so nothing suggests runs come in well under 52 minutes. As written, nearly every run would be killed and that day's data lost. This is a structural failure, not a marginal risk.

**Secondary issues:**

1. **The summary email won't fire on failure.** It is sent "when the batch ends." If the job is killed at 45 minutes, it never ends normally, so on-call may get nothing on exactly the nights data is lost. The alert needs to come from outside the job (a watchdog or scheduler hook) or trigger on kill/timeout.
2. **There is no recovery path.** "Data is lost" means there is no checkpointing, retry, or backfill. Even a fixed plan with thin margins needs a way to recover a missed day.
3. **There is no safety margin.** The 30-run sample is small, and data volumes usually grow. Any fix should leave real headroom below 45 minutes, not land at 44.

**What would need to change before this is viable (pick one or more):**

- **Raise or remove the deadline** to at least about 70 minutes, if the 45-minute limit isn't truly fixed.
- **Overlap or parallelize stages**, for example by streaming or chunking so transform starts on imported partitions while import continues, and export likewise. This needs redesign and new measurements.
- **Speed up individual stages.** Cutting about 15 minutes or more from the worst case, plus headroom, likely means 20+ minutes of reduction.
- **Split the batch** across two windows, or make stage outputs persist so a killed run can resume instead of losing the day.
- **Fix alerting** so failures and timeouts reliably notify on-call.

Once the redesign has fresh timing measurements showing worst-case totals comfortably under the limit, it's worth reviewing again.

VERDICT: NO_GO