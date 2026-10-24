# Review: per-request logging for the payments gateway

## What the plan gets right

- **The INFO line contains no credentials.** It logs method, path without the query string, status, latency and request ID. Stripping the query string closes the common leak where API keys or tokens are passed as `?api_key=...`.
- **The request ID is safe.** It is a random 128-bit value from the gateway, not derived from the token, so it cannot be used to recover or correlate credentials.
- **Bodies are never logged.** This removes the main path for passwords and card data to reach the logs.
- **DEBUG covers the known credential headers.** Bearer tokens and Basic-auth passwords travel in `Authorization`, session cookies in `Cookie`, and API keys in `X-Api-Key`. All three are redacted.
- **Production runs at INFO**, so the full header dump is not normally emitted there.

As written, I don't see a path where the defined credentials reach the logs. The plan meets its own rule.

## Recommended changes

1. **Switch DEBUG header logging from a denylist to an allowlist.** Any header not on the three-item list is logged verbatim. That includes `Proxy-Authorization`, `X-Auth-Token`, `X-Amz-Security-Token`, and any header a future client or partner adds. These lines go to a cluster every engineer can search for 90 days. Logging values only for known-safe headers (`Content-Type`, `User-Agent`, `Accept`, etc.) and names only for the rest fails safe. If you keep the denylist, add at least `Proxy-Authorization` and match header names case-insensitively.

2. **Guard against DEBUG in production.** One mistaken config change would emit every header to the shared cluster. Options include:
   - an alert when production runs at DEBUG,
   - automatic expiry back to INFO,
   - routing DEBUG output to a restricted index with shorter retention.

3. **Confirm no credentials appear in path segments.** Something like `/v1/callbacks/{secret}` or a reset or confirmation token in the path would be logged at INFO. If any route works this way, template or mask it, for example by logging the route pattern instead of the raw path.

4. **Cover outbound logging if it is added.** The stated goal is tracing slow *upstream* calls. If you later log headers on outbound requests, the gateway's own upstream API keys and tokens must get the same treatment.

5. **Add upstream timing to the INFO line.** Total request latency alone won't tell you whether time was spent upstream or in the gateway. An upstream latency field, and an upstream target if several exist, would serve the tracing goal directly at INFO without needing DEBUG.

## Summary

The plan works and doesn't break its credential rule. The denylist redaction and the company-wide log visibility make it fragile, and the INFO line could serve the tracing goal better.

VERDICT: GO_WITH_CHANGES