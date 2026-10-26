"""Offline tests for the authoring probe: the prompt, the mechanical checks of an authored pair, and the driver with a stub runtime. No provider calls."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent.parent
REPO = PARENT.parent.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


pr = load("t_probe", HERE / "probe.py")
ck = pr.checker
rg, rp = pr.rg, pr.rp
RUN = json.loads((PARENT / "v3-run-gemini/manifest.json").read_bytes())
BINARY = RUN["binary"]["sha256"]

FACT = ["The record's time-to-live was lowered to 60 seconds forty-eight hours before the cutover window opens for client traffic.",
        "A sample of forty public resolvers was queried afterwards and every one of them honoured the shortened time-to-live."]
DECOY = "The final cost estimate for the new network's egress charges is not final and does not gate any of the cutover work."
REQUIREMENT = "The cutover must leave no more than five minutes in which clients can reach either the old or the new path of the gateway."


def plan_lines(count=38):
    lines = [f"Change step {i} is applied by the platform team to the payment gateway edge configuration during the agreed window." for i in range(count)]
    lines[2] = REQUIREMENT
    lines[10] = DECOY
    lines[19:19] = FACT
    return lines


def make_report(sound=None, twin=None, oracle=None, extra_before="", extra_after="", drop=None):
    sound = plan_lines() if sound is None else sound
    fact_numbers = [i for i, line in enumerate(sound, 1) if line in FACT]
    twin = [line for line in sound if line not in FACT] if twin is None else twin
    fields = {"requirement_line": str(sound.index(REQUIREMENT) + 1) if REQUIREMENT in sound else "3",
              "sound_fact_lines": ", ".join(map(str, fact_numbers)) or "20", "decoy_lines": str(sound.index(DECOY) + 1) if DECOY in sound else "11",
              "decisive_fact": "The time-to-live was lowered ahead of the cutover.", "why_no_fallback": "No other line bounds how long clients keep the old address.",
              "tempting_alternative": "Certificate renewal timing, which is stated and unrelated."}
    fields.update(oracle or {})
    parts = [extra_before, "CASE-BEGIN", "SOUND-BEGIN", *sound, "SOUND-END", "TWIN-BEGIN", *twin, "TWIN-END", "ORACLE-BEGIN",
             *[f"{k}: {v}" for k, v in fields.items()], "ORACLE-END", "CASE-END", extra_after]
    return "\n".join(p for p in parts if p is not None and p != "" or p in ("SOUND-BEGIN",)) + "\n"


class PromptTests(unittest.TestCase):
    def test_the_prompt_states_the_assignment_the_rules_and_the_exact_output_format(self):
        text = (HERE / "author-prompt.txt").read_text(encoding="utf-8")
        for needle in ("moving the public traffic of a payments API", "no more than five minutes", "lowered to 60 seconds", "between 32 and 44 lines",
                       "exactly the SOUND plan with the decisive-fact lines deleted", "CASE-BEGIN", "ORACLE-END", "requirement_line:", "sound_fact_lines:",
                       "decoy_lines:", "decisive_fact:", "why_no_fallback:", "tempting_alternative:"):
            self.assertIn(needle, text)
        self.assertLess(len(text.encode()), 131072)
        self.assertTrue(set(ck.MARKERS) <= set(text.split()))

    def test_the_prompt_never_mentions_the_review_contract_or_the_corpus(self):
        text = (HERE / "author-prompt.txt").read_text(encoding="utf-8").lower()
        for word in ("machine summary", "blockers_found", "no_blockers_found", "v3", "corpus"):
            self.assertNotIn(word, text)


class CheckerTests(unittest.TestCase):
    def failed(self, report):
        result = ck.check(report)
        return sorted(name for name, ok in result["checks"].items() if not ok), result

    def test_a_clean_pair_passes_every_mechanical_check(self):
        bad, result = self.failed(make_report())
        self.assertEqual(bad, [])
        self.assertTrue(result["allPassed"])
        self.assertEqual((result["details"]["soundLines"], result["details"]["twinLines"]), (40, 38))

    def test_a_twin_that_is_not_exactly_the_sound_plan_minus_the_fact_lines_fails(self):
        sound = plan_lines()
        twin = [line for line in sound if line not in FACT]
        twin[5] = twin[5].replace("applied", "performed")
        self.assertIn("TWIN_IS_SOUND_MINUS_FACT_LINES", self.failed(make_report(twin=twin))[0])
        twin = [line for line in sound if line not in FACT] + ["Clients will be moved within an unknown period."]
        self.assertIn("TWIN_IS_SOUND_MINUS_FACT_LINES", self.failed(make_report(twin=twin))[0])
        self.assertIn("TWIN_IS_SOUND_MINUS_FACT_LINES", self.failed(make_report(twin=sound))[0])           # nothing removed

    def test_missing_misordered_or_repeated_markers_fail_everything_else_is_not_reported(self):
        good = make_report()
        for broken in (good.replace("TWIN-END\n", ""), good.replace("SOUND-BEGIN\n", "", 1), good + "CASE-BEGIN\n"):
            result = ck.check(broken)
            self.assertFalse(result["allPassed"])
            self.assertEqual(result["checks"], {"BLOCKS_IN_ORDER": False})

    def test_text_outside_the_case_block_fails(self):
        self.assertIn("NOTHING_OUTSIDE_THE_CASE", self.failed(make_report(extra_before="Here is the case you asked for."))[0])
        self.assertIn("NOTHING_OUTSIDE_THE_CASE", self.failed(make_report(extra_after="I hope this helps."))[0])

    def test_oracle_problems_are_named(self):
        self.assertIn("ORACLE_FIELDS", self.failed(make_report(oracle={"why_no_fallback": ""}))[0])
        self.assertIn("ORACLE_NUMBERS", self.failed(make_report(oracle={"sound_fact_lines": "twenty"}))[0])
        self.assertIn("ORACLE_NUMBERS_IN_RANGE", self.failed(make_report(oracle={"decoy_lines": "99"}))[0])
        self.assertIn("REQUIREMENT_NOT_A_FACT_LINE", self.failed(make_report(oracle={"requirement_line": "20"}))[0])
        self.assertIn("DECOY_PRESENT_AND_APART_FROM_FACT", self.failed(make_report(oracle={"decoy_lines": "20"}))[0])
        self.assertIn("TWIN_IS_SOUND_MINUS_FACT_LINES", self.failed(make_report(oracle={"sound_fact_lines": "20"}))[0])  # the oracle must name every removed line

    def test_length_shape_meta_words_and_admissions_are_checked(self):
        short = plan_lines(12)
        self.assertIn("SOUND_LENGTH", self.failed(make_report(sound=short))[0])
        shaped = plan_lines()
        shaped[4] = "1. " + shaped[4]
        self.assertIn("LINE_SHAPE", self.failed(make_report(sound=shaped))[0])
        shaped = plan_lines()
        shaped[4] = "Short line."
        self.assertIn("LINE_SHAPE", self.failed(make_report(sound=shaped))[0])
        meta = plan_lines()
        meta[6] = meta[6].replace("Change step 6", "The twin of step 6")
        self.assertIn("NO_META_WORDS", self.failed(make_report(sound=meta))[0])
        admitting = plan_lines()
        admitting[7] = "The size of the largest customer batch is unknown at the time of writing and will be settled by the platform team."
        bad, result = self.failed(make_report(sound=admitting))
        self.assertIn("NO_ADMISSIONS_OUTSIDE_DECOY", bad)
        self.assertEqual(result["details"]["admissionLinesOutsideDecoy"], [8])

    def test_the_decoy_line_must_actually_admit_something(self):
        sound = [line.replace("is not final", "is settled") for line in plan_lines()]
        self.assertIn("DECOY_LINE_ADMITS_SOMETHING", self.failed(make_report(sound=sound))[0])

    def test_the_command_line_prints_json_and_refuses_bad_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.md"
            path.write_text(make_report(), encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ck.main([str(path)]), 0)
            self.assertTrue(json.loads(out.getvalue())["allPassed"])
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ck.main([str(path) + ".missing"]), 2)
                self.assertEqual(ck.main([]), 2)

    def test_the_checker_never_reads_a_model_or_the_oracle_of_a_corpus(self):
        source = (HERE / "check_probe_output.py").read_text(encoding="utf-8")
        for word in ("subprocess", "urllib", "socket", "oracle.json"):
            self.assertNotIn(word, source)


STUB = r'''
import json, shutil, sys
from pathlib import Path
here = Path(__file__).resolve().parent
config = json.loads((here / "stub-config.json").read_text())
args = sys.argv[1:]
if args[0] == "prepare":
    packet, seed = Path(args[1]), Path(args[3])
    shutil.copytree(packet.parent, seed / "packet")
    (seed / "CLI-PLAN.json").write_text("{}")
elif args[0] == "run":
    attempt = Path(args[1])
    assert "--authorize-live" in args and "--qualification" in args
    (attempt / "CLI-GATE.json").write_text("{}")
    if config["mode"] == "stop":
        (attempt / "CLI-RECEIPT.json").write_text(json.dumps({"status": "STOPPED", "failure": {"code": "UNQUALIFIED_STEP"}, "closingFailures": []}))
    else:
        report = config["report"].encode("utf-8")
        (attempt / "GEMINI-REVIEW.md").write_bytes(report)
        (attempt / "CLI-RECEIPT.json").write_text(json.dumps({"status": "REPORT_RECEIVED_PENDING_ADJUDICATION", "failure": None, "closingFailures": [],
            "model": "gemini-3.8-flash-high", "effort": "high", "servedAttestation": "UNAVAILABLE", "retries": 0, "invocations": {"proxy": 1, "native": 1},
            "elapsedSeconds": 1.5, "promptDelivery": {"status": "COMPLETE"}}))
'''


class DriverTests(unittest.TestCase):
    def setup(self, tmp, mode="ok", report=None, binary=BINARY, runtime_name="flash-high"):
        tmp = Path(tmp)
        runtime = tmp / "rt" / runtime_name
        (runtime / "scripts").mkdir(parents=True)
        (runtime / "scripts/cli_review.py").write_text(STUB)
        (runtime / "scripts/stub-config.json").write_text(json.dumps({"mode": mode, "report": report if report is not None else make_report()}))
        caps = tmp / "caps"
        caps.mkdir()
        (caps / "RESULT.json").write_text(json.dumps({"status": "PASS_METADATA_CAPABILITIES_ONLY", "binaryStable": True, "frozenBinary": {"sha256": binary, "bytes": 1},
                                                      "observedVersion": "agy 1.4.1", "model": "gemini-3.8-flash-high", "effort": "high"}))
        (tmp / "q.json").write_text("{}")
        original = rg.runtime_tree_sha
        rg.runtime_tree_sha = lambda directory: RUN["runtime"]["treeSha256"]       # the stub is not the real runtime package
        self.addCleanup(lambda: setattr(rg, "runtime_tree_sha", original))
        return runtime, caps

    def run_probe(self, tmp, runtime, caps, *extra, work="work"):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = pr.main(["--runtime-dir", str(runtime), "--capabilities", str(caps), "--qualification", str(Path(tmp) / "q.json"),
                            "--workdir", str(Path(tmp) / work), *extra])
        return code, json.loads(out.getvalue().strip().splitlines()[-1])

    def test_a_dry_run_prepares_the_packet_and_makes_no_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp)
            code, out = self.run_probe(tmp, runtime, caps)
            self.assertEqual((code, out["status"], out["executed"], out["providerCalls"]), (0, "DRY_RUN_PREPARED_ONLY", False, 0))
            self.assertEqual(out["promptSha256"], rp.sha((HERE / "author-prompt.txt").read_bytes()))
            work = Path(tmp) / "work"
            self.assertTrue((work / "seed/packet/prompt.txt").is_file())
            self.assertFalse((work / "attempt").exists() or (work / "PROBE-SUMMARY.json").exists())
            descriptor = json.loads((work / "packet/PACKET.json").read_bytes())
            self.assertEqual((descriptor["questions"], [s["id"] for s in descriptor["sources"]]), (["Q01"], ["S01"]))

    def test_the_live_call_saves_the_report_the_summary_and_the_mechanical_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp)
            code, out = self.run_probe(tmp, runtime, caps, "--execute")
            self.assertEqual((code, out["status"], out["executed"], out["technicalStop"]), (0, "COMPLETE", True, None))
            work = Path(tmp) / "work"
            self.assertEqual((work / "PROBE-OUTPUT.md").read_text(encoding="utf-8"), make_report())
            summary = json.loads((work / "PROBE-SUMMARY.json").read_bytes())
            self.assertTrue(summary["mechanicalChecks"]["allPassed"])
            self.assertEqual((summary["receipt"]["status"], summary["receipt"]["retries"], summary["receipt"]["servedAttestation"]),
                             ("REPORT_RECEIVED_PENDING_ADJUDICATION", 0, "UNAVAILABLE"))
            self.assertEqual(summary["reportSha256"], rp.sha(make_report().encode()))

    def test_a_report_that_fails_the_mechanical_checks_is_still_saved_and_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, report="I cannot write test cases, but here is a review: no blockers found.")
            code, out = self.run_probe(tmp, runtime, caps, "--execute")
            self.assertEqual((code, out["status"]), (0, "COMPLETE"))
            self.assertFalse(out["mechanicalChecks"]["allPassed"])
            self.assertTrue((Path(tmp) / "work/PROBE-OUTPUT.md").is_file())

    def test_a_runtime_stop_is_recorded_not_retried(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, mode="stop")
            code, out = self.run_probe(tmp, runtime, caps, "--execute")
            self.assertEqual((code, out["status"]), (1, "STOPPED"))
            self.assertTrue(out["technicalStop"].startswith("RUNTIME_STOP:"))
            self.assertFalse((Path(tmp) / "work/PROBE-OUTPUT.md").exists())
            code, out = self.run_probe(tmp, runtime, caps, "--execute")
            self.assertEqual((code, out["reason"]), (1, "PROBE_ALREADY_RUN"))

    def test_a_second_call_or_a_reused_directory_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp)
            self.assertEqual(self.run_probe(tmp, runtime, caps)[0], 0)                         # the dry run
            code, out = self.run_probe(tmp, runtime, caps, "--execute")                         # same directory
            self.assertEqual((code, out["reason"]), (1, "WORKDIR_MUST_BE_NEW"))
            code, out = self.run_probe(tmp, runtime, caps, "--execute", work="live")
            self.assertEqual(code, 0)
            code, out = self.run_probe(tmp, runtime, caps, "--execute", work="live")
            self.assertEqual((code, out["reason"]), (1, "PROBE_ALREADY_RUN"))

    def test_identity_is_bound_to_the_v3_gemini_runtime_and_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, binary="0" * 64)
            code, out = self.run_probe(tmp, runtime, caps, "--execute")
            self.assertEqual((code, out["reason"]), (1, "RUN_BINARY_MISMATCH"))
            self.assertFalse((Path(tmp) / "work/attempt").exists())
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, runtime_name="argon-high")
            code, out = self.run_probe(tmp, runtime, caps, "--execute")
            self.assertEqual((code, out["reason"]), (1, "RUN_RUNTIME_NOT_FLASH_HIGH"))

    def test_the_workdir_may_not_be_inside_the_repository(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = pr.main(["--runtime-dir", str(runtime), "--capabilities", str(caps), "--qualification", str(Path(tmp) / "q.json"),
                                "--workdir", str(REPO / "probe-workdir-must-not-exist"), "--execute"])
            self.assertEqual((code, json.loads(out.getvalue())["reason"]), (1, "WORKDIR_INSIDE_REPOSITORY"))
            self.assertFalse((REPO / "probe-workdir-must-not-exist").exists())


class RunScriptTests(unittest.TestCase):
    """The gated helper script: its pinned expectations match the repository, it refuses ungated live calls, and its dry stage needs the host stage first."""
    SCRIPT = HERE / "run.sh"

    def sh(self, *args, root=None):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ROOT=str(root or Path(tmp) / "root"), AGY="/nonexistent/agy")
            done = subprocess.run(["bash", str(self.SCRIPT), *args], capture_output=True, text=True, env=env, cwd=REPO, check=False, timeout=300)
            return done.returncode, done.stdout, done.stderr

    def test_the_pinned_expectations_match_the_repository(self):
        text = self.SCRIPT.read_text(encoding="utf-8")
        self.assertIn("EXPECT_PROMPT_SHA=" + rp.sha((HERE / "author-prompt.txt").read_bytes()), text)
        self.assertIn("EXPECT_RUN_SHA=" + rp.sha((PARENT / "v3-run-gemini/manifest.json").read_bytes()), text)
        self.assertIn("EXPECT_AGY_SHA=" + BINARY, text)
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for value in (rp.sha((HERE / "author-prompt.txt").read_bytes()), rp.sha((PARENT / "v3-run-gemini/manifest.json").read_bytes()), BINARY):
            self.assertIn(value, brief)
        self.assertTrue(self.SCRIPT.stat().st_mode & 0o111)

    def test_the_live_call_needs_the_go_flag_and_the_host_stage(self):
        code, out, err = self.sh("live")
        self.assertEqual((code, "REFUSED" in err), (2, True))
        code, out, err = self.sh("live", "--go")
        self.assertEqual((code, "RUN_HOST_FIRST" in err), (2, True))
        code, out, err = self.sh("dry")
        self.assertEqual((code, "RUN_HOST_FIRST" in err), (2, True))
        self.assertEqual(self.sh()[0], 2)

    def test_the_checks_stop_before_anything_when_the_binary_is_missing_and_bundling_needs_a_run(self):
        code, out, err = self.sh("checks")
        self.assertEqual(code, 1)
        self.assertTrue("MISMATCH:agy-sha" in err or "MISMATCH:clean-tree" in err)
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.sh("bundle", root=Path(tmp) / "empty")
            self.assertEqual((code, "NOTHING_TO_BUNDLE" in err), (1, True))

    def test_diag_reports_start_up_time_and_load_without_a_model_call(self):
        code, out, err = self.sh("diag")
        self.assertEqual(code, 0, err)
        self.assertRegex(out, r"DIAG python start-up ms: median \d+, p90 \d+, max \d+; load average [\d. ]+; cpus \d+")

    def test_the_brief_documents_the_known_qualification_flake_and_a_single_authorized_rerun(self):
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for needle in ("OFFLINE_RUN_2_STOPPED", "FULL_JSON_FRAME_ACCOUNTED", "0.5 seconds", "Do not retry on your own", "**new** `ROOT`", "$B diag"):
            self.assertIn(needle, brief)

    def test_the_brief_names_the_one_call_and_the_rules(self):
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for needle in ("One live call in total", "stop and send the exact output", "never run it twice", "live --go"):
            self.assertIn(needle, brief)


RESULTS = HERE / "results"


class CommittedResultTests(unittest.TestCase):
    """The committed probe result is the one the write-up describes: hashes, receipt, and the mechanical checks recomputed from the saved report."""

    def test_the_saved_report_hashes_to_the_summary_and_the_receipt_is_clean(self):
        summary = json.loads((RESULTS / "PROBE-SUMMARY.json").read_bytes())
        report = (RESULTS / "PROBE-OUTPUT.md").read_bytes()
        self.assertEqual((rp.sha(report), len(report)), (summary["reportSha256"], summary["reportBytes"]))
        self.assertEqual(summary["promptSha256"], rp.sha((HERE / "author-prompt.txt").read_bytes()))
        self.assertEqual(summary["runManifestSha256"], rp.sha((PARENT / "v3-run-gemini/manifest.json").read_bytes()))
        receipt = json.loads((RESULTS / "CLI-RECEIPT.json").read_bytes())
        self.assertEqual((receipt["status"], receipt["failure"], receipt["closingFailures"], receipt["retries"], receipt["invocations"]),
                         ("REPORT_RECEIVED_PENDING_ADJUDICATION", None, [], 0, {"proxy": 1, "native": 1}))
        self.assertEqual(receipt["native"]["sha256"], BINARY)
        self.assertEqual(receipt["report"]["sha256"], summary["reportSha256"])
        self.assertIsNone(summary["technicalStop"])

    def test_the_mechanical_checks_recomputed_from_the_saved_report_are_the_recorded_ones(self):
        summary = json.loads((RESULTS / "PROBE-SUMMARY.json").read_bytes())
        recomputed = ck.check((RESULTS / "PROBE-OUTPUT.md").read_text(encoding="utf-8"))
        self.assertEqual(recomputed, summary["mechanicalChecks"])
        self.assertTrue(recomputed["allPassed"])
        self.assertEqual((recomputed["details"]["soundLines"], recomputed["details"]["twinLines"]), (36, 34))

    def test_the_write_up_names_the_returned_archive_and_the_two_defects_it_found_in_the_prompt(self):
        text = (RESULTS / "RESULT.md").read_text(encoding="utf-8")
        for needle in ("f6ae439d51ce5817f0bd78126b9ca34b494dec8142ac2b7cdc45ab67fed3af93", "works as a generator", "The requirement sentence is ambiguous",
                       "`tempting_alternative` was misread", "One sample"):
            self.assertIn(needle, text)


if __name__ == "__main__":
    unittest.main()
