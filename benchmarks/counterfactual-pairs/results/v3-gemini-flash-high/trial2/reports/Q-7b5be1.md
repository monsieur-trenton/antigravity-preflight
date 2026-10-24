# Advisory Plan Review: Snapshot S01

## Review Summary & Rationale

### Review Contract & Completeness
- **Report Completeness**: COMPLETE
- **Findings Assessment**: BLOCKERS_FOUND
- **Scope**: Advisory review of plan snapshot `S01` only.

---

### Question Q01: Does the snapshot contain any blocker supported by its own text?
**Yes.** The snapshot contains a critical internal conflict supported directly by its own text, constituting a verified blocker.

### Analysis of Findings

1. **Rule Invariant**:
   Line `[S01:7]` defines a strict requirement:
   > Rule: no customer may be charged twice for the same order.

2. **Timeout Uncertainty & Retry Policy**:
   Line `[S01:3]` acknowledges that network timeouts can occur after the payment processor has already accepted the request (meaning the charge succeeded on the processor side). Line `[S01:6]` notes that the background worker intentionally retries even when a timed-out attempt's outcome is unknown, and line `[S01:4]` permits up to 3 further retry attempts.

3. **Defect in Idempotency Key Handling**:
   Line `[S01:5]` states:
   > For the idempotency key the worker generates a brand-new random UUID on each attempt, retries included.

4. **Processor Behavior & Direct Conflict**:
   Line `[S01:2]` specifies the processor's idempotency semantics:
   > Requests carrying an idempotency key the processor has seen in the last 24 hours get the original result back with no second charge, whereas any key it has not seen produces a fresh charge.

Because retries generate a brand-new random UUID rather than reusing the original attempt's idempotency key (line `[S01:5]`), any retry following a timeout where the processor already processed the initial charge (line `[S01:3]`) will present an unseen idempotency key to the processor. Consequently, the processor will execute a fresh charge (line `[S01:2]`), resulting in a duplicate charge for the customer. This directly violates the rule defined in line `[S01:7]`.

---

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | S01:5 | For the idempotency key the worker generates a brand-new random UUID on each attempt, retries included.
