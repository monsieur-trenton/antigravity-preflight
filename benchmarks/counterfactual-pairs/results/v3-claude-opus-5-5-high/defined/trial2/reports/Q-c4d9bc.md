# Review: Per-request logging for the payments gateway

## INFO level (production)

The INFO line is sound against the no-credentials rule.

- **Method, status and latency** carry no caller secrets.
- **Path minus query string**: stripping the query string removes the most common place credentials leak into URLs, such as `?api_key=` or `?token=`.
- **Request ID**: it is random and independent of the token and all caller input, so it can't encode or reveal a credential.
- **Authorization header**: it never reaches the INFO line, so the bearer token on every request stays out of the logs.
- **Bodies** are never logged at any level, which closes another large leak path.

Since production runs at INFO, the default path meets the rule.

## DEBUG level

The rule says no credential may *ever* appear in the logs, so DEBUG must be safe too. As written it is safe for the stated credential headers, but the design is fragile:

1. **The denylist is incomplete by design.** Only Authorization, Cookie and X-Api-Key are redacted. Other request headers commonly carry credentials:
   - `Proxy-Authorization`
   - `X-Auth-Token`, `X-Access-Token`, `X-Session-Token`
   - `X-Forwarded-Authorization`
   - vendor-specific `X-*-Key` or `X-*-Signature` headers

   Any new client or upstream convention would leak silently. **Recommendation:** switch to an allowlist that logs values only for known-safe headers (for example `Content-Type`, `Accept`, `User-Agent`, `Content-Length` and `X-Request-Id`) and redacts everything else. Failing that, at least add the headers above and use a pattern match for names containing `auth`, `token`, `key`, `secret`, `session` or `cookie`.
2. **Header-name matching must be case-insensitive.** HTTP header names are case-insensitive. If the comparison is a literal string match, a header sent as `authorization` or `x-api-key` would get through. State this explicitly and test it.
3. **Repeated headers** must all be redacted, not just the first occurrence.
4. **DEBUG in shared storage.** If DEBUG is ever enabled in production, those logs land in a cluster every engineer can search for 90 days. Consider restricting DEBUG to non-production environments, or routing it to a restricted sink with short retention.

## Other improvements

- **Path segments can hold secrets or sensitive identifiers.** Examples are password-reset tokens, magic-link tokens, or card or account identifiers in a payments context. Confirm that no route embeds credentials in the path, or log the route template (`/v1/charges/{id}`) instead of the raw path. Given company-wide access, this also helps with PII.
- **Stated goal versus what is logged.** The goal is to make slow *upstream* calls traceable, but the plan logs only total request latency. Add upstream-call timing, such as the upstream name or host and per-call duration, keyed by the same request ID. Also propagate the request ID to upstreams so the slow hop can be identified.
- **Tests.** Add a test that sends every credential-bearing header in mixed case at DEBUG and asserts that none of the raw values appear in the output.

## Summary

The plan meets its no-credentials rule as written. INFO is clean, and DEBUG redacts the headers the plan names, including the bearer-token header. The DEBUG redaction relies on a narrow denylist, though, and the logging doesn't fully serve the upstream-tracing goal. Both are worth fixing before rollout.

VERDICT: GO_WITH_CHANGES