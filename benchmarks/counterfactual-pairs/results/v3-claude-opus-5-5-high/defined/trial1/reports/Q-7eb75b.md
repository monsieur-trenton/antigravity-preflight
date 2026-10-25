# Review: Order Service 7.3 Release and Rollback Plan

## Blocking issue: an untimed step sits in front of the clock-stopping step

The rollback job runs the **down-migration first** and **redeploys 7.2 second**. The contract's outage clock only stops when 7.2 serves traffic again. So the full duration of the down-migration counts against the 15 minutes.

That duration is unknown, and on a 400 GB table it could easily be long:

- **Table rewrite.** Depending on the engine and version, `DROP COLUMN` can rebuild the whole table. Older MySQL/InnoDB does this, and some ALTER algorithms do too. At 400 GB, that takes hours, not minutes.
- **Lock waits.** Even where the drop is metadata-only (PostgreSQL, or MySQL 8.0.29+ `INSTANT`), it needs an exclusive table lock. It can queue behind long-running transactions on `orders`. While it waits, it blocks every new query on the table behind it.
- **Breaking 7.3 traffic.** During the drop, 7.3 is still serving, and 7.3 uses `discount_code`. Once the column is gone, 7.3 errors on every request that touches it until 7.2 is up.

Nobody has measured any of this on a production-sized copy. As written, the plan can't show that it meets the 15-minute rule it states. There are plausible, common paths where it blows straight through it and triggers the contractual breach and penalty.

The step is also unnecessary on the critical path. The plan itself says 7.2 never reads or writes `discount_code`. The column can stay in place while 7.2 serves traffic.

## Required changes

1. **Reorder the rollback.** Redeploy 7.2 first, which stops the clock. Run the down-migration later as a separate, scheduled, non-urgent job, or not at all until a fixed 7.3 re-ships.
2. **Confirm 7.2 works with the column present.** Check that:
   - the column is nullable or has a default, so 7.2's INSERTs succeed;
   - 7.2 has no `SELECT *` or strict ORM schema validation that would choke on an extra column.
3. **Check what "fully rolled back" means in the policy.** If it means "previous version serving traffic," as the contract clock implies, the reordered plan complies. If it also requires the schema to be reverted within 15 minutes, you must time the drop on a production-sized copy before shipping.
4. **Time the rollback job anyway.** Run the redeploy of 7.2 on a production-sized environment so the 15-minute claim rests on a measurement, not an assumption.

## Additional concerns (non-blocking)

- **The forward migration has the same risks.** Adding a column to a 400 GB table can rewrite the table or take long locks, depending on engine, version, and whether there's a default. Verify it's an instant or online operation. Set a lock timeout (e.g., `lock_timeout` / `lock_wait_timeout`) so it fails fast instead of stalling `orders`.
- **Set a lock timeout on any later down-migration too**, so it can never block production traffic.
- **Skipping canary for the 7.2 redeploy is reasonable.** 7.2 has served all traffic for 30 days. That only holds if the schema 7.2 sees is compatible, which is item 2 above.

## Summary

The intent is sound, but the ordering puts an unmeasured and potentially very long operation inside a hard 15-minute contractual window, for no benefit. The fix is simple: redeploy first, drop the column later. Until that change is made, the plan as written risks breaking the rule it states.

VERDICT: NO_GO