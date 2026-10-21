"""Offline tests for the Claude CLI pilot driver using a stub executable. No provider calls."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
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


rc, sc = load("run_pilot_claude"), load("score")
MODEL = "claude-test-model"

STUB = r'''#!/usr/bin/env python3
import json, os, sys
from pathlib import Path
here = Path(__file__).resolve().parent
config = json.loads((here / "stub-config.json").read_text())
def log(entry):
    with open(config["log"], "a") as handle:
        handle.write(json.dumps(entry) + "\n")
if sys.argv[1:] == ["--version"]:
    log({"cmd": "version"})
    print("9.9.9 (Claude Code)")
    sys.exit(0)
stdin = sys.stdin.read()
log({"cmd": "call", "argv": sys.argv[1:], "cwd": os.getcwd(), "cwdEntries": sorted(os.listdir(os.getcwd())), "stdin": stdin})
mode = config["mode"]
summary = "Fine.\nMACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: NO_BLOCKERS_FOUND\n"
served = {config["model"]: {}}
if mode == "garbage":
    print("not json"); sys.exit(0)
if mode == "error":
    print(json.dumps({"type": "result", "subtype": "success", "terminal_reason": "api_error", "is_error": True, "modelUsage": {}})); sys.exit(1)
if mode == "wrongmodel":
    served = {"some-other-model": {}}
if mode == "noformat":
    summary = "Looks fine to me."
print(json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": summary,
                  "total_cost_usd": 0.01, "num_turns": 1, "modelUsage": served}))
'''


class Harness:
    def __init__(self, tmp, mode="ok"):
        self.tmp = Path(tmp)
        self.bin = self.tmp / "bin" / "claude"
        self.bin.parent.mkdir()
        self.bin.write_text(STUB)
        self.bin.chmod(self.bin.stat().st_mode | stat.S_IXUSR)
        self.log = self.tmp / "log.jsonl"
        self.set_mode(mode)
        self.work = self.tmp / "work"

    def set_mode(self, mode):
        (self.bin.parent / "stub-config.json").write_text(json.dumps({"mode": mode, "log": str(self.log), "model": MODEL}))

    def calls(self):
        if not self.log.exists():
            return []
        return [e for e in map(json.loads, self.log.read_text().splitlines()) if e["cmd"] == "call"]

    def ledger(self, trial=1):
        path = self.work / f"responses-trial{trial}.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines()] if path.exists() else []

    def run(self, *extra, bin_path=None):
        argv = ["--claude-bin", str(bin_path or self.bin), "--model", MODEL, "--effort", "high",
                "--workdir", str(self.work), *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rc.main(argv)
        return code, json.loads(out.getvalue().splitlines()[-1])


class ClaudeDriverTests(unittest.TestCase):
    def test_dry_run_makes_no_model_call_and_writes_no_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            code, out = h.run()
            self.assertEqual((code, out["status"], out["prepared"]), (0, "DRY_RUN_PREPARED_ONLY", 24))
            self.assertEqual(h.calls(), [])
            self.assertEqual(h.ledger(), [])
            self.assertFalse((h.work / "trial1/attempts").exists())  # so a later --execute is not misread as interrupted

    def test_dry_run_then_execute_in_the_same_workdir_runs_everything(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            h.run()
            code, out = h.run("--execute")
            self.assertEqual((code, out["executed"], out["stopped"]), (0, 24, 0))

    def test_every_call_is_tool_free_isolated_and_stdin_fed(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            h.run("--execute")
            calls = h.calls()
            self.assertEqual(len(calls), 24)
            for call in calls:
                argv = call["argv"]
                self.assertEqual(argv[argv.index("--tools") + 1], "")
                for flag in ("-p", "--safe-mode", "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config"):
                    self.assertIn(flag, argv)
                self.assertEqual(argv[argv.index("--model") + 1], MODEL)
                self.assertEqual(argv[argv.index("--effort") + 1], "high")
                self.assertNotIn("--fallback-model", argv)
                self.assertEqual(call["cwdEntries"], [])  # empty working directory
                self.assertIn("[S01:1]", call["stdin"])
                self.assertNotIn("expectedClass", call["stdin"])
                self.assertNotIn("oracle", call["stdin"].lower())

    def test_ledger_is_accepted_by_the_scorer_and_labelled_with_route_and_served_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            h.run("--execute")
            result = sc.score(h.ledger())
            trial = result["trials"]["1"]
            self.assertEqual(trial["observations"], 24)
            self.assertEqual(trial["routes"], ["claude-cli"])
            self.assertEqual(trial["requestedModels"], [MODEL])
            self.assertEqual(trial["servedModelsReported"], [MODEL])
            self.assertEqual(trial["pairDiscrimination"]["count"], 0)  # the stub approves everything

    def test_resume_never_reruns_and_interrupted_attempts_are_stops(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            order = sc.load_frozen()[0]["submissionOrder"]
            (h.work / "trial1/attempts" / order[0]).mkdir(parents=True)
            h.run("--execute")
            self.assertEqual(h.ledger()[0]["technicalStop"], "INTERRUPTED_UNKNOWN_STATE")
            self.assertEqual(len(h.calls()), 23)
            code, out = h.run("--execute")
            self.assertEqual(out["skippedAlreadyRecorded"], 24)
            self.assertEqual(len(h.calls()), 23)

    def test_errors_halt_after_three_without_retrying(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp, "error")
            code, out = h.run("--execute")
            self.assertEqual((code, out["status"]), (1, "HALTED_CONSECUTIVE_STOPS"))
            self.assertEqual(len(h.calls()), 3)
            self.assertTrue(all(r["technicalStop"] == "CLAUDE_ERROR:api_error" for r in h.ledger()))

    def test_model_mismatch_is_a_stop_that_keeps_the_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp, "wrongmodel")
            h.run("--execute", "--max-consecutive-stops", "99")
            rows = h.ledger()
            self.assertEqual(len(rows), 24)
            self.assertTrue(all(r["technicalStop"] == "MODEL_MISMATCH" and r["reportSha256"] for r in rows))
            self.assertTrue(all("assessment" not in r for r in rows))  # never scored as the requested model

    def test_unparseable_and_non_json_outputs_are_stops(self):
        for mode, prefix in (("noformat", "UNPARSEABLE_REPORT"), ("garbage", "NO_JSON_OUTPUT")):
            with tempfile.TemporaryDirectory() as tmp:
                h = Harness(tmp, mode)
                h.run("--execute", "--max-consecutive-stops", "99")
                self.assertTrue(all(r["technicalStop"].startswith(prefix) for r in h.ledger()), mode)

    def test_arguments_are_validated(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = Harness(tmp)
            self.assertEqual(h.run(bin_path="claude")[1]["reason"], "CLAUDE_BIN_INVALID")
            h.work = HERE / "work-should-not-exist"
            self.assertEqual(h.run()[1]["reason"], "WORKDIR_INSIDE_REPOSITORY")
            self.assertFalse(h.work.exists())

    def test_driver_never_reads_the_oracle(self):
        self.assertNotIn("oracle.json", (HERE / "run_pilot_claude.py").read_text())


if __name__ == "__main__":
    unittest.main()
