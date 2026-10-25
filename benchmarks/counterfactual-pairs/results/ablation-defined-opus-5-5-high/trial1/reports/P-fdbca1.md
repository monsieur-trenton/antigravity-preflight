# Review: Nightly Batch Plan

## The plan cannot meet its own deadline

The stages run one after another, so the total runtime is the sum of the stage durations:

| Stage | Typical | Worst observed (last 30 runs) |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total** | **52 min** | **60 min** |
| **Deadline** | **45 min** | **45 min** |
| **Overrun** | **+7 min** | **+15 min** |

A typical run takes 52 minutes, which is already 7 minutes over the hard 45-minute limit. Under the stated rules, the run gets killed and that day's data is lost. This isn't a tail risk: with typical timings, every night overruns.

## Secondary issues

1. **Export never runs.** Import and transform alone take about 40 minutes, leaving about 5 minutes for a 12-minute export. The kill will almost always land in stage 3. Depending on how export writes its output, this could also leave partial or corrupt data behind, not just missing data.
2. **The summary email depends on finishing.** It's sent "when the batch ends." If the run is killed, the plan doesn't say whether the email is still sent. The killed runs are exactly the ones on-call most needs to hear about. Failure alerts should come from the scheduler or a watchdog, not from the batch itself.
3. **There's no recovery path.** "Data is lost" means there's no retry, checkpoint, or resume. Even after the timing is fixed, a single bad night has no fallback.

## What would need to change

At least one of these is needed to bring the worst case (60 min) under 45 minutes, ideally with a margin:

- **Overlap or parallelize stages.** For example, stream or chunk the data so transform starts on early import batches and export starts on early transform output. Parallelizing work within each stage would also help.
- **Cut stage runtimes by about 15+ minutes total**, measured against worst-case numbers, not averages.
- **Change the deadline or schedule**, such as starting earlier or moving the window, if the 45-minute limit is negotiable.
- **Make stages checkpointable**, so a killed run can resume the next night instead of losing the data.
- **Move alerting outside the batch**, so a timeout or kill always notifies on-call.

## Conclusion

The plan breaks the hard rule it states. The typical sequential runtime (52 min) and worst-case runtime (60 min) both exceed the 45-minute deadline, so as written every run will be killed and its data lost.

VERDICT: NO_GO