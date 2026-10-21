"""Offline tests for the pilot driver using a stub runtime in place of the native CLI. No provider calls."""
import importlib.util
import io
import json
from pathlib import Path
import contextlib
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rp, sc = load("run_pilot"), load("score")

STUB = r'''
import json, shutil, sys
from pathlib import Path
here = Path(__file__).resolve().parent
config = json.loads((here / "stub-config.json").read_text())
def log(entry):
    with open(config["log"], "a") as handle:
        handle.write(json.dumps(entry) + "\n")
args = sys.argv[1:]
if args[0] == "prepare":
    packet, caps, seed = Path(args[1]), args[2], Path(args[3])
    log({"cmd": "prepare", "profile": args[args.index("--runtime-profile") + 1] if "--runtime-profile" in args else None})
    shutil.copytree(packet.parent, seed / "packet")
    (seed / "CLI-PLAN.json").write_text("{}")
elif args[0] == "run":
    attempt = Path(args[1])
    assert "--authorize-live" in args and "--qualification" in args
    log({"cmd": "run", "attempt": attempt.name})
    mode = config["mode"]
    if mode == "stop":
        (attempt / "CLI-RECEIPT.json").write_text(json.dumps({"status": "STOPPED", "failure": {"code": "PROCESS_EXIT"}}))
    else:
        report = {"approve": "Looks fine.\nMACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: NO_BLOCKERS_FOUND\n",
                  "garbage": "I think it is fine."}[mode]
        (attempt / "GEMINI-REVIEW.md").write_text(report)
        (attempt / "CLI-RECEIPT.json").write_text(json.dumps({"status": "REPORT_RECEIVED_PENDING_ADJUDICATION"}))
'''


class Harness:
    def __init__(self, tmp, runtime_name="flash-high", mode="approve"):
        self.tmp = Path(tmp)
        self.runtime = self.tmp / "rt" / runtime_name
        (self.runtime / "scripts").mkdir(parents=True)
        (self.runtime / "scripts/cli_review.py").write_text(STUB)
        self.log = self.tmp / "log.jsonl"
        self.set_mode(mode)
        (self.tmp / "caps").mkdir()
        (self.tmp / "q.json").write_text("{}")
        self.work = self.tmp / "work"

    def set_mode(self, mode):
        (self.runtime / "scripts/stub-config.json").write_text(json.dumps({"mode": mode, "log": str(self.log)}))

    def calls(self, cmd):
        if not self.log.exists():
            return []
        return [e for e in map(json.loads, self.log.read_text().splitlines()) if e["cmd"] == cmd]

    def run(self, *extra, profile=None):
        argv = ["--runtime-dir", str(self.runtime), "--capabilities", str(self.tmp / "caps"),
                "--qualification", str(self.tmp / "q.json"), "--workdir", str(self.work), *extra]
        if profile:
            argv += ["--runtime-profile", profile]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rp.main(argv)
        return code, json.loads(out.getvalue().splitlines()[-1])


class ParserTests(unittest.TestCase):
    def test_parses_findings_with_pipes_in_quote(self):
        text = "x\nMACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: BLOCKERS_FOUND\nFINDING: BLOCKER | VERIFIED | 3 | a | b\nFINDING: RISK | UNVERIFIED | - | -\n"
        parsed = rp.parse_report(text)
        self.assertEqual(parsed["findings"][0], {"severity": "BLOCKER", "evidence": "VERIFIED", "line": 3, "quote": "a | b"})
        self.assertEqual(parsed["findings"][1]["line"], 0)

    def test_rejects_malformed_reports(self):
        bad = ["no summary", "MACHINE SUMMARY\nCOMPLETENESS: COMPLETE\n",
               "MACHINE SUMMARY\nCOMPLETENESS: MAYBE\nASSESSMENT: NO_BLOCKERS_FOUND\n",
               "MACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: NO_BLOCKERS_FOUND\nFINDING: BLOCKER | VERIFIED | x | q\n",
               "MACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: NO_BLOCKERS_FOUND\nthanks!\n"]
        for text in bad:
            with self.assertRaises(rp.Stop, msg=text):
                rp.parse_report(text)


class DriverTests(unittest.TestCase):
    def test_dry_run_makes_no_native_run_and_writes_no_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            code, out = h.run()
            self.assertEqual((code, out["status"], out["prepared"]), (0, "DRY_RUN_PREPARED_ONLY", 24))
            self.assertEqual(len(h.calls("prepare")), 24)
            self.assertEqual(h.calls("run"), [])
            self.assertFalse((h.work / "responses-trial1.jsonl").exists())

    def test_execute_runs_each_case_once_and_the_scorer_accepts_the_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            code, out = h.run("--execute")
            self.assertEqual((code, out["executed"]), (0, 24))
            self.assertEqual(len(h.calls("run")), 24)
            ledger = h.work / "responses-trial1.jsonl"
            result = sc.score([json.loads(line) for line in ledger.read_text().splitlines()])
            trial = result["trials"]["1"]
            self.assertEqual(trial["observations"], 24)
            self.assertEqual(trial["changedPlansJudgedCorrectly"]["count"], 0)  # the stub approves everything
            self.assertEqual(trial["pairDiscrimination"]["count"], 0)

    def test_resume_never_reruns_recorded_cases(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            h.run("--execute")
            code, out = h.run("--execute")
            self.assertEqual(out["skippedAlreadyRecorded"], 24)
            self.assertEqual(len(h.calls("run")), 24)

    def test_interrupted_attempt_is_recorded_as_a_stop_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            order = sc.load_frozen()[0]["submissionOrder"]
            (h.work / "trial1/attempts" / order[0]).mkdir(parents=True)
            h.run("--execute")
            rows = [json.loads(l) for l in (h.work / "responses-trial1.jsonl").read_text().splitlines()]
            self.assertEqual(rows[0]["case"], order[0])
            self.assertEqual(rows[0]["technicalStop"], "INTERRUPTED_UNKNOWN_STATE")
            self.assertEqual(len(h.calls("run")), 23)

    def test_halts_after_consecutive_stops_without_retrying(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp, mode="stop")
            code, out = h.run("--execute")
            self.assertEqual((code, out["status"]), (1, "HALTED_CONSECUTIVE_STOPS"))
            self.assertEqual(len(h.calls("run")), 3)
            rows = [json.loads(l) for l in (h.work / "responses-trial1.jsonl").read_text().splitlines()]
            self.assertTrue(all(r["technicalStop"].startswith("RUNTIME_STOP") for r in rows))

    def test_unparseable_report_is_a_stop_that_preserves_the_report_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp, mode="garbage")
            h.run("--execute", "--max-consecutive-stops", "99")
            rows = [json.loads(l) for l in (h.work / "responses-trial1.jsonl").read_text().splitlines()]
            self.assertEqual(len(rows), 24)
            self.assertTrue(all(r["technicalStop"].startswith("UNPARSEABLE_REPORT") and r["reportSha256"] for r in rows))

    def test_route_must_be_explicit_and_consistent(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(Harness(tmp).run(profile="argon-high")[1]["reason"], "PROFILE_MUST_MATCH_RUNTIME")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(Harness(tmp, "argon-high").run()[1]["reason"], "PROFILE_MUST_MATCH_RUNTIME")
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp, "argon-high")
            self.assertEqual(h.run(profile="argon-high")[0], 0)
            self.assertEqual(h.calls("prepare")[0]["profile"], "argon-high")

    def test_flash_embeds_evidence_in_the_prompt_and_argon_does_not(self):
        for name, expect in (("flash-high", True), ("argon-high", False)):
            with tempfile.TemporaryDirectory() as tmp:
                h = Harness(tmp, name)
                h.run(profile="argon-high" if name == "argon-high" else None)
                case = sc.load_frozen()[0]["submissionOrder"][0]
                prompt = (h.work / "trial1/packets" / case / "prompt.txt").read_text()
                self.assertEqual("[S01:1]" in prompt, expect, name)

    def test_workdir_inside_repository_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            h.work = HERE / "work-should-not-exist"
            self.assertEqual(h.run()[1]["reason"], "WORKDIR_INSIDE_REPOSITORY")
            self.assertFalse(h.work.exists())

    def test_driver_never_reads_the_oracle_or_sends_it(self):
        source = (HERE / "run_pilot.py").read_text()
        self.assertNotIn("oracle.json", source)
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            h.run()
            names = [p.name for p in (h.work).rglob("*") if p.is_file()]
            self.assertFalse(any("oracle" in n for n in names))
            texts = " ".join(p.read_text() for p in h.work.rglob("*.txt"))
            self.assertNotIn("expectedClass", texts)


if __name__ == "__main__":
    unittest.main()
