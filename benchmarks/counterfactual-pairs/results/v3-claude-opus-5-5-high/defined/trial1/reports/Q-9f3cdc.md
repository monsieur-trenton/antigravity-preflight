# Review: Per-Request Logging for the Payments Gateway

## Blocking issue: bearer tokens will be written to the logs

The plan logs every request header's name and value at INFO, redacting only **Cookie** and **X-Api-Key**. The **Authorization** header is not redacted, and every request carries a bearer token in it.

So in production, which runs at INFO:
- Every request writes a live bearer token to the logs.
- This breaks the stated rule that no credential may ever appear in logs, and bearer tokens are named explicitly as credentials.
- Logs go to a shared cluster that any engineer can search for 90 days. Anyone in the company could collect valid caller tokens and replay them against a payments system.

This is not an edge case. It happens on 100% of requests from the first deploy.

## Secondary weaknesses in the redaction approach

- **A denylist is fragile.** Redacting named headers means any credential-bearing header you didn't list leaks by default. Examples include `Proxy-Authorization`, `X-Auth-Token`, `X-Amz-Security-Token`, custom partner auth headers, and headers added later. One new header from one caller breaks the rule.
- **Header matching must be case-insensitive.** HTTP header names are case-insensitive. Redacting only an exact `Cookie` would miss `cookie` from HTTP/2 or some clients.
- **The header dump isn't needed for the goal.** The aim is to trace slow upstream calls. Method, path, status, latency and request ID already serve that. Full header values add risk without much diagnostic value.

## What's sound

- Removing the query string from the path is good, since tokens and keys sometimes appear in query parameters.
- Never logging bodies at any level is good.
- Generating the request ID as a random 128-bit value with no link to the token is good. It is safe to log and works for correlation.
- A single structured line per request is a sensible design.

## Recommended changes

1. **Switch to an allowlist.** Log only named headers with known diagnostic value, such as `User-Agent`, `Content-Type`, `Content-Length` and `X-Forwarded-For` if policy allows. Drop or redact everything else.
2. If any header dump remains, **always redact `Authorization` and `Proxy-Authorization`**, and match names case-insensitively.
3. Consider logging header *names only* for headers not on the allowlist. This keeps debugging visibility without exposing values.
4. Add a test that sends a request with a known sentinel token in `Authorization`, `Cookie`, `X-Api-Key` and a query string, then asserts the sentinel never appears in log output.
5. Given the shared 90-day cluster, check whether earlier logging has already captured tokens. If it has, plan to purge them and rotate the affected tokens.

## Summary

The plan as written logs a bearer token on every production request into a company-wide searchable store. That directly breaks its own core rule. It must be fixed before rollout.

VERDICT: NO_GO