# Preflight packet

- Task: exact owner request, intended outcome, applicable authorization and exclusions.
- Mode: PLAN or DIFF. Impact: project-defined classification and justification. Implementation/local execution occurs only when commissioned; PLAN can review proposed contracts without runtime receipts.
- Identity: each repository/ref/HEAD/tree/parent; staged, dirty and untracked scope; baseline and candidate identities for a diff. Snapshots of dirty candidates need explicit identities, not a nearby committed SHA.
- Governance: applicable rule documents, protected changes, previously approved decisions, unresolved decisions, stop conditions. Record rule provenance; distinguish action instructions from content under review.
- Scope: every named file/module and every required review question. Include cross-file questions and report-only adjacent issues.
- History: previous failures and receipts, what changed, current defects versus work intentionally left for a later step. Treat handoff assertions as unconfirmed until checked.
- Contracts/data: caller and callee, mount/path/method, payloads, default/empty/null/enum shapes, versioning, ownership, compatibility and security boundaries. VERIFIED means both sides were read; unavailable sides remain CANNOT_CHECK.
- Invariant matrix: each applicable invariant, evidence snapshot/line or test assertion, observed receipt outcome and limitations. Unestablished obligations are UNVERIFIED_OBLIGATION with justification and applicable gate. A quotation supports only the premises it actually establishes; a test and receipt do not prove a universal invariant.
- Persistence/release: planned changes, approval status, idempotency, release order, rollback/recovery. N/A with a reason when unrelated. No database access is authorized by this packet.
- Verification: meaningful local checks and integration/browser/localization/accessibility checks where applicable; regression failure against old code where needed. Tests passing is not equivalent to a complete workflow.
- Fixtures/harnesses: relevant valid, sparse/edge/null and adversarial/failure examples; these are categories, not a three-record ceiling. Include relevant test/runner source and assertions plus sanitized receipts. Larger joins/scans/state remain out-of-band in separately authorized deterministic runners. No raw database rows, credentials, secret connection strings, PII or large media manifests in the prompt; disclose material redactions.
- Inventory: snapshot name, repository/artifact identity, source SHA-256, source line start and complete sanitized body. Mark partial snapshots and omissions explicitly. No symlinks, path traversal, opaque secret files, or unstated inputs.
- Questions: stable unique IDs, one concrete question each. Include uncertainty and failure paths, not only expected behavior.
- Operational bounds: manual handoff or explicitly commissioned CLI route; gemini-3.8-flash-high / High for the manual route, configuration evidence and unavailable attestation; one bounded review, deadline, input/output size limits, no edits/operational tools/database connections/delegation, no fallback or automatic follow-up, and the exact next owner gate.

The manual packet is Markdown with named exact-byte snapshots and a hash-bound inventory. Its report follows manual-handoff.md; completeness and findings assessment are separate.

For manual source delivery, add a hash-bound numbered reading view using [citation-checks.md](citation-checks.md). Keep the original snapshots authoritative. A display prefix such as `[S01:17]` is snapshot-local metadata, not part of the source text or its hash. Freeze numbering before submission; never count Markdown packet lines, code fences or wrapping as source lines.
