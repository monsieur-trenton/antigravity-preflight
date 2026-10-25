## Review

**The plan violates its own core rule.** The rule says only finance-admin members may approve refunds, but the controls allow support-lead members to do it too:

1. `approve_refund` authorizes any caller whose token has `refunds:approve`.
2. Support-lead members are issued tokens with `refunds:approve`.
3. The endpoint does no other authorization check.

So a support-lead who is not in finance-admin can call `approve_refund` and succeed. This is not an edge case. It is how the system is designed to behave for an entire group.

**The other controls don't close the gap:**

- **15-minute expiry and revocation on leaving the group** limit how long a token stays valid. But revocation is tied to "the group that justified the scope," and for a support-lead that group is support-lead. Their token stays valid for as long as they remain a support-lead.
- **Audit logging** records unauthorized approvals after they happen. It doesn't stop them, so the rule is still broken.

**Required changes (any one of these fixes the violation):**

- **Stop issuing `refunds:approve` to support-lead.** If support-leads need some refund capability, give them a separate scope, such as `refunds:request` or `refunds:read`.
- **Add a group check to the endpoint.** Have `approve_refund` also verify current finance-admin membership, through a group claim in the token or a live directory lookup. Defense in depth means doing this even after fixing the scope issuance.
- If support-leads are *meant* to approve refunds, **change the rule instead**, and get explicit sign-off from whoever owns that policy.

**Secondary suggestions, once the above is fixed:**

- Make sure the audit log is tamper-resistant, and record the scope and group basis along with the identity.
- Consider alerting on approvals by anyone outside finance-admin, as a check that catches misconfiguration.

VERDICT: NO_GO