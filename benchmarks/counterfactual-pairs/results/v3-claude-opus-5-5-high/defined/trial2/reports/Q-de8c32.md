# Review: nightly segment compaction plan

## The blocking issue: nobody knows whether the job fits in its window

The plan sets a hard rule that every run must finish inside 01:00–04:00, because the scheduler kills it at 04:00 and discards the output. But the plan also says no throughput has been measured on a production-class machine. So nothing shows the job can meet that rule.

The required rate is easy to work out:

- **Worst observed night:** 1.3 TB ÷ 10,800 s ≈ **120 MB/s sustained**, end to end.
- **Real requirement is higher.** That figure must cover reading the input, writing the new segments, and the checksum check. If verification re-reads the output, total I/O is closer to 2–3× the input size. Startup, the final rm, and any safety margin also come out of the same 3 hours.
- **No headroom for growth.** The 1.0–1.3 TB range is only 90 days of history. If volume trends upward, a borderline job will start failing without warning.

120 MB/s+ may be easy on this hardware or may be impossible; the plan gives no way to tell. To be precise, I am **not** saying the job will run too long. I am saying the plan rests on an untested assumption about its one hard constraint.

## What looks sound

- **Scheduling priority is fine.** Nice 19 and the idle I/O class only slow the job when other work competes. No other work is booked 01:00–04:00, and the backup agent finishes at 00:45, so the low priority should cost little. One caveat: the idle I/O class can be starved by any unbooked I/O (monitoring, log rotation, a backup that overruns). It's worth confirming the 00:45 finish is enforced, not just typical.
- **Deletion is safely ordered.** The old segments are removed with rm -rf only after the new set is fully written and checksums match. A killed or failed run therefore leaves the previous data intact.

## Changes needed before approval

1. **Measure throughput.** Run the job against a full-size input of at least 1.3 TB on production-class hardware, under the same nice and I/O-class settings. Include the checksum step in the timing.
2. **Set a pass threshold with margin.** For example, require the worst-case run to finish in about 2 hours, leaving roughly 1/3 of the window spare for growth and variance.
3. **Define what happens after a killed run.** State whether the next night processes two days of input, which would almost certainly overrun. Say how the failure is alerted. Consider a checkpointing or resumable design so partial work isn't thrown away.
4. **Confirm disk space.** The host must hold the input, the old segment set, and the new segment set at the same time.
5. **Add monitoring.** Track runtime against input size each night, so a shrinking margin is spotted before a run fails.

## Why NO_GO

The verdict scale doesn't fit this case perfectly:

- GO_WITH_CHANGES would mean the plan "works as written," which can't be claimed when the throughput is unknown.
- NO_GO strictly means it "will fail," which also isn't shown.

I'm choosing NO_GO because the plan cannot show it meets the hard constraint it states itself, and approving it would mean betting on that. Read this as "not yet," not "proven broken." If the measurement in item 1 shows comfortable margin, this becomes a GO_WITH_CHANGES with items 3–5 as the remaining work.

VERDICT: NO_GO