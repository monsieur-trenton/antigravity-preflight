# Review: Per-Request Logging for the Payments Gateway

The plan holds up against its own rule that no credential ever appears in the logs. I checked each logged field against the definition of credentials (bearer tokens, API keys, passwords, session cookies).

## INFO level (production)

- **Method, status, latency:** none of these can carry a credential.
- **Path without query string:** removing the query string closes the most common leak, which is keys or tokens passed as `?api_key=` or `?token=`. Nothing in the plan suggests credentials appear in path segments.
- **Request ID:** it is random and 128 bits, with no link to the token or any caller input. It can't encode or leak a credential, and it can't be used to correlate back to one.
- **Bodies:** never logged, so passwords or keys in payloads can't leak.

Production runs at INFO, so the company-wide, 90-day searchable cluster only ever gets these fields. That wide audience is the reason the rule matters, and INFO meets it.

## DEBUG level

The only credential the plan says callers send is the bearer token in `Authorization`, and that value is redacted. `Cookie` (session cookies) and `X-Api-Key` (API keys) are also redacted. Bodies stay excluded. Nothing stated in the plan would put a credential into a DEBUG line either.

## Optional hardening (not required changes)

- **Match header names case-insensitively.** HTTP/2 sends header names in lowercase (`authorization`). Exact-case matching would miss them. The plan's wording implies the header itself rather than a particular spelling, but the implementation and tests should confirm this.
- **Consider an allowlist for DEBUG headers.** Logging only known-safe headers, or adding `Proxy-Authorization` and any custom auth headers to the redaction list, would guard against future integrations that send credentials in headers the plan doesn't mention today.
- **Add a test that asserts no token appears in output.** Send a request with a known sentinel token at DEBUG and check that the token string never shows up in the output.

None of these fix a failure in the plan as written. They only make a working design more robust.

VERDICT: GO