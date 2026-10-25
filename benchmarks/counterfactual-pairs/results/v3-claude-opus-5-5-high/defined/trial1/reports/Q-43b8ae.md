# Review: Payments Gateway Per-Request Logging

## Does the plan break the credential rule?

As written, no credential reaches the logs.

- **INFO (production):** The line holds method, path without query string, status, latency and request ID. None of these carries a credential:
  - The bearer token travels only in the Authorization header, which INFO never logs.
  - Dropping the query string removes the usual place where tokens or keys leak into URLs.
  - The request ID is random and not derived from the token, so it can't reveal or correlate to one.
- **DEBUG:** All three headers that carry the named credentials are redacted:
  - Authorization holds the bearer token.
  - Cookie holds session cookies.
  - X-Api-Key holds API keys.
- **Passwords:** These would only appear in bodies, which are never logged.

So the plan works and meets its own rule. The weak point is the DEBUG redaction, which is a denylist. It is safe only while every credential-carrying header is on the list.

## Recommended changes

1. **Use an allowlist for DEBUG headers instead of a denylist.** Log values only for known-safe headers (Content-Type, User-Agent, Accept, X-Request-ID, and so on) and redact everything else. With the denylist, any credential in a header nobody listed goes straight to a cluster every engineer can search for 90 days. Examples:
   - Proxy-Authorization
   - X-Auth-Token
   - A vendor-specific key header
   - A client mistakenly putting its token somewhere else

   Right now the rule's safety depends on the list staying complete forever.
2. **If you keep the denylist, at least add Proxy-Authorization** and match header names case-insensitively. HTTP header names are case-insensitive, and an exact-case match on `Authorization` would miss `authorization`, which HTTP/2 always sends in lowercase.
3. **Clarify whether outbound upstream calls are logged.** The stated goal is tracing slow upstream calls. If the gateway logs headers on its own requests to upstream providers, those may carry the gateway's API keys or credentials under different header names. The same redaction or allowlist must apply there.
4. **Check paths for embedded secrets.** Confirm that no route puts a token, key or reset code in the path itself (e.g. `/callbacks/{secret}`, `/reset/{token}`). If any do, template the path (`/reset/:token`) before logging.
5. **Guard DEBUG in production.** Add a config check or alert so DEBUG can't be switched on in production unnoticed. If it must be enabled for an incident, make it time-limited. Consider sending DEBUG output to a restricted-access sink rather than the company-wide cluster.
6. **Minor:** DEBUG headers like X-Forwarded-For or User-Agent may hold personal data (IP addresses). They aren't credentials, but with company-wide 90-day access, ask privacy/compliance whether that's acceptable.

## Summary

The plan meets its stated rule today: INFO is clean, and DEBUG redacts the headers that carry the defined credentials. The DEBUG redaction is fragile, though. Switching to an allowlist, matching names case-insensitively, and covering outbound upstream headers would make the guarantee robust rather than dependent on a complete list.

VERDICT: GO_WITH_CHANGES