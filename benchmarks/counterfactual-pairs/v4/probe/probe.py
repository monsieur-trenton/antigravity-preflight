"""Run the authoring probe: one native turn that asks the Gemini reviewer runtime to write one case pair. Nothing is scored and nothing is reviewed.

The native runtime was qualified as a tool-free reviewer, not as a text generator. This asks one question, once: does it return a usable
authored case when the prompt is an authoring assignment? It is bound to the same runtime package and `agy` binary as the v3 Gemini run
(run_gemini_v3.check_identity), makes exactly one live call and only with --execute, never retries, and refuses a second call in the same
working directory.

Usage: probe.py --runtime-dir runtime/flash-high --capabilities DIR --qualification FILE --workdir NEW_DIR [--execute]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rg = load("probe_run_gemini_v3", PARENT / "run_gemini_v3.py")
checker = load("probe_check_output", HERE / "check_probe_output.py")
rp = rg.rp
RUN_MANIFEST = PARENT / "v3-run-gemini" / "manifest.json"
CORPUS_MANIFEST = PARENT / "v3" / "manifest.json"
PROMPT = HERE / "author-prompt.txt"
PLACEHOLDER = b"Probe: no snapshot is reviewed in this turn; the assignment is in the prompt.\n"
RECEIPT_FIELDS = ("status", "failure", "closingFailures", "model", "effort", "servedAttestation", "retries", "invocations", "promptDelivery",
                  "elapsedSeconds", "processes", "privateHomeAbsent", "socketDirectoryAbsent")


def write_packet(directory, prompt):
    (directory / "snapshots").mkdir(parents=True)
    (directory / "prompt.txt").write_bytes(prompt)
    (directory / "snapshots/S01.txt").write_bytes(PLACEHOLDER)
    descriptor = {"schemaVersion": 1, "mode": "PLAN", "questions": ["Q01"],
                  "prompt": {"path": "prompt.txt", "sha256": rp.sha(prompt), "bytes": len(prompt)},
                  "sources": [{"id": "S01", "path": "snapshots/S01.txt", "sha256": rp.sha(PLACEHOLDER), "bytes": len(PLACEHOLDER)}]}
    (directory / "PACKET.json").write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    return directory / "PACKET.json"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--capabilities", required=True)
    parser.add_argument("--qualification", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--execute", action="store_true", help="make the one live native call; without it only prepare")
    args = parser.parse_args(argv)
    try:
        runtime = Path(args.runtime_dir).resolve()
        rp.need((runtime / "scripts/cli_review.py").is_file(), "RUNTIME_MISSING")
        work = Path(args.workdir).resolve()
        rp.need(rp.ROOT not in work.parents and work != rp.ROOT, "WORKDIR_INSIDE_REPOSITORY")
        rp.need(not (work / "attempt").exists(), "PROBE_ALREADY_RUN")
        rp.need(not work.exists() or not any(work.iterdir()), "WORKDIR_MUST_BE_NEW")  # a dry-run directory is never reused for the live call
        run = rg.load_run(RUN_MANIFEST)
        rg.check_identity(run, runtime, args.capabilities, rp.sha(CORPUS_MANIFEST.read_bytes()))
        prompt = PROMPT.read_bytes()
        rp.need(0 < len(prompt) <= 131072, "PROMPT_SIZE")
        work.mkdir(parents=True, exist_ok=True)
        packet = write_packet(work / "packet", prompt)
        seed, attempt = work / "seed", work / "attempt"
        prepare = [sys.executable, "-B", "-I", str(runtime / "scripts/cli_review.py"), "prepare", str(packet), str(Path(args.capabilities).resolve()), str(seed)]
        done = subprocess.run(prepare, capture_output=True, text=True, timeout=300, check=False)
        rp.need(done.returncode == 0 and not (seed / "CLI-GATE.json").exists(), "PREPARE_FAILED")
        summary = {"promptSha256": rp.sha(prompt), "promptBytes": len(prompt), "runManifestSha256": run["sha256"], "executed": False}
        if not args.execute:
            print(json.dumps(dict(summary, status="DRY_RUN_PREPARED_ONLY", providerCalls=0)))
            return 0
        shutil.copytree(seed, attempt, symlinks=True)
        rp.need(rp.inventory(seed) == rp.inventory(attempt), "SEED_COPY_MISMATCH")
        started = time.monotonic()
        live = [sys.executable, "-B", "-I", str(runtime / "scripts/cli_review.py"), "run", str(attempt), "--qualification", str(Path(args.qualification).resolve()), "--authorize-live"]
        try:
            subprocess.run(live, capture_output=True, text=True, timeout=rp.RUN_TIMEOUT_SECONDS, check=False)
            stop = None
        except subprocess.TimeoutExpired:
            stop = "WRAPPER_TIMEOUT"
        wall = round(time.monotonic() - started, 2)
        summary.update(executed=True, wallSeconds=wall)
        try:
            receipt = json.loads((attempt / "CLI-RECEIPT.json").read_bytes())
        except (OSError, ValueError):
            receipt = None
            stop = stop or "NO_RECEIPT"
        summary["receipt"] = {k: receipt.get(k) for k in RECEIPT_FIELDS} if receipt else None
        report_path = attempt / "GEMINI-REVIEW.md"
        if receipt and receipt.get("status") == "REPORT_RECEIVED_PENDING_ADJUDICATION" and report_path.is_file():
            report = report_path.read_bytes()
            (work / "PROBE-OUTPUT.md").write_bytes(report)
            summary.update(reportSha256=rp.sha(report), reportBytes=len(report))
            try:
                summary["mechanicalChecks"] = checker.check(report.decode("utf-8"))
            except UnicodeError:
                summary["mechanicalChecks"] = {"allPassed": False, "checks": {}, "details": {"reason": "report is not UTF-8"}}
        else:
            stop = stop or "RUNTIME_STOP:" + json.dumps((receipt or {}).get("failure") or (receipt or {}).get("closingFailures") or "UNSPECIFIED", sort_keys=True)[:120]
        summary["technicalStop"] = stop
        (work / "PROBE-SUMMARY.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(dict(summary, status="COMPLETE" if not stop else "STOPPED")))
        return 0 if not stop else 1
    except rp.Stop as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
