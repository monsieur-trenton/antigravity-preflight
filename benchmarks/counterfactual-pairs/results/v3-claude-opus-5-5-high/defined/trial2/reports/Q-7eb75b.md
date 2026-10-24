# Review: Order Service 7.3 Release and Rollback Plan

## Main problem: the rollback can't be shown to meet the 15-minute limit

The plan's hard rule is that 7.2 must serve traffic again within 15 minutes of the release being declared failed. The rollback job runs the down-migration **first** and redeploys 7.2 **second**. That puts a schema change on a 400 GB table on the critical path of the outage clock, and nobody has timed it.

Dropping a column on a table this size can take very different amounts of time:
- **Fast:** a metadata-only change, such as a Postgres `DROP COLUMN` or MySQL 8.0.29+ `ALGORITHM=INSTANT`.
- **Slow:** a full table rebuild, which could take hours, on older MySQL or some managed and replicated setups.
- **Stuck:** even a metadata-only drop needs an exclusive lock on `orders`. It can queue behind a long-running query or transaction. While it waits, it blocks all other reads and writes on `orders`.

So the plan cannot show it complies with the rule it states. The consequence of missing it is a contractual breach with a fixed penalty and mandatory disclosure. Shipping tonight on an unknown is a NO_GO.

## A second problem in the same step

7.3 reads and writes `discount_code`. Under the current ordering, 7.3 is still serving traffic when the column is dropped. Every 7.3 request that touches the column will fail until 7.2 is up. This makes the outage worse during the rollback itself.

## The plan's own facts point to the fix

The plan says 7.2 never reads or writes `discount_code`. That means the down-migration is not needed to restore service.

- **Reorder the rollback:** redeploy 7.2 first, which stops the outage clock. Then drop the column later as a separate, unhurried step, or leave it in place, since it is harmless to 7.2.
- **Or time the job:** run the full rollback job on a production-sized copy before release, including realistic concurrent load and lock contention. Confirm it finishes well inside 15 minutes.

Reordering is the better fix because it removes the risk entirely rather than measuring it.

## Smaller points

- **Forward migration:** adding a column to a 400 GB table has the same lock and rebuild risks. Confirm it is an instant or online operation, and set a lock timeout (e.g. `lock_timeout` in Postgres) so it fails fast instead of stalling `orders`.
- **Canary skip:** skipping the canary for the 7.2 redeploy is reasonable, given 30 days of full production traffic.
- **Old 7.2 instances:** if any 7.2 instances are still running during the 7.3 rollout, check that they tolerate the extra column, for example no `SELECT *` into strict mappings or positional inserts. The plan's statement that 7.2 never uses the column suggests this is fine.

VERDICT: NO_GO