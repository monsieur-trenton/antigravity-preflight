## Review

**The rule:** only members of `finance-admin` may approve refunds.

**What the plan actually allows:**

1. `approve_refund` accepts any caller whose token carries `refunds:approve`.
2. Tokens with `refunds:approve` are issued to members of **both** `finance-admin` and `support-lead`.
3. The endpoint does no other authorization check.

Together, these mean a `support-lead` member who is not in `finance-admin` can approve refunds. That breaks the rule the plan sets out to enforce. The problem is a direct consequence of the plan as written, not a rare edge case.

**Why the other controls don't fix it:**

- **15-minute expiry and revocation on group exit** only limit how long a *legitimately held* scope stays valid. A current `support-lead` member holds the scope legitimately under this plan, so neither control applies.
- **Audit logging with caller identity** records the violation after it happens. It doesn't prevent it.

**Required changes (any one of these fixes it):**

- **Stop issuing `refunds:approve` to `support-lead`.** If support leads need a related capability, such as requesting or recommending refunds, give it a separate scope like `refunds:request`.
- **Or add a group check at the endpoint.** `approve_refund` would verify that the caller is currently in `finance-admin`, in addition to checking the scope. Read membership from the token's group claim or from a live directory lookup, and make sure the claim can't be produced from `support-lead` membership.

The first option is cleaner because it keeps "scope = permission" true. The second adds defense in depth and is worth doing anyway.

**Minor notes (not blocking):**

- Make sure the audit log is append-only and tamper-evident, and that it records the group or scope basis the approval relied on. This makes it easy to spot misuse like the one above.
- Confirm that revocation on group exit is enforced at the token service (introspection or a revocation list), not only when the token is next refreshed.

VERDICT: NO_GO