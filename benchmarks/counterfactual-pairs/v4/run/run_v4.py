"""Run corpus v4 through a reviewer route in small, resumable blocks, one turn per case, under a frozen run manifest. Never parses the oracle (it only verifies the corpus pins, which include the oracle's hash).

Routes: `claude` (the Claude CLI, tools disabled; arms skill, skill-go, bare) and `gemini` (the qualified native flash-high runtime; arms skill, bare). The schedule
(schedule.py) says which (block, arm, trial) comes next; this driver finds the first step of the route that is not complete, runs its unrecorded cases in the corpus's
frozen submission order, and stops at a case boundary. A recorded case, including a stop, is never run again: zero retries. A case directory with no ledger row is recorded
as INTERRUPTED_UNKNOWN_STATE. State lives only in the workdir (ledgers, attempts, blocks.jsonl), so a run can be paused for days and continued by any session that has it.

It makes live calls only with --execute, and only as many as --steps, --max-cases and --max-minutes allow. It also stops at a case boundary when the host load is above
--max-load, when the stop file exists, after --max-consecutive-stops stops in a row, or when --max-total-usd is spent. It runs at low CPU and I/O priority.

Commands:
  status  --route R --workdir W --split S                          progress, next step, measured cost per block
  next    --route R --workdir W --split S --corpus DIR --run-manifest FILE [route options] [--execute] [--steps N] [--max-cases N] [--max-minutes M]
  bundle  --workdir W --out FILE.tar.gz                            the evidence to hand back (ledgers, requests, reports, receipts, block log)
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import time
from types import SimpleNamespace

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
PAIRS = V4.parent
REVIEW = V4 / "review"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rpc = load("v4run_run_pilot_claude", PAIRS / "run_pilot_claude.py")
rp = rpc.rp
rr = load("v4run_review_requests", REVIEW / "review_requests.py")
pv4 = load("v4run_parse_v4", V4 / "parse_v4.py")
sch = load("v4run_schedule", HERE / "schedule.py")
ROOT = rp.ROOT
ARMS = {"claude": ("skill", "skill-go", "bare"), "gemini": ("skill", "bare")}
ROUTE_LABELS = {"claude": "claude-cli", "gemini": "native-flash-high"}
STOP_FILE = "STOP"
LABEL_BRACKETS = re.compile(r"\[(S[0-9]{2}:[0-9]+)\]")
DEFAULT_RESERVE = {"claude": 120.0, "gemini": 600.0}


class Halt(Exception):
    """A clean stop between cases; carries the reason."""


def sha(data):
    return hashlib.sha256(data).hexdigest()


# ---------------------------------------------------------------- frozen files

def load_run_manifest(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    manifest = json.loads(data)
    rp.need(manifest.get("kind") == "V4_RUN_FROZEN", "RUN_MANIFEST_KIND")
    for name, expected in manifest["pins"].items():
        target = ROOT / name
        rp.need(target.is_file() and sha(target.read_bytes()) == expected, "RUN_PIN_MISMATCH:" + name)
    manifest["sha256"] = sha(data)
    return manifest


def load_corpus(path):
    """Verify every pin of the corpus manifest; return the manifest and a function from case to {source: lines}. Parses no oracle."""
    corpus = Path(path).resolve()
    manifest = json.loads((corpus / "manifest.json").read_bytes())
    for name, expected in manifest["pins"].items():
        target = corpus / name
        rp.need(target.is_file() and sha(target.read_bytes()) == expected, "CORPUS_PIN_MISMATCH:" + name)

    def sources(case):
        found = {}
        for source in ("S01", "S02"):
            file = corpus / "packets" / case / f"{source}.txt"
            if file.is_file():
                found[source] = file.read_bytes().decode("utf-8").split("\n")[:-1]
        rp.need("S01" in found, "UNKNOWN_CASE:" + case)
        return found

    return corpus, manifest, sources


def load_schedule(path, run, corpus_manifest):
    data = Path(path).read_bytes()
    schedule = json.loads(data)
    rp.need(schedule.get("kind") == "V4_RUN_SCHEDULE", "SCHEDULE_KIND")
    rp.need(sha(data) == run["scheduleSha256"], "SCHEDULE_NOT_THE_FROZEN_ONE")
    rp.need(set(schedule["submissionOrder"]) == set(corpus_manifest["submissionOrder"]), "SCHEDULE_CORPUS_MISMATCH")
    return schedule


def tolerant_parse(text):
    """parse_v4.parse_report with the one preregistered relaxation: a line field written `[S02:5]` is read as `S02:5`; the row records it."""
    relaxed = LABEL_BRACKETS.sub(r"\1", text)
    try:
        parsed = pv4.parse_report(relaxed)
    except pv4.Stop as error:  # parse_v4 loads its own copy of run_pilot, so its Stop is another class
        raise rp.Stop(str(error))
    if relaxed != text:
        parsed["bracketedLineFieldRead"] = True
    return parsed


def bare_parse(text):
    try:
        return rr.parse_bare(text)
    except ValueError as error:
        raise rp.Stop(str(error))


# ---------------------------------------------------------------- steps and ledgers

def route_steps(schedule, route, include_optional):
    steps = list(schedule["routes"][route]["steps"])
    if include_optional and route in schedule["optional"]:
        steps += [dict(s, optional=True, step=len(steps) + n) for n, s in enumerate(schedule["optional"][route]["steps"], 1)]
    return steps


def block_cases(schedule, block_id):
    for group in (schedule["blocks"], schedule["repeatBlocks"]):
        for block in group:
            if block["id"] == block_id:
                return block["cases"]
    raise rp.Stop("UNKNOWN_BLOCK")


def ledger_path(work, route, arm, trial):
    return work / f"responses-{route}-{arm}-trial{trial}.jsonl"


def attempt_dir(work, route, arm, trial):
    return work / f"{route}-{arm}-trial{trial}"


def step_state(work, schedule, route, step):
    """(recorded rows by case, cases of the block not yet recorded)."""
    done = rp.recorded(ledger_path(work, route, step["arm"], step["trial"]))
    cases = block_cases(schedule, step["block"])
    return done, [c for c in cases if c not in done]


def next_step(work, schedule, route, include_optional):
    for step in route_steps(schedule, route, include_optional):
        if step_state(work, schedule, route, step)[1]:
            return step
    return None


def read_blocks(work):
    path = work / "blocks.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()] if path.is_file() else []


def status(work, schedule, route, include_optional=False):
    steps = route_steps(schedule, route, include_optional)
    finished = [s for s in steps if not step_state(work, schedule, route, s)[1]]
    pending = next_step(work, schedule, route, include_optional)
    log = [row for row in read_blocks(work) if row["route"] == route]
    cases = sum(row["casesRecorded"] for row in log)
    wall = sum(row["wallSeconds"] for row in log)
    stops = sum(row["stops"] for row in log)
    out = {"route": route, "stepsTotal": len(steps), "stepsComplete": len(finished), "next": pending,
           "casesRecordedInBlockRuns": cases, "stopsInBlockRuns": stops,
           "meanSecondsPerCase": round(wall / cases, 1) if cases else None,
           "totalCostUsd": round(sum(row.get("costUsd") or 0 for row in log), 4),
           "peakChildRssKb": max((row.get("peakChildRssKb") or 0 for row in log), default=0),
           "maxLoadAtStart": max((row.get("loadAvgStart") or 0 for row in log), default=0)}
    if pending:
        todo = step_state(work, schedule, route, pending)[1]
        out["nextStepCasesLeft"] = len(todo)
        if out["meanSecondsPerCase"]:
            out["nextStepEstimateMinutes"] = round(len(todo) * out["meanSecondsPerCase"] / 60, 1)
    return out


# ---------------------------------------------------------------- one case

def prepare_arm(route, arm, args):
    """(system prompt, request builder, parser) for an arm of a route."""
    if route == "claude":
        system = (rr.ABLATION / "bare-system.txt").read_text(encoding="utf-8").rstrip("\n") if arm == "bare" else rpc.SYSTEM_PROMPT
        return system, bare_parse if arm == "bare" else tolerant_parse
    return None, bare_parse if arm == "bare" else tolerant_parse


def claude_case(args, case, sources, request, work, arm, trial, empty_mcp, system, parse):
    trial_dir = attempt_dir(work, "claude", arm, trial)
    trial_dir.mkdir(parents=True, exist_ok=True)
    arm_spec = {"name": arm, "system": system, "build": lambda prompt, lines: request, "parse": parse}
    snapshot = ("\n".join(sources["S01"]) + "\n").encode("utf-8")
    return rpc.run_case(args, case, "", snapshot, trial_dir, empty_mcp, arm_spec)


def write_packet(directory, request, sources):
    """A native packet: the request is the prompt (the runtime sends exactly its bytes), the sources are listed as files, identical for every arm."""
    (directory / "snapshots").mkdir(parents=True)
    (directory / "prompt.txt").write_bytes(request)
    rows = []
    for source in sorted(sources):
        body = ("\n".join(sources[source]) + "\n").encode("utf-8")
        (directory / "snapshots" / f"{source}.txt").write_bytes(body)
        rows.append({"id": source, "path": f"snapshots/{source}.txt", "sha256": sha(body), "bytes": len(body)})
    descriptor = {"schemaVersion": 1, "mode": "PLAN", "questions": ["Q01"],
                  "prompt": {"path": "prompt.txt", "sha256": sha(request), "bytes": len(request)}, "sources": rows}
    (directory / "PACKET.json").write_text(json.dumps(descriptor, indent=2) + "\n", encoding="utf-8")
    return directory / "PACKET.json"


def gemini_case(args, case, sources, request, work, arm, trial, parse, execute):
    trial_dir = attempt_dir(work, "gemini", arm, trial) if execute else work / "dry" / f"gemini-{arm}-trial{trial}"
    packet = write_packet(trial_dir / "packets" / case, request, sources)
    seed, attempt = trial_dir / "seeds" / case, trial_dir / "attempts" / case
    seed.parent.mkdir(parents=True, exist_ok=True)
    attempt.parent.mkdir(parents=True, exist_ok=True)
    prepare = rp.cli(args, "prepare", str(packet), str(Path(args.capabilities).resolve()), str(seed))
    done = subprocess.run(prepare, capture_output=True, text=True, timeout=300, check=False)
    rp.need(done.returncode == 0 and not (seed / "CLI-GATE.json").exists(), "PREPARE_FAILED")
    if not execute:
        return None
    shutil.copytree(seed, attempt, symlinks=True)
    rp.need(rp.inventory(seed) == rp.inventory(attempt), "SEED_COPY_MISMATCH")
    started = time.monotonic()
    live = rp.cli(args, "run", str(attempt), "--qualification", str(Path(args.qualification).resolve()), "--authorize-live")
    try:
        subprocess.run(live, capture_output=True, text=True, timeout=rp.RUN_TIMEOUT_SECONDS, check=False)
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
    row = {"reportSha256": sha(report), "wallSeconds": wall, "receiptSha256": sha((attempt / "CLI-RECEIPT.json").read_bytes())}
    try:
        row.update(parse(report.decode("utf-8")))
    except (rp.Stop, UnicodeError) as error:
        row["technicalStop"] = "UNPARSEABLE_REPORT:" + (str(error) if isinstance(error, rp.Stop) else "UNICODE")
    return row


# ---------------------------------------------------------------- resource guards

def lower_priority():
    """Best effort: nice 10 and idle I/O class, so a block yields to the owner's other work."""
    try:
        if os.nice(0) < 10:
            os.nice(10 - os.nice(0))
    except OSError:
        pass
    try:
        subprocess.run(["ionice", "-c3", "-p", str(os.getpid())], capture_output=True, timeout=10, check=False)
    except (OSError, subprocess.SubprocessError):
        pass


def child_usage():
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return usage.ru_utime + usage.ru_stime, usage.ru_maxrss


class Budget:
    def __init__(self, args, route):
        self.args, self.route = args, route
        self.started = time.monotonic()
        self.longest = 0.0
        self.cases = 0
        self.spent = 0.0
        self.consecutive = 0

    def check(self, work):
        """Raise Halt between cases when any guard says stop."""
        a = self.args
        if (work / STOP_FILE).exists() or (a.stop_file and Path(a.stop_file).exists()):
            raise Halt("STOP_FILE")
        if a.max_cases is not None and self.cases >= a.max_cases:
            raise Halt("MAX_CASES")
        reserve = max(self.longest * 1.5, DEFAULT_RESERVE[self.route])
        if a.max_minutes is not None and time.monotonic() - self.started + reserve >= a.max_minutes * 60:
            raise Halt("TIME_BUDGET")
        if a.max_total_usd is not None and self.spent >= a.max_total_usd:
            raise Halt("SPEND_CAP")
        if a.max_load is not None and os.getloadavg()[0] > a.max_load:
            raise Halt("HOST_LOAD")

    def note(self, row):
        self.cases += 1
        self.longest = max(self.longest, row.get("wallSeconds") or 0)
        self.spent += row.get("costUsd") or 0
        if row.get("technicalStop"):
            self.consecutive += 1
            if self.consecutive >= self.args.max_consecutive_stops:
                raise Halt("CONSECUTIVE_STOPS")
        else:
            self.consecutive = 0


# ---------------------------------------------------------------- next

def stamp_for(route, arm, run, args, request, extra):
    stamp = {"route": ROUTE_LABELS[route], "arm": arm, "runManifestSha256": run["sha256"], "requestSha256": sha(request), "requestBytes": len(request)}
    stamp.update(extra)
    return stamp


def run_next(args):
    route = args.route
    rp.need(route in ARMS, "UNKNOWN_ROUTE")
    work = Path(args.workdir).resolve()
    rp.need(ROOT not in work.parents and work != ROOT, "WORKDIR_INSIDE_REPOSITORY")
    run = load_run_manifest(args.run_manifest)
    rp.need(run["split"] == args.split, "RUN_SPLIT_MISMATCH")
    corpus, corpus_manifest, sources_of = load_corpus(args.corpus)
    rp.need(sha((corpus / "manifest.json").read_bytes()) == run["corpus"]["manifestSha256"], "RUN_CORPUS_MISMATCH")
    schedule = load_schedule(args.schedule or HERE / f"schedule-{args.split}.json", run, corpus_manifest)
    extra, system = {}, None
    if route == "claude":
        binary = Path(args.claude_bin)
        rp.need(binary.is_absolute() and binary.is_file() and os.access(binary, os.X_OK), "CLAUDE_BIN_INVALID")
        spec = run["routes"]["claude"]
        rp.need(args.model == spec["model"] and args.effort == spec["effort"], "RUN_MODEL_MISMATCH")
        version = subprocess.run([str(binary), "--version"], capture_output=True, text=True, timeout=60, check=False)
        rp.need(version.returncode == 0 and version.stdout.strip(), "CLAUDE_VERSION_FAILED")
        extra = {"requestedModel": args.model, "effort": args.effort, "claudeVersion": version.stdout.strip()}
        args.max_budget_usd = args.max_case_usd
    else:
        gem = load("v4run_gemini_identity", PAIRS / "run_gemini_v3.py")
        runtime = Path(args.runtime_dir).resolve()
        rp.need((runtime / "scripts/cli_review.py").is_file(), "RUNTIME_MISSING")
        spec = run["routes"]["gemini"]
        rp.need(runtime.name == "flash-high" and gem.runtime_tree_sha(runtime) == spec["runtime"]["treeSha256"], "RUN_RUNTIME_TREE_MISMATCH")
        caps = json.loads((Path(args.capabilities) / "RESULT.json").read_bytes())
        rp.need(caps.get("status") == "PASS_METADATA_CAPABILITIES_ONLY" and caps.get("binaryStable") is True, "CAPABILITIES_NOT_PASS")
        rp.need(caps.get("frozenBinary", {}).get("sha256") == spec["binary"]["sha256"], "RUN_BINARY_MISMATCH")
        rp.need(spec["binary"]["versionContains"] in str(caps.get("observedVersion")), "RUN_BINARY_VERSION_MISMATCH")
        rp.need(caps.get("model") == spec["runtime"]["model"] and caps.get("effort") == spec["runtime"]["effort"], "RUN_MODEL_MISMATCH")
        extra = {"binarySha256": caps["frozenBinary"]["sha256"]}
        args.runtime_profile = None
    work.mkdir(parents=True, exist_ok=True)
    if not args.execute:
        shutil.rmtree(work / "dry", ignore_errors=True)
    lower_priority()
    budget = Budget(args, route)
    summary = {"route": route, "execute": bool(args.execute), "runManifestSha256": run["sha256"], "blockRuns": [], "providerCallsFromThisScript": 0}
    empty_mcp = work / "empty-mcp.json"
    if route == "claude":
        empty_mcp.write_text('{"mcpServers": {}}\n', encoding="utf-8")
    reason = "NO_MORE_STEPS"
    for _ in range(args.steps):
        step = next_step(work, schedule, route, args.include_optional)
        if step is None:
            break
        arm, trial = step["arm"], step["trial"]
        rp.need(arm in ARMS[route], "ARM_NOT_ON_ROUTE")
        done, todo = step_state(work, schedule, route, step)
        system, parse = prepare_arm(route, arm, args)
        ledger = ledger_path(work, route, arm, trial)
        order = {c: n for n, c in enumerate(schedule["submissionOrder"])}
        record = {"runId": f"{int(time.time())}", "route": route, "arm": arm, "trial": trial, "block": step["block"], "step": step["step"], "execute": bool(args.execute),
                  "startedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"), "loadAvgStart": round(os.getloadavg()[0], 2), "casesRecorded": 0, "stops": 0,
                  "costUsd": 0.0, "dryCasesPrepared": 0}
        cpu0, _ = child_usage()
        t0 = time.monotonic()
        halted = None
        for case in sorted(todo, key=order.__getitem__):
            try:
                budget.check(work)
            except Halt as stop:
                halted = str(stop)
                break
            sources = sources_of(case)
            request = rr.build(arm, sources)
            rp.need(0 < len(request) <= 131072, "PROMPT_SIZE")
            stamp = stamp_for(route, arm, run, args, request, extra)
            if args.execute and (attempt_dir(work, route, arm, trial) / "attempts" / case).exists():
                row = {"technicalStop": "INTERRUPTED_UNKNOWN_STATE"}  # zero retries: record, never rerun
            else:
                try:
                    if route == "claude":
                        stamp["systemPromptSha256"] = sha(system.encode("utf-8"))
                        row = claude_case_dispatch(args, case, sources, request, work, arm, trial, empty_mcp, system, parse)
                    else:
                        row = gemini_case(args, case, sources, request, work, arm, trial, parse, args.execute)
                except (rp.Stop, OSError, subprocess.SubprocessError) as error:
                    reason_text = str(error) if isinstance(error, rp.Stop) else type(error).__name__
                    if not args.execute:
                        summary["dryRunStopped"] = {"case": case, "reason": reason_text}
                        print(json.dumps(summary))
                        return 1
                    row = {"technicalStop": reason_text}
                if row is None:
                    record["dryCasesPrepared"] += 1
                    continue
            row.update(stamp)
            row.update({"case": case, "trial": trial, "block": step["block"], "step": step["step"], "recordedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z")})
            with ledger.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(row, sort_keys=True) + "\n")
            record["casesRecorded"] += 1
            record["stops"] += bool(row.get("technicalStop"))
            record["costUsd"] = round(record["costUsd"] + (row.get("costUsd") or 0), 6)
            try:
                budget.note(row)
            except Halt as stop:
                halted = str(stop)
                break
        cpu1, rss = child_usage()
        record.update(endedAt=time.strftime("%Y-%m-%dT%H:%M:%S%z"), wallSeconds=round(time.monotonic() - t0, 1), loadAvgEnd=round(os.getloadavg()[0], 2),
                      childCpuSeconds=round(cpu1 - cpu0, 1), peakChildRssKb=rss, stoppedBecause=halted, stepComplete=not step_state(work, schedule, route, step)[1])
        if args.execute and (record["casesRecorded"] or halted):
            with (work / "blocks.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, sort_keys=True) + "\n")
        summary["blockRuns"].append(record)
        if halted:
            reason = halted
            break
        reason = "STEPS_DONE"
        if not args.execute:
            break  # a dry run records nothing, so the same step would come up again
    summary["stoppedBecause"] = reason
    summary["status"] = "COMPLETE" if args.execute else "DRY_RUN_PREPARED_ONLY"
    print(json.dumps(summary))
    return 0 if reason not in ("CONSECUTIVE_STOPS",) else 1


def claude_case_dispatch(args, case, sources, request, work, arm, trial, empty_mcp, system, parse):
    """Dry runs write their request files under work/dry, never into the attempts of a live run."""
    if not args.execute:
        dry = work / "dry" / f"claude-{arm}-trial{trial}"
        dry.mkdir(parents=True, exist_ok=True)
        cwd = dry / "dry-requests" / case
        cwd.mkdir(parents=True)
        (cwd / "request.txt").write_bytes(request)
        return None
    return claude_case(args, case, sources, request, work, arm, trial, empty_mcp, system, parse)


# ---------------------------------------------------------------- bundle

def redacted_ledger(path):
    """A ledger without plan text: each finding's quotation is replaced by its hash and length."""
    lines = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        for finding in row.get("findings", []):
            quote = finding.pop("quote", "")
            finding["quoteSha256"], finding["quoteChars"] = sha(quote.encode("utf-8")), len(quote)
        lines.append(json.dumps(row, sort_keys=True))
    return ("\n".join(lines) + "\n").encode("utf-8")


def bundle(args):
    work = Path(args.workdir).resolve()
    out = Path(args.out).resolve()
    rp.need(work.is_dir() and ROOT not in out.parents, "BAD_PATHS")
    if args.redacted:
        import io
        names = []
        with tarfile.open(out, "w:gz") as tar:
            for path in sorted(work.glob("responses-*.jsonl")) + [work / "blocks.jsonl"]:
                if not path.is_file():
                    continue
                data = redacted_ledger(path) if path.name.startswith("responses-") else path.read_bytes()
                info = tarfile.TarInfo(path.name)
                info.size = len(data)
                tar.addfile(info, io.BytesIO(data))
                names.append(path.name)
            for receipt in sorted(work.glob("gemini-*/attempts/*/CLI-RECEIPT.json")):
                tar.add(receipt, arcname=str(receipt.relative_to(work)))
                names.append(str(receipt.relative_to(work)))
        print(json.dumps({"status": "BUNDLED_REDACTED", "files": len(names), "archive": str(out), "sha256": sha(out.read_bytes())}))
        return 0
    keep = []
    for path in sorted(work.rglob("*")):
        rel = path.relative_to(work)
        if not path.is_file() or rel.parts[0] == "dry" or "cwd" in rel.parts or "seeds" in rel.parts or "packets" in rel.parts:
            continue
        if path.name in ("claude-stderr.txt",) or path.suffix in (".jsonl", ".json", ".md", ".txt") or rel.name == "CLI-RECEIPT.json":
            keep.append(path)
    with tarfile.open(out, "w:gz") as tar:
        for path in keep:
            tar.add(path, arcname=str(path.relative_to(work)))
    print(json.dumps({"status": "BUNDLED", "files": len(keep), "archive": str(out), "sha256": sha(out.read_bytes())}))
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("status", "next"):
        p = sub.add_parser(name)
        p.add_argument("--route", required=True, choices=sorted(ARMS))
        p.add_argument("--workdir", required=True, help="outside the repository; reused to resume")
        p.add_argument("--split", required=True, choices=("dev", "test"))
        p.add_argument("--schedule", help="default: schedule-<split>.json beside this file")
        p.add_argument("--include-optional", action="store_true", help="include the optional repeat steps (needs the owner's approval)")
    nxt = sub.choices["next"]
    nxt.add_argument("--corpus", required=True)
    nxt.add_argument("--run-manifest", required=True)
    nxt.add_argument("--execute", action="store_true", help="make live calls; without it only build the requests")
    nxt.add_argument("--steps", type=int, default=1, help="block-runs to do in this invocation (default 1)")
    nxt.add_argument("--max-cases", type=int, help="stop after this many cases in this invocation")
    nxt.add_argument("--max-minutes", type=float, help="do not start a case that could end after this many minutes")
    nxt.add_argument("--max-load", type=float, default=1.5, help="stop between cases when the 1-minute load average exceeds this (default 1.5)")
    nxt.add_argument("--stop-file", help="stop between cases when this file exists (the workdir's STOP file always works)")
    nxt.add_argument("--max-total-usd", type=float, help="claude: stop after this spend in this invocation")
    nxt.add_argument("--max-case-usd", type=float, default=1.0, help="claude: per-case spend cap passed to the CLI")
    nxt.add_argument("--max-consecutive-stops", type=int, default=3)
    nxt.add_argument("--claude-bin")
    nxt.add_argument("--model")
    nxt.add_argument("--effort", choices=rpc.EFFORTS)
    nxt.add_argument("--runtime-dir")
    nxt.add_argument("--capabilities")
    nxt.add_argument("--qualification")
    bun = sub.add_parser("bundle")
    bun.add_argument("--workdir", required=True)
    bun.add_argument("--out", required=True)
    bun.add_argument("--redacted", action="store_true", help="ledgers with quotations hashed, block log and receipts only; no reports, requests or plan text (safe to hand to a session that must not see sealed text)")
    args = parser.parse_args(argv)
    try:
        if args.command == "bundle":
            return bundle(args)
        if args.command == "status":
            schedule = json.loads(Path(args.schedule or HERE / f"schedule-{args.split}.json").read_bytes())
            print(json.dumps(status(Path(args.workdir).resolve(), schedule, args.route, args.include_optional), indent=1))
            return 0
        if args.route == "claude":
            rp.need(args.claude_bin and args.model and args.effort, "CLAUDE_OPTIONS_REQUIRED")
        else:
            rp.need(args.runtime_dir and args.capabilities and args.qualification, "GEMINI_OPTIONS_REQUIRED")
        rp.need(args.steps >= 1, "BAD_STEPS")
        return run_next(args)
    except (rp.Stop, OSError, ValueError, KeyError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, rp.Stop) else type(error).__name__}))
        return 1


if __name__ == "__main__":
    sys.exit(main())
