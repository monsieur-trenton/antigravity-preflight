# Review: Shared-Redis Dashboard Cache

The plan meets its isolation rule. A few gaps around staleness and robustness are worth fixing.

## Isolation: holds

- **Tenant is in the key.** Dashboard IDs restart at 1 for each tenant, so `dashboard_id` alone would collide. Putting `tenant_id` in the key fixes that.
- **Tenant comes from a trusted source.** The gateway stamps `tenant_id` after authentication, so a client cannot choose another tenant's namespace.
- **No other keys are touched.** The handler only uses the key built from the current request, so it never reads another tenant's entry.
- **Leaving out the user ID is fine.** Every user in a tenant may see every dashboard, so per-user keys are not needed.

A response cached for tenant A can only be served under a key starting `dash:A:`. Tenant B's requests always build `dash:B:…`. The rule holds.

## Recommended changes

1. **Delimit or encode the key parts.** `range` is likely client-supplied. `tenant_id` and `dashboard_id` are probably colon-free, but the plan doesn't say so. Validate that tenant and dashboard IDs contain no `:`. Also normalize `range` (canonical format, whitelist or parse) or hash it. This keeps keys unambiguous and stops callers from inflating key count with variants like `7d`, `7D`, `07d`.

2. **Say how invalidation finds every range.** "Editing removes its cached entries" covers many `range` values. Use one of these:
   - a per-dashboard index set (`SADD dash-idx:{t}:{d} <key>`), or
   - a version counter in the key (`dash:{t}:{d}:v{n}:{range}`), bumped on edit.

   Do not use `KEYS` or a broad `SCAN` on a shared cluster.

3. **Close the invalidate/write race.** A render that started before an edit can finish after the delete and write stale data back for up to 300s. A version counter in the key solves this. So does a compare-on-write against the version or edit timestamp.

4. **Confirm the rendered payload is not personalized.** If the output contains anything user-specific (name, locale, timezone, "last viewed"), it will leak within a tenant. That doesn't break the stated rule, but it is wrong. Either strip such content or add those dimensions to the key.

5. **Account for the shared cluster.**
   - Set memory limits and an eviction policy (e.g., `allkeys-lru`) so one tenant's volume can't evict everyone else's data.
   - Consider per-tenant key quotas or metrics.
   - If the threat model requires it, use Redis ACLs or key-prefix restrictions as defense in depth.

6. **Handle Redis failure.** Fall back to rendering directly when Redis is unavailable, with short timeouts, so cache problems don't take dashboards down.

VERDICT: GO_WITH_CHANGES