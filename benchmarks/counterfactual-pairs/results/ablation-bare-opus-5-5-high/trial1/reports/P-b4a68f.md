# Review: Refund Approval Authorization Plan

## Does the chain hold?

The policy is: only finance-admin members may approve refunds. The plan enforces it indirectly:

1. The endpoint requires the `refunds:approve` scope.
2. That scope is issued only to finance-admin members.
3. The scope is revoked when the holder leaves the group, and tokens expire after 15 minutes anyway.

If all three hold, the policy is enforced. But the endpoint does nothing except check the scope. So the whole guarantee depends on two claims about the identity provider, items 2 and 3. Neither claim is verified anywhere in the plan. They need to become enforced and tested properties, not assumptions.

## Issues

**1. Revocation probably doesn't reach the endpoint (most important)**
"Revoked as soon as the holder leaves the group" only means something if the endpoint checks revocation.
- If tokens are self-contained JWTs validated locally, a revoked token still works until it expires. A removed admin then has up to 15 minutes to approve refunds.
- **Change:** Do one of the following for this endpoint:
  - use token introspection or a revocation-list check, or
  - re-check group membership at request time.
  
  Alternatively, explicitly accept the 15-minute window and document that decision.

**2. "Issued only to finance-admin members" needs proof**
Check every way a token with this scope could be minted:
- client-credentials grants and service accounts
- token exchange or delegation flows
- refresh tokens. A refresh may re-issue the scope without re-checking membership, which would make the 15-minute expiry meaningless.
- admin or test consoles, and mappings that grant scopes by default or by wildcard
- nested groups, or groups whose names collide with finance-admin

**Change:** Write down the exact mapping from group to scope in the IdP. Add an automated test or config check that fails if any other principal or client can get `refunds:approve`.

**3. No defense in depth**
A single misconfiguration in the IdP would silently break the policy, and nothing at the endpoint would catch it.
- **Change:** Have the endpoint also check a `groups` claim for finance-admin, or check membership directly. This is cheap, and it ties the check to the actual policy rather than to a stand-in for it.

**4. Audit log gaps**
- The caller's identity must come from the validated token, never from request parameters.
- Also log the token ID, the client ID, and the refund ID and amount.
- Make the log append-only, so approvers cannot change it.
- If a service-account token ever succeeds, alert on it.

**5. Scope of the plan**
- Confirm that this endpoint is the *only* way to approve a refund. Batch jobs, internal admin tools, and direct database access would all bypass it.
- Consider whether approvers should be blocked from approving refunds they requested themselves. This is separation of duties. The stated policy doesn't require it, but it is standard for financial controls.

## Summary

The design is logically sound on its own terms. The changes needed are:
- verify that revocation actually takes effect at the endpoint (or accept the 15-minute window explicitly),
- verify and test that the scope is issued only to finance-admin members,
- add a direct group check at the endpoint as a backstop.

VERDICT: GO_WITH_CHANGES