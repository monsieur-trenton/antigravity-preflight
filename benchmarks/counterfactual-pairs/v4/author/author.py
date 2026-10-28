"""Author the v4 pairs through the qualified native runtime: one live call per pair (and one per wording-B rewording), checked mechanically, every call recorded.

The runtime was qualified as a tool-free reviewer; the probe (../probe/) showed it can serve as a generator through a thin wrapper, and this is that wrapper, bound to the
same runtime package and `agy` binary as the v3 Gemini run. Without --execute it only builds the prompts (no model call). With --execute it makes at most --max-calls live
calls in this invocation, never in a reused call directory, and never more than --max-attempts reports for one pair and purpose (a runtime stop produces none and does not count, up to two per pair). A failed attempt is not an observation: it is
recorded in calls.jsonl with its mechanical check results and the report is kept, and the pair may be tried again until the attempts are used up. Nothing is scored here.

Outputs under --workdir (which may be reused to resume; it must be outside the repository):
  prompts/<pair>.<A|B>.txt   the exact prompts            calls.jsonl     one row per call
  calls/<pair>-<purpose>-aN/ the packet, seed, attempt     accepted/<pair>.<A|B>.md   the unmodified reports that passed every mechanical check

Usage: author.py --split dev|test --runtime-dir DIR --capabilities DIR --qualification FILE --workdir DIR [--pairs ID,ID] [--reword] [--max-calls N]
                 [--max-attempts N] [--max-consecutive-stops N] [--execute]
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
sys.path.insert(0, str(HERE))
import check_author as ca  # noqa: E402
import prompts  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load("author_probe", HERE.parent / "probe" / "probe.py")
rg, rp = probe.rg, probe.rg.rp
RUN_MANIFEST, CORPUS_MANIFEST = probe.RUN_MANIFEST, probe.CORPUS_MANIFEST
DEFAULT_MAX_ATTEMPTS = 2
MAX_STOPS_PER_PAIR = 2


def failed_names(result):
    return sorted(name for name, ok in result["checks"].items() if not ok)


def native_call(runtime, capabilities, qualification, prompt, call_dir):
    """One live native turn in a new directory. Returns {"report": bytes|None, "receipt": {...}|None, "technicalStop": str|None, "wallSeconds": float}."""
    rp.need(not call_dir.exists(), "CALL_DIRECTORY_EXISTS")
    call_dir.mkdir(parents=True)
    packet = probe.write_packet(call_dir / "packet", prompt)
    seed, attempt = call_dir / "seed", call_dir / "attempt"
    prepare = [sys.executable, "-B", "-I", str(runtime / "scripts/cli_review.py"), "prepare", str(packet), str(Path(capabilities).resolve()), str(seed)]
    done = subprocess.run(prepare, capture_output=True, text=True, timeout=300, check=False)
    rp.need(done.returncode == 0 and not (seed / "CLI-GATE.json").exists(), "PREPARE_FAILED")
    shutil.copytree(seed, attempt, symlinks=True)
    rp.need(rp.inventory(seed) == rp.inventory(attempt), "SEED_COPY_MISMATCH")
    started = time.monotonic()
    live = [sys.executable, "-B", "-I", str(runtime / "scripts/cli_review.py"), "run", str(attempt), "--qualification", str(Path(qualification).resolve()), "--authorize-live"]
    stop = None
    try:
        subprocess.run(live, capture_output=True, text=True, timeout=rp.RUN_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        stop = "WRAPPER_TIMEOUT"
    wall = round(time.monotonic() - started, 2)
    try:
        receipt = json.loads((attempt / "CLI-RECEIPT.json").read_bytes())
    except (OSError, ValueError):
        receipt, stop = None, stop or "NO_RECEIPT"
    report_path = attempt / "GEMINI-REVIEW.md"
    report = None
    if receipt and receipt.get("status") == "REPORT_RECEIVED_PENDING_ADJUDICATION" and report_path.is_file():
        report = report_path.read_bytes()
    else:
        stop = stop or "RUNTIME_STOP:" + json.dumps((receipt or {}).get("failure") or (receipt or {}).get("closingFailures") or "UNSPECIFIED", sort_keys=True)[:120]
    return {"report": report, "receipt": {k: receipt.get(k) for k in probe.RECEIPT_FIELDS} if receipt else None, "technicalStop": stop, "wallSeconds": wall}


def read_ledger(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--capabilities", required=True)
    parser.add_argument("--qualification", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--pairs", help="comma-separated pair ids (default: every pair of the split, in assignment order)")
    parser.add_argument("--reword", action="store_true", help="author the wording-B rewordings of accepted pairs instead of new pairs")
    parser.add_argument("--max-calls", type=int, default=1, help="live calls in this invocation (default 1)")
    parser.add_argument("--max-attempts", type=int, default=DEFAULT_MAX_ATTEMPTS, help="attempts per pair and purpose, counting every earlier row of the ledger")
    parser.add_argument("--max-consecutive-stops", type=int, default=3)
    parser.add_argument("--execute", action="store_true", help="make live calls; without it only build the prompts")
    args = parser.parse_args(argv)
    try:
        runtime = Path(args.runtime_dir).resolve()
        rp.need((runtime / "scripts/cli_review.py").is_file(), "RUNTIME_MISSING")
        work = Path(args.workdir).resolve()
        rp.need(rp.ROOT not in work.parents and work != rp.ROOT, "WORKDIR_INSIDE_REPOSITORY")
        rp.need(args.max_calls >= 1 and args.max_attempts >= 1, "BAD_LIMITS")
        run = rg.load_run(RUN_MANIFEST)
        rg.check_identity(run, runtime, args.capabilities, rp.sha(CORPUS_MANIFEST.read_bytes()))
        doc = json.loads((HERE / f"assignments-{args.split}.json").read_bytes())
        seeds = json.loads((HERE / "seeds.json").read_bytes())
        rp.need(doc["seedSha256"] == seeds[args.split]["sha256"], "SEED_MISMATCH")
        instances = doc["instances"]
        if args.pairs:
            wanted = args.pairs.split(",")
            rp.need(all(any(i["pair"] == w for i in instances) for w in wanted), "UNKNOWN_PAIR")
            instances = [i for i in instances if i["pair"] in wanted]
        if args.reword:
            instances = [i for i in instances if i["wordingB"]]
        purpose, wording = ("reword", "B") if args.reword else ("author", "A")
        for sub in ("prompts", "calls", "accepted"):
            (work / sub).mkdir(parents=True, exist_ok=True)
        ledger = work / "calls.jsonl"
        summary = {"split": args.split, "purpose": purpose, "runManifestSha256": run["sha256"], "dryRun": not args.execute, "pairsSelected": len(instances), "calls": 0,
                   "accepted": 0, "failedChecks": 0, "technicalStops": 0, "alreadyAccepted": 0, "attemptsUsedUp": [], "waitingForAccepted": []}
        consecutive = 0
        for instance in instances:
            pair = instance["pair"]
            family, domain = prompts.family_of(instance), prompts.domain_of(instance)
            accepted_a, accepted_b = work / "accepted" / f"{pair}.A.md", work / "accepted" / f"{pair}.B.md"
            target = accepted_b if args.reword else accepted_a
            if target.is_file():
                summary["alreadyAccepted"] += 1
                continue
            if args.reword:
                if not accepted_a.is_file():
                    summary["waitingForAccepted"].append(pair)
                    continue
                result_a, parsed_a = ca.analyse(accepted_a.read_text(encoding="utf-8"), instance, family)
                rp.need(result_a["allPassed"] and parsed_a, "ACCEPTED_A_NO_LONGER_PASSES:" + pair)
                prompt = prompts.reword_prompt(instance, parsed_a).encode("utf-8")
            else:
                prompt = prompts.author_prompt(instance, family, domain).encode("utf-8")
            rp.need(0 < len(prompt) <= 131072, "PROMPT_SIZE")
            (work / "prompts" / f"{pair}.{wording}.txt").write_bytes(prompt)
            if not args.execute:
                continue
            own = [row for row in read_ledger(ledger) if row["pair"] == pair and row["purpose"] == purpose]
            # a call that ended in a runtime stop produced no report and does not use up an attempt, but no pair gets more than two calls beyond its limit
            used = sum(1 for row in own if not row.get("technicalStop"))
            if used >= args.max_attempts or len(own) >= args.max_attempts + MAX_STOPS_PER_PAIR:
                summary["attemptsUsedUp"].append(pair)
                continue
            if summary["calls"] >= args.max_calls:
                break
            number = len(own) + 1
            call_dir = work / "calls" / f"{pair}-{purpose}-a{number}"
            row = {"split": args.split, "pair": pair, "purpose": purpose, "attempt": number, "promptSha256": rp.sha(prompt), "promptBytes": len(prompt),
                   "runManifestSha256": run["sha256"], "accepted": False}
            if call_dir.exists():
                row.update(technicalStop="INTERRUPTED_UNKNOWN_STATE")  # zero silent retries: the earlier call's outcome is unknown, so it is recorded and counts
            else:
                try:
                    outcome = native_call(runtime, args.capabilities, args.qualification, prompt, call_dir)
                except (rp.Stop, OSError, subprocess.SubprocessError) as error:
                    outcome = {"report": None, "receipt": None, "technicalStop": str(error) if isinstance(error, rp.Stop) else type(error).__name__, "wallSeconds": 0}
                summary["calls"] += 1
                row.update(wallSeconds=outcome["wallSeconds"], receipt=outcome["receipt"], technicalStop=outcome["technicalStop"])
                if outcome["report"] is not None:
                    report = outcome["report"]
                    (call_dir / "REPORT.md").write_bytes(report)
                    row.update(reportSha256=rp.sha(report), reportBytes=len(report))
                    try:
                        text = report.decode("utf-8")
                        result, parsed = (ca.analyse(text, instance, family) if not args.reword else ca.analyse_reword(text, parsed_a, instance, family))
                    except UnicodeError:
                        result = {"allPassed": False, "checks": {"UTF8": False}, "details": {}}
                    row.update(allPassed=result["allPassed"], failedChecks=failed_names(result), details=result["details"])
                    if result["allPassed"]:
                        target.write_bytes(report)
                        row["accepted"] = True
                        summary["accepted"] += 1
                    else:
                        summary["failedChecks"] += 1
            with ledger.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            if row.get("technicalStop"):
                summary["technicalStops"] += 1
                consecutive += 1
                if consecutive >= args.max_consecutive_stops:
                    summary["halted"] = "CONSECUTIVE_STOPS"
                    break
            else:
                consecutive = 0
        print(json.dumps(dict(summary, status="DRY_RUN_PREPARED_ONLY" if not args.execute else "COMPLETE", providerCalls=summary["calls"])))
        return 0
    except rp.Stop as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
