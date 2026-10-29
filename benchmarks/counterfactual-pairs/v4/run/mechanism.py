"""The blind mechanism reading of the preregistration: build reading items from a run directory, read them, and turn the answers into the scorer's judgments. Needs the full
corpus (the oracle's decisive-fact text), so it runs where the sealed text lives; the reader sees a decisive-fact description and one report, never the arm, route, trial or case.

  build   --corpus DIR --run-manifest FILE --workdir DIR --out DIR      items/<item>.json (decisive fact and report) and key.json (item to route/arm/trial/case); keep the key away from the reader
  read    --items DIR --claude-bin BIN --model ID --effort E --out FILE one tool-free Claude turn per item, no retry; answers.jsonl
  ingest  --key FILE --answers FILE OUTPUT_JSON                          the judgments list for analyze_v4.py --judgments

Items: every twin whose verdict is the right one in trial 1 of every arm, and every twin whose verdict differs between trials of the same arm. A model reading is not a human one, and
a Claude reader is not independent of the Claude arms; it feeds no headline rate.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
LABELS = ("NAMED", "NOT_NAMED", "WRONG_MECHANISM")
SYSTEM = ("You are reading one review of a plan. You have no tools. Decide only whether the review names the stated decisive fact; judge the review's text, not the plan.")
QUESTION = """DECISIVE FACT (what makes the plan wrong or unestablished):
{fact}

REVIEW:
{report}

Does the review name the decisive fact, as the reason for its verdict or for one of its findings? Wording may differ; a review that only says the plan is risky, or names a different problem, does not.
Answer with exactly one line: LABEL: NAMED, LABEL: NOT_NAMED (it names no such thing) or LABEL: WRONG_MECHANISM (it blocks or flags the plan for a different reason, and not this one).
"""


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rv = load("v4mech_run_v4", HERE / "run_v4.py")
sv = load("v4mech_score_v4", V4 / "score_v4.py")
rp = rv.rp
sha = rv.sha


def report_text(work, route, arm, trial, case):
    attempt = rv.attempt_dir(work, route, arm, trial) / "attempts" / case
    return (attempt / ("REVIEW.md" if route == "claude" else "GEMINI-REVIEW.md")).read_text(encoding="utf-8")


def build(corpus_dir, run_manifest, workdir, out):
    work, out = Path(workdir), Path(out)
    rp.need(not out.exists() or not any(out.iterdir()), "OUT_MUST_BE_NEW")
    run = rv.load_run_manifest(run_manifest)
    oracle = sv.Corpus(corpus_dir).oracle
    ledgers = {}
    for route in rv.ARMS:
        for ledger in sorted(work.glob(f"responses-{route}-*-trial*.jsonl")):
            for line in ledger.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    ledgers.setdefault((route, row["arm"]), {}).setdefault(row["trial"], {})[row["case"]] = row
    wanted = {}
    for (route, arm), trials in ledgers.items():
        for trial, rows in trials.items():
            for case, row in rows.items():
                truth = oracle[case]
                if row.get("technicalStop") or truth["role"] != "changed":
                    continue
                right = sv.RANK[row["assessment"]] == {"DEFECT": 2, "UNCERTAIN": 1}[truth["expectedClass"]]
                other = [t[case] for tt, t in trials.items() if tt != trial and case in t and not t[case].get("technicalStop")]
                disagree = any(o["assessment"] != row["assessment"] for o in other)
                if (trial == 1 and right) or disagree:
                    wanted[(route, arm, trial, case)] = truth
    (out / "items").mkdir(parents=True)
    key = {}
    for (route, arm, trial, case), truth in sorted(wanted.items(), key=lambda kv: sha(("|".join(map(str, kv[0])) + run["sha256"]).encode())):
        item = sha(("|".join(map(str, (route, arm, trial, case))) + "|item").encode())[:10]
        (out / "items" / f"{item}.json").write_text(json.dumps({"item": item, "decisiveFact": truth["mechanism"], "report": report_text(work, route, arm, trial, case)}, indent=1) + "\n", encoding="utf-8")
        key[item] = {"route": route, "arm": arm, "trial": trial, "case": case}
    (out / "key.json").write_text(json.dumps(key, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": "BUILT", "items": len(key), "providerCalls": 0}))
    return 0


def read(items, claude_bin, model, effort, out):
    rpc = rv.rpc
    items, out = Path(items), Path(out)
    args = SimpleNamespace(claude_bin=claude_bin, model=model, effort=effort, max_budget_usd=1.0)
    empty = out.parent / "empty-mcp.json"
    empty.write_text('{"mcpServers": {}}\n', encoding="utf-8")
    done = {json.loads(l)["item"] for l in out.read_text(encoding="utf-8").splitlines() if l.strip()} if out.exists() else set()
    for path in sorted((items / "items").glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data["item"] in done:
            continue
        cwd = out.parent / "reader-cwd" / data["item"]
        cwd.mkdir(parents=True)
        run = subprocess.run(rpc.claude_command(args, empty, SYSTEM), input=QUESTION.format(fact=data["decisiveFact"], report=data["report"]), capture_output=True, text=True,
                             cwd=str(cwd), timeout=600, check=False)
        label, error = None, None
        try:
            payload = json.loads(run.stdout)
            lines = [l.strip() for l in payload["result"].splitlines() if l.strip()]
            label = lines[-1].split(":", 1)[1].strip() if lines and lines[-1].startswith("LABEL:") else None
        except (ValueError, KeyError, TypeError):
            error = "NO_JSON"
        with out.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"item": data["item"], "label": label if label in LABELS else None, "error": error or (None if label in LABELS else "NO_LABEL")}) + "\n")
    print(json.dumps({"status": "READ", "answers": str(out)}))
    return 0


def ingest(key_file, answers_file):
    key = json.loads(Path(key_file).read_text(encoding="utf-8"))
    judgments = []
    for line in Path(answers_file).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        answer = json.loads(line)
        if answer.get("label") in LABELS and answer["item"] in key:
            judgments.append(dict(key[answer["item"]], label=answer["label"], namesMechanism=answer["label"] == "NAMED"))
    return judgments


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    b = sub.add_parser("build")
    for flag in ("--corpus", "--run-manifest", "--workdir", "--out"):
        b.add_argument(flag, required=True)
    r = sub.add_parser("read")
    for flag in ("--items", "--claude-bin", "--model", "--out"):
        r.add_argument(flag, required=True)
    r.add_argument("--effort", required=True)
    i = sub.add_parser("ingest")
    i.add_argument("--key", required=True)
    i.add_argument("--answers", required=True)
    i.add_argument("output")
    args = parser.parse_args(argv)
    try:
        if args.command == "build":
            return build(args.corpus, args.run_manifest, args.workdir, args.out)
        if args.command == "read":
            return read(args.items, args.claude_bin, args.model, args.effort, args.out)
        Path(args.output).write_text(json.dumps(ingest(args.key, args.answers), indent=1) + "\n", encoding="utf-8")
        return 0
    except (rp.Stop, OSError, ValueError, KeyError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, rp.Stop) else type(error).__name__}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
