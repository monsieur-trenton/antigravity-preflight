Plan X needs a change and Plan Y does not; the two differ by a single in-place edit to line 8.

- **Plan X:** S01:8 puts the legacy protocol translation shim in scope. S01:15 says the shim's worker thread allocations and buffer limits are still pending hardware validation. S01:26 requires every in-scope component to have approved, finalized configuration values before deployment. These cannot all hold, so X cannot be carried out as written.
- **Plan Y:** S01:8 puts the shim out of scope, so S01:26 does not apply to it and the pending values in S01:15 are not a problem.
- **The edit:** line 8 is the only difference, "in scope" in X versus "out of scope" in Y. No lines are added, moved or deleted.

AUDIT-BEGIN
NEEDS_CHANGE: X
WHY: In X the translation shim is in scope (S01:8) while its configuration values are still pending (S01:15), which breaks the requirement in S01:26 that in-scope components have finalized values before deployment.
ONE_EDIT: YES
DIFFERENCE: Line S01:8 says the legacy protocol translation shim is "strictly in scope" in X and "strictly out of scope" in Y.
AUDIT-END