# Preflight decision record

Packet/report/configuration hashes and evidence root:
Candidate repository/HEAD/tree or dirty snapshot identity:
Route, configured model/effort, observed capabilities and unavailable attestation:
Runtime/transport status (where applicable; manual report receipt is not CLI admission):
Original unchanged report SHA-256; citation-ledger SHA-256 and extraction-completeness check:
Numbered-view and source-inventory identities; local citation-check result and first failure (remaining checks UNRUN on stop):
Codex-computed report completeness (COMPLETE / INCOMPLETE), required missing evidence and reasons:
Codex-computed advisory assessment (BLOCKERS_FOUND / CHANGES_RECOMMENDED / NO_BLOCKERS_FOUND); incomplete assessments apply only to inspected evidence:

| Finding | Independent check and citation | Disposition | Reason | Amendment and resulting identity |
| --- | --- | --- | --- | --- |

Record every original finding, including notes, rejected and unresolved findings. Check every factual premise against its evidence; quotation presence alone does not verify the claim. Findings must not disappear when the packet or candidate changes. Missing required context makes the report incomplete and prevents readiness; it is not automatically a code defect. Owner authority conflicts stay needs-owner until explicitly resolved. Remediation stays within current task authorization.

A matched citation ledger alone does not admit a report. Preserve mismatched citations without remapping or repairing the original return. Any separately authorized source assessment receives its own record and citations; it cannot retroactively validate the failed report.

Required verification completed:
Outstanding blockers/risks and their dispositions, plus UNVERIFIED_OBLIGATION items with justification and applicable gate:
Owner decisions already provided, with provenance:
Readiness recommendation: WITHHOLD_FROM_REVIEW / READY_FOR_REVIEW / NEEDS_OWNER_DECISION.
Independent reviewer: receives this record, the original findings, and the exact final candidate. Review rejects or unresolved claims independently; preflight does not satisfy formal review or release checks.
