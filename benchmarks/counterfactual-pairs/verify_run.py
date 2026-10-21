"""Verify the integrity of a run_pilot_claude.py working directory against a frozen corpus; no model calls.

Checks the corpus pins, then for every trial: one ledger row per case with none missing or duplicated; every
recorded request is byte-identical to what the frozen corpus and the committed driver produce; every ledger report
hash matches its saved report; the saved report equals the CLI's result field; the stamp (route, model, effort,
system-prompt hash) is consistent and matches the arguments; the served model matches the request. Technical stops
are reported, not treated as failures. It never reads the oracle or scores anything.

Usage: verify_run.py --corpus DIR --workdir DIR --model MODEL_ID --effort EFFORT [--trials 1,2]
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest()


def check_pins(corpus):
    manifest = json.loads((corpus / "manifest.json").read_bytes())
    bad = [name for name, expected in manifest["pins"].items()
           if not (corpus / name).is_file() or sha((corpus / name).read_bytes()) != expected]
    return manifest, bad


def verify(corpus, workdir, model, effort, trials):
    rc = load("run_pilot_claude")
    rp = rc.rp
    manifest, bad_pins = check_pins(corpus)
    failures = [f"CORPUS_PIN_MISMATCH:{name}" for name in bad_pins]
    prompt = (corpus / "prompt.txt").read_text(encoding="utf-8")
    expected_system = sha(rc.SYSTEM_PROMPT.encode("utf-8"))
    order = manifest["submissionOrder"]
    report = {"corpus": str(corpus), "manifestSha256": sha((corpus / "manifest.json").read_bytes()),
              "casesInCorpus": manifest["cases"], "trials": {}}
    versions, served, cost_total = set(), set(), 0.0
    for trial in trials:
        ledger = workdir / f"responses-trial{trial}.jsonl"
        if not ledger.is_file():
            failures.append(f"LEDGER_MISSING:trial{trial}")
            continue
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        cases = [r["case"] for r in rows]
        if len(set(cases)) != len(cases):
            failures.append(f"DUPLICATE_CASES:trial{trial}")
        if set(cases) != set(order):
            failures.append(f"CASE_SET_MISMATCH:trial{trial}:missing={len(set(order) - set(cases))}:extra={len(set(cases) - set(order))}")
        if cases != order[:len(cases)]:
            failures.append(f"RECORDED_OUT_OF_ORDER:trial{trial}")
        stops, walls = {}, []
        for row in rows:
            tag = f"trial{trial}:{row['case']}"
            walls.append(row.get("wallSeconds", 0))
            cost_total += row.get("costUsd") or 0
            versions.add(row.get("claudeVersion"))
            served.update(row.get("servedModels", []))
            stamp_ok = (row.get("route") == rc.ROUTE and row.get("requestedModel") == model and row.get("effort") == effort
                        and row.get("systemPromptSha256") == expected_system and row.get("trial") == trial)
            if not stamp_ok:
                failures.append(f"STAMP_MISMATCH:{tag}")
            if row.get("technicalStop"):
                code = row["technicalStop"].split(":")[0]
                stops[code] = stops.get(code, 0) + 1
                continue
            attempt = workdir / f"trial{trial}" / "attempts" / row["case"]
            packet = corpus / "packets" / (row["case"] + ".txt")
            try:
                expected_request = rp.request_text(prompt, packet.read_text(encoding="utf-8").split("\n")[:-1], True)
                if (attempt / "request.txt").read_bytes() != expected_request:
                    failures.append(f"REQUEST_MISMATCH:{tag}")
                review = (attempt / "REVIEW.md").read_bytes()
                if sha(review) != row.get("reportSha256"):
                    failures.append(f"REPORT_HASH_MISMATCH:{tag}")
                output = json.loads((attempt / "claude-output.json").read_text(encoding="utf-8"))
                if output.get("result", "").encode("utf-8") != review:
                    failures.append(f"REPORT_NOT_CLI_RESULT:{tag}")
            except (OSError, ValueError):
                failures.append(f"EVIDENCE_MISSING:{tag}")
            if not any(m.startswith(model) for m in row.get("servedModels", [])):
                failures.append(f"SERVED_MODEL_MISMATCH:{tag}")
        report["trials"][str(trial)] = {"observations": len(rows), "technicalStops": stops,
                                        "meanWallSeconds": round(sum(walls) / len(walls), 1) if walls else None}
    report.update({"claudeVersions": sorted(str(v) for v in versions), "servedModelsReported": sorted(served),
                   "totalCostUsd": round(cost_total, 4), "failures": failures, "providerCalls": 0})
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", default=str(HERE))
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--effort", required=True)
    parser.add_argument("--trials", default="1,2")
    args = parser.parse_args(argv)
    report = verify(Path(args.corpus).resolve(), Path(args.workdir).resolve(), args.model, args.effort,
                    [int(t) for t in args.trials.split(",")])
    print(json.dumps(report, indent=2))
    return 1 if report["failures"] else 0


if __name__ == "__main__":
    sys.exit(main())
