# Review: Shared Redis Cache for Rendered Dashboards

**The plan satisfies its isolation rule as written.**

**Isolation analysis**
- **Trusted tenant identity.** The tenant_id comes from the gateway after authentication, not from client input. So a caller cannot claim another tenant's identity.
- **Colliding dashboard IDs are separated.** Dashboard 42 in tenant A and dashboard 42 in tenant B map to `dash:A:42:{range}` and `dash:B:42:{range}`. These are different keys.
- **Key scope.** The handler only touches the key derived from the current request. That key always carries the caller's own tenant_id. No code path reads another tenant's entry.
- **Omitting the user ID is correct.** Visibility is tenant-wide, so per-user keys would only lower the hit rate. They would add no protection.
- **Freshness.** The 300 s TTL plus immediate deletion on edit bounds staleness. Staleness is a freshness matter in any case, not an isolation one.

**Optional hardening (not required)**
1. **Key delimiters.** Make sure tenant_id has a fixed format with no `:` (e.g., UUID or integer), and that `range` is validated or normalized against an allowlist. A tenant_id containing a delimiter could in theory make two different tuples produce the same string. With gateway-issued IDs this is unlikely. Validating `range` also stops clients from creating unbounded key variety.
2. **Invalidation completeness.** "Removes its cached entries" must cover every `range` variant for that dashboard. Options are a fixed set of ranges, a per-dashboard set of keys, or a version counter in the key. Avoid `KEYS`/`SCAN` on a shared cluster. Missing a variant only means stale data for up to 300 s, not a cross-tenant leak.
3. **Defense in depth.** You could store tenant_id inside the cached value and check it on read. This would catch any future bug that builds keys incorrectly.
4. **Tenant offboarding.** Decide how a deleted tenant's entries are purged, or simply let the TTL expire them.

None of these is needed for the plan to work or to meet its stated rule.

VERDICT: GO