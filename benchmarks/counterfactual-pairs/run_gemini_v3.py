"""Run corpus v3 through the qualified native flash-high route under a frozen run manifest, one native turn per case.

A thin, separate driver around run_pilot.py (which is not modified, so the evidence recorded with it stays tied to unchanged code). What it
adds: the run is bound to v3-run-gemini/manifest.json (corpus, runtime package, binary identity, parser, preregistration); the report parser
reads a snapshot label 'S01:<n>' in a FINDING's line field as line n (the one relaxation the Gemini pilot's four format stops motivated,
fixed in the preregistration and recorded on every row that used it); every ledger row is stamped. Everything else is run_pilot's: the
frozen prompt, the inline numbered snapshot, prepare, byte-verified seed copy, exactly one native turn, no retry, recorded stops, resume.

Without --execute it only prepares (no model, no agy turn). The oracle is never read here.

Usage:
  run_gemini_v3.py --runtime-dir runtime/flash-high --capabilities DIR --qualification FILE --workdir NEW_DIR
                   --corpus benchmarks/counterfactual-pairs/v3 --run-manifest benchmarks/counterfactual-pairs/v3-run-gemini/manifest.json [--trial N] [--execute]
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rp = load("run_pilot_for_gemini_v3", HERE / "run_pilot.py")
rl = load("reparse_lenient_for_gemini_v3", HERE / "reparse_lenient.py")
ROOT = rp.ROOT
ROUTE = "native-flash-high"
PARSER = "snapshot-label-tolerant"
STRICT_PARSE = rp.parse_report


def tolerant_parse(text):
    """run_pilot.parse_report with the single preregistered relaxation; marks a row whose finding used it."""
    relaxed = rl.lenient_text(text)
    parsed = STRICT_PARSE(relaxed)
    if relaxed != text:
        parsed["snapshotLabelRead"] = True
    return parsed


def runtime_tree_sha(directory):
    """One hash over every file of a runtime package (path and bytes), so a changed script or asset is detected."""
    digest = hashlib.sha256()
    for path in sorted(Path(directory).rglob("*")):
        if path.is_symlink():
            raise rp.Stop("SYMLINK_IN_RUNTIME")
        if path.is_file() and "__pycache__" not in path.parts:
            digest.update(str(path.relative_to(directory)).encode("utf-8") + b"\0" + hashlib.sha256(path.read_bytes()).digest())
    return digest.hexdigest()


def load_run(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    manifest = json.loads(data)
    rp.need(manifest.get("kind") == "V3_GEMINI_RUN_FROZEN", "RUN_MANIFEST_KIND")
    for filename, expected in manifest["pins"].items():
        target = path.parent / filename
        rp.need(target.is_file() and rp.sha(target.read_bytes()) == expected, "RUN_PIN_MISMATCH:" + filename)
    manifest["sha256"] = rp.sha(data)
    return manifest


def check_identity(run, runtime, capabilities, corpus_manifest_sha):
    """Everything that can be bound before a model turn: corpus, runtime package, route, and the frozen binary the capabilities probe recorded."""
    rp.need(corpus_manifest_sha == run["corpus"]["manifestSha256"], "RUN_CORPUS_MISMATCH")
    rp.need(runtime.name == "flash-high" and run["runtime"]["profile"] is None, "RUN_RUNTIME_NOT_FLASH_HIGH")
    rp.need(runtime_tree_sha(runtime) == run["runtime"]["treeSha256"], "RUN_RUNTIME_TREE_MISMATCH")
    try:
        caps = json.loads((Path(capabilities) / "RESULT.json").read_bytes())
    except (OSError, ValueError):
        raise rp.Stop("CAPABILITIES_UNREADABLE")
    rp.need(caps.get("status") == "PASS_METADATA_CAPABILITIES_ONLY" and caps.get("binaryStable") is True, "CAPABILITIES_NOT_PASS")
    rp.need(caps.get("frozenBinary", {}).get("sha256") == run["binary"]["sha256"], "RUN_BINARY_MISMATCH")
    rp.need(run["binary"]["versionContains"] in str(caps.get("observedVersion")), "RUN_BINARY_VERSION_MISMATCH")
    rp.need(caps.get("model") == run["runtime"]["model"] and caps.get("effort") == run["runtime"]["effort"], "RUN_MODEL_MISMATCH")
    return caps


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--runtime-dir", required=True)
    parser.add_argument("--capabilities", required=True)
    parser.add_argument("--qualification", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--trial", type=int, default=1)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--run-manifest", required=True)
    parser.add_argument("--execute", action="store_true", help="make live native calls; without it only prepare")
    parser.add_argument("--max-consecutive-stops", type=int, default=3)
    args = parser.parse_args(argv)
    args.runtime_profile = None
    try:
        runtime = Path(args.runtime_dir).resolve()
        rp.need((runtime / "scripts/cli_review.py").is_file(), "RUNTIME_MISSING")
        args.inline_evidence = True
        work = Path(args.workdir).resolve()
        rp.need(ROOT not in work.parents and work != ROOT, "WORKDIR_INSIDE_REPOSITORY")
        corpus = Path(args.corpus).resolve()
        score = rp.load_module("score", HERE / "score.py")
        manifest, _ = score.load_frozen(corpus)
        prompt = (corpus / "prompt.txt").read_bytes().decode("utf-8")
        run = load_run(args.run_manifest)
        caps = check_identity(run, runtime, args.capabilities, rp.sha((corpus / "manifest.json").read_bytes()))
        rp.parse_report = tolerant_parse  # run_case looks the parser up at call time
        trial_dir = work / f"trial{args.trial}"
        ledger = work / f"responses-trial{args.trial}.jsonl"
        work.mkdir(parents=True, exist_ok=True)
        done = rp.recorded(ledger)
        consecutive = 0
        stamp = {"route": ROUTE, "parser": PARSER, "runManifestSha256": run["sha256"], "binarySha256": caps["frozenBinary"]["sha256"]}
        summary = {"prepared": 0, "executed": 0, "stopped": 0, "skippedAlreadyRecorded": 0, "route": ROUTE, "parser": PARSER,
                   "runManifestSha256": run["sha256"]}
        for case in manifest["submissionOrder"]:
            if case in done:
                summary["skippedAlreadyRecorded"] += 1
                continue
            if args.execute and (trial_dir / "attempts" / case).exists():
                row = {"technicalStop": "INTERRUPTED_UNKNOWN_STATE"}  # zero retries: record, never rerun
            else:
                snapshot = (corpus / "packets" / (case + ".txt")).read_bytes()
                try:
                    row = rp.run_case(args, case, prompt, snapshot, trial_dir)
                except (rp.Stop, OSError, subprocess.SubprocessError) as error:
                    reason = str(error) if isinstance(error, rp.Stop) else type(error).__name__
                    if not args.execute:
                        print(json.dumps(dict(summary, status="DRY_RUN_STOPPED", case=case, reason=reason)))
                        return 1
                    row = {"technicalStop": reason}
                if row is None:
                    summary["prepared"] += 1
                    continue
            row.update(stamp)
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
    except (rp.Stop, OSError, ValueError, KeyError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, rp.Stop) else type(error).__name__}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
