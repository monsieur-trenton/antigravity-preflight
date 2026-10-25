# Review: Refund Approval Authorization Plan

## Does the plan satisfy its own rule?

**Rule:** Only members of `finance-admin` may approve refunds.

The plan meets this rule through a chain of guarantees:

1. The endpoint requires the `refunds:approve` scope.
2. That scope is issued only to `finance-admin` members.
3. A token is revoked as soon as its holder leaves the group.

If all three hold, every accepted caller is a current `finance-admin` member. The plan works as written. However, the rule depends entirely on the token system, with no second check, so several weak points should be addressed.

## Issues and recommended changes

**1. The endpoint must actually enforce revocation.**
"Revoked as soon as the holder leaves" only helps if the endpoint checks revocation status on every call, through token introspection or a revocation list. If the endpoint validates self-contained tokens (e.g., JWT signature and expiry) locally, a revoked token keeps working until it expires. That gives up to a 15-minute window where a former member can still approve refunds, which breaks the rule. The plan should state the revocation check explicitly as an endpoint requirement.

**2. "Issued only to members" needs to cover every issuance path.**
Check that nothing else can mint or carry this scope:
- service accounts or client-credentials grants
- admin or impersonation tokens
- token exchange or delegation flows
- refresh tokens that re-mint the scope without rechecking group membership

Refresh is the most likely gap. Group membership should be re-evaluated at every issuance, not only at first login.

**3. Add defense in depth at the endpoint.**
"The endpoint performs no other authorization check" means one misconfiguration in the identity provider, such as a broad scope mapping or a policy edit, silently breaks the rule. Have the endpoint also verify current `finance-admin` membership, either from a fresh groups claim or a directory lookup. This is cheap and protects a sensitive financial action.

**4. Strengthen the audit log.**
- Record the token ID, the scope, and the group membership at approval time.
- Make the log append-only or tamper-evident.
- Alert on approvals where the caller was not in `finance-admin` at that moment. This turns the audit trail into a detection control.

**5. Consider separation of duties (optional, outside the stated rule).**
Nothing stops a `finance-admin` member from approving a refund they requested or that benefits them. If that matters, add a check that the approver differs from the requester.

**6. Limit the damage from stolen tokens.**
Fifteen minutes is reasonable, but a stolen bearer token is fully usable during that time. For this endpoint, consider sender-constrained tokens (mTLS or DPoP) or step-up authentication.

## Summary

The logic holds if its premises hold, so the plan does not fail as written. But it rests on a single control. The most important fix is making the endpoint's revocation check explicit, because without it the "revoked immediately" guarantee is not real at the point of enforcement. Adding a direct group-membership check would remove the single point of failure.

VERDICT: GO_WITH_CHANGES