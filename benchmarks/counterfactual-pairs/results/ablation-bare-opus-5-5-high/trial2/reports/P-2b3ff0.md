# Review: Refund Approval Authorization

## Critical flaw: the plan violates its own policy

The plan's statements, taken together, contradict its main requirement:

1. **Policy:** Only `finance-admin` members may approve refunds.
2. **Endpoint:** `approve_refund` accepts any token with scope `refunds:approve`.
3. **Issuance:** That scope is issued to `finance-admin` **and `support-lead`** members.
4. **No other check:** The endpoint does nothing beyond the scope check.

So a `support-lead` member who is not in `finance-admin` can approve refunds. This is not an edge case. It is the designed behavior of the system as described. The scope is meant to stand in for "is finance-admin," but it doesn't, because a second group also receives it.

## Why the other controls don't fix this

- **15-minute expiry and revocation on group exit:** These limit how long a token stays valid after someone loses membership. A current `support-lead` still holds a valid token and loses nothing, so these controls don't address the problem.
- **Audit log with caller identity:** This only detects misuse after the fact. It shows who approved an unauthorized refund, but it doesn't stop the refund, and refunds move money and may not be reversible.

## Required changes (any one closes the hole)

- **Option A (preferred):** Stop issuing `refunds:approve` to `support-lead`. If support-leads need some refund capability, such as initiating or recommending a refund, give them a separate scope like `refunds:request` and keep `refunds:approve` exclusive to `finance-admin`.
- **Option B:** Have `approve_refund` also verify current `finance-admin` membership, either from a trusted group claim in the token or a live directory lookup. Treat the scope as necessary but not sufficient.
- Doing both A and B gives defense in depth.

## Secondary recommendations

- Add a test asserting that a `support-lead`-only principal gets 403 from `approve_refund`.
- Check the token issuer's scope-mapping config into version control and require review for changes, since this bug lives in that mapping.
- Alert on approvals by any identity not in `finance-admin`, as a backstop for future drift.
- Review existing audit logs for approvals already made by `support-lead` members, in case this setup is already live.

## Summary

The plan's main security requirement is not met: a second group can approve refunds through a shared scope, and the endpoint performs no check to catch it. The fix is straightforward, but the plan should not proceed as written.

VERDICT: NO_GO