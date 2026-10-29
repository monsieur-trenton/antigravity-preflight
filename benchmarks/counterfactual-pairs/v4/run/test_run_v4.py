"""Offline tests for the v4 run tooling: schedule, block driver (stub Claude and stub native runtime), verifier, analysis, mechanism tool and the skill file. No provider calls.

The dev corpus stands in for the sealed test corpus: the same code paths, public text.
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
PAIRS = V4.parent
REPO = PAIRS.parent.parent
DEV = V4 / "dev"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rv = load("t_run_v4", HERE / "run_v4.py")
sch = load("t_schedule", HERE / "schedule.py")
vv = load("t_verify_v4", HERE / "verify_v4.py")
an = load("t_analyze_v4", HERE / "analyze_v4.py")
mech = load("t_mechanism", HERE / "mechanism.py")
brm = load("t_build_run_manifest", HERE / "build_run_manifest.py")
gem = load("t_run_gemini_v3", PAIRS / "run_gemini_v3.py")
rr = rv.rr
SCHEDULE = json.loads((HERE / "schedule-dev.json").read_bytes())
MODEL = "claude-opus-5-5"

CLAUDE_STUB = '''#!{python}
import json, sys
from pathlib import Path
args = sys.argv[1:]
if args == ["--version"]:
    print("2.1.306 (Claude Code)")
    sys.exit(0)
cfg = json.loads((Path(__file__).resolve().parent / "stub-config.json").read_text())
request = sys.stdin.read()
bare = "Please review this plan." in request
mode = cfg["mode"]
verdict = {{"approve": "NO_BLOCKERS_FOUND", "changes": "CHANGES_RECOMMENDED", "block": "BLOCKERS_FOUND"}}.get(mode, "NO_BLOCKERS_FOUND")
short = {{"NO_BLOCKERS_FOUND": "GO", "CHANGES_RECOMMENDED": "GO_WITH_CHANGES", "BLOCKERS_FOUND": "NO_GO"}}[verdict]
if mode == "garbage":
    report = "I think it is fine."
elif bare:
    report = "Looks fine.\\n\\nVERDICT: " + short
else:
    head = "Rationale.\\n\\nMACHINE SUMMARY\\nCOMPLETENESS: COMPLETE\\nASSESSMENT: " + verdict + "\\n"
    finding = ""
    if mode == "bracket":
        text = [l for l in request.splitlines() if l.startswith("[S01:3] ")][0][len("[S01:3] "):]
        finding = "FINDING: BLOCKER | VERIFIED | [S01:3] | " + text + "\\n"
    report = head + finding
model = args[args.index("--model") + 1]
print(json.dumps({{"result": report, "total_cost_usd": 0.01, "num_turns": 1, "modelUsage": {{cfg.get("served", model): {{}}}}, "is_error": False, "safety_stops": None}}))
'''

NATIVE_STUB = r'''
import hashlib, json, shutil, sys
from pathlib import Path
here = Path(__file__).resolve().parent
config = json.loads((here / "stub-config.json").read_text())
args = sys.argv[1:]
sha = lambda b: hashlib.sha256(b).hexdigest()
if args[0] == "prepare":
    packet, seed = Path(args[1]), Path(args[3])
    shutil.copytree(packet.parent, seed / "packet")
    (seed / "CLI-PLAN.json").write_text("{}")
elif args[0] == "run":
    attempt = Path(args[1])
    assert "--authorize-live" in args and "--qualification" in args
    prompt = (attempt / "packet/prompt.txt").read_bytes()
    bare = b"Please review this plan." in prompt
    verdict = {"approve": "NO_BLOCKERS_FOUND", "changes": "CHANGES_RECOMMENDED"}[config["mode"]]
    short = {"NO_BLOCKERS_FOUND": "GO", "CHANGES_RECOMMENDED": "GO_WITH_CHANGES"}[verdict]
    report = (b"Fine.\n\nVERDICT: " + short.encode()) if bare else ("Rationale.\n\nMACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: " + verdict + "\n").encode()
    frame = json.dumps(dict(event="user", message=dict(content=prompt.decode("utf-8")))).encode() + b"\n"
    (attempt / "GEMINI-REVIEW.md").write_bytes(report)
    receipt = {"status": "REPORT_RECEIVED_PENDING_ADJUDICATION", "failure": None, "closingFailures": [],
               "model": "gemini-3.8-flash-high", "effort": "high", "retries": 0, "invocations": {"proxy": 1, "native": 1},
               "processes": {"native": {"spawned": True, "reaped": True}, "proxy": {"spawned": True, "reaped": True}},
               "privateHomeAbsent": True, "socketDirectoryAbsent": True,
               "promptDelivery": {"status": "COMPLETE", "wireBytes": len(frame), "bytesWritten": len(frame)},
               "native": {"sha256": config["binary"], "bytes": 1}, "report": {"sha256": sha(report), "bytes": len(report)}}
    receipt.update(config.get("receipt", {}))
    (attempt / "CLI-RECEIPT.json").write_text(json.dumps(receipt))
'''


class Harness:
    def __init__(self, tmp, mode="approve", receipt=None):
        self.tmp = Path(tmp)
        self.work = self.tmp / "work"
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        self.claude = self.bin / "claude"
        self.claude.write_text(CLAUDE_STUB.format(python=sys.executable))
        self.claude.chmod(self.claude.stat().st_mode | stat.S_IXUSR)
        self.runtime = self.tmp / "rt" / "flash-high"
        (self.runtime / "scripts").mkdir(parents=True)
        (self.runtime / "scripts/cli_review.py").write_text(NATIVE_STUB)
        self.set_mode(mode, receipt)
        v3 = json.loads((PAIRS / "v3-run-gemini/manifest.json").read_bytes())
        self.binary = v3["binary"]["sha256"]
        self.caps = self.tmp / "caps"
        self.caps.mkdir()
        (self.caps / "RESULT.json").write_text(json.dumps({"status": "PASS_METADATA_CAPABILITIES_ONLY", "binaryStable": True, "frozenBinary": {"sha256": self.binary, "bytes": 1},
                                                           "observedVersion": "agy 1.4.1", "model": "gemini-3.8-flash-high", "effort": "high"}))
        (self.tmp / "q.json").write_text("{}")
        self.write_config(mode, receipt)
        manifest = brm.build("dev")
        manifest["routes"]["gemini"]["runtime"]["treeSha256"] = gem.runtime_tree_sha(self.runtime)
        self.manifest_path = self.tmp / "run.json"
        self.write_manifest(manifest)

    def write_manifest(self, manifest):
        self.manifest_path.write_text(json.dumps(manifest, indent=1) + "\n")

    def write_config(self, mode, receipt=None, served=None):
        config = {"mode": mode, "binary": self.binary if hasattr(self, "binary") else "", "receipt": receipt or {}}
        if served:
            config["served"] = served
        (self.runtime / "scripts/stub-config.json").write_text(json.dumps(config))
        (self.bin / "stub-config.json").write_text(json.dumps(config))

    def set_mode(self, mode, receipt=None, served=None):
        self.write_config(mode, receipt, served)
        if hasattr(self, "manifest_path"):
            manifest = json.loads(self.manifest_path.read_text())
            manifest["routes"]["gemini"]["runtime"]["treeSha256"] = gem.runtime_tree_sha(self.runtime)
            self.write_manifest(manifest)

    def argv(self, route, *extra, execute=True, load="1000000"):
        base = ["next", "--route", route, "--workdir", str(self.work), "--split", "dev", "--corpus", str(DEV), "--run-manifest", str(self.manifest_path), "--max-load", load]
        if route == "claude":
            base += ["--claude-bin", str(self.claude), "--model", MODEL, "--effort", "high"]
        else:
            base += ["--runtime-dir", str(self.runtime), "--capabilities", str(self.caps), "--qualification", str(self.tmp / "q.json")]
        if execute:
            base.append("--execute")
        return base + list(extra)

    def run(self, route, *extra, **kw):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rv.main(self.argv(route, *extra, **kw))
        return code, json.loads(out.getvalue().strip().splitlines()[-1])

    def ledger(self, route, arm, trial=1):
        path = rv.ledger_path(self.work, route, arm, trial)
        return [json.loads(line) for line in path.read_text().splitlines()] if path.is_file() else []

    def verify(self, route):
        return vv.verify(DEV, self.manifest_path, self.work, route)


class WithHarness(unittest.TestCase):
    def harness(self, **kw):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        return Harness(tmp.name, **kw)


class ScheduleTests(unittest.TestCase):
    def test_committed_schedules_are_current_and_the_test_case_set_matches_the_sealed_manifest(self):
        for split in ("dev", "test"):
            built = sch.build(split)
            sch.check_against_manifest(built, split)
            self.assertEqual((HERE / f"schedule-{split}.json").read_text(), sch.render(built))
        test = sch.build("test")
        self.assertEqual((test["pairs"], test["cases"], len(test["blocks"])), (71, 166, 12))

    def test_every_case_is_in_exactly_one_block_with_its_whole_pair_and_blocks_mix_kinds(self):
        for split in ("dev", "test"):
            seed, instances = sch.surviving_pairs(split)
            schedule = sch.build(split)
            counts = {}
            for block in schedule["blocks"]:
                for case in block["cases"]:
                    counts[case] = counts.get(case, 0) + 1
                members = {c for i in instances if i["pair"] in block["pairs"] for c in sch.cases_of(seed, i)}
                self.assertEqual(set(block["cases"]), members)
                self.assertLessEqual(len(block["pairs"]), 6)
            self.assertEqual(set(counts.values()), {1})
            self.assertEqual(set(counts), set(schedule["submissionOrder"]))
            kinds = {b["id"]: {i["kind"] for i in instances if i["pair"] in b["pairs"]} for b in schedule["blocks"]}
            self.assertTrue(all(len(k) >= 2 for k in kinds.values()))

    def test_each_route_runs_every_block_for_every_arm_and_trial_once_and_alternates_the_arm_order(self):
        schedule = sch.build("test")
        for route, spec in schedule["routes"].items():
            keys = [(s["block"], s["arm"], s["trial"]) for s in spec["steps"]]
            self.assertEqual(len(keys), len(set(keys)))
            self.assertEqual(len(keys), 12 * len(spec["arms"]) * spec["trials"])
            first = [s["arm"] for s in spec["steps"] if s["trial"] == 1][::2]
            self.assertEqual(set(first), set(spec["arms"]))  # neither arm is always first
            self.assertEqual([s["step"] for s in spec["steps"]], list(range(1, len(keys) + 1)))
        self.assertEqual({r["id"] for r in schedule["repeatBlocks"]}, {"R01", "R02", "R03", "R04"})
        self.assertEqual({s["trial"] for s in schedule["optional"]["gemini"]["steps"]}, {2})
        self.assertLessEqual(sum(len(r["pairs"]) for r in schedule["repeatBlocks"]), 24)

    def test_the_repeat_pairs_are_the_hash_drawn_ones(self):
        seed, instances = sch.surviving_pairs("test")
        drawn = sorted(instances, key=lambda i: sch.sha(i["pair"] + "|v4-repeat"))[:24]
        self.assertEqual({p for r in sch.build("test")["repeatBlocks"] for p in r["pairs"]}, {i["pair"] for i in drawn})

    def test_the_schedule_builder_opens_no_packet_and_no_oracle(self):
        source = (HERE / "schedule.py").read_text()
        for word in ('"oracle', "'oracle", '/ "packets"'):
            self.assertNotIn(word, source)


class RunManifestTests(unittest.TestCase):
    def test_build_pins_existing_files_and_binds_the_schedule_and_corpus(self):
        for split in ("dev", "test"):
            manifest = brm.build(split)
            self.assertEqual(manifest["scheduleSha256"], rv.sha((HERE / f"schedule-{split}.json").read_bytes()))
            self.assertEqual(manifest["routes"]["claude"]["model"], MODEL)
            for name in manifest["pins"]:
                self.assertTrue((REPO / name).is_file(), name)
        self.assertEqual(brm.build("test")["corpus"]["manifestSha256"], "2d13d47576d404154171126410dfbe31e076c194ebd561693479e332851b4b25")

    def test_a_changed_pin_stops_the_driver(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = brm.build("dev")
            name = next(iter(manifest["pins"]))
            manifest["pins"][name] = "0" * 64
            path = Path(tmp) / "m.json"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(rp_stop()):
                rv.load_run_manifest(path)


def rp_stop():
    return rv.rp.Stop


class DriverTests(WithHarness):
    def test_status_before_anything_ran_names_step_one(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rv.main(["status", "--route", "claude", "--workdir", str(Path(tempfile.mkdtemp()) / "w"), "--split", "dev"])
        data = json.loads(out.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual((data["stepsComplete"], data["stepsTotal"], data["next"]["step"]), (0, 16, 1))

    def test_dry_run_builds_requests_writes_no_ledger_and_can_repeat(self):
        h = self.harness()
        for _ in range(2):
            code, summary = h.run("claude", execute=False)
            self.assertEqual((code, summary["status"], summary["providerCallsFromThisScript"]), (0, "DRY_RUN_PREPARED_ONLY", 0))
        self.assertEqual(h.ledger("claude", "bare") + h.ledger("claude", "skill"), [])
        self.assertTrue(list((h.work / "dry").rglob("request.txt")))
        code, summary = h.run("gemini", execute=False)
        self.assertEqual((code, summary["status"]), (0, "DRY_RUN_PREPARED_ONLY"))

    def test_a_case_cap_stops_at_a_boundary_and_the_next_call_resumes_then_moves_on(self):
        h = self.harness()
        step1 = SCHEDULE["routes"]["claude"]["steps"][0]
        code, summary = h.run("claude", "--max-cases", "3")
        self.assertEqual((code, summary["stoppedBecause"]), (0, "MAX_CASES"))
        rows = h.ledger("claude", step1["arm"])
        self.assertEqual(len(rows), 3)
        order = {c: n for n, c in enumerate(SCHEDULE["submissionOrder"])}
        self.assertEqual([r["case"] for r in rows], sorted([r["case"] for r in rows], key=order.__getitem__))
        block = next(b for b in SCHEDULE["blocks"] if b["id"] == step1["block"])
        code, summary = h.run("claude")
        self.assertEqual(summary["blockRuns"][0]["casesRecorded"], len(block["cases"]) - 3)
        self.assertTrue(summary["blockRuns"][0]["stepComplete"])
        self.assertEqual(len(h.ledger("claude", step1["arm"])), len(block["cases"]))
        self.assertEqual({(r["block"], r["step"], r["trial"], r["arm"]) for r in h.ledger("claude", step1["arm"])}, {(step1["block"], 1, 1, step1["arm"])})
        code, summary = h.run("claude")
        self.assertEqual(summary["blockRuns"][0]["step"], 2)
        self.assertEqual(h.verify("claude")["failures"], [])
        log = [json.loads(l) for l in (h.work / "blocks.jsonl").read_text().splitlines()]
        self.assertEqual([r["casesRecorded"] for r in log][:3], [3, len(block["cases"]) - 3, log[2]["casesRecorded"]])
        self.assertTrue(all("peakChildRssKb" in r and "childCpuSeconds" in r and "loadAvgStart" in r for r in log))

    def test_steps_chain_within_the_guards(self):
        h = self.harness()
        code, summary = h.run("claude", "--steps", "2")
        self.assertEqual([r["step"] for r in summary["blockRuns"]], [1, 2])
        self.assertEqual(summary["stoppedBecause"], "STEPS_DONE")
        arms = {r["arm"] for r in summary["blockRuns"]}
        self.assertEqual(arms, {"skill", "skill-go"})

    def test_time_budget_stop_file_and_host_load_stop_before_a_case(self):
        h = self.harness()
        code, summary = h.run("claude", "--max-minutes", "0.01")
        self.assertEqual(summary["stoppedBecause"], "TIME_BUDGET")
        h.work.mkdir(exist_ok=True)
        (h.work / "STOP").write_text("")
        code, summary = h.run("claude")
        self.assertEqual(summary["stoppedBecause"], "STOP_FILE")
        (h.work / "STOP").unlink()
        original = rv.os.getloadavg
        rv.os.getloadavg = lambda: (9.0, 9.0, 9.0)
        try:
            code, summary = h.run("claude", load="1.5")
        finally:
            rv.os.getloadavg = original
        self.assertEqual(summary["stoppedBecause"], "HOST_LOAD")
        self.assertEqual(h.ledger("claude", "skill") + h.ledger("claude", "skill-go"), [])

    def test_an_attempt_without_a_row_is_recorded_as_a_stop_and_never_rerun(self):
        h = self.harness()
        step = SCHEDULE["routes"]["claude"]["steps"][0]
        case = next(c for c in SCHEDULE["submissionOrder"] if c in next(b for b in SCHEDULE["blocks"] if b["id"] == step["block"])["cases"])
        (rv.attempt_dir(h.work, "claude", step["arm"], 1) / "attempts" / case).mkdir(parents=True)
        h.run("claude", "--max-cases", "1")
        self.assertEqual(h.ledger("claude", step["arm"])[0]["technicalStop"], "INTERRUPTED_UNKNOWN_STATE")

    def test_three_unparseable_reports_in_a_row_halt_the_run_and_are_recorded_not_replaced(self):
        h = self.harness(mode="garbage")
        code, summary = h.run("claude")
        self.assertEqual((code, summary["stoppedBecause"]), (1, "CONSECUTIVE_STOPS"))
        rows = h.ledger("claude", SCHEDULE["routes"]["claude"]["steps"][0]["arm"])
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(r["technicalStop"].startswith("UNPARSEABLE_REPORT") for r in rows))
        self.assertEqual(h.verify("claude")["failures"], [])

    def test_a_bracketed_line_field_is_read_and_marked(self):
        h = self.harness(mode="bracket")
        h.run("claude", "--max-cases", "1")
        row = h.ledger("claude", SCHEDULE["routes"]["claude"]["steps"][0]["arm"])[0]
        if SCHEDULE["routes"]["claude"]["steps"][0]["arm"] != "bare":
            self.assertTrue(row["bracketedLineFieldRead"])
            self.assertEqual(row["findings"][0]["line"], 3)
            self.assertEqual(row["findings"][0]["source"], "S01")

    def test_a_non_requested_served_model_is_a_stop(self):
        h = self.harness()
        h.set_mode("approve", served="claude-other")
        h.run("claude", "--max-cases", "1")
        self.assertEqual(h.ledger("claude", SCHEDULE["routes"]["claude"]["steps"][0]["arm"])[0]["technicalStop"], "MODEL_MISMATCH")

    def test_wrong_model_or_corpus_or_split_stops_before_any_case(self):
        h = self.harness()
        argv = h.argv("claude")
        argv[argv.index("--model") + 1] = "claude-sonnet-5-5"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(rv.main(argv), 1)
        self.assertIn("RUN_MODEL_MISMATCH", out.getvalue())
        self.assertFalse(list(h.work.glob("responses-*")))
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "dev"
            shutil.copytree(DEV, copy)
            (copy / "packets" / next(p.name for p in (copy / "packets").iterdir()) / "S01.txt").write_text("tampered\n")
            argv = h.argv("claude")
            argv[argv.index("--corpus") + 1] = str(copy)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(rv.main(argv), 1)
            self.assertIn("CORPUS_PIN_MISMATCH", out.getvalue())

    def test_the_gemini_route_runs_blocks_and_verifies_with_its_receipts(self):
        h = self.harness(mode="changes")
        step = SCHEDULE["routes"]["gemini"]["steps"][0]
        code, summary = h.run("gemini", "--max-cases", "2")
        self.assertEqual((code, summary["stoppedBecause"]), (0, "MAX_CASES"))
        rows = h.ledger("gemini", step["arm"])
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["route"] == "native-flash-high" and r["binarySha256"] == h.binary and r["assessment"] == "CHANGES_RECOMMENDED" for r in rows))
        result = h.verify("gemini")
        self.assertEqual(result["failures"], [])
        # a packet carries the same sources for both arms; only the prompt file differs
        case = rows[0]["case"]
        packet = rv.attempt_dir(h.work, "gemini", step["arm"], 1) / "packets" / case
        self.assertTrue((packet / "snapshots" / "S01.txt").is_file())
        self.assertEqual((packet / "prompt.txt").read_bytes(), rr.build(step["arm"], rv.load_corpus(DEV)[2](case)))

    def test_gemini_stops_on_a_wrong_binary_or_runtime(self):
        h = self.harness()
        caps = json.loads((h.caps / "RESULT.json").read_text())
        caps["frozenBinary"]["sha256"] = "0" * 64
        (h.caps / "RESULT.json").write_text(json.dumps(caps))
        code, summary = h.run("gemini")
        self.assertEqual((code, summary["reason"]), (1, "RUN_BINARY_MISMATCH"))

    def test_neither_driver_reads_the_oracle(self):
        for name in ("run_v4.py", "verify_v4.py", "schedule.py"):
            self.assertNotIn("oracle.json", (HERE / name).read_text(), name)


class VerifierTests(WithHarness):
    def run_some(self):
        h = self.harness()
        h.run("claude", "--max-cases", "4")
        return h

    def test_tampering_is_found(self):
        h = self.run_some()
        step = SCHEDULE["routes"]["claude"]["steps"][0]
        attempts = rv.attempt_dir(h.work, "claude", step["arm"], 1) / "attempts"
        case = h.ledger("claude", step["arm"])[0]["case"]
        report = attempts / case / "REVIEW.md"
        original = report.read_bytes()
        report.write_bytes(original + b" ")
        self.assertTrue(any(f.startswith("REPORT_HASH") for f in h.verify("claude")["failures"]))
        report.write_bytes(original)
        (attempts / case / "request.txt").write_bytes(b"changed")
        self.assertTrue(any(f.startswith("SAVED_REQUEST") for f in h.verify("claude")["failures"]))
        (attempts / case / "request.txt").write_bytes(rr.build(step["arm"], rv.load_corpus(DEV)[2](case)))
        self.assertEqual(h.verify("claude")["failures"], [])
        (attempts / "R-ffffff").mkdir()
        self.assertTrue(any(f.startswith("ATTEMPT_WITHOUT_ROW") for f in h.verify("claude")["failures"]))

    def test_a_row_with_another_run_stamp_or_a_wrong_block_is_found(self):
        h = self.run_some()
        step = SCHEDULE["routes"]["claude"]["steps"][0]
        ledger = rv.ledger_path(h.work, "claude", step["arm"], 1)
        rows = [json.loads(l) for l in ledger.read_text().splitlines()]
        rows[0]["runManifestSha256"] = "0" * 64
        other = next(x for x in SCHEDULE["routes"]["claude"]["steps"] if x["arm"] == step["arm"] and x["trial"] == 1 and x["block"] != step["block"])
        rows[1]["block"], rows[1]["step"] = other["block"], other["step"]
        ledger.write_text("".join(json.dumps(r) + "\n" for r in rows))
        failures = h.verify("claude")["failures"]
        self.assertTrue(any(f.startswith("STAMP") for f in failures))
        self.assertTrue(any(f.startswith("CASE_NOT_IN_BLOCK") for f in failures))

    def test_gemini_receipt_faults_are_found(self):
        h = self.harness(mode="changes", receipt={"retries": 1})
        h.run("gemini", "--max-cases", "1")
        self.assertTrue(any(f.startswith("RECEIPT") for f in h.verify("gemini")["failures"]))


class AnalysisTests(WithHarness):
    def test_exact_sign_test(self):
        self.assertEqual(an.sign_test(0, 0), 1.0)
        self.assertEqual(an.sign_test(5, 0), 0.0625)
        self.assertEqual(an.sign_test(1, 1), 1.0)
        self.assertAlmostEqual(an.sign_test(8, 1), 0.0391, places=3)

    def run_all(self, h, route, steps):
        for _ in range(steps):
            h.run(route)

    def test_a_partial_run_is_analysed_on_the_blocks_completed_in_every_arm_and_says_so(self):
        h = self.harness(mode="approve")
        h.run("claude", "--steps", "4")  # block 1 and 2, both arms, trial 1; trial 2 not started
        result = an.analyze(DEV, h.manifest_path, h.work)
        arm = result["arms"]["claude/skill"]
        self.assertEqual(arm["blocksComplete"], {"1": 2})  # trial 2 has not started: only trial 1 is scored, on its two complete blocks
        self.assertEqual(arm["casesScored"], {"1": len(SCHEDULE["blocks"][0]["cases"]) + len(SCHEDULE["blocks"][1]["cases"])})
        h2 = Harness(tempfile.mkdtemp(), mode="approve")
        self.addCleanup(shutil.rmtree, h2.tmp, True)
        h2.run("claude", "--steps", "16")
        result = an.analyze(DEV, h2.manifest_path, h2.work)
        for name in ("claude/skill", "claude/skill-go"):
            self.assertEqual(result["arms"][name]["blocksComplete"], {"1": 4, "2": 4})
            self.assertEqual(result["arms"][name]["casesScored"], {"1": 46, "2": 46})
            self.assertEqual(set(result["arms"][name]["score"]["trials"]), {"1", "2"})
        comparison = next(c for c in result["comparisons"] if c["id"] == "H4")
        self.assertEqual(comparison["blocksUsed"], 4)
        self.assertEqual(comparison["metrics"]["soundGo"]["aOnly"] + comparison["metrics"]["soundGo"]["bOnly"], 0)
        self.assertEqual(comparison["metrics"]["soundGo"]["matchedUnits"], 46)  # 23 sound members x 2 trials
        self.assertEqual(h2.verify("claude")["failures"], [])
        self.assertIn("claude/skill", result["subgroups"])

    def test_gemini_arms_are_compared_across_wording_free_dev_units(self):
        h = self.harness(mode="changes")
        h.run("gemini", "--steps", "8")
        result = an.analyze(DEV, h.manifest_path, h.work)
        comparison = next(c for c in result["comparisons"] if c["id"] == "H5")
        self.assertEqual(comparison["blocksUsed"], 4)
        self.assertEqual(comparison["metrics"]["strictPair"]["matchedUnits"], 23)
        self.assertEqual(result["arms"]["gemini/bare"]["score"]["trials"]["1"]["verdictOnly"]["soundHedged"]["count"], 23)

    def test_redacted_bundle_has_no_plan_text_and_no_reports(self):
        h = self.harness(mode="bracket")
        h.run("claude", "--steps", "2")
        archive = h.tmp / "out.tar.gz"
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(rv.main(["bundle", "--workdir", str(h.work), "--out", str(archive), "--redacted"]), 0)
        import tarfile
        with tarfile.open(archive) as tar:
            names = tar.getnames()
            text = b"".join(tar.extractfile(n).read() for n in names)
        self.assertTrue(all(n.startswith("responses-") or n == "blocks.jsonl" or n.endswith("CLI-RECEIPT.json") for n in names))
        self.assertNotIn(b'"quote"', text)
        self.assertIn(b"quoteSha256", text)
        lines = rv.load_corpus(DEV)[2]
        case = next(iter(SCHEDULE["blocks"][0]["cases"]))
        self.assertNotIn(lines(case)["S01"][2].encode(), text)


class MechanismTests(WithHarness):
    def test_items_hide_route_arm_trial_and_case_and_answers_become_judgments(self):
        h = self.harness(mode="changes")
        h.run("claude", "--steps", "4")
        out = h.tmp / "mech"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            self.assertEqual(mech.build(DEV, h.manifest_path, h.work, out), 0)
        key = json.loads((out / "key.json").read_text())
        self.assertGreater(len(key), 0)
        for item in (out / "items").glob("*.json"):
            data = json.loads(item.read_text())
            self.assertEqual(sorted(data), ["decisiveFact", "item", "report"])
            self.assertNotIn(key[data["item"]]["case"], item.read_text())
        answers = h.tmp / "answers.jsonl"
        first = sorted(key)[0]
        answers.write_text(json.dumps({"item": first, "label": "NAMED"}) + "\n" + json.dumps({"item": sorted(key)[1], "label": None, "error": "NO_LABEL"}) + "\n")
        judgments = mech.ingest(out / "key.json", answers)
        self.assertEqual(len(judgments), 1)
        self.assertEqual((judgments[0]["namesMechanism"], judgments[0]["case"]), (True, key[first]["case"]))


class WrapperTests(WithHarness):
    def wrapper(self, h, *args):
        import subprocess
        env = {"PATH": os.environ["PATH"], "HOME": str(h.tmp), "V4_BENCH_ENV": str(h.tmp / "none.env"), "V4_WORKDIR": str(h.work), "V4_SPLIT": "dev", "V4_CORPUS": str(DEV),
               "V4_RUN_MANIFEST": str(h.manifest_path), "V4_CLAUDE_BIN": str(h.claude)}
        return subprocess.run(["bash", str(HERE / "blocks.sh"), *args], capture_output=True, text=True, env=env, timeout=120)

    def test_status_and_a_dry_run_make_no_call_and_execute_is_never_implied(self):
        h = self.harness()
        done = self.wrapper(h, "status", "claude")
        self.assertEqual(json.loads(done.stdout)["stepsTotal"], 16)
        done = self.wrapper(h, "next", "claude", "--max-load", "1000000")
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1])["status"], "DRY_RUN_PREPARED_ONLY")
        self.assertFalse(list(h.work.glob("responses-*")))
        done = self.wrapper(h, "next", "claude", "--execute", "--max-cases", "1", "--max-load", "1000000")
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1])["blockRuns"][0]["casesRecorded"], 1)
        self.assertEqual(json.loads(self.wrapper(h, "verify", "claude").stdout)["failures"], [])

    def test_stop_and_resume_toggle_the_stop_file(self):
        h = self.harness()
        self.wrapper(h, "stop")
        self.assertTrue((h.work / "STOP").is_file())
        done = self.wrapper(h, "next", "claude", "--execute", "--max-load", "1000000")
        self.assertEqual(json.loads(done.stdout.strip().splitlines()[-1])["stoppedBecause"], "STOP_FILE")
        self.wrapper(h, "resume")
        self.assertFalse((h.work / "STOP").exists())

    def test_a_missing_setting_is_an_error_not_a_default(self):
        h = self.harness()
        import subprocess
        done = subprocess.run(["bash", str(HERE / "blocks.sh"), "next", "gemini"], capture_output=True, text=True,
                              env={"PATH": os.environ["PATH"], "HOME": str(h.tmp), "V4_BENCH_ENV": str(h.tmp / "none.env"), "V4_WORKDIR": str(h.work)}, timeout=60)
        self.assertNotEqual(done.returncode, 0)


class SkillFileTests(unittest.TestCase):
    def test_the_skill_names_its_commands_and_its_rules(self):
        skill = (REPO / ".claude/skills/v4-benchmark-blocks/SKILL.md").read_text(encoding="utf-8")
        self.assertTrue(skill.startswith("---\nname: v4-benchmark-blocks\n"))
        for text in ("run_v4.py", "status", "--execute", "--max-minutes", "--max-load", "STOP", "verify_v4.py", "bundle", "--redacted", "never open", "owner"):
            self.assertIn(text, skill)
        handoff = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for text in ("schedule-test.json", "run_v4.py", "verify_v4.py", "analyze_v4.py", "mechanism.py"):
            self.assertIn(text, handoff)


if __name__ == "__main__":
    unittest.main()
