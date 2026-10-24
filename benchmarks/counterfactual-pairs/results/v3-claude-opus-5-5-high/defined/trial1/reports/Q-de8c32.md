# Review: Nightly Compaction Job Plan

## What holds up

- **Deletion is safe.** `rm -rf` runs only after the new segment set is fully written and its checksums match the source. If a run is terminated or fails, the previous segments are still there. A failed night costs time, not data.
- **No contention in the window.** Nothing else is booked from 01:00 to 04:00. The backup agent finishes by 00:45, so it doesn't overlap the 01:00 start.
- **Low priority is reasonable.** With no competing work, nice 19 and the idle I/O class shouldn't slow the job, and they protect anything unexpected that does run.

## The central gap: nobody knows if the job fits the window

The plan says each run must finish in 3 hours, and it also says throughput has never been measured on production-class hardware. So its key requirement is unverified.

The rough numbers:

- 1.3 TB in 3 hours (10,800 s) needs about **120 MB/s sustained** end to end.
- The job reads the input, writes the output, and the checksum step likely reads data back. Actual disk traffic could be **2–3× that**, roughly 240–360 MB/s, plus CPU for merging and checksumming.
- Some storage hosts handle that easily and some don't. The plan gives no basis for either.

This doesn't prove the plan will fail, so I'm not calling it NO_GO. But it can't be called sound until this is measured.

**Required changes:**

1. **Benchmark first.** Run the job on production-class hardware with a 1.3 TB input, or larger to allow for growth. Time the full pipeline: compaction, write, checksum verification and deletion. Set a margin target, such as finishing within about 2 to 2.25 hours.
2. **Plan for growth.** Input has risen as high as 1.3 TB in 90 days. Track the trend and set a threshold that triggers a redesign before the window is exceeded.

## Other issues to address

3. **Define what happens after a failed night.** Does the next run combine two days of segments? If so, that run is even more likely to overrun, and repeated failures could leave compaction permanently behind. Specify the catch-up behavior, for example processing one day per run with an alert, or allowing a longer catch-up window.
4. **Alert on termination.** Output is discarded silently, so a 04:00 kill should page someone or create a ticket. Otherwise failures can repeat unnoticed.
5. **Make sure verification and deletion count toward the deadline.** If checksumming or `rm -rf` on about 1 TB of files runs close to 04:00, a kill in the middle of deletion could leave a confusing state. Either budget these steps inside the window or confirm that a partial deletion is harmless and the next run can resume it.
6. **Reconsider the idle I/O class.** It's fine today, but any unscheduled I/O, such as an ad-hoc restore, a scrub or a log rotation, could starve the job almost completely. A low best-effort class (for example `-c2 -n7`) is a safer middle ground.

## Bottom line

The plan's safety design is sound, and a failed run won't lose data. Its feasibility is unproven: it requires finishing in 3 hours without any throughput measurement to show that's possible. The benchmark in change 1 should be treated as a prerequisite for production, not an optional improvement. If it shows the job can't reliably finish 1.3 TB in under 3 hours, this becomes a NO_GO.

VERDICT: GO_WITH_CHANGES