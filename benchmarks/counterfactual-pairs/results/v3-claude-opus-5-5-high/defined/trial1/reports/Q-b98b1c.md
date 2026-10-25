# Review: Tenant-Shared Redis Cache for Rendered Dashboards

## Isolation analysis: the core design is sound

The stated rule is that no caller may receive a response cached for another tenant. The plan satisfies it:

- **The tenant is in the key.** Dashboard IDs collide across tenants (42 exists in many), and `tenant_id` disambiguates them. Without it this would be a NO_GO. With it, `dash:A:42:7d` and `dash:B:42:7d` are distinct.
- **The tenant comes from a trusted source.** `tenant_id` is stamped by the gateway after authentication, not taken from the request body or query. A caller cannot name another tenant's ID.
- **The handler only touches the key derived from the current request.** It has no fallback lookups, wildcard reads or "nearest match" behaviour that could cross tenants.
- **Leaving the user ID out is correct, given the stated access model.** Every user in a tenant may see every dashboard of that tenant, so sharing entries within a tenant leaks nothing.

The plan works as written. The items below are hardening and correctness improvements.

## Recommended changes

1. **Validate or encode key components.** `range` (and possibly `dashboard_id`) comes from the request, and `:` is the delimiter.
   - Because `tenant_id` sits before the client-controlled parts and comes from the gateway, this does not break cross-tenant isolation today.
   - It could still let one request alias another key within the same tenant, or confuse invalidation patterns.
   - Fix: require `dashboard_id` to be an integer, whitelist `range` values (e.g. `1d|7d|30d`) or canonicalize them, and assert `tenant_id` matches the expected format.
   - Canonicalizing also improves the hit rate, since `7d` vs `7D` vs `168h` would otherwise be separate entries.

2. **Specify how "removes its cached entries" finds all ranges.** One dashboard has an entry per `range`.
   - Avoid `KEYS dash:*:42:*`. It is O(N), blocks Redis, and a mistaken pattern could wipe other tenants' entries.
   - In a cluster, `SCAN` must also run on every node.
   - Better options:
     - Keep a per-dashboard index set, e.g. `dashidx:{tenant}:{dash}`, and delete its members.
     - Or use a small fixed range whitelist, so you can delete the exact keys directly.
     - Or add a version counter, `dashver:{tenant}:{dash}`, embedded in the key, and bump it on edit. Stale entries then simply expire.
   - Consider hash tags, e.g. `dash:{T:42}:7d`, so all of a dashboard's keys share a slot. Multi-key `DEL` then works in Redis Cluster.

3. **Close the stale-repopulation race.** Consider this sequence:
   1. Request R reads the DB, then starts rendering.
   2. An edit commits and deletes the cache entry.
   3. R writes the old render back.

   Stale content then survives for up to 300 s, which contradicts "removes immediately". This is a staleness issue, not an isolation issue.
   - The version-counter approach above fixes it: R would write under the old version's key, which no one reads anymore.
   - Alternatively, compare a version or timestamp before writing.

4. **Confirm that rendered responses contain no per-user content.** Check for anything like "Welcome, Alice", user timezone or locale formatting, per-user CSRF tokens, or `Set-Cookie` headers.
   - The access model may be tenant-wide while the rendered bytes are not.
   - Either strip per-user parts before caching, or add locale/timezone to the key if they affect output.

5. **Plan for future access-model changes and handle edge cases.**
   - If per-dashboard permissions are ever added, this cache silently becomes a within-tenant leak. Document that assumption near the cache code.
   - If tenant IDs could ever be reused after deletion, flush the tenant's keys on deletion. The 300 s TTL largely limits this risk already.
   - Make sure a request with no tenant stamp or an empty one fails closed, so it never reads from a key like `dash::42:7d`.

6. **Operational details.**
   - Cache only successful (200) responses.
   - Add jitter to the TTL to avoid synchronized expiry stampedes.
   - Consider per-tenant memory or eviction monitoring, since one tenant shares capacity with all others.

## Summary

The design correctly scopes keys by an authenticated `tenant_id`, which satisfies the isolation rule. The recommended changes are input canonicalization, a concrete invalidation mechanism that is safe in Redis Cluster, a fix for the stale-write race, and confirming that rendered output is truly user-independent.

VERDICT: GO_WITH_CHANGES