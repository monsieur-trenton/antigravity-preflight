"""Offline tests for the bare-arm ablation: frozen files, driver, verifier, scorer and analysis. No provider calls."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
V2 = PARENT / "v2"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


an = load("abl_analyze", HERE / "analyze.py")
rc = load("abl_driver", PARENT / "run_pilot_claude.py")
sc = load("abl_score", PARENT / "score.py")
vr = load("abl_verify", PARENT / "verify_run.py")
claude_tests = load("abl_claude_tests", PARENT / "test_run_pilot_claude.py")
ORACLE = {c["case"]: c for c in json.loads((V2 / "oracle/oracle.json").read_bytes())["cases"]}
MODEL = claude_tests.MODEL


class FrozenFilesTests(unittest.TestCase):
    def test_manifest_is_current_and_tied_to_the_v2_corpus(self):
        build = load("abl_build", HERE / "build_manifest.py")
        self.assertEqual((HERE / "manifest.json").read_bytes(), build.build())
        manifest = json.loads((HERE / "manifest.json").read_bytes())
        self.assertEqual(manifest["corpus"]["manifestSha256"], rc.rp.sha((V2 / "manifest.json").read_bytes()))
        self.assertEqual(sorted(manifest["pins"]), ["PREREGISTRATION.md", "bare-request.txt", "bare-system.txt", "rubric.json"])

    def test_bare_request_is_actually_bare(self):
        arm = rc.load_arm("bare")
        case = next(iter(ORACLE))
        lines = (V2 / "packets" / (case + ".txt")).read_text().splitlines()
        request = arm["build"]("ignored corpus prompt", lines).decode("utf-8")
        for line in lines:
            self.assertIn(line, request)
        self.assertNotIn("[S01:", request)
        self.assertNotIn("ignored corpus prompt", request)
        for word in ("BLOCKER", "RISK", "VERIFIED", "UNVERIFIED", "CANNOT_CHECK", "evidence", "snapshot", "MACHINE SUMMARY", "contract"):
            self.assertNotIn(word, request, word)
        self.assertTrue(request.startswith("Please review this plan."))
        self.assertIn("VERDICT: NO_GO", request)
        self.assertEqual(arm["system"], "You are a helpful assistant.")

    def test_the_rubric_covers_every_family_and_compiles(self):
        import re
        rubric = json.loads((HERE / "rubric.json").read_bytes())["families"]
        self.assertEqual(set(rubric), {c["family"] for c in ORACLE.values()})
        for groups in rubric.values():
            for group in groups:
                for pattern in group:
                    re.compile(pattern)

    def test_tampered_bare_prompt_or_wrong_corpus_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "ablation"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            (copy / "bare-system.txt").write_text("You are an expert reviewer.\n", encoding="utf-8")
            original = rc.ABLATION
            rc.ABLATION = copy
            try:
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_arm("bare")
                self.assertEqual(str(raised.exception), "ABLATION_PIN_MISMATCH:bare-system.txt")
            finally:
                rc.ABLATION = original
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp)
            code, out = h.run("--arm", "bare")  # default corpus is v1, which the bare arm is not pinned to
            self.assertEqual((code, out["reason"]), (1, "ABLATION_CORPUS_MISMATCH"))


DEFINED = HERE / "defined"
DEFINITION_BLOCK = ["Verdicts mean this:",
                    "GO: the plan needs no changes.",
                    "GO_WITH_CHANGES: the plan works as written but should be improved.",
                    "NO_GO: the plan as written will fail or break a rule it states.",
                    ""]


class DefinedArmFrozenFilesTests(unittest.TestCase):
    def test_defined_request_differs_from_bare_by_exactly_the_definition_block(self):
        import difflib
        case = next(iter(ORACLE))
        lines = (V2 / "packets" / (case + ".txt")).read_text().splitlines()
        bare = rc.load_arm("bare")["build"]("x", lines).decode("utf-8").splitlines()
        defined = rc.load_arm("defined")["build"]("x", lines).decode("utf-8").splitlines()
        added = [l[2:] for l in difflib.ndiff(bare, defined) if l.startswith("+ ")]
        removed = [l for l in difflib.ndiff(bare, defined) if l.startswith("- ")]
        self.assertEqual((added, removed), (DEFINITION_BLOCK[:-1] + [""] if added[-1:] == [""] else DEFINITION_BLOCK[:-1], []))
        for word in ("evidence", "snapshot", "BLOCKER", "VERIFIED", "[S01:", "citation", "quote"):
            self.assertNotIn(word, "\n".join(defined), word)

    def test_system_prompt_is_identical_to_the_bare_arm(self):
        self.assertEqual(rc.load_arm("defined")["system"], rc.load_arm("bare")["system"])
        self.assertEqual(rc.load_arm("defined")["system"], "You are a helpful assistant.")

    def test_manifest_is_current_tied_to_the_corpus_and_borrows_the_bare_files_by_hash(self):
        build = load("abl_defined_build", DEFINED / "build_manifest.py")
        self.assertEqual((DEFINED / "manifest.json").read_bytes(), build.build())
        manifest = json.loads((DEFINED / "manifest.json").read_bytes())
        bare_pins = json.loads((HERE / "manifest.json").read_bytes())["pins"]
        self.assertEqual(manifest["corpus"]["manifestSha256"], rc.rp.sha((V2 / "manifest.json").read_bytes()))
        self.assertEqual(manifest["borrowed"], {k: bare_pins[k] for k in ("bare-system.txt", "rubric.json")})
        self.assertEqual(sorted(manifest["pins"]), ["PREREGISTRATION.md", "defined-request.txt"])

    def test_the_bare_arms_own_manifest_is_untouched_so_its_evidence_still_verifies(self):
        manifest = json.loads((HERE / "manifest.json").read_bytes())
        self.assertEqual(manifest["pins"]["bare-request.txt"], "13e4760dcb101c98f67879e2dee6e42c39fbfa42acd11c10d1be2e67f00d5fc7")
        self.assertEqual(rc.rp.sha((HERE / "manifest.json").read_bytes()), "35d7ea8dd779078b95b3c854da645f3039f91bec2cec068c8f9355fab4c4dcbb")

    def test_tampering_with_the_request_or_a_borrowed_file_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "ablation"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            originals = (rc.ABLATION, rc.DEFINED)
            try:
                rc.ABLATION, rc.DEFINED = copy, copy / "defined"
                (copy / "defined" / "defined-request.txt").write_text("{plan}\nVERDICT: GO\n", encoding="utf-8")
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_arm("defined")
                self.assertEqual(str(raised.exception), "ABLATION_PIN_MISMATCH:defined-request.txt")
                shutil.copy(DEFINED / "defined-request.txt", copy / "defined" / "defined-request.txt")
                (copy / "bare-system.txt").write_text("You are an expert reviewer.\n", encoding="utf-8")
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_arm("defined")
                self.assertEqual(str(raised.exception), "ABLATION_PIN_MISMATCH:bare-system.txt")
            finally:
                rc.ABLATION, rc.DEFINED = originals


class DefinedArmDriverTests(unittest.TestCase):
    def run_defined(self, tmp, verdict="GO_WITH_CHANGES", *extra):
        h = claude_tests.Harness(tmp)
        (h.bin.parent / "stub-config.json").write_text(json.dumps({"mode": "ok", "log": str(h.log), "model": MODEL, "verdict": verdict}))
        code, out = h.run("--arm", "defined", "--corpus", str(V2), "--execute", *extra)
        return h, code, out

    def test_defined_run_uses_the_defined_prompt_and_the_bare_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_defined(tmp, "NO_GO")
            self.assertEqual((code, out["executed"], out["arm"]), (0, 40, "defined"))
            for call in h.calls():
                argv = call["argv"]
                self.assertEqual(argv[argv.index("--system-prompt") + 1], "You are a helpful assistant.")
                self.assertEqual(argv[argv.index("--tools") + 1], "")
                self.assertIn("NO_GO: the plan as written will fail or break a rule it states.", call["stdin"])
                self.assertNotIn("[S01:", call["stdin"])
            manifest_sha = rc.rp.sha((DEFINED / "manifest.json").read_bytes())
            self.assertTrue(all(r["arm"] == "defined" and r["armManifestSha256"] == manifest_sha for r in h.ledger()))

    def test_defined_ledger_scores_verifies_and_the_wrong_arm_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _, _ = self.run_defined(tmp, "NO_GO")
            result = sc.score(h.ledger(), V2)["trials"]["1"]
            self.assertEqual(result["arms"], ["defined"])
            self.assertEqual(result["verdictOnly"]["soundBlocked"]["count"], 20)
            self.assertEqual(vr.verify(V2, h.work, MODEL, "high", [1], "defined")["failures"], [])
            self.assertTrue(vr.verify(V2, h.work, MODEL, "high", [1], "bare")["failures"])  # same prompt family, different arm

    def test_defined_arm_refuses_another_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp)
            code, out = h.run("--arm", "defined")
            self.assertEqual((code, out["reason"]), (1, "ABLATION_CORPUS_MISMATCH"))


DEFINED_GO = HERE / "defined-go"
OPTIONAL_SENTENCE = "Optional suggestions that only make a working plan more robust are not changes it needs; if that is all you have, the verdict is GO."


class FourthArmFrozenFilesTests(unittest.TestCase):
    def test_request_differs_from_the_defined_arm_by_exactly_one_sentence(self):
        import difflib
        case = next(iter(ORACLE))
        lines = (V2 / "packets" / (case + ".txt")).read_text().splitlines()
        defined = rc.load_arm("defined")["build"]("x", lines).decode("utf-8").splitlines()
        fourth = rc.load_arm("defined-go")["build"]("x", lines).decode("utf-8").splitlines()
        diff = [l for l in difflib.ndiff(defined, fourth) if l[:2] in ("+ ", "- ")]
        self.assertEqual(diff, ["+ " + OPTIONAL_SENTENCE])
        self.assertEqual(fourth.index(OPTIONAL_SENTENCE), fourth.index("NO_GO: the plan as written will fail or break a rule it states.") + 1)
        self.assertEqual(rc.load_arm("defined-go")["system"], "You are a helpful assistant.")

    def test_manifest_is_current_tied_to_the_corpus_and_borrows_the_bare_files_by_hash(self):
        build = load("abl_defined_go_build", DEFINED_GO / "build_manifest.py")
        self.assertEqual((DEFINED_GO / "manifest.json").read_bytes(), build.build())
        manifest = json.loads((DEFINED_GO / "manifest.json").read_bytes())
        bare_pins = json.loads((HERE / "manifest.json").read_bytes())["pins"]
        self.assertEqual(manifest["corpus"]["manifestSha256"], rc.rp.sha((V2 / "manifest.json").read_bytes()))
        self.assertEqual(manifest["borrowed"], {k: bare_pins[k] for k in ("bare-system.txt", "rubric.json")})
        self.assertEqual(sorted(manifest["pins"]), ["PREREGISTRATION.md", "defined-go-request.txt"])

    def test_the_earlier_arms_manifests_are_untouched_so_their_evidence_still_verifies(self):
        self.assertEqual(rc.rp.sha((HERE / "manifest.json").read_bytes()), "35d7ea8dd779078b95b3c854da645f3039f91bec2cec068c8f9355fab4c4dcbb")
        self.assertEqual(rc.rp.sha((DEFINED / "manifest.json").read_bytes()), "60f9268660ec0fb2fd545d2c835d5997eaa2f1362a798af7e92a43415d817484")

    def test_tampering_with_the_request_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "ablation"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            original = rc.DEFINED_GO, rc.ABLATION
            try:
                rc.ABLATION, rc.DEFINED_GO = copy, copy / "defined-go"
                (copy / "defined-go" / "defined-go-request.txt").write_text("{plan}\nVERDICT: GO\n", encoding="utf-8")
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_arm("defined-go")
                self.assertEqual(str(raised.exception), "ABLATION_PIN_MISMATCH:defined-go-request.txt")
            finally:
                rc.DEFINED_GO, rc.ABLATION = original


class FourthArmDriverTests(unittest.TestCase):
    def run_arm(self, tmp, verdict="GO", *extra):
        h = claude_tests.Harness(tmp)
        (h.bin.parent / "stub-config.json").write_text(json.dumps({"mode": "ok", "log": str(h.log), "model": MODEL, "verdict": verdict}))
        code, out = h.run("--arm", "defined-go", "--corpus", str(V2), "--execute", *extra)
        return h, code, out

    def test_run_uses_the_fourth_prompt_and_the_bare_isolation_and_stamps_its_own_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_arm(tmp)
            self.assertEqual((code, out["executed"], out["arm"]), (0, 40, "defined-go"))
            for call in h.calls():
                argv = call["argv"]
                self.assertEqual(argv[argv.index("--system-prompt") + 1], "You are a helpful assistant.")
                self.assertEqual(argv[argv.index("--tools") + 1], "")
                self.assertIn(OPTIONAL_SENTENCE, call["stdin"])
            manifest_sha = rc.rp.sha((DEFINED_GO / "manifest.json").read_bytes())
            self.assertTrue(all(r["arm"] == "defined-go" and r["armManifestSha256"] == manifest_sha for r in h.ledger()))

    def test_ledger_scores_as_verdict_only_verifies_and_the_wrong_arm_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _, _ = self.run_arm(tmp)
            result = sc.score(h.ledger(), V2)["trials"]["1"]
            self.assertEqual(result["arms"], ["defined-go"])
            self.assertEqual(result["verdictOnly"]["soundClean"]["count"], 20)
            self.assertEqual(vr.verify(V2, h.work, MODEL, "high", [1], "defined-go")["failures"], [])
            self.assertTrue(vr.verify(V2, h.work, MODEL, "high", [1], "defined")["failures"])

    def test_refuses_another_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp)
            code, out = h.run("--arm", "defined-go")
            self.assertEqual((code, out["reason"]), (1, "ABLATION_CORPUS_MISMATCH"))


class FourthArmAnalysisTests(unittest.TestCase):
    def analysis(self, first, second):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            write_arm(a, first)
            write_arm(b, second)
            return an.analyze(V2, {"first": a, "second": b})

    def test_strict_and_defect_twin_metrics_are_added_beside_the_existing_ones(self):
        hedges_sound = lambda truth: "CHANGES_RECOMMENDED" if truth["expectedClass"] == "SOUND" else ideal(truth)
        block = self.analysis(hedges_sound, ideal)["allPairs"]
        self.assertEqual((block["strictPairDiscrimination"]["first"]["count"], block["strictPairDiscrimination"]["second"]["count"]), (0, 40))
        self.assertEqual((block["strictPaired"]["onlyFirst"], block["strictPaired"]["onlySecond"]), (0, 40))
        self.assertEqual((block["defectTwinsBlocked"]["second"]["count"], block["defectTwinsBlocked"]["second"]["of"]), (36, 36))
        self.assertEqual(block["defectTwinBlockedPaired"]["onlyFirst"] + block["defectTwinBlockedPaired"]["onlySecond"], 0)

    def label(self, vs_defined, vs_skill):
        wrap = lambda clean, lost: {"allPairs": {"soundCleanPaired": clean, "changedTwinCorrectPaired": lost}}
        paired = lambda first, second: {"onlyFirst": first, "onlySecond": second, "exactTwoSidedSignTestP": an.sign_test(first, second)}
        return an.fourth_arm_label(wrap(paired(*vs_defined[0]), paired(*vs_defined[1])), wrap(paired(*vs_skill), paired(0, 0)))

    def test_preregistered_labels_in_order(self):
        # vs_defined = ((clean onlyFirst=defined, onlySecond=defined-go), (correct-twin onlyFirst=defined, onlySecond=defined-go))
        self.assertEqual(self.label(((0, 14), (0, 0)), (3, 0)), "closes the sound-plan gap")
        self.assertEqual(self.label(((0, 14), (0, 0)), (5, 0)), "closes the sound-plan gap")
        self.assertEqual(self.label(((0, 14), (0, 0)), (6, 0)), "partly closes the sound-plan gap")
        self.assertEqual(self.label(((1, 5), (0, 0)), (3, 0)), "does not close the sound-plan gap")      # 5 against 1, p = 0.22
        self.assertEqual(self.label(((0, 0), (0, 0)), (16, 0)), "does not close the sound-plan gap")
        self.assertEqual(self.label(((9, 0), (0, 0)), (16, 0)), "worse on sound plans")
        self.assertEqual(self.label(((0, 14), (3, 0)), (0, 0)), "costs detection")                      # a cleaner result does not rescue it
        self.assertEqual(self.label(((0, 14), (2, 0)), (0, 0)), "closes the sound-plan gap")            # two lost twins is below the guard


class ParserTests(unittest.TestCase):
    def test_verdict_line_is_the_only_hook(self):
        for text, raw in (("Review.\nVERDICT: GO", "GO"), ("x\n**VERDICT: GO_WITH_CHANGES**\n", "GO_WITH_CHANGES"),
                          ("x\n`VERDICT: NO_GO`", "NO_GO"), ("x\n\nVERDICT:NO_GO\n\n", "NO_GO")):
            self.assertEqual(rc.parse_bare(text)["verdictRaw"], raw, text)
        mapped = rc.parse_bare("a\nVERDICT: GO_WITH_CHANGES")
        self.assertEqual((mapped["assessment"], mapped["findings"], mapped["completeness"]), ("CHANGES_RECOMMENDED", [], "COMPLETE"))
        for bad in ("", "no verdict here", "VERDICT: GO\nThanks for asking!", "VERDICT: MAYBE", "verdict: go", "VERDICT: GOOD"):
            with self.assertRaises(rc.rp.Stop, msg=bad):
                rc.parse_bare(bad)


class DriverTests(unittest.TestCase):
    def run_bare(self, tmp, verdict="GO", *extra):
        h = claude_tests.Harness(tmp)
        (h.bin.parent / "stub-config.json").write_text(json.dumps({"mode": "ok", "log": str(h.log), "model": MODEL, "verdict": verdict}))
        code, out = h.run("--arm", "bare", "--corpus", str(V2), "--execute", *extra)
        return h, code, out

    def test_bare_run_uses_the_bare_prompt_and_the_same_isolation(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_bare(tmp, "GO_WITH_CHANGES")
            self.assertEqual((code, out["executed"], out["stopped"], out["arm"]), (0, 40, 0, "bare"))
            for call in h.calls():
                argv = call["argv"]
                self.assertEqual(argv[argv.index("--system-prompt") + 1], "You are a helpful assistant.")
                self.assertEqual(argv[argv.index("--tools") + 1], "")
                for flag in ("--safe-mode", "--no-session-persistence", "--disable-slash-commands", "--strict-mcp-config"):
                    self.assertIn(flag, argv)
                self.assertEqual(argv[argv.index("--model") + 1], MODEL)
                self.assertNotIn("[S01:", call["stdin"])
                self.assertNotIn("oracle", call["stdin"].lower())
            rows = h.ledger()
            self.assertTrue(all(r["arm"] == "bare" and r["assessment"] == "CHANGES_RECOMMENDED" and r["findings"] == [] and r["armManifestSha256"]
                                for r in rows))

    def test_ledger_scores_and_verifies_as_the_bare_arm(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _, _ = self.run_bare(tmp, "NO_GO")
            result = sc.score(h.ledger(), V2)["trials"]["1"]
            self.assertEqual(result["arms"], ["bare"])
            self.assertEqual(result["falseBlockersOnSoundPlans"]["count"], 20)  # NO_GO on every sound plan
            self.assertEqual(result["verdictOnly"]["soundBlocked"]["count"], 20)
            self.assertEqual(result["verdictOnly"]["pairOrderedVerdictOnly"]["count"], 0)
            report = vr.verify(V2, h.work, MODEL, "high", [1], "bare")
            self.assertEqual(report["failures"], [])
            self.assertTrue(vr.verify(V2, h.work, MODEL, "high", [1], "skill")["failures"])  # the wrong arm is caught

    def test_a_missing_verdict_line_is_a_technical_stop_not_a_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp, "noformat")
            code, out = h.run("--arm", "bare", "--corpus", str(V2), "--execute", "--max-consecutive-stops", "99")
            rows = h.ledger()
            self.assertEqual(len(rows), 40)
            self.assertTrue(all(r["technicalStop"] == "UNPARSEABLE_REPORT:NO_VERDICT_LINE" and "assessment" not in r for r in rows))

    def test_a_second_served_model_beside_the_requested_one_is_a_stop(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp, "twomodels")
            h.run("--arm", "bare", "--corpus", str(V2), "--execute", "--max-consecutive-stops", "99")
            rows = h.ledger()
            self.assertTrue(all(r["technicalStop"] == "MODEL_MISMATCH" and r["reportSha256"] and "assessment" not in r for r in rows))
            self.assertEqual(rows[0]["servedModels"], sorted([MODEL, "claude-other"]))

    def test_a_safety_interruption_is_named_and_never_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp, "safety")
            h.run("--arm", "bare", "--corpus", str(V2), "--execute", "--max-consecutive-stops", "99")
            rows = h.ledger()
            self.assertTrue(all(r["technicalStop"] == "SAFETY_INTERRUPTED:1" and "assessment" not in r for r in rows))
            report = vr.verify(V2, h.work, MODEL, "high", [1], "bare")
            self.assertEqual(report["failures"], [])  # recorded as a stop, so the verifier accepts it

    def test_default_arm_is_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp)
            code, out = h.run("--corpus", str(V2), "--execute")
            self.assertEqual((code, out["arm"]), (0, "skill"))
            self.assertTrue(all(r["arm"] == "skill" for r in h.ledger()))


class ScorerTests(unittest.TestCase):
    def grade(self, role_class, verdict):
        truth = next(t for t in ORACLE.values() if t["expectedClass"] == role_class)
        row = {"case": truth["case"], "arm": "bare", "completeness": "COMPLETE", "findings": [], "assessment": verdict}
        return sc.grade(row, truth, V2)[0]

    def test_bare_verdict_grading(self):
        self.assertEqual(self.grade("SOUND", "NO_BLOCKERS_FOUND"), "CORRECT")
        self.assertEqual(self.grade("SOUND", "CHANGES_RECOMMENDED"), "HEDGED")
        self.assertEqual(self.grade("SOUND", "BLOCKERS_FOUND"), "FALSE_BLOCKER")
        self.assertEqual(self.grade("DEFECT", "BLOCKERS_FOUND"), "CORRECT")
        self.assertEqual(self.grade("DEFECT", "CHANGES_RECOMMENDED"), "MISSED")
        self.assertEqual(self.grade("UNCERTAIN", "CHANGES_RECOMMENDED"), "CORRECT")
        self.assertEqual(self.grade("UNCERTAIN", "BLOCKERS_FOUND"), "OVERCLAIMED")
        self.assertEqual(self.grade("UNCERTAIN", "NO_BLOCKERS_FOUND"), "MISSED")


def write_arm(directory, policy, model=MODEL, report=lambda truth: "report text"):
    for trial in (1, 2):
        (directory / f"trial{trial}/reports").mkdir(parents=True)
        lines = []
        for case, truth in ORACLE.items():
            lines.append(json.dumps({"case": case, "trial": trial, "assessment": policy(truth), "completeness": "COMPLETE", "findings": [],
                                     "requestedModel": model, "effort": "high", "claudeVersion": "9.9", "servedModels": [model], "costUsd": 0.01}))
            (directory / f"trial{trial}/reports/{case}.md").write_text(report(truth), encoding="utf-8")
        (directory / f"trial{trial}/responses.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ideal(truth):
    return {"SOUND": "NO_BLOCKERS_FOUND", "DEFECT": "BLOCKERS_FOUND", "UNCERTAIN": "CHANGES_RECOMMENDED"}[truth["expectedClass"]]


def blocks_everything(truth):
    return "BLOCKERS_FOUND"


SAMPLE_REPORTS = {
    "output_bytes": "three values of 700 bytes exceed 1500",
    "required_coverage": "only changed sources, not the inventory",
    "ownership_authorization": "the fixed nightly tag matches concurrent runs",
    "absent_vs_null": "null and absent both become 0",
    "caller_callee": "main still checks None but ConfigError is raised",
    "deadline_arithmetic": "22 + 18 + 12 = 52 minutes against 45",
    "migration_order": "NOT NULL in step 3 runs before the step 2 backfill",
    "unit_mismatch": "the timeout is in milliseconds so timeout=5 is 5 ms",
    "permission_chain": "support-lead also gets the scope finance-admin should hold",
    "runtime_budget": "throughput is not measured; 22 MB/s is needed",
}


class SampleReportTests(unittest.TestCase):
    def test_every_sample_report_satisfies_its_own_rubric_so_the_helper_cannot_rot(self):
        rubric = json.loads((HERE / "rubric.json").read_bytes())["families"]
        self.assertEqual(set(SAMPLE_REPORTS), set(rubric))
        for family, text in SAMPLE_REPORTS.items():
            self.assertTrue(all(any(re.search(p, text, re.I) for p in group) for group in rubric[family]), family)


class AnalysisTests(unittest.TestCase):
    def analyze(self, first, second, excluded=(), **kw):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            write_arm(a, first)
            write_arm(b, second, **kw)
            return an.analyze(V2, {"skill": a, "bare": b}, excluded)

    def test_sign_test_values(self):
        self.assertEqual(an.sign_test(0, 0), 1.0)
        self.assertEqual(an.sign_test(6, 0), 0.0312)
        self.assertEqual(an.sign_test(5, 0), 0.0625)
        self.assertEqual(an.sign_test(8, 3), 0.2266)
        self.assertEqual(an.sign_test(4, 4), 1.0)

    def test_identical_arms_have_no_discordance(self):
        r = self.analyze(ideal, ideal)
        paired = r["allPairs"]["primaryPaired"]
        self.assertEqual((paired["matchedUnits"], paired["onlyFirst"], paired["onlySecond"], paired["exactTwoSidedSignTestP"]), (40, 0, 0, 1.0))
        self.assertEqual(r["allPairs"]["primaryOrdinalPairDiscrimination"]["skill"]["count"], 40)
        self.assertTrue(r["comparability"]["sameModelEffortAndCliVersion"])

    def test_an_over_blocking_arm_loses_every_unit(self):
        r = self.analyze(ideal, blocks_everything)
        paired = r["allPairs"]["primaryPaired"]
        self.assertEqual((paired["onlyFirst"], paired["onlySecond"]), (40, 0))
        self.assertLess(paired["exactTwoSidedSignTestP"], 1e-9)
        self.assertEqual(r["allPairs"]["soundPlansBlocked"]["bare"]["count"], 40)
        self.assertEqual(r["allPairs"]["soundPlansBlocked"]["skill"]["count"], 0)
        self.assertEqual(r["allPairs"]["soundNotBlockedPaired"]["onlyFirst"], 40)

    def test_a_better_bare_arm_is_reported_in_its_direction(self):
        r = self.analyze(blocks_everything, ideal)
        paired = r["allPairs"]["primaryPaired"]
        self.assertEqual((paired["onlyFirst"], paired["onlySecond"]), (0, 40))

    def test_exclusion_gives_an_adjusted_view_beside_the_headline(self):
        r = self.analyze(ideal, ideal, excluded=["caller_callee"])
        self.assertEqual(r["allPairs"]["primaryPaired"]["matchedUnits"], 40)
        self.assertEqual(r["adjusted"]["primaryPaired"]["matchedUnits"], 36)
        self.assertEqual(r["excludedFamilies"], ["caller_callee"])

    def test_comparability_flags_a_different_model(self):
        r = self.analyze(ideal, ideal, model="some-other-model")
        self.assertFalse(r["comparability"]["sameModelEffortAndCliVersion"])

    def test_mechanism_rubric_counts_only_blocked_defect_twins(self):
        keyword_report = lambda truth: SAMPLE_REPORTS[truth["family"]]
        hit = self.analyze(ideal, ideal, report=keyword_report)["arms"]["bare"]["mechanismMentionedAmongBlockedDefectTwins"]
        self.assertEqual((hit["of"], hit["count"] > 0), (36, True))
        miss = self.analyze(ideal, ideal, report=lambda truth: "nothing relevant")["arms"]["bare"]["mechanismMentionedAmongBlockedDefectTwins"]
        self.assertEqual(miss["count"], 0)

    def test_the_committed_pilot_2_evidence_loads_in_this_layout(self):
        pilot2 = PARENT / "results/pilot2-v2-claude-opus-5-5-high"
        r = an.analyze(V2, {"skill": pilot2, "again": pilot2})
        self.assertEqual(r["allPairs"]["primaryOrdinalPairDiscrimination"]["skill"], {"count": 40, "of": 40, "wilson95": [0.912, 1.0]})
        self.assertEqual(r["allPairs"]["primaryPaired"]["onlyFirst"], 0)
        self.assertEqual(r["arms"]["skill"]["technicalStops"], {})

    def test_documented_rule_view_reclassifies_one_arm_only_and_sits_beside_the_as_run_view(self):
        case = next(c for c, t in ORACLE.items() if t["family"] == "output_bytes" and t["role"] == "changed")
        adjudication = {"technicalStops": [{"arm": "bare", "trial": 2, "case": case, "code": "MODEL_MISMATCH", "reason": "mixed model"}]}
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp) / "a", Path(tmp) / "b"
            write_arm(a, ideal)
            write_arm(b, ideal)
            for directory in (a, b):  # stamp each ledger with its arm, as the driver does
                for trial in (1, 2):
                    ledger = directory / f"trial{trial}/responses.jsonl"
                    arm = "skill" if directory is a else "bare"
                    ledger.write_text("\n".join(json.dumps(dict(json.loads(line), arm=arm)) for line in ledger.read_text().splitlines()) + "\n")
            result = an.analyze(V2, {"skill": a, "bare": b}, (), adjudication)
        self.assertEqual(result["arms"]["bare"]["technicalStops"], {})                      # as run: nothing excluded
        view = result["documentedRuleView"]
        self.assertEqual(view["arms"]["bare"]["technicalStops"], {"RECLASSIFIED": 1})
        self.assertEqual(view["arms"]["skill"]["technicalStops"], {})                       # the same case id in the other arm is untouched
        self.assertEqual(view["allPairs"]["primaryPaired"]["matchedUnits"], 39)
        self.assertEqual(result["allPairs"]["primaryPaired"]["matchedUnits"], 40)

    def test_verdict_follows_finding_measures_the_gap_the_bare_arm_showed(self):
        keyword_report = lambda truth: SAMPLE_REPORTS[truth["family"]]
        soft_defects = lambda truth: "CHANGES_RECOMMENDED" if truth["expectedClass"] == "DEFECT" else ideal(truth)
        found_but_soft = self.analyze(ideal, soft_defects, report=keyword_report)["arms"]["bare"]["verdictFollowsFinding"]
        self.assertEqual((found_but_soft["count"], found_but_soft["of"]), (0, 36))     # named in prose, verdict soft
        followed = self.analyze(ideal, ideal, report=keyword_report)["arms"]["bare"]["verdictFollowsFinding"]
        self.assertEqual((followed["count"], followed["of"]), (36, 36))
        nothing_found = self.analyze(ideal, soft_defects, report=lambda truth: "nothing relevant")["arms"]["bare"]["verdictFollowsFinding"]
        self.assertEqual(nothing_found["of"], 0)                                        # no finding, nothing to follow

    def test_analysis_never_reads_a_ledger_it_was_not_given(self):
        self.assertNotIn("results/pilot", (HERE / "analyze.py").read_text())


if __name__ == "__main__":
    unittest.main()
