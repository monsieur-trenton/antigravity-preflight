# Review: Refund Approval Authorization Plan

## Does the plan meet the requirement?

**Yes, if its premises hold.** The reasoning is:

1. The endpoint admits only tokens with `refunds:approve`.
2. Only finance-admin members receive that scope.
3. Therefore only finance-admin members can approve.

The deduction is valid. But the whole control depends on step 2, and the endpoint does no check of its own. The plan states premises 2 and 5 as facts without saying how they are enforced or verified. Those are the gaps.

## Concerns

**1. Revocation may not take effect at the endpoint (most important).**
"Revoked as soon as the holder leaves the group" only matters if the endpoint checks revocation. If it validates self-contained tokens (e.g., JWTs) locally by signature and expiry, a revoked token keeps working until it expires. A departing member then keeps approval power for up to 15 minutes.
- *Change:* State how the endpoint validates tokens. Either use introspection or a revocation-list check on every call, or explicitly accept the 15-minute window as a known risk.

**2. The token issuer is a single point of failure.**
"Issued only to members of finance-admin" has to hold on every issuance path, not just the interactive login. Paths to check:
- client-credentials or service-account grants
- token exchange or delegation flows
- refresh tokens (is membership re-checked on refresh?)
- admin-editable scope-to-role mappings
- dev or test issuers trusted by the same endpoint

A misconfiguration on any of these silently breaks the policy.
- *Change:* List every issuance path and confirm each one enforces the group check. Treat changes to the scope mapping as privileged and audited.

**3. There is no defense in depth.**
Because the endpoint does nothing beyond the scope check, any issuer bug becomes a policy violation.
- *Change (recommended):* Have the endpoint also verify group membership, from a token claim or a directory lookup. Alternatively, record why you rely on the scope alone.

**4. Standard token validation is not mentioned.**
The plan doesn't say whether the endpoint checks issuer, audience, signature algorithm, and expiry. A token minted for another service, or by another trusted issuer, could carry the same scope string.
- *Change:* Require strict `iss` and `aud` validation and an allow-list of signing algorithms.

**5. Separation of duties is not addressed.**
Nothing stops a finance-admin from approving a refund they requested or that benefits them. This is outside the stated requirement, but it is a common audit finding for refund flows.

**6. The audit log needs integrity guarantees.**
- It should be append-only or tamper-evident.
- It should record the token ID (`jti`), the client ID, and the subject.
- It should not be writable by finance-admin members.
- Decide whether an approval fails if the audit write fails. It should fail closed.

## Summary

The design is sound and meets the requirement as written. However, it rests on two unverified premises: issuance being restricted on every path, and revocation actually being enforced at the endpoint. Confirm or fix those two before shipping. Adding a direct group check at the endpoint is strongly advised.

VERDICT: GO_WITH_CHANGES