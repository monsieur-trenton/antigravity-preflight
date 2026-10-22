# Review: Nightly Batch Plan

## Timing check

The stages run one after another, so the batch duration is the sum of the stage durations:

| Stage | Typical | Worst observed |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total** | **52 min** | **60 min** |

The hard limit is **45 minutes**.

## Finding: the plan fails on every run

- **A typical run takes 52 minutes**, 7 minutes over the limit.
- **A worst-case run takes 60 minutes**, 15 minutes over.
- **The best case is still over.** Each stage's typical time is above its minimum, so the true best case is unknown. But a run would need to be about 13% faster than typical in every stage to finish in time, and nothing in the 30 measured runs suggests that happens.

Because overrunning runs are killed, the batch will be killed most or all nights and that day's data will be lost. This is not an edge-case risk. It is the expected outcome.

**Secondary issue:** the summary email is sent "when the batch ends." If a killed run never reaches that step, on-call won't be told about the failure, so the data loss could go unnoticed.

## Required changes (at least one must close a 15-minute gap)

1. **Run stages in parallel or pipelined.** For example, transform and export could process data in chunks while import is still running. This is the most likely way to fit under 45 minutes.
2. **Make the stages faster** by a combined 15+ minutes at worst case, for example through parallelism within stages or incremental/delta imports instead of full imports.
3. **Get the deadline changed or the batch split**, for example by moving export to a separate job with its own window.
4. **Add checkpointing**, so a killed run can resume instead of losing the day's data.
5. **Send an alert when a run is killed or times out**, not just when it finishes. A watchdog or dead-man's-switch alert would cover this.

After any change, check the new **worst-case** total (not the typical total) against 45 minutes, with some safety margin.

VERDICT: NO_GO