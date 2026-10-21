"""Offline tests for the v2 corpus and its scoring. Simulated reviewers only; no provider calls."""
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
PARENT = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bc = load("v2_build_corpus", HERE / "build_corpus.py")
sc = load("v2_score", PARENT / "score.py")
claude_tests = load("v2_claude_tests", PARENT / "test_run_pilot_claude.py")
ORACLE = {c["case"]: c for c in json.loads((HERE / "oracle/oracle.json").read_bytes())["cases"]}


def finding(case, severity, evidence, line=None):
    line = line or ORACLE[case]["decisiveLine"]
    return {"severity": severity, "evidence": evidence, "line": line, "quote": sc.packet_lines(case, HERE)[line - 1]}


def row(case, assessment, findings=()):
    return {"case": case, "completeness": "COMPLETE", "assessment": assessment, "findings": list(findings)}


def perfect(case, truth):
    if truth["expectedClass"] == "SOUND":
        return row(case, "NO_BLOCKERS_FOUND")
    if truth["expectedClass"] == "DEFECT":
        return row(case, "BLOCKERS_FOUND", [finding(case, "BLOCKER", "VERIFIED")])
    return row(case, "CHANGES_RECOMMENDED", [finding(case, "RISK", "UNVERIFIED")])


def cautious(case, truth):
    """Hedges on every sound plan with an unverified risk, never blocks one; catches every defect."""
    if truth["expectedClass"] == "SOUND":
        return row(case, "CHANGES_RECOMMENDED", [finding(case, "RISK", "UNVERIFIED", line=1)])
    return perfect(case, truth)


def reject_everything(case, truth):
    return row(case, "BLOCKERS_FOUND", [finding(case, "BLOCKER", "VERIFIED")])


def approve_everything(case, truth):
    return row(case, "NO_BLOCKERS_FOUND")


def score(policy):
    rows = [policy(case, truth) for case, truth in ORACLE.items()]
    return sc.score(rows, HERE)["trials"]["1"]


class CorpusTests(unittest.TestCase):
    def test_committed_corpus_matches_generator(self):
        for name, data in bc.build().items():
            if name != bc.PREREGISTRATION:
                self.assertEqual((HERE / name).read_bytes(), data, name)

    def test_shape_and_difficulty_mix(self):
        self.assertEqual(len(ORACLE), 40)
        families = {t["family"] for t in ORACLE.values()}
        self.assertEqual(len(families), 10)
        classes = {f: next(t["expectedClass"] for t in ORACLE.values() if t["family"] == f and t["role"] == "changed") for f in families}
        self.assertEqual(sorted(set(classes.values())), ["DEFECT", "UNCERTAIN"])
        self.assertEqual(sum(v == "UNCERTAIN" for v in classes.values()), 1)
        difficulty = {f: next(t["difficulty"] for t in ORACLE.values() if t["family"] == f) for f in families}
        self.assertEqual(sorted(set(difficulty.values())), ["direct", "evidence_gap", "inference"])
        self.assertEqual(sum(v == "direct" for v in difficulty.values()), 2)
        self.assertEqual(sum(v == "inference" for v in difficulty.values()), 7)
        for family in families:
            group = [t for t in ORACLE.values() if t["family"] == family]
            self.assertEqual(sorted((t["wording"], t["role"]) for t in group),
                             [("A", "changed"), ("A", "sound"), ("B", "changed"), ("B", "sound")])
        for truth in ORACLE.values():
            self.assertIn(truth["decisiveLine"], truth["citeAnyOf"])

    def test_twin_differs_from_sound_in_exactly_the_decisive_line(self):
        for family, spec in bc.FAMILIES.items():
            for wording in ("A", "B"):
                sound, twin = bc.plan_lines(family, wording, "sound"), bc.plan_lines(family, wording, "twin")
                self.assertEqual([i + 1 for i, (a, b) in enumerate(zip(sound, twin)) if a != b], [spec["line"]], (family, wording))
                self.assertEqual(len(sound), len(twin))
                self.assertTrue(set(spec["cite"]) <= set(range(1, len(sound) + 1)))

    def test_packets_leak_no_labels_and_manifest_hides_the_oracle_and_preregistration(self):
        words = [f.replace("_", " ") for f in bc.FAMILIES] + list(bc.FAMILIES) + [
            "DEFECT", "SOUND", "UNCERTAIN", "oracle", "inference", "evidence_gap", "distractor", "counterfactual"]
        for path in (HERE / "packets").glob("*.txt"):
            text = path.read_text(encoding="utf-8").lower()
            for word in words:
                self.assertNotIn(word.lower(), text, (path.name, word))
        manifest = json.loads((HERE / "manifest.json").read_bytes())
        visible = " ".join(manifest["reviewerVisible"])
        self.assertNotIn("oracle", visible)
        self.assertNotIn("PREREGISTRATION", visible)
        self.assertIn("PREREGISTRATION.md", manifest["pins"])
        self.assertEqual(len(manifest["submissionOrder"]), 40)

    def test_prompt_is_identical_to_v1_so_routes_stay_comparable(self):
        self.assertEqual((HERE / "prompt.txt").read_bytes(), (PARENT / "prompt.txt").read_bytes())

    def test_sound_plans_carry_distractors_that_the_twin_keeps(self):
        for family in ("ownership_authorization", "output_bytes"):
            sound = bc.plan_lines(family, "A", "sound")
            twin = bc.plan_lines(family, "A", "twin")
            self.assertTrue(any("rm -rf" in l or "debug log" in l for l in sound))
            self.assertTrue(any("rm -rf" in l or "debug log" in l for l in twin))

    def test_frozen_files_cannot_be_edited_unnoticed(self):
        with tempfile.TemporaryDirectory() as raw:
            copy = Path(raw) / "corpus"
            import shutil
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            self.assertTrue(sc.load_frozen(copy))
            (copy / "PREREGISTRATION.md").write_text("edited", encoding="utf-8")
            with self.assertRaises(sc.Invalid):
                sc.load_frozen(copy)


class MetricTests(unittest.TestCase):
    def test_perfect_reviewer(self):
        t = score(perfect)
        self.assertEqual((t["pairDiscrimination"]["count"], t["pairOrderedCalibrated"]["count"]), (20, 20))
        self.assertEqual(t["falseBlockersOnSoundPlans"]["count"], 0)
        self.assertEqual(t["unsupportedVerifiedFindings"], 0)
        self.assertEqual(set(t["pairOrderedCalibratedByDifficulty"]), {"direct", "evidence_gap", "inference"})

    def test_cautious_reviewer_gets_zero_strict_but_near_full_ordinal_credit(self):
        t = score(cautious)
        self.assertEqual(t["pairDiscrimination"]["count"], 0)       # strict metric punishes hedging
        # The preregistered primary credits every pair except the evidence-gap family, where hedging on the sound
        # plan and the correct CHANGES_RECOMMENDED on the twin leave nothing to order (a documented limit).
        self.assertEqual(t["pairOrderedCalibrated"]["count"], 18)
        self.assertEqual(t["perFamily"]["runtime_budget"]["pairsOrderedCalibrated"], "0/2")
        self.assertEqual(t["falseBlockersOnSoundPlans"]["count"], 0)
        self.assertEqual(t["hedgedOnSoundPlans"]["count"], 20)

    def test_degenerate_reviewers_earn_no_primary_credit(self):
        self.assertEqual(score(reject_everything)["pairOrderedCalibrated"]["count"], 0)
        self.assertEqual(score(approve_everything)["pairOrderedCalibrated"]["count"], 0)
        self.assertEqual(score(reject_everything)["falseBlockersOnSoundPlans"]["count"], 20)

    def test_overclaiming_the_uncertainty_case_fails_calibration(self):
        def policy(case, truth):
            if truth["expectedClass"] == "UNCERTAIN":
                return reject_everything(case, truth)
            return perfect(case, truth)
        t = score(policy)
        self.assertEqual(t["pairOrderedCalibrated"]["count"], 18)
        self.assertEqual(t["perFamily"]["runtime_budget"]["pairsOrderedCalibrated"], "0/2")

    def test_any_listed_supporting_line_counts_as_the_mechanism(self):
        truth = next(t for t in ORACLE.values() if t["family"] == "deadline_arithmetic" and t["role"] == "changed")
        other = next(line for line in truth["citeAnyOf"] if line != truth["decisiveLine"])
        case = truth["case"]
        outcome, detail = sc.grade(row(case, "BLOCKERS_FOUND", [finding(case, "BLOCKER", "VERIFIED", line=other)]), truth, HERE)
        self.assertEqual((outcome, detail["mechanismCited"]), ("CORRECT", True))
        outcome, _ = sc.grade(row(case, "BLOCKERS_FOUND", [finding(case, "BLOCKER", "VERIFIED", line=6)]), truth, HERE)
        self.assertEqual(outcome, "DETECTED_WITHOUT_DECISIVE_CITATION")

    def test_adjudication_adds_an_adjusted_block_beside_the_all_pairs_result(self):
        adjudication = {"invalidPairs": [{"family": "caller_callee", "wordings": ["A", "B"], "reason": "test"}]}
        rows = [perfect(case, truth) for case, truth in ORACLE.items()]
        result = sc.score(rows, HERE, adjudication)
        self.assertEqual(result["trials"]["1"]["pairOrderedCalibrated"], sc.score(rows, HERE)["trials"]["1"]["pairOrderedCalibrated"])
        self.assertEqual(result["trials"]["1"]["pairOrderedCalibrated"]["of"], 20)
        adjusted = result["adjusted"]
        self.assertEqual(adjusted["excludedPairs"], ["caller_callee/A", "caller_callee/B"])
        self.assertEqual(adjusted["trials"]["1"]["observations"], 36)
        self.assertEqual(adjusted["trials"]["1"]["pairOrderedCalibrated"]["of"], 18)
        self.assertNotIn("adjusted", sc.score(rows, HERE))
        with self.assertRaises(sc.Invalid):
            sc.score(rows, HERE, {"invalidPairs": [{"family": "caller_callee", "wordings": ["A"], "reason": " "}]})

    def test_unsupported_verified_quote_fails_the_gate(self):
        def policy(case, truth):
            r = perfect(case, truth)
            if truth["expectedClass"] == "DEFECT":
                r["findings"][0]["quote"] = "invented text"
            return r
        t = score(policy)
        self.assertEqual(t["unsupportedVerifiedFindings"], 18)
        self.assertFalse(t["pilotGate"]["unsupportedVerifiedIsZero"])


class DriverTests(unittest.TestCase):
    def test_claude_driver_runs_the_v2_corpus_and_the_scorer_accepts_the_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp)
            code, out = h.run("--corpus", str(HERE), "--execute")
            self.assertEqual((code, out["executed"], out["stopped"]), (0, 40, 0))
            calls = h.calls()
            self.assertEqual(len(calls), 40)
            self.assertTrue(all("expectedClass" not in c["stdin"] and "oracle" not in c["stdin"].lower() for c in calls))
            result = sc.score(h.ledger(), HERE)
            self.assertEqual(result["trials"]["1"]["observations"], 40)
            self.assertEqual(result["casesInCorpus"], 40)

    def test_default_corpus_is_still_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp)
            code, out = h.run()
            self.assertEqual((code, out["prepared"]), (0, 24))


if __name__ == "__main__":
    unittest.main()
