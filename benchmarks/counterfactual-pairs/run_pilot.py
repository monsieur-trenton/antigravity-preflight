"""Drive the frozen counterfactual corpus through an already qualified native runtime, one turn per case.

This script performs no authentication or qualification. The caller supplies a frozen capabilities
directory and an offline qualification envelope for a host and runtime they are authorized to use.
Without --execute it only prepares packets (no agy, no provider). With --execute it runs exactly one
native turn per case: no retries, no repair, no fallback. A case with any recorded outcome, including a
stop, is never run again. The oracle is never read here.

Usage:
  run_pilot.py --runtime-dir runtime/flash-high --capabilities CAPS --qualification ENVELOPE --workdir NEW_DIR [--trial N] [--execute]
  run_pilot.py --runtime-dir runtime/argon-high --runtime-profile argon-high ...
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
RUN_TIMEOUT_SECONDS = 900  # above the runtime's own 600 s active limit; a hung wrapper is a stop, not a retry

QUESTION = "Q01"
FORMAT_SUFFIX = """
Question Q01: Does the snapshot contain any blocker supported by its own text? Answer from the snapshot only.

Write a short rationale, then finish the report with exactly this block, with no text after it:
MACHINE SUMMARY
COMPLETENESS: <COMPLETE or INCOMPLETE>
ASSESSMENT: <BLOCKERS_FOUND or CHANGES_RECOMMENDED or NO_BLOCKERS_FOUND>
FINDING: <BLOCKER or RISK or NOTE> | <VERIFIED or UNVERIFIED or CANNOT_CHECK> | <snapshot line number, or - if none> | <exact single-line quotation from that line, or - if none>
Write one FINDING line per finding, and none if there are no findings. Use only snapshot S01. Copy quotations exactly, without added quote marks.
"""


class Stop(ValueError):
    pass


def need(condition, code):
    if not condition:
        raise Stop(code)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def parse_report(text):
    """Parse the machine summary; raise Stop when the report does not follow the format."""
    marker = text.rfind("MACHINE SUMMARY")
    need(marker >= 0, "NO_MACHINE_SUMMARY")
    completeness = assessment = None
    findings = []
    for raw in text[marker:].splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("COMPLETENESS:"):
            need(completeness is None, "DUPLICATE_COMPLETENESS")
            completeness = line.split(":", 1)[1].strip()
        elif line.startswith("ASSESSMENT:"):
            need(assessment is None, "DUPLICATE_ASSESSMENT")
            assessment = line.split(":", 1)[1].strip()
        elif line.startswith("FINDING:"):
            parts = [p.strip() for p in line.split(":", 1)[1].split("|", 3)]
            need(len(parts) == 4, "MALFORMED_FINDING")
            severity, evidence, number, quote = parts
            if number == "-":
                number, quote = "0", ""
            need(number.isdigit(), "MALFORMED_FINDING")
            findings.append({"severity": severity, "evidence": evidence, "line": int(number),
                             "quote": "" if quote == "-" else quote})
        else:
            raise Stop("UNEXPECTED_LINE_AFTER_SUMMARY")
    need(completeness in ("COMPLETE", "INCOMPLETE"), "INVALID_COMPLETENESS")
    need(assessment in ("BLOCKERS_FOUND", "CHANGES_RECOMMENDED", "NO_BLOCKERS_FOUND"), "INVALID_ASSESSMENT")
    return {"completeness": completeness, "assessment": assessment, "findings": findings}


def inventory(root):
    rows = {}
    for path in sorted(root.rglob("*")):
        need(not path.is_symlink(), "SYMLINK_IN_EVIDENCE")
        rows[str(path.relative_to(root))] = ("dir", path.stat().st_mode & 0o7777) if path.is_dir() else \
            ("file", path.stat().st_mode & 0o7777, sha(path.read_bytes()))
    return rows


def request_text(prompt, lines, inline_evidence):
    body = prompt.rstrip("\n") + "\n"
    if inline_evidence:  # original Flash route: the prompt itself must carry the numbered evidence
        body += "\nSNAPSHOT S01 (numbered reading view; copy quotations from the row, without the prefix)\n"
        body += "".join(f"[S01:{n}] {text}\n" for n, text in enumerate(lines, 1))
    return (body + FORMAT_SUFFIX).encode("utf-8")


def write_packet(directory, case, prompt, snapshot, inline_evidence):
    lines = snapshot.decode("utf-8").split("\n")[:-1]
    request = request_text(prompt, lines, inline_evidence)
    (directory / "snapshots").mkdir(parents=True)
    (directory / "prompt.txt").write_bytes(request)
    (directory / "snapshots/S01.txt").write_bytes(snapshot)
    descriptor = {
        "schemaVersion": 1, "mode": "PLAN", "questions": [QUESTION],
        "prompt": {"path": "prompt.txt", "sha256": sha(request), "bytes": len(request)},
        "sources": [{"id": "S01", "path": "snapshots/S01.txt", "sha256": sha(snapshot), "bytes": len(snapshot)}],
    }
    (directory / "PACKET.json").write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    return directory / "PACKET.json"


def cli(args, *command):
    return [sys.executable, "-B", "-I", str(Path(args.runtime_dir).resolve() / "scripts/cli_review.py"), *command]


def run_case(args, case, prompt, snapshot, trial_dir):
    packet = write_packet(trial_dir / "packets" / case, case, prompt, snapshot, args.inline_evidence)
    seed, attempt = trial_dir / "seeds" / case, trial_dir / "attempts" / case
    seed.parent.mkdir(parents=True, exist_ok=True)
    attempt.parent.mkdir(parents=True, exist_ok=True)
    prepare = cli(args, "prepare", str(packet), str(Path(args.capabilities).resolve()), str(seed))
    if args.runtime_profile:
        prepare += ["--runtime-profile", args.runtime_profile]
    done = subprocess.run(prepare, capture_output=True, text=True, timeout=300, check=False)
    need(done.returncode == 0 and not (seed / "CLI-GATE.json").exists(), "PREPARE_FAILED")
    if not args.execute:
        return None
    shutil.copytree(seed, attempt, symlinks=True)
    need(inventory(seed) == inventory(attempt), "SEED_COPY_MISMATCH")
    started = time.monotonic()
    live = cli(args, "run", str(attempt), "--qualification", str(Path(args.qualification).resolve()), "--authorize-live")
    try:
        subprocess.run(live, capture_output=True, text=True, timeout=RUN_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return {"technicalStop": "WRAPPER_TIMEOUT", "wallSeconds": round(time.monotonic() - started, 2)}
    wall = round(time.monotonic() - started, 2)
    try:
        receipt = json.loads((attempt / "CLI-RECEIPT.json").read_bytes())
    except (OSError, ValueError):
        return {"technicalStop": "NO_RECEIPT", "wallSeconds": wall}
    if receipt.get("status") != "REPORT_RECEIVED_PENDING_ADJUDICATION":
        failure = receipt.get("failure") or receipt.get("closingFailures") or "UNSPECIFIED"
        return {"technicalStop": "RUNTIME_STOP:" + json.dumps(failure, sort_keys=True)[:120], "wallSeconds": wall}
    report = (attempt / "GEMINI-REVIEW.md").read_bytes()
    row = {"reportSha256": sha(report), "wallSeconds": wall}
    try:
        row.update(parse_report(report.decode("utf-8")))
    except (Stop, UnicodeError) as error:
        row["technicalStop"] = "UNPARSEABLE_REPORT:" + (str(error) if isinstance(error, Stop) else "UNICODE")
    return row


def recorded(ledger):
    if not ledger.exists():
        return {}
    return {json.loads(line)["case"]: json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime-dir", required=True, help="runtime/flash-high or runtime/argon-high; no default so the route is always explicit")
    parser.add_argument("--runtime-profile", help="required for argon-high (argon-high); never implied")
    parser.add_argument("--capabilities", required=True)
    parser.add_argument("--qualification", required=True)
    parser.add_argument("--workdir", required=True, help="outside the repository; reused only to resume the same trial")
    parser.add_argument("--trial", type=int, default=1)
    parser.add_argument("--execute", action="store_true", help="make live native calls; without it only prepare")
    parser.add_argument("--max-consecutive-stops", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        runtime = Path(args.runtime_dir).resolve()
        need((runtime / "scripts/cli_review.py").is_file(), "RUNTIME_MISSING")
        args.inline_evidence = runtime.name == "flash-high"
        need((args.runtime_profile is not None) == (runtime.name == "argon-high"), "PROFILE_MUST_MATCH_RUNTIME")
        work = Path(args.workdir).resolve()
        need(ROOT not in work.parents and work != ROOT, "WORKDIR_INSIDE_REPOSITORY")
        score = load_module("score", HERE / "score.py")
        manifest, _ = score.load_frozen()  # verifies every frozen pin, including prompt, packets and oracle
        prompt = (HERE / "prompt.txt").read_bytes().decode("utf-8")
        trial_dir = work / f"trial{args.trial}"
        ledger = work / f"responses-trial{args.trial}.jsonl"
        work.mkdir(parents=True, exist_ok=True)
        done = recorded(ledger)
        consecutive = 0
        summary = {"prepared": 0, "executed": 0, "stopped": 0, "skippedAlreadyRecorded": 0}
        for case in manifest["submissionOrder"]:
            if case in done:
                summary["skippedAlreadyRecorded"] += 1
                continue
            if args.execute and (trial_dir / "attempts" / case).exists():
                # State unknown after an interruption. Zero retries: record a stop, never re-run.
                row = {"technicalStop": "INTERRUPTED_UNKNOWN_STATE"}
            else:
                snapshot = (HERE / "packets" / (case + ".txt")).read_bytes()
                try:
                    row = run_case(args, case, prompt, snapshot, trial_dir)
                except (Stop, OSError, subprocess.SubprocessError) as error:
                    reason = str(error) if isinstance(error, Stop) else type(error).__name__
                    if not args.execute:  # a dry run never writes the response ledger
                        print(json.dumps(dict(summary, status="DRY_RUN_STOPPED", case=case, reason=reason)))
                        return 1
                    row = {"technicalStop": reason}
                if row is None:
                    summary["prepared"] += 1
                    continue
            row.update({"case": case, "trial": args.trial})
            with ledger.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            if row.get("technicalStop"):
                summary["stopped"] += 1
                consecutive += 1
                if consecutive >= args.max_consecutive_stops:
                    print(json.dumps(dict(summary, status="HALTED_CONSECUTIVE_STOPS", ledger=str(ledger))))
                    return 1
            else:
                summary["executed"] += 1
                consecutive = 0
        print(json.dumps(dict(summary, status="COMPLETE" if args.execute else "DRY_RUN_PREPARED_ONLY",
                              ledger=str(ledger) if args.execute else None, providerCallsFromThisScript=0)))
        return 0
    except (Stop, OSError, ValueError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, Stop) else type(error).__name__}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
