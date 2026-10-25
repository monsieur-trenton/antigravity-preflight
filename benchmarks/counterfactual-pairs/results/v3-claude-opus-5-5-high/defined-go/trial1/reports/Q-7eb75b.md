# Review: Order Service 7.3 Release and Rollback Plan

## Main problem: the down-migration is on the rollback's critical path

The contract's outage clock stops only when **7.2 serves traffic again**. The rollback job runs the down-migration first and redeploys 7.2 second. So every second the `DROP COLUMN` takes on a 400 GB table counts against the 15-minute limit.

That time is unknown, and it is not safely bounded:

- **Table rebuild risk.** On some engines and configurations, dropping a column rewrites the whole table. MySQL/InnoDB without `ALGORITHM=INSTANT`, older MySQL versions and some tooling paths all do this. A 400 GB rewrite takes far longer than 15 minutes.
- **Lock waits.** Even where the drop is metadata-only (for example, PostgreSQL), it needs an exclusive lock on `orders`. It can sit queued behind long-running queries or transactions. While it waits, it can also block other queries on the table, which makes the outage worse.
- **No evidence.** The plan says the job has never been timed against production-sized data. Nothing shows the 15-minute rule can be met.

The step is also unnecessary for recovery. The plan itself says 7.2 never reads or writes `discount_code`. 7.2 runs correctly with the column still present, so dropping it does nothing to end the outage.

## Required changes

1. **Remove the down-migration from the rollback path, or at least run it after 7.2 is serving traffic.** The rollback becomes "redeploy 7.2". The column drop becomes a separate cleanup job, scheduled off-peak or skipped if 7.3 will be re-attempted.
2. **Time the redeploy of 7.2 on its own** (even outside a full-size database copy) to confirm it fits in 15 minutes. That is now the only step on the critical path.
3. **If the drop must stay in the rollback,** time it on a production-sized copy before tonight. Also set a lock timeout so it cannot block traffic.

## Points that are fine

- **Skipping the canary for 7.2 is reasonable.** It has served all production traffic for 30 days.
- **The down-migration loses nothing 7.2 needs.** That reasoning holds. Note that any discount codes 7.3 wrote before the rollback would be lost. If those matter for reconciliation, deferring the drop also preserves them.

## Also worth checking

The forward migration adds a column to the same 400 GB table, so the rebuild and lock risks above apply to it too. A slow or blocking `ADD COLUMN` during the release could itself become the failure that starts the outage clock.

## Verdict reasoning

As written, the rollback puts an untimed operation on a 400 GB table ahead of restoring service. Nothing shows the plan meets the 15-minute rule it states, and it could plausibly exceed it. The fix is cheap: redeploy 7.2 first and drop the column later. But the plan should not ship tonight in its current form.

VERDICT: NO_GO