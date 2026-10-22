# Review: Refund Approval Authorization Plan

The plan enforces its rule: only finance-admin members may approve refunds.

## How the rule holds

1. **Issuance:** A `refunds:approve` token goes only to finance-admin members.
2. **Enforcement:** The endpoint requires that scope, so no one else can call it.
3. **Leaving the group:** Tokens are revoked as soon as the holder leaves finance-admin. A former member can't keep using a token issued while they were in the group. Revocation, not the 15-minute expiry, is what closes this gap. The expiry is a backstop.
4. **Auditability:** Every approval records the caller's identity, so each one can be traced to a member.

Together, these mean every valid token with the scope belongs to a current member. A single scope check at the endpoint is therefore enough to enforce the rule. I found no path in the plan as written that lets a non-member approve a refund.

## Optional hardening (not required)

- **Defense in depth:** The endpoint could also check current group membership directly. That would protect against a misconfigured token issuer or a revocation failure, but the plan doesn't depend on it.
- **Revocation reliability:** Confirm that revocation actually reaches the endpoint, for example by checking a revocation list or validating tokens against the issuer. A delay there would bring back a short window that the plan assumes doesn't exist.
- **Stolen tokens:** Sender-constrained tokens (mTLS or DPoP) would stop a leaked token from being used by someone else. This is a general token-security improvement, not a gap in the stated design.
- **Audit integrity:** Make the audit log append-only or tamper-evident.

None of these are needed for the plan to meet its rule.

VERDICT: GO