"""Run the blind audit of a built v4 corpus through the Claude CLI: one tool-free turn per call, never retried; no oracle class reaches a request.

Calls (wording A only): `member` for every case shown alone, `pair` for every pair with the two members unlabelled in a seed-determined order, and `claim` for every gap
twin of an omitted-unknown or decoy pair, which shows the author's own why-no-fallback sentence against the twin. The questions are those of SPEC.md. Without --execute it only
writes the requests (no model call). With --execute it makes at most --max-calls calls; a call with any recorded outcome, including a stop, is never run again.

The route is the Claude CLI (`claude -p --tools ''` in a fresh empty directory), as for the Claude review arms: its isolation is configuration, not containment.

Usage: audit.py --claude-bin /abs/claude --model MODEL_ID --effort EFFORT --corpus DIR --workdir NEW_DIR [--max-calls N] [--max-budget-usd X] [--execute]
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent.parent
sys.path.insert(0, str(HERE))
import audit_parse  # noqa: E402
import audit_prompts  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rpc = load("audit_run_pilot_claude", PARENT / "run_pilot_claude.py")
s4 = load("audit_score_v4", HERE.parent / "score_v4.py")
rp = rpc.rp
ROUTE = "claude-cli-audit"
GAP_KINDS = ("omitted_unknown", "decoy_pair")


def schedule(corpus):
    """[(call id, call type, subject, request)] for wording A, in a seed-determined order that does not follow kind, family or class."""
    seed = corpus.manifest["authoring"]["seedSha256"]
    oracle = corpus.oracle
    sources_of = lambda case: {r["id"]: corpus.lines(case, r["id"]) for r in oracle[case]["sources"]}
    calls = []
    pairs = {}
    for case, record in oracle.items():
        if record["wording"] != "A":
            continue
        pairs.setdefault(record["pair"], {})[record["role"]] = case
        calls.append((f"member:{case}", "member", case, audit_prompts.member_request(sources_of(case))))
        if record["role"] == "changed" and record["kind"] in GAP_KINDS:
            calls.append((f"claim:{case}", "claim", case, audit_prompts.claim_request(sources_of(case), record["whyNoFallback"])))
    for pair, cases in sorted(pairs.items()):
        calls.append((f"pair:{pair}", "pair", pair, audit_prompts.pair_request(seed, pair, sources_of(cases["sound"]), sources_of(cases["changed"]))))
    return sorted(calls, key=lambda c: hashlib.sha256(f"{seed}|audit-call-order|{c[0]}".encode()).hexdigest())


def run_call(args, call_id, call_type, request, work, empty_mcp):
    attempt = work / ("attempts" if args.execute else "dry-requests") / call_id.replace(":", "_")
    cwd = attempt / "cwd"
    cwd.mkdir(parents=True)
    (attempt / "request.txt").write_text(request, encoding="utf-8")
    if not args.execute:
        return None
    started = time.monotonic()
    try:
        done = subprocess.run(rpc.claude_command(args, empty_mcp, audit_prompts.system_prompt()), input=request, capture_output=True, text=True, cwd=str(cwd),
                              timeout=rpc.CALL_TIMEOUT_SECONDS, check=False)
    except subprocess.TimeoutExpired:
        return {"technicalStop": "WRAPPER_TIMEOUT", "wallSeconds": round(time.monotonic() - started, 2)}
    wall = round(time.monotonic() - started, 2)
    (attempt / "claude-output.json").write_text(done.stdout, encoding="utf-8")
    (attempt / "claude-stderr.txt").write_text(done.stderr[:20000], encoding="utf-8")
    try:
        payload = json.loads(done.stdout)
        rp.need(isinstance(payload, dict), "OUTPUT_NOT_OBJECT")
    except (ValueError, rp.Stop):
        return {"technicalStop": f"NO_JSON_OUTPUT:exit{done.returncode}", "wallSeconds": wall}
    row = {"wallSeconds": wall, "costUsd": payload.get("total_cost_usd"), "numTurns": payload.get("num_turns"), "safetyStops": payload.get("safety_stops"),
           "servedModels": rpc.served_models(payload), "route": ROUTE}
    if done.returncode != 0 or payload.get("is_error") or not isinstance(payload.get("result"), str):
        row["technicalStop"] = "CLAUDE_ERROR:" + str(payload.get("terminal_reason") or payload.get("subtype") or done.returncode)[:60]
        return row
    report = payload["result"]
    (attempt / "ANSWER.md").write_text(report, encoding="utf-8")
    row["reportSha256"] = rp.sha(report.encode("utf-8"))
    if payload.get("safety_stops"):
        row["technicalStop"] = f"SAFETY_INTERRUPTED:{payload.get('safety_stops')}"
        return row
    if not row["servedModels"] or not all(m.startswith(args.model) for m in row["servedModels"]):
        row["technicalStop"] = "MODEL_MISMATCH"
        return row
    try:
        row["answer"] = audit_parse.parse(report, call_type)
    except audit_parse.AuditParseError as error:
        row["technicalStop"] = "UNPARSEABLE_ANSWER:" + str(error)
    return row


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--claude-bin", required=True)
    parser.add_argument("--model", required=True, help="exact model id; no default and no fallback")
    parser.add_argument("--effort", required=True, choices=rpc.EFFORTS)
    parser.add_argument("--corpus", required=True, help="a built v4 corpus directory (build_corpus.py output)")
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--max-calls", type=int, default=1000000)
    parser.add_argument("--max-budget-usd", type=float, default=1.0, help="per-call spend cap passed to the CLI")
    parser.add_argument("--max-consecutive-stops", type=int, default=3)
    parser.add_argument("--execute", action="store_true", help="make live model calls; without it only write the requests")
    args = parser.parse_args(argv)
    try:
        binary = Path(args.claude_bin)
        rp.need(binary.is_absolute() and binary.is_file() and os.access(binary, os.X_OK), "CLAUDE_BIN_INVALID")
        work = Path(args.workdir).resolve()
        rp.need(rp.ROOT not in work.parents and work != rp.ROOT, "WORKDIR_INSIDE_REPOSITORY")
        corpus = s4.Corpus(Path(args.corpus).resolve())
        rp.need(not corpus.legacy, "NOT_A_V4_CORPUS")
        calls = schedule(corpus)
        version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=60, check=False)
        rp.need(version.returncode == 0 and version.stdout.strip(), "CLAUDE_VERSION_FAILED")
        work.mkdir(parents=True, exist_ok=True)
        empty_mcp = work / "empty-mcp.json"
        empty_mcp.write_text('{"mcpServers": {}}\n', encoding="utf-8")
        ledger = work / "audit-answers.jsonl"
        done = {json.loads(l)["call"] for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()} if ledger.is_file() else set()
        stamp = {"route": ROUTE, "requestedModel": args.model, "effort": args.effort, "claudeVersion": version.stdout.strip(),
                 "systemPromptSha256": rp.sha(audit_prompts.system_prompt().encode("utf-8")), "corpusManifestSha256": rp.sha((Path(args.corpus) / "manifest.json").read_bytes())}
        summary = {"callsScheduled": len(calls), "prepared": 0, "executed": 0, "stopped": 0, "alreadyRecorded": 0}
        consecutive = 0
        for call_id, call_type, subject, request in calls:
            if call_id in done:
                summary["alreadyRecorded"] += 1
                continue
            if args.execute and summary["executed"] >= args.max_calls:
                break
            if args.execute and (work / "attempts" / call_id.replace(":", "_")).exists():
                row = {"technicalStop": "INTERRUPTED_UNKNOWN_STATE"}
            else:
                try:
                    row = run_call(args, call_id, call_type, request, work, empty_mcp)
                except (rp.Stop, OSError, subprocess.SubprocessError) as error:
                    row = {"technicalStop": str(error) if isinstance(error, rp.Stop) else type(error).__name__}
                if row is None:
                    summary["prepared"] += 1
                    continue
            row.update(stamp)
            row.update({"call": call_id, "type": call_type, "subject": subject, "requestSha256": rp.sha(request.encode("utf-8"))})
            with ledger.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            summary["executed"] += 1
            if row.get("technicalStop"):
                summary["stopped"] += 1
                consecutive += 1
                if consecutive >= args.max_consecutive_stops:
                    summary["halted"] = "CONSECUTIVE_STOPS"
                    break
            else:
                consecutive = 0
        print(json.dumps(dict(summary, status="COMPLETE" if args.execute else "DRY_RUN_PREPARED_ONLY", route=ROUTE, providerCalls=summary["executed"])))
        return 0
    except rp.Stop as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error)}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
