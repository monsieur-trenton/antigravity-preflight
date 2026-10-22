# Review of the Nightly Batch Plan

## Timing against the 75-minute deadline

Because the stages run one after another and never overlap, total runtime is the sum of the three stages.

| Stage | Typical | Max observed (30 runs) |
|---|---|---|
| 1. Import | 22 min | 25 min |
| 2. Transform | 18 min | 21 min |
| 3. Export | 12 min | 14 min |
| **Total** | **52 min** | **60 min** |

- **Typical case:** 52 minutes leaves 23 minutes (about 31%) of headroom.
- **Worst case:** If every stage hit its observed maximum on the same night, the total would be 60 minutes. That still leaves 15 minutes (20%) of headroom. This bound is conservative, since the stage maximums probably didn't all happen on the same run.

The plan fits within its stated hard limit even in the pessimistic case. Nothing in the plan as written breaks a rule it states or is expected to fail.

## Optional suggestions (robustness only, not required)

1. **Alert on a killed run.** The summary email goes out "when the batch ends." If the 75-minute kill skips that step, on-call might not learn that the day's data was lost. A separate deadline or watchdog alert would close that gap.
2. **Track duration trends.** The 15-minute worst-case margin is solid today. If data volume grows, import is the most likely stage to eat into it. A warning threshold, for example at 65 minutes, would give early notice.
3. **Recovery path.** The plan accepts that an overrun loses that day's data. A documented rerun or backfill procedure would reduce the impact if it ever happens.

These suggestions would make a working plan more robust. None of them is needed for the plan to meet its requirements.

VERDICT: GO