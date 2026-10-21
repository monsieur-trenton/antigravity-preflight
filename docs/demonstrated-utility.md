# Demonstrated Utility: Four Failure Modes Prevented by Antigravity Preflight

`antigravity-preflight` provides deterministic quality and containment guarantees for AI-assisted code plan and diff reviews. Instead of treating large language model (LLM) outputs as authoritative decisions, the preflight architecture subjects all reviewer claims and streams to strict local verification.

This document outlines the four primary failure modes of LLM code reviews and demonstrates how `antigravity-preflight` deterministically stops them with zero live spend ($0.00) and zero provider calls.

---

## 1. Adversarial Citation Verification (Eliminating Hallucinated Quotes)

### The Failure Mode
LLMs frequently hallucinate code quotes when justifying review findings. Common distortions include:
- Substituting standard library identifiers (e.g., claiming `raise PermissionError()` instead of `raise PermissionDenied()`).
- Pointing to wrong line coordinates (off-by-one errors or line drift).
- Citing non-existent lines in a file.

### How Antigravity Preflight Stops It
The manual citations engine ([`manual_citations.py`](../skills/antigravity-preflight/scripts/manual_citations.py)) enforces exact byte and line coordinates against cryptographically pinned source files. If any character, word, or line number fails to match the staged snapshot verbatim, the citation check halts immediately:

```bash
python3 -B -I skills/antigravity-preflight/scripts/manual_citations.py check \
  examples/plan/inventory.json examples/plan/citations.json
```
- **Valid Verbatim Citation**:
  ```json
  {"status": "CITATIONS_MATCHED", "citations": 2, "scope": "SUPPLIED_LEDGER_ONLY_NOT_REVIEW_ADMISSION"}
  ```
- **Hallucinated or Shifted Citation**:
  ```json
  {"status": "STOPPED", "reason": "QUOTE_MISMATCH", "remainingChecks": "UNRUN"}
  ```

---

## 2. Tool Sandboxing & Unadmitted Execution Denial

### The Failure Mode
Untrusted code or prompt injections within review packets might attempt to trick the reviewer into executing operational tools (e.g., executing shell commands via `run_command`, writing arbitrary files, or delegating work to unvetted subagents).

### How Antigravity Preflight Stops It
The streaming reviewer harness ([`cli_review.py`](../runtime/argon-high/scripts/cli_review.py)) strictly parses incoming streaming events from the CLI process. Only passive review events (`user_input`, `agent_response`, and a terminal `finish` tool) are admitted. 

Any attempt to invoke operational tools or pass delegation payloads aborts the review stream immediately:
- **Operational Tool Attempt**: Rejected with `OPERATIONAL_TOOL`.
- **Subagent Delegation Attempt**: Rejected with `DELEGATION_PAYLOAD`.
- **Tool Error / Abnormal State**: Rejected with `STEP_STATE`.

---

## 3. Untrusted Input & Path Traversal Boundary Defense

### The Failure Mode
Untrusted input packages or repositories may embed malicious paths attempting directory traversal (`../../etc/shadow`), absolute path references, Windows backslash escapes, symlink traversal, or duplicate JSON keys.

### How Antigravity Preflight Stops It
All workspace and packet files are validated through strict path isolation checks:
- Paths containing `..` or leading slashes are immediately rejected with `PATH_ESCAPE`.
- Workspace keys with backslashes are rejected with `WORKSPACE_PATH`.
- Symlinked files within source and workspace trees are refused with `SYMLINK_REFUSED`.
- Input payloads with duplicate JSON keys are rejected with `DUPLICATE_KEY`.

---

## 4. Deterministic Line-Numbered Reading Views

### The Failure Mode
Discrepancies in line endings (CRLF on Windows vs. LF on Linux) frequently cause off-by-one errors between reviewers and human adjudicators.

### How Antigravity Preflight Solves It
The render command compiles a normalized reading view where line endings are strictly standardized to LF and anchored by source IDs and lines:
```bash
python3 -B -I skills/antigravity-preflight/scripts/manual_citations.py render \
  examples/plan/inventory.json /tmp/reading-view.txt
```
Sample rendered output:
```text
NUMBERED READING VIEW — derived; original snapshots retain their hashes.

SOURCE S01 sha256=de68b0f7 lines=2
[S01:1] Missing required source coverage makes the report INCOMPLETE.
[S01:2] A report with incomplete coverage cannot authorize readiness.
```

---

## Automated Continuous Validation

All four utility demonstrations are automated in [`tools/test_demonstrated_utility.py`](../tools/test_demonstrated_utility.py). The suite runs completely offline using synthetic doubles:

```bash
python3 -B -I tools/test_demonstrated_utility.py
```
Expected output:
```json
{"status": "PASS", "cases": 4, "checks": 15, "providerCalls": 0, "spend": 0.0}
```
