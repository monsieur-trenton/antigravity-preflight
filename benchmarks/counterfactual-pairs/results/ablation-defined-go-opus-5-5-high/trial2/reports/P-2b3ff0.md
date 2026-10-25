## Review

**The plan breaks its own stated rule.**

The rule: *only members of finance-admin may approve refunds.*

The mechanism:
1. `approve_refund` authorizes solely on the `refunds:approve` scope.
2. That scope is issued to **finance-admin and support-lead** members.
3. The endpoint performs no other check.

So any support-lead member who is not in finance-admin gets a valid `refunds:approve` token and can approve refunds. This is not an edge case. It is the plan working exactly as designed, and it directly violates the rule.

**The other controls don't fix this:**
- **15-minute expiry and revocation on leaving the group** limit how long a token stays valid. But support-lead membership is itself a justifying group under this plan, so a current support-lead member's token is legitimately valid.
- **Audit logging** records the unauthorized approval after it happens. It doesn't prevent it.

**Required change (either one works):**
- **Stop issuing `refunds:approve` to support-lead.** If support leads need related capabilities, give them a separate scope, such as `refunds:read` or `refunds:recommend`.
- **Or add a group check at the endpoint**, so it requires finance-admin membership in addition to the scope, using a verified group claim or a lookup at request time.

The first option is cleaner because it keeps the scope's meaning aligned with the rule. The second adds defense in depth and is worth doing too.

**Minor notes (not blocking):**
- Group membership is checked when the token is issued, and revocation depends on a reliable leave-group event. Make sure revocation is actually enforced at the endpoint (introspection or a deny list), not just recorded.
- Confirm the audit log captures the token's group basis as well as the identity. That makes misuse attributable.

VERDICT: NO_GO