## Review

**The plan breaks its own core rule.** The rule says only **finance-admin** members may approve refunds. Here is how the remaining statements interact with it:

1. `approve_refund` authorizes any caller whose token has `refunds:approve`.
2. That scope is issued to **finance-admin and support-lead** members.
3. The endpoint does no other authorization check.

So a support-lead member who is not in finance-admin gets a valid token, calls the endpoint, and the approval succeeds. This is a direct violation, not an edge case. It follows from the plan's normal operation.

**The other controls don't fix this:**
- **15-minute expiry and revocation on leaving the group:** These limit how long a token stays valid. They don't change who receives one. A support-lead keeps the token legitimately for as long as they stay in support-lead.
- **Audit logging:** This records the violation after it happens but does not prevent it. It also shows the system treats these approvals as normal behavior.

**Ways to fix it (pick one):**
- **Stop issuing `refunds:approve` to support-lead.** If support-leads need refund-related access, give them a separate scope, such as `refunds:request` or `refunds:read`.
- **Or add a second check at the endpoint** that the caller is currently in finance-admin, for example from a group claim or a directory lookup. Then the scope alone is not enough. This also protects against future scope issuance mistakes.
- Ideally do both, since a single scope check makes the endpoint depend entirely on the token issuer being configured correctly.

**Smaller points to fix while revising:**
- **Revocation timing:** "Revoked as soon as the holder leaves the group" only works if the endpoint checks revocation status. If it only validates the token signature and expiry, a removed user keeps access for up to 15 minutes. State which behavior applies.
- **Overlapping memberships:** Say how a token is handled when the user is in both groups and leaves only one. Revocation should depend on whether the user is still in finance-admin.
- **Audit log contents:** Record the group or authorization basis for each approval, not just the caller's identity, so violations can be found.

VERDICT: NO_GO