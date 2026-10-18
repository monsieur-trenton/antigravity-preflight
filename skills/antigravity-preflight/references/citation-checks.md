# Manual citation preparation and checking

Use this local utility to reduce coordinate mistakes in manual packets. It makes no provider calls and does not use or qualify the separately commissioned Antigravity CLI runtime or native observer. A passing quotation check is not report admission, proof of reading, or substantive verification.

## Prepare the numbered view

Freeze sanitized UTF-8 snapshots before hashing. Put this small inventory beside the snapshots; paths are relative to that inventory, must stay beneath its directory and cannot use symlinks. Use the same IDs and hashes in the packet's main inventory; this utility inventory is a projection, not a second source of truth.

```json
{"sources":[{"id":"S01","path":"snapshots/reader.js","sha256":"<64 lowercase hex characters>"}]}
```

```bash
python3 -B -I "$HOME/.codex/skills/antigravity-preflight/scripts/manual_citations.py" render inventory.json NUMBERED-SOURCES.txt
```

The output file must be new. Supply the numbered view together with the exact original snapshots and record the view's hash in the packet inventory. Each `[S01:17]` prefix identifies **snapshot-local line 17**; it is display metadata, excluded from source hashes and quotations. The utility hashes the original bytes before rendering. LF delimits lines; CRLF is one line ending; a terminal newline does not create another source line. Unicode separators inside a line do not renumber the snapshot. Excerpt-original coordinates belong in separate metadata.

Ask Gemini to copy each decisive single-line quotation directly from this view, excluding its prefix. If it cannot locate exact evidence at a coordinate, it must use `UNVERIFIED` or `CANNOT_CHECK` and explain the gap rather than guess a line. Report source hashes as supplied identities, not as reviewer-computed authentication. A numbered view cannot establish that the model read all supplied material.

## Check the unchanged return

Preserve and hash the original report before extraction. Codex extracts every explicit quotation and source coordinate from findings **and question answers**, assigning stable ledger IDs such as `F01-P1` and `Q01-P1`. Bind the extraction ledger to the original report hash in the task's decision record and manually check extraction completeness. Do not alter coordinates or quotes during extraction.

```json
{"citations":[{"id":"F01-P1","source":"S01","line":17,"quote":"exact non-empty text from that line"}]}
```

```bash
python3 -B -I "$HOME/.codex/skills/antigravity-preflight/scripts/manual_citations.py" check inventory.json CITATIONS.json
```

Exit 0 / `CITATIONS_MATCHED` means every supplied ledger quote occurs verbatim on its specified source line after source hashes authenticate. Whitespace, spelling and Unicode are not normalized. Exit 1 / `STOPPED` ends checks at the first failure; remaining checks are `UNRUN`. Failure output contains a classification, not source text, supplied quotations or host paths. An empty ledger is refused; if no quotation was required, record that justified N/A separately instead of treating an empty check as a pass.

The utility does not parse the Markdown report, prove extraction completeness, validate source/question coverage, or decide whether quotations support the finding. Those remain Codex checks under the manual handoff protocol. Retain the original report, inventory, numbered view, extraction ledger and result with task evidence. A mismatch withholds admission of the report; it does not prove the finding false. Never search for a better coordinate to repair the original report. A separately authorized source assessment must produce a separate record with new citations and preserve the failed return.

Commands above use the typical installed skill path; use your actual installation path for another skill directory. In a repository checkout use `skills/antigravity-preflight/scripts/manual_citations.py`. Matching permits any nonempty substring on the selected line, including a single character; context, extraction completeness and every premise require separate human or adjudicator assessment.
