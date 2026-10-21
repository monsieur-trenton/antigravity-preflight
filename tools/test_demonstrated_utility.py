"""Automated test suite demonstrating the four core failure modes prevented by antigravity-preflight.

Exercises deterministic citation verification, tool sandboxing, input boundary defense,
and line-numbered reading views using synthetic fixtures. Zero provider calls, $0.00 spend.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent

# Load manual_citations module from skills
spec_mc = importlib.util.spec_from_file_location(
    "manual_citations",
    ROOT / "skills/antigravity-preflight/scripts/manual_citations.py"
)
mc = importlib.util.module_from_spec(spec_mc)
spec_mc.loader.exec_module(mc)

# Load cli_review module from Argon runtime
spec_cr = importlib.util.spec_from_file_location(
    "cli_review",
    ROOT / "runtime/argon-high/scripts/cli_review.py"
)
cr = importlib.util.module_from_spec(spec_cr)
spec_cr.loader.exec_module(cr)


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def test_exact_versus_hallucinated_citations() -> int:
    """Utility 1: Eliminates LLM quotation hallucinations and line coordinate drift."""
    checks = 0
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        src_text = "def handle_auth(token):\n    if not token:\n        raise PermissionDenied()\n    return True\n"
        (root / "api.py").write_text(src_text, encoding="utf-8")
        src_hash = sha(src_text)

        inv = {
            "sources": [{
                "id": "api-v1",
                "path": "api.py",
                "sha256": src_hash
            }]
        }
        inv_path = root / "inventory.json"
        inv_path.write_text(json.dumps(inv), encoding="utf-8")
        sources = mc.read_sources(inv_path)

        # 1. Exact verbatim citation succeeds
        exact_ledger = {
            "citations": [{
                "id": "C1",
                "source": "api-v1",
                "line": 3,
                "quote": "raise PermissionDenied()"
            }]
        }
        matched = mc.check(sources, exact_ledger)
        assert matched == 1, f"Expected 1 matched citation, got {matched}"
        checks += 1

        # 2. Hallucinated / drifting quote fails (common LLM substitution)
        drift_ledger = {
            "citations": [{
                "id": "C2",
                "source": "api-v1",
                "line": 3,
                "quote": "raise PermissionError()"
            }]
        }
        try:
            mc.check(sources, drift_ledger)
            raise AssertionError("Expected QUOTE_MISMATCH for hallucinated quote")
        except mc.Invalid as err:
            assert str(err) == "QUOTE_MISMATCH", f"Expected QUOTE_MISMATCH, got {err}"
            checks += 1

        # 3. Correct quote on wrong line fails
        shifted_ledger = {
            "citations": [{
                "id": "C3",
                "source": "api-v1",
                "line": 2,
                "quote": "raise PermissionDenied()"
            }]
        }
        try:
            mc.check(sources, shifted_ledger)
            raise AssertionError("Expected QUOTE_MISMATCH for line shift")
        except mc.Invalid as err:
            assert str(err) == "QUOTE_MISMATCH", f"Expected QUOTE_MISMATCH, got {err}"
            checks += 1

        # 4. Out-of-bounds line coordinate fails
        oob_ledger = {
            "citations": [{
                "id": "C4",
                "source": "api-v1",
                "line": 99,
                "quote": "raise PermissionDenied()"
            }]
        }
        try:
            mc.check(sources, oob_ledger)
            raise AssertionError("Expected LINE_OUT_OF_RANGE for line 99")
        except mc.Invalid as err:
            assert str(err) == "LINE_OUT_OF_RANGE", f"Expected LINE_OUT_OF_RANGE, got {err}"
            checks += 1

    return checks


def test_tool_sandboxing_and_execution_denial() -> int:
    """Utility 2: Strictly prevents operational tool execution and unauthorized agent delegation."""
    checks = 0

    init_event = {
        "event": "init",
        "init": {
            "model": cr.MODEL,
            "agent": "preflight-inline",
            "cwd": "/review",
            "permission_mode": "request-review",
            "tools": ["finish"]
        }
    }

    # 1. Passive review stream with finish tool succeeds
    stream_clean = cr.Stream()
    stream_clean.line(json.dumps(init_event).encode("utf-8"))
    stream_clean.line(json.dumps({
        "event": "step_update",
        "step_update": {"step_type": "agent_response", "state": "DONE", "step_index": 0}
    }).encode("utf-8"))
    stream_clean.line(json.dumps({
        "event": "step_update",
        "step_update": {"step_type": "tool", "tool_name": "finish", "state": "DONE", "step_index": 1}
    }).encode("utf-8"))
    stream_clean.line(json.dumps({
        "event": "result",
        "result": {"status": "SUCCESS", "num_turns": 1, "response": "Clean review assessment."}
    }).encode("utf-8"))
    assert stream_clean.result["response"] == "Clean review assessment."
    checks += 1

    # 2. Operational tool (e.g., run_command) execution attempt is rejected
    stream_exec = cr.Stream()
    stream_exec.line(json.dumps(init_event).encode("utf-8"))
    try:
        stream_exec.line(json.dumps({
            "event": "step_update",
            "step_update": {"step_type": "tool", "tool_name": "run_command", "state": "ACTIVE", "step_index": 0}
        }).encode("utf-8"))
        raise AssertionError("Expected OPERATIONAL_TOOL rejection for run_command")
    except ValueError as err:
        assert str(err) == "OPERATIONAL_TOOL", f"Expected OPERATIONAL_TOOL, got {err}"
        checks += 1

    # 3. Subagent delegation payload is rejected
    stream_deleg = cr.Stream()
    stream_deleg.line(json.dumps(init_event).encode("utf-8"))
    try:
        stream_deleg.line(json.dumps({
            "event": "step_update",
            "step_update": {
                "step_type": "agent_response",
                "state": "ACTIVE",
                "step_index": 0,
                "subagent_info": {"subagents": [{"name": "researcher"}]}
            }
        }).encode("utf-8"))
        raise AssertionError("Expected DELEGATION_PAYLOAD rejection")
    except ValueError as err:
        assert str(err) == "DELEGATION_PAYLOAD", f"Expected DELEGATION_PAYLOAD, got {err}"
        checks += 1

    # 4. Tool execution error is caught and rejected
    stream_err = cr.Stream()
    stream_err.line(json.dumps(init_event).encode("utf-8"))
    try:
        stream_err.line(json.dumps({
            "event": "step_update",
            "step_update": {"step_type": "tool", "tool_name": "finish", "state": "ERROR", "step_index": 0}
        }).encode("utf-8"))
        raise AssertionError("Expected STEP_STATE rejection for tool error")
    except ValueError as err:
        assert str(err) == "STEP_STATE", f"Expected STEP_STATE, got {err}"
        checks += 1

    return checks


def test_admission_boundary_and_path_defense() -> int:
    """Utility 3: Rejects path traversal escapes, symlinks, and duplicate keys at the boundary."""
    checks = 0

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        safe_file = root / "valid.txt"
        safe_file.write_text("safe content\n", encoding="utf-8")

        # 1. Directory traversal path escape is rejected
        try:
            cr.local_file(root, "../../etc/shadow")
            raise AssertionError("Expected PATH_ESCAPE rejection for ../")
        except ValueError as err:
            assert str(err) == "PATH_ESCAPE", f"Expected PATH_ESCAPE, got {err}"
            checks += 1

        # 2. Absolute path is rejected
        try:
            cr.local_file(root, "/etc/passwd")
            raise AssertionError("Expected PATH_ESCAPE rejection for absolute path")
        except ValueError as err:
            assert str(err) == "PATH_ESCAPE", f"Expected PATH_ESCAPE, got {err}"
            checks += 1

        # 3. Backslash in workspace key is rejected
        try:
            cr.workspace_key("subdir\\escape")
            raise AssertionError("Expected WORKSPACE_PATH rejection for backslash")
        except ValueError as err:
            assert str(err) == "WORKSPACE_PATH", f"Expected WORKSPACE_PATH, got {err}"
            checks += 1

        # 4. Symlinks inside the tree are refused
        symlink_file = root / "symlinked.txt"
        symlink_file.symlink_to(safe_file)
        try:
            cr.local_file(root, "symlinked.txt")
            raise AssertionError("Expected SYMLINK_REFUSED rejection")
        except ValueError as err:
            assert str(err) == "SYMLINK_REFUSED", f"Expected SYMLINK_REFUSED, got {err}"
            checks += 1

        # 5. Duplicate JSON keys are rejected
        duplicate_json = b'{"mode": "A_PLAN", "mode": "B_DIFF"}'
        try:
            cr.decode(duplicate_json)
            raise AssertionError("Expected DUPLICATE_KEY rejection")
        except ValueError as err:
            assert str(err) == "DUPLICATE_KEY", f"Expected DUPLICATE_KEY, got {err}"
            checks += 1

    return checks


def test_deterministic_reading_view_rendering() -> int:
    """Utility 4: Generates deterministic, line-numbered reading views with invariant character offsets."""
    checks = 0

    # 1. Source lines split handles standard LF and CRLF consistently
    lf_bytes = b"alpha\nbeta\ngamma\n"
    crlf_bytes = b"alpha\r\nbeta\r\ngamma\r\n"
    lines_lf = mc.source_lines(lf_bytes)
    lines_crlf = mc.source_lines(crlf_bytes)
    assert lines_lf == ["alpha", "beta", "gamma"], f"Unexpected LF split: {lines_lf}"
    assert lines_crlf == ["alpha", "beta", "gamma"], f"Unexpected CRLF split: {lines_crlf}"
    checks += 1

    # 2. Reading view contains exact [source:line] tags and SHA-256 integrity header
    fake_sources = {
        "S01": {
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "lines": ["import sys", "print('hello')"]
        }
    }
    view = mc.render(fake_sources)
    assert "NUMBERED READING VIEW" in view
    assert "SOURCE S01 sha256=e3b0c442" in view
    assert "[S01:1] import sys\n" in view
    assert "[S01:2] print('hello')\n" in view
    checks += 1

    return checks


def main():
    total_checks = 0
    total_checks += test_exact_versus_hallucinated_citations()
    total_checks += test_tool_sandboxing_and_execution_denial()
    total_checks += test_admission_boundary_and_path_defense()
    total_checks += test_deterministic_reading_view_rendering()

    summary = {
        "status": "PASS",
        "cases": 4,
        "checks": total_checks,
        "providerCalls": 0,
        "spend": 0.0
    }
    print(json.dumps(summary))


if __name__ == "__main__":
    main()
