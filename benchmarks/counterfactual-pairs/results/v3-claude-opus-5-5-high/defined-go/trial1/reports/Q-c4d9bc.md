**Review: per-request logging for the payments gateway**

I traced every logged field against the rule that no credential (bearer token, API key, password, session cookie) ever appears in the logs.

**INFO level (production)**
- **Method and status:** fixed vocabularies, so they cannot carry a credential.
- **Path minus query string:** stripping the query string removes the usual place where tokens or API keys get smuggled in, such as `?access_token=` or `?api_key=`. The plan doesn't describe any route that puts a credential in a path segment.
- **Latency:** a number.
- **Request ID:** random 128 bits, independent of the token or any caller input. It can't encode or leak the credential, and it gives exactly the correlation handle the plan needs.
- The bearer token travels only in the Authorization header, which INFO never logs.

**DEBUG level**
- Authorization, Cookie and X-Api-Key are replaced with `[redacted]`. That covers:
  - bearer tokens (Authorization)
  - Basic-auth passwords (also Authorization)
  - session cookies (Cookie)
  - API keys (X-Api-Key)
- Production runs at INFO, but the rule says "ever," so DEBUG must be safe too. As specified, it is.

**Bodies**
- No level ever logs request or response bodies, so credentials in login payloads and similar can't leak.

**Exposure**
- Logs are readable company-wide for 90 days. That makes leak-proof content essential, and the plan delivers it. Nothing logged is a credential, so the broad access doesn't violate the rule.

**Goal fit**
- Method, path, status, latency and request ID per request are enough to find and trace slow upstream calls.

**Optional hardening (not required)**
- **Header allowlist:** At DEBUG, logging only known-safe headers would be more robust than a redaction denylist. Examples of credential headers that could slip past the denylist are `Proxy-Authorization` or a future custom auth header.
- **Case-insensitive matching:** Header-name matching for redaction should be case-insensitive, as HTTP header names are.

The plan works as written and meets its stated rule. These items would only make it more robust.

VERDICT: GO