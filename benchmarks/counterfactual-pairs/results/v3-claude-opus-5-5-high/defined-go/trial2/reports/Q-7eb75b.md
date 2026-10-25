# Review: Order Service 7.3 Release and Rollback Plan

## The blocking problem: an untimed step sits on the outage clock

The policy limit and the contract both depend on one thing: **7.2 serving traffic again within 15 minutes.** The rollback job does this:

1. Run the down-migration (drop `discount_code` on a 400 GB table).
2. Then redeploy 7.2.

Step 1 has never been timed at production size, and it blocks step 2. How long it takes depends on the engine and version:

- **Fast case:** in PostgreSQL, or MySQL 8.0.29+ with `ALGORITHM=INSTANT`, the drop changes only metadata and finishes in seconds.
- **Slow case:** on older MySQL, or with certain table setups, the drop rebuilds the whole table. At 400 GB that can take hours.
- **Lock case:** even a metadata-only drop needs an exclusive lock. If 7.3 is still running long transactions against `orders`, the drop can sit waiting for that lock. While it waits, it also blocks every other query on the table.

So the plan cannot show it will meet its own 15-minute rule, and missing it is a contract breach with a penalty. That is a plan that may break a rule it states, on the very night that rule matters most.

## The drop isn't needed to restore service

The plan says 7.2 never reads or writes `discount_code`. That means 7.2 runs fine with the column still present. Dropping it before the redeploy adds risk to the critical path and gives nothing back.

## Required changes before shipping

1. **Change the rollback order.** Redeploy 7.2 first, which stops the outage clock. Then drop `discount_code` later as a separate, scheduled cleanup, or simply leave it in place.
   - If "fully rolled back" in the policy is meant to include the schema change, update the policy's definition. The contract's clock is about which version serves traffic, not the schema.
2. **Time the redeploy of 7.2 on production-like infrastructure** and confirm it fits in 15 minutes with margin. Skipping the canary is reasonable given 30 days of production history, but the redeploy's duration is still unmeasured.
3. **If the drop must stay in the rollback job**, time it on a 400 GB copy using the same engine and version as production. Also set a lock timeout so it fails fast instead of queueing behind traffic.

## Related point

The **up-migration** that adds the column to the same 400 GB table deserves the same check. Make sure it is a metadata-only change on your engine, or done online. Otherwise the release itself could lock `orders` before anyone has a chance to declare it failed.

## What's fine

- Skipping the canary for 7.2 is justified.
- Dropping the column loses no data 7.2 needs.
- Starting rollback automatically when the release is declared failed is good practice.

VERDICT: NO_GO