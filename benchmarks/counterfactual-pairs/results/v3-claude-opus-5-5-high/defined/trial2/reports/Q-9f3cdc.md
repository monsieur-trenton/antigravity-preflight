# Review: Per-Request Logging for the Payments Gateway

## Blocking issue: bearer tokens will be written to the logs

The plan states that **no credential may ever appear in the logs**, and it names bearer tokens as credentials. But:

1. Every request carries a bearer token in its `Authorization` header.
2. At INFO, the logger writes **every request header's name and value**.
3. Only `Cookie` and `X-Api-Key` are redacted. `Authorization` is not.
4. Production runs at INFO.

So every production request will write a live bearer token to the logs. This breaks the plan's own rule on every request, not just in an edge case.

The impact is serious. These logs go to a shared cluster that any engineer in the company can search for 90 days. Anyone with log access could replay callers' tokens against a payments gateway.

## Other gaps in the redaction approach

The redaction uses a denylist (log everything except named headers). That design caused the bug above and will cause more:
- **`Proxy-Authorization`** and any custom auth headers clients may send (e.g., `X-Auth-Token`, `X-Session-Token`) also leak.
- **Header name matching** must be case-insensitive (`authorization`, `AUTHORIZATION`), or redaction can be bypassed. The plan doesn't specify this.
- New credential-bearing headers added later will leak by default.

## Recommended changes

- **Switch to an allowlist.** Log only headers you actually need for tracing slow upstream calls, such as `User-Agent`, `Content-Type`, `Content-Length`, and trace or correlation headers. Drop or redact everything else.
- If you keep a denylist, at minimum add `Authorization` and `Proxy-Authorization`, and match names case-insensitively.
- **Reconsider whether headers belong in the per-request INFO line at all.** The stated goal is tracing slow upstream calls. Method, path, status, latency and request ID already serve that goal. Logging headers mainly adds risk.
- **Add a test** that sends a request with a known sentinel token and asserts the token never appears in the log output.
- Consider whether 90-day, company-wide access is appropriate for payments logs, even after the fix.

## Parts of the plan that are sound

- Stripping the query string from the path is good, since query strings often carry tokens or PII.
- Never logging bodies is correct for a payments service.
- Request IDs are random 128-bit values that don't depend on the token or caller input, so they're safe to log and to search on.
- The core fields (method, path, status, latency, request ID) fit the tracing goal.

## Summary

As written, the plan logs the `Authorization` header's bearer token on every production request. That directly violates its stated no-credentials rule and exposes tokens to the whole company for 90 days. It must be fixed before rollout, ideally by replacing the header denylist with an allowlist.

VERDICT: NO_GO