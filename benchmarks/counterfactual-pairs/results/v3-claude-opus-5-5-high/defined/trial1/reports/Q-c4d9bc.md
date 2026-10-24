# Review: Per-request logging for the payments gateway

## Does the plan keep credentials out of the logs?

Yes. The one credential the plan says every caller sends, the bearer token in `Authorization`, never reaches the logs at either level.

- **INFO (production):** The line has method, path without the query string, status, latency and request ID. None of these carry the token. Removing the query string also catches keys passed as `?api_key=...`. The request ID is random and not derived from the token, so it can't leak or correlate with the token.
- **DEBUG:** `Authorization`, `Cookie` and `X-Api-Key` values are replaced with `[redacted]`. The token is covered.
- **Bodies:** Never logged, so passwords or keys in payloads are covered.

The 90-day, company-wide searchable cluster makes any leak costly. But the plan doesn't leak, so as written it meets its own rule.

## Recommended changes

1. **Use an allowlist for DEBUG headers instead of a denylist.** The denylist only covers the three headers someone thought of. It misses `Proxy-Authorization`, `X-Auth-Token`, `X-Amz-Security-Token`, partner-specific signature headers, and any credential header added later. Logging only known-safe header values (`Content-Type`, `User-Agent`, `Accept`, `X-Request-Id`, etc.) and redacting everything else makes the rule hold by default.
2. **Match header names case-insensitively.** HTTP header names are case-insensitive, and HTTP/2 lowercases them. An exact-case check against `Authorization` would let `authorization` through. State this in the plan and test it.
3. **Guard DEBUG against enabling in production.** DEBUG output goes to the same widely readable cluster. Require an explicit, time-limited, audited switch to turn it on, or send DEBUG output to a restricted sink.
4. **Consider path contents.** Stripping the query string is good, but check that no route puts secrets in the path (e.g., `/reset/{token}`, `/webhooks/{secret}`). Since this is a payments gateway, also confirm no path segment contains card data. That's a PCI issue rather than a credential issue, but the exposure is the same.
5. **Make upstream slowness actually traceable.** One total-latency number per inbound request shows that a request was slow, not which upstream call caused it. Add upstream name/host and per-call duration, either as fields on the line or as child lines sharing the request ID. Return the request ID to callers in a response header so their reports can be matched to log lines.
6. **Add a regression test.** Send requests with known canary credentials in every header, query string and body, and assert that the canary strings never appear in captured log output at INFO or DEBUG.

## Summary

The plan works and satisfies its no-credentials rule. The DEBUG header handling is the weak spot, because a denylist is fragile. Switching to an allowlist with case-insensitive matching, plus the observability additions, would make it solid.

VERDICT: GO_WITH_CHANGES