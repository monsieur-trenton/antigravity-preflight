# Review: Nightly Compaction Plan

## Summary

The plan is reasonable, and it has a safety net: a hard cancel with reporting. Its central assumption has not been tested, though. Nobody knows whether one thread can process 40 GB in 30 minutes on this host. Fix that before rollout.

## The core arithmetic

- 40 GB / 1800 s ≈ **22 MB/s sustained**, from start to finish, with no margin.
- That rate is plausible on many hosts, but not guaranteed. It depends on what "compaction" involves:
  - **Sequential copy/merge on SSD:** easily hundreds of MB/s. Comfortable.
  - **Decompress and recompress** (e.g. gzip at default levels): single-threaded gzip often runs at 20–50 MB/s. Borderline.
  - **Sort or merge with random I/O, or spinning disks, or shared/throttled cloud volumes:** could fall well below 22 MB/s. It would fail every night.
- No headroom is budgeted for startup, final fsync/rename, a noisy neighbor, or input growth. If the input grows 10–20%, a pass that barely fits today stops fitting.

## Issues

### 1. Throughput is unmeasured (blocking)
- **Change:** Run the compaction on the target host, or an identical one, against a representative input at the same time of night.
- **Target:** at least ~1.5× the required rate (≥ ~35 MB/s), so the job finishes in ≤ 20 minutes.
- If it misses that target, change the design before going live. Options: parallelize, use incremental/partitioned compaction, use a cheaper codec, or widen the window.

### 2. Cancellation semantics are unspecified
"Cancelled and reported" is only safe if cancellation leaves the system in a good state. The plan should state:
- Compaction writes to a temp location and atomically swaps in only on success. A cancel must never leave half-compacted live data.
- Temp output is cleaned up on cancel. Otherwise 40 GB of orphaned partial files pile up each night.
- Whether completed partitions or chunks are kept (resumable) or thrown away. All-or-nothing on a 40 GB job is fragile.

### 3. Failure loop / growth spiral
If compaction is cancelled night after night, the uncompacted data grows. That makes the next run even less likely to finish. The plan should define:
- How many consecutive cancellations trigger escalation (e.g. 2 → page, not just a report).
- A fallback, such as a manual run in a wider window or chunked catch-up.

### 4. Single thread is a choice, not a given
If the benchmark is borderline, parallelism is the obvious lever. If single-threading is deliberate (to limit contention with other nightly jobs, or because of ordering requirements), write down why. Then everyone knows what can be changed.

### 5. Progress logging could carry more signal
Per-minute logs are good. Make each entry include bytes processed, the current rate, and a projected finish time. Then:
- An early-warning alert can fire when the projection exceeds the window, say by minute 10, rather than at minute 30.
- You get real throughput history for capacity planning without extra work.

### 6. Resource prerequisites
State the free-disk requirement for compaction output plus temp space, likely up to about 40 GB extra in the worst case. Check it before starting, and fail fast with a clear report if it's not available.

## Required before go
1. Benchmark on the target host and confirm ≥ ~1.5× margin.
2. Document and verify atomic swap and cleanup on cancel.

## Recommended
3. Escalation after repeated cancellations, plus a catch-up path.
4. Rate and ETA in the progress log, with an early "won't finish" alert.
5. Pre-flight disk-space check.
6. Track input size growth and re-check the margin periodically.

VERDICT: GO_WITH_CHANGES