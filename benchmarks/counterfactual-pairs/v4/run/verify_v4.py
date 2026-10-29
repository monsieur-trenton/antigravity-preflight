"""Verify a v4 run directory against the frozen corpus, schedule and run manifest, without reading the oracle; no model calls.

For every ledger of a route: each row belongs to a scheduled (block, arm, trial) step and to a case of that block, appears once, carries the run manifest's hash and its route,
and its recorded request equals the request rebuilt from the pinned files and the corpus packets (the saved request, and for Gemini the packet's prompt and the wire frame size).
Each report equals the hash in its row, re-parses to the same assessment and findings, and the route's own evidence holds: Claude, the served models are the requested one and
no safety stop; Gemini, a clean receipt (one proxy and one native invocation, no retries, processes reaped, prompt delivered, the pinned model, effort and binary). Attempt directories
without a ledger row are listed.

Usage: verify_v4.py --corpus DIR --run-manifest FILE --workdir DIR --route claude|gemini [--schedule FILE] [--include-optional]
Prints a JSON object with "failures" (empty when the directory verifies) and the coverage of the route's steps. Exit 0 only when there are no failures.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rv = load("v4verify_run_v4", HERE / "run_v4.py")
rp, rr = rv.rp, rv.rr
sha = rv.sha


def verify(corpus, run_manifest, workdir, route, schedule_path=None, include_optional=False):
    failures = []

    def fail(code, where):
        failures.append(f"{code}:{where}")

    work = Path(workdir)
    run = rv.load_run_manifest(run_manifest)
    corpus_dir, corpus_manifest, sources_of = rv.load_corpus(corpus)
    if sha((corpus_dir / "manifest.json").read_bytes()) != run["corpus"]["manifestSha256"]:
        fail("RUN_CORPUS_MISMATCH", "-")
    schedule = rv.load_schedule(schedule_path or HERE / f"schedule-{run['split']}.json", run, corpus_manifest)
    steps = rv.route_steps(schedule, route, True)
    allowed = {(s["block"], s["arm"], s["trial"]): s for s in steps if include_optional or not s.get("optional")}
    label = rv.ROUTE_LABELS[route]
    spec = run["routes"][route]
    seen_cases = {}
    rows_total = stops = 0
    for ledger in sorted(work.glob(f"responses-{route}-*-trial*.jsonl")):
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        if not rows:
            continue
        arm, trial = rows[0].get("arm"), rows[0].get("trial")
        if ledger != rv.ledger_path(work, route, arm, trial):
            fail("LEDGER_NAME", ledger.name)
        keyed = set()
        for row in rows:
            case, where = row.get("case"), f"{ledger.name}:{row.get('case')}"
            rows_total += 1
            if (arm, trial) != (row.get("arm"), row.get("trial")):
                fail("MIXED_LEDGER", where)
            if case in keyed:
                fail("DUPLICATE_ROW", where)
            keyed.add(case)
            step = allowed.get((row.get("block"), arm, trial))
            if step is None or row.get("step") != step["step"]:
                fail("UNSCHEDULED_STEP", where)
                continue
            if case not in rv.block_cases(schedule, row["block"]):
                fail("CASE_NOT_IN_BLOCK", where)
                continue
            if row.get("runManifestSha256") != run["sha256"] or row.get("route") != label:
                fail("STAMP", where)
            request = rr.build(arm, sources_of(case))
            if row.get("requestSha256") != sha(request) or row.get("requestBytes") != len(request):
                fail("REQUEST_HASH", where)
            if row.get("technicalStop"):
                stops += 1
            attempt = rv.attempt_dir(work, route, arm, trial) / "attempts" / case
            if row.get("technicalStop") == "INTERRUPTED_UNKNOWN_STATE":
                continue
            check_evidence(fail, row, attempt, request, route, arm, spec, where)
        seen_cases[(arm, trial)] = keyed
    for (arm, trial), keyed in seen_cases.items():
        folder = rv.attempt_dir(work, route, arm, trial) / "attempts"
        if folder.is_dir():
            for directory in sorted(folder.iterdir()):
                if directory.name not in keyed:
                    fail("ATTEMPT_WITHOUT_ROW", f"{arm}/trial{trial}/{directory.name}")
    coverage = [{"step": s["step"], "block": s["block"], "arm": s["arm"], "trial": s["trial"], "complete": not rv.step_state(work, schedule, route, s)[1]}
                for s in steps if include_optional or not s.get("optional")]
    return {"failures": failures, "route": route, "rows": rows_total, "technicalStops": stops, "stepsComplete": sum(c["complete"] for c in coverage),
            "stepsTotal": len(coverage), "coverage": coverage, "providerCalls": 0}


def check_evidence(fail, row, attempt, request, route, arm, spec, where):
    parse = rv.bare_parse if arm == "bare" else rv.tolerant_parse
    if route == "claude":
        saved = attempt / "request.txt"
        if not saved.is_file() or saved.read_bytes() != request:
            fail("SAVED_REQUEST", where)
        report_file = attempt / "REVIEW.md"
        if row.get("technicalStop", "").startswith(("NO_JSON_OUTPUT", "WRAPPER_TIMEOUT", "CLAUDE_ERROR")) and not report_file.is_file():
            return
        models = row.get("servedModels") or []
        if not row.get("technicalStop") and (not models or not all(m.startswith(spec["model"]) for m in models)):
            fail("SERVED_MODEL", where)
        if row.get("safetyStops") and not row.get("technicalStop"):
            fail("SAFETY_STOP_NOT_RECORDED", where)
        if row.get("requestedModel") != spec["model"] or row.get("effort") != spec["effort"]:
            fail("REQUESTED_MODEL", where)
    else:
        report_file = attempt / "GEMINI-REVIEW.md"
        prompt = attempt / "packet" / "prompt.txt"
        if not prompt.is_file() or prompt.read_bytes() != request:
            fail("PACKET_PROMPT", where)
        receipt_file = attempt / "CLI-RECEIPT.json"
        if not receipt_file.is_file():
            if row.get("technicalStop") not in ("NO_RECEIPT", "WRAPPER_TIMEOUT"):
                fail("NO_RECEIPT", where)
            return
        receipt = json.loads(receipt_file.read_bytes())
        if row.get("technicalStop") and not row.get("reportSha256"):
            return
        ok = (receipt.get("status") == "REPORT_RECEIVED_PENDING_ADJUDICATION" and receipt.get("model") == spec["runtime"]["model"]
              and receipt.get("effort") == spec["runtime"]["effort"] and receipt.get("retries") == 0
              and receipt.get("invocations") == {"proxy": 1, "native": 1} and receipt.get("privateHomeAbsent") is True
              and receipt.get("socketDirectoryAbsent") is True and (receipt.get("native") or {}).get("sha256") == spec["binary"]["sha256"]
              and all((p or {}).get("reaped") for p in (receipt.get("processes") or {}).values()))
        if not ok:
            fail("RECEIPT", where)
        frame = json.dumps(dict(event="user", message=dict(content=request.decode("utf-8")))).encode() + b"\n"
        delivery = receipt.get("promptDelivery") or {}
        if delivery.get("status") != "COMPLETE" or delivery.get("wireBytes") != len(frame):
            fail("PROMPT_DELIVERY", where)
        if row.get("receiptSha256") != sha(receipt_file.read_bytes()):
            fail("RECEIPT_HASH", where)
    if not report_file.is_file():
        fail("MISSING_REPORT", where)
        return
    report = report_file.read_bytes()
    if row.get("reportSha256") != sha(report):
        fail("REPORT_HASH", where)
        return
    try:
        parsed = parse(report.decode("utf-8"))
    except (rp.Stop, UnicodeError) as error:
        if not str(row.get("technicalStop", "")).startswith("UNPARSEABLE_REPORT"):
            fail("PARSE_STOP_NOT_RECORDED", where + ":" + str(error))
        return
    if row.get("technicalStop") and not row["technicalStop"].startswith("SAFETY_INTERRUPTED") and row["technicalStop"] != "MODEL_MISMATCH":
        fail("STOP_WITH_PARSEABLE_REPORT", where)
    if row.get("assessment") != parsed["assessment"] or row.get("findings", []) != parsed["findings"]:
        if not row.get("technicalStop"):
            fail("REPARSE_DIFFERS", where)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--run-manifest", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--route", required=True, choices=sorted(rv.ARMS))
    parser.add_argument("--schedule")
    parser.add_argument("--include-optional", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = verify(args.corpus, args.run_manifest, args.workdir, args.route, args.schedule, args.include_optional)
    except (rp.Stop, OSError, ValueError, KeyError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, rp.Stop) else type(error).__name__}))
        return 1
    print(json.dumps(result, indent=1))
    return 0 if not result["failures"] else 1


if __name__ == "__main__":
    sys.exit(main())
