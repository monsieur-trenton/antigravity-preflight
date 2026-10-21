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

## 2. Tool Sandboxing: Pre-Execution Native Hook & Post-Hoc Stream Admission

### The Failure Mode
Untrusted code or prompt injections within review packets might attempt to trick the reviewer into executing operational tools (e.g., executing shell commands via `run_command`, writing arbitrary files, or delegating work to unvetted subagents).

### How Antigravity Preflight Stops It (Dual-Layer Containment)
Preflight implements tool containment at two distinct architectural boundaries:

1. **Pre-Execution Native Hook Boundary (Prevention)**:
   The native CLI execution engine intercepts every tool call *before* invocation through the `PreToolUse` hook defined in [`.agents/hooks.json`](../runtime/argon-high/assets/cli-review/.agents/hooks.json). The hook points to [`deny_tools.py`](../runtime/argon-high/assets/cli-review/deny_tools.py) with wildcard matching (`*`):
   - Only the terminal `finish` tool produces `{"decision": "allow"}`.
   - Any operational tool (`run_command`, `write_to_file`, etc.) produces `{"decision": "deny"}` and is blocked before execution.
   - All attempted invocations are audited via `AGY_PREFLIGHT_AUDIT`.
   - Any malformed or unparseable tool call defaults to `"deny"`.

2. **Post-Hoc Stream Admission Boundary (Defense-in-Depth)**:
   Even if an operational tool event were somehow reported in the subprocess stream, the streaming parser ([`cli_review.py Stream`](../runtime/argon-high/scripts/cli_review.py)) acts as a secondary admission filter:
   - Operational tool events abort the stream with `OPERATIONAL_TOOL`.
   - Subagent delegation payloads abort the stream with `DELEGATION_PAYLOAD`.
   - Incomplete steps or nonzero tool errors abort the stream with `STEP_STATE`.

This separation guarantees that sandboxing does not rely solely on post-hoc stream rejection: tools are denied before execution by the native hook, and stream admission confirms compliance afterward.

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
{"status": "PASS", "cases": 4, "checks": 21, "providerCalls": 0, "spend": 0.0}
```
