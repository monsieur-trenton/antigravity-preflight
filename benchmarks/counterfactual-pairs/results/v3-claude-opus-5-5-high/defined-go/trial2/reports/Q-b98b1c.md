# Plan review: tenant-shared Redis cache for rendered dashboards

The plan meets its isolation rule as written.

## Isolation analysis

- **The tenant is part of the key, and it comes from a trusted source.** `tenant_id` is set by the gateway after authentication. The caller cannot supply or spoof it. Every key a request can touch is therefore inside that caller's tenant namespace.
- **Colliding dashboard IDs are handled.** Dashboard 42 in tenant A is `dash:A:42:{range}`, and in tenant B it is `dash:B:42:{range}`. Restarting numbering per tenant cannot cause cross-tenant hits.
- **The handler touches only the key built from the current request.** No lookup path can reach a key built from another tenant's ID.
- **Leaving out the user ID is correct.** Every user in a tenant may see every dashboard in that tenant, so sharing entries within a tenant is intended. It does not breach the stated rule, which only concerns crossing tenants.
- **Freshness is bounded.** The TTL is 300 seconds, and edits invalidate entries immediately. Staleness is a correctness concern, not an isolation one, and both mechanisms cover it.

## Optional hardening (not required)

- **Delimiter safety.** `range` comes from the request and may contain `:`. It sits after the tenant segment, so it cannot move a key into another tenant's namespace. For hygiene, consider normalizing or encoding `range` to a canonical form. That also improves the hit rate, since equivalent ranges would map to one key. The same applies to `tenant_id` if its format could ever include `:`, although its gateway origin makes that unlikely.
- **Invalidating every range.** "Removes its cached entries" means deleting every `{range}` variant of a dashboard. Avoid `KEYS`/`SCAN` across a cluster for this. Instead, keep a per-dashboard set of range keys, or use a version counter in the key, such as `dash:{tenant}:{id}:v{n}:{range}`.
- **Edit/fill race.** A render that is in flight during an edit could write a stale entry back after the delete. The 300-second TTL bounds the damage. A version counter would remove the race entirely.
- **Cluster slotting.** If invalidation uses multi-key operations, a hash tag such as `dash:{tenant:id}:...` keeps one dashboard's keys in the same slot.

None of these are needed for the plan to work or to satisfy its isolation rule.

VERDICT: GO