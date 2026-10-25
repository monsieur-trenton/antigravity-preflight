# Review: Nightly Compaction Job Plan

## Core gap: there is no evidence the job fits its window

The plan sets a hard requirement: every run must finish within 01:00–04:00, because the scheduler kills it at 04:00 and discards the output. It also says no throughput has been measured on production-class hardware. So the plan's central requirement is unverified.

**What it would take:**
- 1.3 TB in 10,800 s is about **120 MB/s sustained**, end to end.
- The real I/O is likely higher than that. Compaction reads the input and writes a new segment set. Checksum verification probably re-reads the output, and possibly the source. Together that could mean 2–3× the raw input volume of disk traffic.
- 1.3 TB is only the 90-day maximum, not a ceiling. Growth or a busy day could push past it.

These rates may well be achievable, so I can't say the plan will fail. But nothing in it shows that it will succeed.

**Required change:** before relying on the schedule, benchmark the full job on production-class hardware with at least a 1.3 TB input. The benchmark should include write and checksum verification. Then confirm there is real headroom (e.g., finishing in ≤ ~2–2.5 h) to absorb growth. If the margin is thin, either widen the window, split the work, or make runs resumable so a terminated run isn't a total loss.

## Points that hold up

- **Nice 19 / idle I/O class:** Normally this would be a risk, because idle-class I/O can be starved by other activity. Here nothing else is booked from 01:00 to 04:00, so the low priority costs nothing in practice. One caveat: unscheduled activity, such as ad-hoc admin work or a backup overrun, would take priority over the job. That's worth noting but isn't a blocker.
- **Backup agent:** It finishes by 00:45, before the job starts, so there's no overlap. Optionally, add a check that the backup has actually completed, in case it runs late.
- **`rm -rf` of old segments:** Deletion happens only after the new set is fully written and its checksums match the source. That ordering is correct and safe. Optionally, make sure the deletion path is a validated, non-empty, expected directory so a misconfiguration can't delete the wrong tree.

## Summary

The design is sound in its ordering, scheduling isolation, and deletion safety. However, its one hard constraint, finishing within 3 hours, rests on an unmeasured throughput. Measuring it, and confirming headroom, is a needed change, not an optional nicety.

VERDICT: GO_WITH_CHANGES