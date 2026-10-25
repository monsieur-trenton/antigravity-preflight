# Review: Nightly Compaction Job Plan

## What holds up

- **The deletion is safe.** `rm -rf` on the previous segments only runs after the new set is fully written and its checksums match the source. A terminated or failed run leaves the old data intact, so a failure costs time but not data.
- **Low priority costs nothing here.** Nice 19 and the idle I/O class only lose out to competing work. Nothing else is booked from 01:00 to 04:00, and the backup agent finishes at 00:45. The job should get the whole machine for the window.
- **The backup cannot overlap.** It ends 15 minutes before the job starts.

## The gap: nothing shows the job fits in 3 hours

The plan states a hard rule: each night's run must finish within the 3-hour window, because the scheduler kills it at 04:00 and discards the output. Nothing in the plan shows that this rule is met.

- **Required rate:** 1.3 TB in 10,800 s is about 120 MB/s sustained, end to end. That covers reading the input, writing the output and computing checksums, with no margin.
- **Measured rate:** none. The plan says no throughput figure exists for a production-class machine.
- **Plausibility:** 120 MB/s may be easy on NVMe. It is not safe to assume when reads and writes share spinning disks, or when checksumming is CPU-bound at nice 19.

This is not just extra robustness. It is the one requirement the plan names as mandatory, and it is unverified. The plan also has no response if a run is killed. Because output is discarded, a job that is too slow for 1.3 TB fails every heavy night. It is unclear whether the next night picks up the missed day or the backlog just grows.

I am not calling this NO_GO because nothing shows the job *will* fail. The rate needed may be well within what the hardware can do. But the plan cannot be signed off until that is shown.

## Required changes

1. **Measure throughput** on a production-class machine using a full-size input of about 1.3 TB, with the same nice and ionice settings. Confirm it finishes well under 3 hours, for example within 2–2.5 hours, so normal growth has room.
2. **Define what happens when a run is killed:** alerting, and whether the next night retries the missed day or combines the backlog.
3. **Optionally,** log each night's runtime and alert when it nears the limit, so growth toward 3 hours is caught before a night fails.

If the benchmark shows a comfortable margin, the rest of the plan is sound as written.

VERDICT: GO_WITH_CHANGES