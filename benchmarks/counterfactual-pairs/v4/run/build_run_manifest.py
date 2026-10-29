"""Write or check the frozen run manifest of the v4 reviewer run: what binds the corpus, the schedule, the reviewer files, the drivers and the preregistration; no model calls.

The manifest is written at the freeze, after the preregistration is final: it pins that file's hash, so any later edit breaks the check. Until then `--write` is for rehearsal
(the dev split) and tests. The Gemini runtime package and `agy` binary are the ones of the v3 Gemini run (v3-run-gemini/manifest.json), re-checked against the tree on disk.

Usage: build_run_manifest.py --split dev|test (--write FILE | --check FILE | --print)
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
PAIRS = V4.parent
REPO = PAIRS.parent.parent
PIN_FILES = ["benchmarks/counterfactual-pairs/v4/review/PREREGISTRATION.md", "benchmarks/counterfactual-pairs/v4/review/manifest.json",
             "benchmarks/counterfactual-pairs/v4/review/prompt.txt", "benchmarks/counterfactual-pairs/v4/review/format-suffix.txt",
             "benchmarks/counterfactual-pairs/v4/review/bare-request.txt", "benchmarks/counterfactual-pairs/v4/review/bare-reference-lead.txt",
             "benchmarks/counterfactual-pairs/v4/review/review_requests.py",
             "benchmarks/counterfactual-pairs/v4/run/schedule.py", "benchmarks/counterfactual-pairs/v4/run/run_v4.py",
             "benchmarks/counterfactual-pairs/v4/run/verify_v4.py", "benchmarks/counterfactual-pairs/v4/run/analyze_v4.py",
             "benchmarks/counterfactual-pairs/v4/run/mechanism.py", "benchmarks/counterfactual-pairs/v4/parse_v4.py",
             "benchmarks/counterfactual-pairs/v4/score_v4.py", "benchmarks/counterfactual-pairs/run_pilot.py",
             "benchmarks/counterfactual-pairs/run_pilot_claude.py", "benchmarks/counterfactual-pairs/run_gemini_v3.py"]
CLAUDE = {"model": "claude-opus-5-5", "effort": "high", "arms": ["skill", "skill-go"], "trials": 2}
GEMINI_ARMS = ["skill", "bare"]


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha(data):
    return hashlib.sha256(data).hexdigest()


def corpus_sha(split):
    if split == "test":
        return json.loads((V4 / "test-audit-revision" / "sealed-manifest-final.json").read_bytes())["manifestSha256"]
    return sha((V4 / "dev" / "manifest.json").read_bytes())


def build(split):
    v3 = json.loads((PAIRS / "v3-run-gemini" / "manifest.json").read_bytes())
    gem = load("brm_run_gemini_v3", PAIRS / "run_gemini_v3.py")
    tree = gem.runtime_tree_sha(REPO / "runtime" / "flash-high")
    if tree != v3["runtime"]["treeSha256"]:
        raise ValueError("RUNTIME_TREE_CHANGED")
    rpc = load("brm_run_pilot_claude", PAIRS / "run_pilot_claude.py")
    schedule = (HERE / f"schedule-{split}.json").read_bytes()
    return {"kind": "V4_RUN_FROZEN", "split": split, "corpus": {"manifestSha256": corpus_sha(split)}, "scheduleSha256": sha(schedule),
            "routes": {"claude": dict(CLAUDE, systemPromptSha256=sha(rpc.SYSTEM_PROMPT.encode("utf-8"))),
                       "gemini": {"arms": GEMINI_ARMS, "trials": 1, "runtime": v3["runtime"], "binary": v3["binary"],
                                  "persona": "preflight-inline (fixed by the runtime, identical for every arm)"}},
            "parser": {"skill-style": "parse_v4 with a line field written [S02:5] read as S02:5 (recorded on the row)", "bare": "last non-empty line is one VERDICT line"},
            "pins": {name: sha((REPO / name).read_bytes()) for name in PIN_FILES}, "providerCalls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write")
    group.add_argument("--check")
    group.add_argument("--print", action="store_true")
    args = parser.parse_args(argv)
    try:
        text = json.dumps(build(args.split), indent=1) + "\n"
    except (ValueError, OSError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, ValueError) else type(error).__name__}))
        return 1
    if args.write:
        Path(args.write).write_text(text, encoding="utf-8")
    elif args.check:
        same = Path(args.check).is_file() and Path(args.check).read_text(encoding="utf-8") == text
        print(json.dumps({"status": "PASS" if same else "FAIL", "providerCalls": 0}))
        return 0 if same else 1
    else:
        print(text, end="")
        return 0
    print(json.dumps({"status": "WRITTEN", "sha256": sha(text.encode("utf-8")), "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
