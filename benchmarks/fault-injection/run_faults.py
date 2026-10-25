"""Offline fault injection against the manual citation checker; no model or provider calls.

Starts from the valid baseline in examples/plan, applies one fault per variant, and runs the
real manual_citations.py command line. Mechanical faults must be stopped with the expected
reason. Semantic faults (a verbatim but misleading quotation) are recorded as passing through,
because the script proves text placement only. Checks that have no script in the manual route
are listed as not exercised, never scored.

Usage: run_faults.py [--check] [RESULTS_JSON]
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent.parent
TOOL = ROOT / "skills/antigravity-preflight/scripts/manual_citations.py"
BASELINE = ROOT / "examples/plan"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "results.json"

# Reason code -> gate layer, as implemented by manual_citations.py.
LAYER = {
    "SOURCE_HASH_MISMATCH": "PIN_AND_PATH",
    "SOURCE_PATH_ESCAPE": "PIN_AND_PATH",
    "SOURCE_SYMLINK": "PIN_AND_PATH",
    "SOURCE_NOT_REGULAR": "PIN_AND_PATH",
    "DUPLICATE_JSON_KEY": "STRICT_PARSING",
    "UNKNOWN_SOURCE": "LEDGER_SCHEMA",
    "INVALID_QUOTE": "LEDGER_SCHEMA",
    "DUPLICATE_CITATION_ID": "LEDGER_SCHEMA",
    "EMPTY_LEDGER": "LEDGER_SCHEMA",
    "LINE_OUT_OF_RANGE": "LINE_AND_QUOTE",
    "QUOTE_MISMATCH": "LINE_AND_QUOTE",
}


def edit_json(path, change):
    data = json.loads(path.read_bytes())
    change(data)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def ledger_edit(change):
    def mutate(work):
        edit_json(work / "citations.json", change)
    return mutate


def inventory_edit(change):
    def mutate(work):
        edit_json(work / "inventory.json", change)
    return mutate


def hash_drift(work):
    with (work / "snapshots/contract.txt").open("a", encoding="utf-8") as handle:
        handle.write("Added after the hash was pinned.\n")


def source_missing(work):
    (work / "snapshots/proposal.txt").unlink()


def source_symlink(work):
    target = work / "snapshots/contract.txt"
    elsewhere = work / "elsewhere.txt"
    target.rename(elsewhere)  # identical bytes, so only the symlink rule can reject it
    target.symlink_to(elsewhere)


def duplicate_json_key(work):
    text = (work / "citations.json").read_text(encoding="utf-8")
    (work / "citations.json").write_text(text.replace('"line": 2,', '"line": 2, "line": 3,', 1),
                                         encoding="utf-8")


def set_cite(index, **fields):
    def change(data):
        data["citations"][index].update(fields)
    return ledger_edit(change)


def duplicate_id(data):
    data["citations"][1]["id"] = data["citations"][0]["id"]


def empty_ledger(data):
    data["citations"] = []


def escape_path(data):
    data["sources"][0]["path"] = "../outside.txt"


# (id, family, description, mutator, expected reason or None when the script cannot detect it)
MECHANICAL = [
    ("source_hash_drift", "Evidence integrity", "Snapshot edited after its hash was pinned", hash_drift, "SOURCE_HASH_MISMATCH"),
    ("source_missing", "Evidence integrity", "Required source file is absent", source_missing, "SOURCE_NOT_REGULAR"),
    ("path_escape", "Evidence integrity", "Inventory path points outside the packet", inventory_edit(escape_path), "SOURCE_PATH_ESCAPE"),
    ("source_symlink", "Evidence integrity", "Snapshot replaced by a symlink with identical bytes", source_symlink, "SOURCE_SYMLINK"),
    ("duplicate_json_key", "Strict parsing", "Ledger repeats a key to hide a value", duplicate_json_key, "DUPLICATE_JSON_KEY"),
    ("empty_ledger", "Ledger shape", "Report supplies no citations at all", ledger_edit(empty_ledger), "EMPTY_LEDGER"),
    ("duplicate_citation_id", "Ledger shape", "Two citations share one identifier", ledger_edit(duplicate_id), "DUPLICATE_CITATION_ID"),
    ("unknown_source", "Ledger shape", "Citation names a source that was never supplied", set_cite(0, source="S09"), "UNKNOWN_SOURCE"),
    ("multiline_quote", "Ledger shape", "Quotation spans several lines", set_cite(0, quote="Missing required source coverage makes the report INCOMPLETE.\nAn incomplete report"), "INVALID_QUOTE"),
    ("wrong_line", "Quotation", "Right text, wrong line coordinate", set_cite(0, line=1), "QUOTE_MISMATCH"),
    ("wrong_source", "Quotation", "Right text attributed to the wrong source", set_cite(0, source="S02"), "QUOTE_MISMATCH"),
    ("hallucinated_quote", "Quotation", "Paraphrase presented as a verbatim quote", set_cite(0, quote="Missing required source coverage makes the report VALID."), "QUOTE_MISMATCH"),
    ("line_out_of_range", "Quotation", "Citation beyond the end of the file", set_cite(0, line=99), "LINE_OUT_OF_RANGE"),
]

SEMANTIC = [
    ("negation_dropped_quote", "Quotation", "Substring drops \"Do not\", reversing the source",
     set_cite(1, quote="check whether every supplied source was covered."), None),
    ("single_word_quote", "Quotation", "One-word quotation that proves almost nothing",
     set_cite(0, quote="source"), None),
]

NOT_EXERCISED = [
    ("missing_required_source_coverage", "Report coverage", "Report never mentions a required source", "Codex coverage check (SKILL.md step 3)"),
    ("unanswered_required_question", "Report coverage", "A required review question gets no answer", "Codex coverage check (SKILL.md step 3)"),
    ("report_modified_after_receipt", "Report custody", "Report bytes change after they were received", "Record and compare the report hash"),
    ("embedded_instruction_followed", "Model behaviour", "Reviewer obeys an instruction hidden in source text", "Needs live model trials (docs/testing-next.md, test 2)"),
]


def run_variant(mutator):
    with tempfile.TemporaryDirectory() as raw:
        work = Path(raw) / "plan"
        shutil.copytree(BASELINE, work)
        if mutator is not None:
            mutator(work)
        done = subprocess.run(
            [sys.executable, "-B", "-I", str(TOOL), "check", str(work / "inventory.json"), str(work / "citations.json")],
            capture_output=True, text=True, timeout=60, check=False)
    receipt = json.loads(done.stdout)
    return done.returncode, receipt


def build():
    code, baseline = run_variant(None)
    if code != 0 or baseline.get("status") != "CITATIONS_MATCHED":
        raise SystemExit("BASELINE_NOT_VALID: " + json.dumps(baseline))
    faults = []
    failures = []
    for fault_id, family, description, mutator, expected in MECHANICAL + SEMANTIC:
        code, receipt = run_variant(mutator)
        stopped = receipt.get("status") == "STOPPED"
        reason = receipt.get("reason")
        if expected is not None:
            kind = "MECHANICAL"
            passed = stopped and reason == expected
        else:
            kind = "SEMANTIC"
            passed = not stopped  # recorded limit: the script is not expected to detect these
        if not passed:
            failures.append(fault_id)
        faults.append({
            "id": fault_id, "family": family, "description": description, "kind": kind,
            "automation": "SCRIPT", "expectedReason": expected, "observedStatus": receipt["status"],
            "observedReason": reason, "layer": LAYER.get(reason), "expectationMet": passed,
        })
    for fault_id, family, description, owner in NOT_EXERCISED:
        faults.append({
            "id": fault_id, "family": family, "description": description, "kind": "MANUAL",
            "automation": "NOT_EXERCISED", "owner": owner, "observedStatus": None,
            "observedReason": None, "layer": None, "expectationMet": None,
        })
    mech = [f for f in faults if f["kind"] == "MECHANICAL"]
    sem = [f for f in faults if f["kind"] == "SEMANTIC"]
    results = {
        "kind": "OFFLINE_FAULT_INJECTION_MANUAL_CITATIONS",
        "scope": "manual_citations.py check only; coverage, question, custody and model-behaviour checks are not exercised",
        "tool": {"path": str(TOOL.relative_to(ROOT)), "sha256": hashlib.sha256(TOOL.read_bytes()).hexdigest()},
        "baseline": {"status": baseline["status"], "citations": baseline["citations"]},
        "summary": {
            "mechanicalFaults": len(mech),
            "mechanicalStopped": sum(f["observedStatus"] == "STOPPED" for f in mech),
            "mechanicalReasonMatched": sum(f["expectationMet"] is True for f in mech),
            "mechanicalPassedThrough": sum(f["observedStatus"] != "STOPPED" for f in mech),
            "semanticFaults": len(sem),
            "semanticPassedThroughToManualCheck": sum(f["observedStatus"] != "STOPPED" for f in sem),
            "notExercised": len(faults) - len(mech) - len(sem),
            "providerCalls": 0,
        },
        "faults": faults,
    }
    return results, failures


def main(argv):
    check = "--check" in argv
    paths = [a for a in argv if not a.startswith("--")]
    output = Path(paths[0]) if paths else DEFAULT_OUTPUT
    results, failures = build()
    if failures:
        print(json.dumps({"status": "UNEXPECTED_OUTCOME", "faults": failures}))
        return 1
    text = json.dumps(results, indent=2) + "\n"
    if check:
        if not output.is_file() or output.read_text(encoding="utf-8") != text:
            print(json.dumps({"status": "STALE_RESULTS", "path": str(output)}))
            return 1
    else:
        output.write_text(text, encoding="utf-8")
    summary = results["summary"]
    print(json.dumps({"status": "PASS", **summary}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
