"""Verify a run_gemini_v3.py working directory against the frozen corpus and run manifest; no model calls, no oracle.

For one trial's workdir: the corpus pins and run manifest; one ledger row per case, none missing or duplicated, in the frozen submission
order; every row stamped with the run manifest hash, route and parser; for every observation that reached a report, the packet's prompt
is byte-identical to what the frozen prompt and corpus produce (what the model was sent), the saved report matches the ledger hash and the
receipt's report hash, re-parsing it with the run's parser reproduces the ledger row (or the recorded stop), and the receipt is clean:
status, no failure, model and effort as frozen, zero retries, one proxy and one native invocation, every spawned process reaped, private
home and socket directory gone, prompt delivered in full (wire bytes equal to the framed prompt), and the native binary's SHA-256 equal to the frozen
one. Stops are listed, not failures. The model that served each turn is not attestable on this route and is not checked.

Usage: verify_gemini_run.py --corpus DIR --run-manifest FILE --workdir DIR [--trial N]
"""
import argparse
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


def expected_wire_bytes(prompt_bytes):
    """What the runtime records as wireBytes: the prompt travels as one stream-json user event plus a newline, not as the bare prompt.
    Checked against all 48 receipts of the Gemini pilot (results/pilot-flash-high) in test_run.py."""
    frame = json.dumps(dict(event="user", message=dict(content=prompt_bytes.decode("utf-8")))).encode() + b"\n"
    return len(frame)


def check_receipt(receipt, run, expected_prompt, report_bytes, rp):
    problems = []
    if receipt.get("status") != "REPORT_RECEIVED_PENDING_ADJUDICATION" or receipt.get("failure") or receipt.get("closingFailures"):
        problems.append("RECEIPT_NOT_CLEAN")
    if receipt.get("model") != run["runtime"]["model"] or receipt.get("effort") != run["runtime"]["effort"]:
        problems.append("RECEIPT_MODEL_OR_EFFORT")
    if receipt.get("retries") != 0 or receipt.get("invocations") != {"proxy": 1, "native": 1}:
        problems.append("RECEIPT_RETRIES_OR_INVOCATIONS")
    processes = receipt.get("processes") or {}
    if not processes or any(p.get("spawned") and not p.get("reaped") for p in processes.values()):
        problems.append("PROCESS_NOT_REAPED")
    if receipt.get("privateHomeAbsent") is not True or receipt.get("socketDirectoryAbsent") is not True:
        problems.append("SANDBOX_NOT_CLEANED")
    delivery = receipt.get("promptDelivery") or {}
    wire = expected_wire_bytes(expected_prompt)
    if delivery.get("status") != "COMPLETE" or delivery.get("wireBytes") != wire or delivery.get("bytesWritten") != wire:
        problems.append("PROMPT_DELIVERY")
    if (receipt.get("native") or {}).get("sha256") != run["binary"]["sha256"]:
        problems.append("NATIVE_BINARY_HASH")
    if (receipt.get("report") or {}).get("sha256") != rp.sha(report_bytes):
        problems.append("RECEIPT_REPORT_HASH")
    return problems


def verify(corpus, run_manifest, workdir, trial):
    rg = load("run_gemini_v3_for_verify", HERE / "run_gemini_v3.py")
    rp = rg.rp
    failures = []
    manifest = json.loads((corpus / "manifest.json").read_bytes())
    for name, expected in manifest["pins"].items():
        if not (corpus / name).is_file() or rp.sha((corpus / name).read_bytes()) != expected:
            failures.append("CORPUS_PIN_MISMATCH:" + name)
    try:
        run = rg.load_run(run_manifest)
    except (rp.Stop, OSError, ValueError, KeyError) as error:
        return {"failures": ["RUN_MANIFEST:" + (str(error) if isinstance(error, rp.Stop) else type(error).__name__)], "providerCalls": 0}
    if rp.sha((corpus / "manifest.json").read_bytes()) != run["corpus"]["manifestSha256"]:
        failures.append("RUN_CORPUS_MISMATCH")
    prompt = (corpus / "prompt.txt").read_text(encoding="utf-8")
    order = manifest["submissionOrder"]
    ledger = Path(workdir) / f"responses-trial{trial}.jsonl"
    report = {"corpus": str(corpus), "runManifestSha256": run["sha256"], "trial": trial, "casesInCorpus": manifest["cases"]}
    if not ledger.is_file():
        return dict(report, failures=failures + ["LEDGER_MISSING"], providerCalls=0)
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = [r["case"] for r in rows]
    if len(set(cases)) != len(cases):
        failures.append("DUPLICATE_CASES")
    if set(cases) != set(order):
        failures.append(f"CASE_SET_MISMATCH:missing={len(set(order) - set(cases))}:extra={len(set(cases) - set(order))}")
    if cases != order[:len(cases)]:
        failures.append("RECORDED_OUT_OF_ORDER")
    stops, walls, labels = {}, [], 0
    attempts = Path(workdir) / f"trial{trial}"
    for row in rows:
        tag = row["case"]
        walls.append(row.get("wallSeconds", 0))
        if (row.get("route"), row.get("parser"), row.get("runManifestSha256"), row.get("trial"), row.get("binarySha256")) != \
                (rg.ROUTE, rg.PARSER, run["sha256"], trial, run["binary"]["sha256"]):
            failures.append(f"STAMP_MISMATCH:{tag}")
        stop = row.get("technicalStop")
        if stop:
            stops[stop.split(":")[0]] = stops.get(stop.split(":")[0], 0) + 1
        attempt = attempts / "attempts" / tag
        packet = attempts / "packets" / tag
        snapshot = (corpus / "packets" / (tag + ".txt")).read_bytes()
        try:
            expected_prompt = rp.request_text(prompt, snapshot.decode("utf-8").split("\n")[:-1], True)
            if (packet / "prompt.txt").read_bytes() != expected_prompt or (packet / "snapshots/S01.txt").read_bytes() != snapshot:
                failures.append(f"REQUEST_MISMATCH:{tag}")
        except OSError:
            if not stop or stop in ("INTERRUPTED_UNKNOWN_STATE",):
                failures.append(f"EVIDENCE_MISSING:{tag}")
            continue
        if stop and not stop.startswith("UNPARSEABLE_REPORT"):
            continue  # a runtime stop or timeout: no report to check; it is listed
        try:
            report_bytes = (attempt / "GEMINI-REVIEW.md").read_bytes()
            receipt = json.loads((attempt / "CLI-RECEIPT.json").read_bytes())
        except (OSError, ValueError):
            failures.append(f"EVIDENCE_MISSING:{tag}")
            continue
        if rp.sha(report_bytes) != row.get("reportSha256"):
            failures.append(f"REPORT_HASH_MISMATCH:{tag}")
        failures += [f"{p}:{tag}" for p in check_receipt(receipt, run, expected_prompt, report_bytes, rp)]
        try:
            parsed = rg.tolerant_parse(report_bytes.decode("utf-8"))
            if stop:
                failures.append(f"STOP_BUT_REPORT_PARSES:{tag}")
            else:
                for key in ("assessment", "completeness", "findings"):
                    if parsed[key] != row.get(key):
                        failures.append(f"LEDGER_DIFFERS_FROM_REPARSE:{tag}")
                        break
                if bool(parsed.get("snapshotLabelRead")) != bool(row.get("snapshotLabelRead")):
                    failures.append(f"LABEL_FLAG_MISMATCH:{tag}")
                labels += bool(parsed.get("snapshotLabelRead"))
        except (rp.Stop, UnicodeError) as error:
            code = "UNPARSEABLE_REPORT:" + (str(error) if isinstance(error, rp.Stop) else "UNICODE")
            if stop != code:
                failures.append(f"REPARSE_STOP_MISMATCH:{tag}")
    report.update({"observations": len(rows), "technicalStops": stops, "snapshotLabelsRead": labels,
                   "meanWallSeconds": round(sum(walls) / len(walls), 1) if walls else None, "failures": failures, "providerCalls": 0})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--run-manifest", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--trial", type=int, default=1)
    args = parser.parse_args(argv)
    report = verify(Path(args.corpus).resolve(), args.run_manifest, Path(args.workdir).resolve(), args.trial)
    print(json.dumps(report, indent=2))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
