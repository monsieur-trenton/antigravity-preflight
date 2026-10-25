# Review: Refund Approval Authorization Plan

## Critical issue: the plan violates its own policy

The stated rule is that **only finance-admin members may approve refunds**. The mechanics allow more than that:

1. `approve_refund` accepts any token with `refunds:approve`.
2. That scope is issued to **finance-admin and support-lead** members.
3. The endpoint does no other authorization check.

**Result:** any support-lead member who is not in finance-admin can approve refunds. This is a built-in privilege escalation, not an edge case.

The other controls don't close this gap:

- **15-minute expiry and revocation on leaving the group** limit stale or stolen credentials. But support-leads hold the scope legitimately, so their tokens are valid and won't be revoked.
- **Audit logging** is a detective control, not a preventive one. It shows *who* approved an unauthorized refund after the money has moved. It is still worth keeping.

## Required changes (pick one, preferably the first)

**A. Fix scope issuance.** Issue `refunds:approve` only to finance-admin. If support-lead needs some refund capability (viewing, initiating, recommending), give it a separate scope such as `refunds:request` or `refunds:read`. The scope name currently implies a permission the policy says support-lead must not have.

**B. Add a check at the endpoint.** Require both `refunds:approve` and current finance-admin membership, verified from a claim or a live directory lookup. This adds defense in depth even if you also do A.

Doing both is the strongest option. A fixes the root cause, and B guards against future scope-issuance mistakes.

## Secondary points to verify

- **Revocation "as soon as" the holder leaves the group:** confirm this is enforced in practice. For self-contained JWTs it requires introspection or a denylist. Otherwise the real window is up to 15 minutes, which may be acceptable but should be stated honestly.
- **Audit log integrity:** make the log append-only or tamper-evident. Record the token's group basis, the refund ID, the amount, and the result, not just the identity.
- **Find out why support-lead got this scope.** If a workflow depends on it, removing the scope will break that workflow. Plan a replacement scope or approval-request flow before rollout.
- **Retroactive check:** if this design is already live, review the audit log for approvals by support-lead members who weren't in finance-admin.
- Consider dual control or amount thresholds for large refunds, as a policy decision separate from this fix.

## Summary

The token lifecycle and audit controls are reasonable. The core authorization property, however, is broken as written: a non-authorized group can approve refunds. The plan should not proceed until scope issuance is corrected and/or the endpoint enforces finance-admin membership.

VERDICT: NO_GO