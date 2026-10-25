# Review: Refund Approval Authorization Plan

## Does the plan satisfy its own rule?

The rule is that only finance-admin members may approve refunds. The plan enforces this through a chain of guarantees:

1. The endpoint requires `refunds:approve`.
2. That scope is issued only to finance-admin members.
3. Tokens are revoked as soon as the holder leaves the group, and they expire after 15 minutes anyway.

If each link holds, every accepted caller is a current finance-admin member. So the plan works as written. But it rests entirely on the token layer, and the endpoint adds no protection of its own. That fragility is worth fixing.

## Concerns and recommended changes

**1. Revocation must actually be enforced at the endpoint (most important).**
The plan says tokens are "revoked as soon as the holder leaves the group." That only protects the endpoint if it checks revocation on every request, through introspection or a revocation list. Many systems validate self-contained tokens such as JWTs locally, checking only signature and expiry. In that setup, a revoked token keeps working for up to 15 minutes. A just-removed member could then approve refunds, which would break the stated rule. The plan should state that validation includes a live revocation check, or fall back to change #2.

**2. Add a direct group-membership check at the endpoint.**
"The endpoint performs no other authorization check" means one mistake in scope issuance silently breaks the rule. Examples include a misconfigured client, an admin granting the scope by hand, a service account, or a future change to the issuance logic. Checking finance-admin membership in the endpoint, against the identity provider or a short-TTL cache, costs little and turns a single point of failure into defense in depth.

**3. Bind tokens to their holder.**
A stolen or leaked bearer token lets a non-member approve refunds, at least in effect. Sender-constrained tokens (mTLS-bound or DPoP) would close this gap. At minimum, the plan should accept this risk explicitly. Fifteen minutes limits the exposure but does not remove it.

**4. Make issuance auditable and testable.**
The guarantee in step 2 lives in the authorization server, not in this plan's component. Name the single place where `refunds:approve` is granted. Add an automated test or periodic check confirming that no non-member holds or can obtain the scope.

**5. Strengthen the audit log.**
Alongside the caller's identity, record the token ID (`jti`), the issuing client, the refund ID and amount, and a timestamp. Consider also recording group membership at approval time. Write the log to append-only or tamper-evident storage, so it can support after-the-fact review if something above fails.

**6. Consider separation of duties (optional).**
The plan doesn't say whether a finance-admin can approve a refund they requested themselves. If that matters, the endpoint should enforce approver ≠ requester. Scope checks alone can't express that rule.

## Summary

The logic is sound if every stated premise holds. The weak point is that the endpoint trusts the token completely, and the revocation guarantee may not hold if tokens are validated locally. Enforce revocation at the endpoint, add a direct membership check, and harden token binding and the audit log.

VERDICT: GO_WITH_CHANGES