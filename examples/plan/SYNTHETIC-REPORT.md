# Synthetic example report — not a model result

Configuration: not applicable; this report was authored as documentation. No model was called, and no runtime behavior was verified.

| Source | Supplied SHA-256 | Coverage |
| --- | --- | --- |
| S01 | de68b0f7dfb253263790a3d1f854a802e8a3be3f500bdc55057e33df775651eb | COMPLETE |
| S02 | 865d3a24fd66254c7a9726acaebbcbb6d286a8d6f09e23fd5916d06f2edbe771 | COMPLETE |

Q01: ANSWERED. The proposal conflicts with the contract's required coverage check.

F01 — BLOCKER, contract mismatch, VERIFIED against these supplied snapshots. S01:2 says “Missing required source coverage makes the report INCOMPLETE.” S02:2 says “Do not check whether every supplied source was covered.” The proposal can accept an empty-findings report with unread required sources. Require complete source coverage before readiness.

Completeness: COMPLETE within this two-source example. Assessment: BLOCKERS_FOUND. No code defect, runtime execution, independent review or owner authorization is inferred.
