# Review: Per-Request Logging for the Payments Gateway

## Blocking issue: bearer tokens will be logged in production

The plan logs every request header's name and value at INFO, and redacts only `Cookie` and `X-Api-Key`. The `Authorization` header is not on that list.

The plan itself states that:
- every request carries a bearer token in `Authorization`,
- bearer tokens count as credentials,
- the production log level is INFO.

So every production request writes a live bearer token into the logs. That breaks the service's rule that no credential ever appears in its logs. The impact is serious because the shared logging cluster is searchable by any engineer in the company for 90 days. Anyone could pull valid caller tokens and replay them against the payments gateway.

## Required changes

1. **Redact `Authorization`.** Add `Proxy-Authorization` too, since it carries credentials the same way.
2. **Switch from a denylist to an allowlist.** Log only the headers you actually need for tracing slow upstream calls, such as `User-Agent`, `Content-Type`, `Content-Length` and any trace/correlation headers. Redact or drop everything else. A denylist fails silently whenever a caller or client library adds a new credential-bearing header, such as a custom `X-Auth-Token` or `X-Session`. That failure would also break the rule.
3. **Match header names case-insensitively.** HTTP header names are case-insensitive, so `authorization` or `x-api-key` from some clients must be caught. The plan doesn't specify this.

## Parts that are sound

- Logging the path without its query string avoids leaking credentials or PII passed as query parameters.
- Never logging request or response bodies at any level is correct for a payments service.
- Request IDs are random 128-bit values with no link to the token or caller input, so they are safe to log and useful for correlation.
- Method, status, latency and request ID on one line give you what you need to trace slow upstream calls.

## Optional suggestions

- Add a test that sends requests with `Authorization`, `Cookie` and `X-Api-Key` headers and asserts that none of their values appear in the log output.
- Consider whether the full header dump needs to be at INFO at all. Logging only the summary line at INFO, plus a few allowlisted headers, keeps volume down and reduces exposure.

Because the plan as written logs bearer tokens at the production log level, it breaks a rule it states.

VERDICT: NO_GO