# Review: Per-Request Logging for the Payments Gateway

## Blocking issue: bearer tokens will be written to the logs

The plan logs every request header's name and value at INFO. It redacts only **Cookie** and **X-Api-Key**.

- Every request carries a bearer token in its **Authorization** header.
- Authorization is not on the redaction list, so its value (`Bearer <token>`) is logged in plain text.
- Production runs at INFO, so this happens on every request in production.
- The stated rule is that no credential ever appears in the logs, and bearer tokens are listed as credentials.

The impact is wider than a rule violation. These logs go to a shared cluster that any engineer in the company can search for 90 days. Every caller's live token would be exposed to a large audience for a long time. That is a credential leak, not a hygiene problem.

The plan therefore breaks a rule it states. A short redaction allowlist means the line meant to catch slow upstream calls also captures caller credentials.

## Required changes

1. **Redact Authorization.** At minimum, add it to the redaction list. Consider also redacting `Proxy-Authorization` and any custom auth or session headers the gateway accepts. Passwords and session cookies are credentials too, and could arrive in headers other than Cookie.
2. **Switch from a denylist to an allowlist.** Log only headers known to be safe and useful, such as `User-Agent`, `Content-Type`, `Content-Length`, `X-Forwarded-For` and trace headers. Redact or drop everything else. A denylist fails open whenever a new credential-bearing header shows up. An allowlist fails closed.
3. **Consider whether headers are needed at all.** The stated goal is tracing slow upstream calls. The one-line summary already gives you method, path, status, latency and request ID, which covers that goal. You may not need header logging at INFO.

## What is already sound

- **Query strings are stripped from paths.** This avoids leaking tokens or keys passed as query parameters.
- **Bodies are never logged at any level.** This rules out credentials in payloads.
- **Request IDs are random 128-bit values** unrelated to the token or other caller input. They can't be used to recover or correlate credentials, so they are safe to log and to search on.

## Optional suggestions

- Add a test or log-scrubbing check that fails CI if anything resembling `Bearer ` or a known key prefix appears in the log output.
- Since tokens may already have been logged in other environments, check whether any existing log data needs purging and whether tokens need rotating.

VERDICT: NO_GO