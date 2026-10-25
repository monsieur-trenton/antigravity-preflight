# Review: Refund Approval Authorization Plan

**The rule:** Only members of `finance-admin` may approve refunds.

The plan meets this rule through a chain of claims:

1. **The endpoint gate.** `approve_refund` accepts a caller only if their token carries `refunds:approve`.
2. **The issuance gate.** That scope is issued only to `finance-admin` members.
3. **Expiry and revocation.** Tokens expire after 15 minutes and are revoked as soon as the holder leaves the group. A valid token therefore always belongs to a current member, not just someone who was a member when the token was issued.

Taken together, these mean every caller the endpoint accepts is a current `finance-admin` member. Having no other check at the endpoint is fine, because the scope already stands in for group membership. The audit log does not enforce the rule, but it makes approvals traceable to a person.

I found no gap in the plan as written. Each step follows from what the plan states.

## Optional hardening (not required)

- **Check revocation at the endpoint.** If tokens are self-contained (such as JWTs) and checked only locally, a revoked token could still work until it expires, up to 15 minutes. Introspecting the token, or checking a revocation list, makes "revoked as soon as" true in practice.
- **Bind tokens to their holder.** Bearer tokens can be stolen or replayed. Sender-constrained tokens (DPoP or mTLS) prevent a non-member from using a leaked token.
- **Keep the scope out of delegated tokens.** Make sure token exchange, impersonation, or service-account flows cannot mint `refunds:approve` for someone outside the group.
- **Log the token identifier.** Recording the token ID and issuance time with each approval makes later investigation easier.

These items make a working plan more robust. They are not changes the plan needs.

VERDICT: GO