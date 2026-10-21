"""Offline tests for the counterfactual corpus and scorer. Simulated reviewers only; no provider calls."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bc, sc = load("build_corpus"), load("score")
ORACLE = {c["case"]: c for c in json.loads((HERE / "oracle/oracle.json").read_bytes())["cases"]}


def finding(case, severity, evidence, line=None):
    line = line or ORACLE[case]["decisiveLine"]
    return {"severity": severity, "evidence": evidence, "line": line, "quote": sc.packet_lines(case)[line - 1]}


def respond(policy):
    return [policy(case, truth) for case, truth in ORACLE.items()]


def perfect(case, truth):
    kind = truth["expectedClass"]
    if kind == "SOUND":
        return {"case": case, "completeness": "COMPLETE", "assessment": "NO_BLOCKERS_FOUND", "findings": []}
    if kind == "DEFECT":
        return {"case": case, "completeness": "COMPLETE", "assessment": "BLOCKERS_FOUND",
                "findings": [finding(case, "BLOCKER", "VERIFIED")]}
    return {"case": case, "completeness": "INCOMPLETE", "assessment": "CHANGES_RECOMMENDED",
            "findings": [finding(case, "RISK", "UNVERIFIED")]}


def reject_everything(case, truth):
    return {"case": case, "completeness": "COMPLETE", "assessment": "BLOCKERS_FOUND",
            "findings": [finding(case, "BLOCKER", "VERIFIED")]}


def approve_everything(case, truth):
    return {"case": case, "completeness": "COMPLETE", "assessment": "NO_BLOCKERS_FOUND", "findings": []}


class CorpusTests(unittest.TestCase):
    def test_committed_corpus_matches_generator(self):
        for name, data in bc.build().items():
            self.assertEqual((HERE / name).read_bytes(), data, name)

    def test_shape(self):
        self.assertEqual(len(ORACLE), 24)
        families = {t["family"] for t in ORACLE.values()}
        self.assertEqual(len(families), 6)
        for family in families:
            group = [t for t in ORACLE.values() if t["family"] == family]
            self.assertEqual(sorted((t["wording"], t["role"]) for t in group),
                             [("A", "changed"), ("A", "sound"), ("B", "changed"), ("B", "sound")])

    def test_twin_differs_from_sound_in_exactly_one_line_at_the_decisive_line(self):
        for family, spec in bc.FAMILIES.items():
            for wording in ("A", "B"):
                sound = bc.plan_lines(family, wording, "sound")
                twin = bc.plan_lines(family, wording, "twin")
                changed = [i + 1 for i, (a, b) in enumerate(zip(sound, twin)) if a != b]
                self.assertEqual(changed, [spec["line"]], (family, wording))

    def test_packets_leak_no_labels(self):
        words = [f.replace("_", " ") for f in bc.FAMILIES] + list(bc.FAMILIES) + ["DEFECT", "SOUND", "UNCERTAIN", "oracle"]
        for path in (HERE / "packets").glob("*.txt"):
            text = path.read_text(encoding="utf-8")
            for word in words:
                self.assertNotIn(word.lower(), text.lower(), (path.name, word))

    def test_reviewer_visible_files_exclude_the_oracle(self):
        manifest = json.loads((HERE / "manifest.json").read_bytes())
        self.assertFalse(any("oracle" in name for name in manifest["reviewerVisible"]))
        self.assertEqual(len(manifest["submissionOrder"]), 24)


class ScorerTests(unittest.TestCase):
    def trial(self, policy):
        return sc.score(respond(policy))["trials"]["1"]

    def test_perfect_reviewer(self):
        result = self.trial(perfect)
        self.assertEqual(result["pairDiscrimination"]["count"], 12)
        self.assertEqual(result["falseBlockersOnSoundPlans"]["count"], 0)
        self.assertEqual(result["unsupportedVerifiedFindings"], 0)
        self.assertTrue(result["pilotGate"]["unsupportedVerifiedIsZero"])

    def test_reject_everything_gets_no_discrimination_credit(self):
        result = self.trial(reject_everything)
        self.assertEqual(result["pairDiscrimination"]["count"], 0)
        self.assertEqual(result["falseBlockersOnSoundPlans"]["count"], 12)
        # It still "detects" the five defect families, which is exactly why sound controls matter.
        self.assertEqual(result["perFamily"]["output_bytes"]["outcomes"]["A/changed"], "CORRECT")
        self.assertEqual(result["perFamily"]["runtime_budget"]["outcomes"]["A/changed"], "OVERCLAIMED")

    def test_approve_everything_gets_no_discrimination_credit(self):
        result = self.trial(approve_everything)
        self.assertEqual(result["pairDiscrimination"]["count"], 0)
        self.assertEqual(result["falseBlockersOnSoundPlans"]["count"], 0)
        self.assertEqual(result["changedPlansJudgedCorrectly"]["count"], 0)

    def test_blocker_on_wrong_line_is_not_credited_as_mechanism(self):
        def policy(case, truth):
            row = perfect(case, truth)
            if truth["expectedClass"] == "DEFECT":
                row["findings"] = [finding(case, "BLOCKER", "VERIFIED", line=1)]
            return row
        outcomes = self.trial(policy)["perFamily"]["caller_callee"]["outcomes"]
        self.assertEqual(outcomes["A/changed"], "DETECTED_WITHOUT_DECISIVE_CITATION")

    def test_unsupported_verified_quote_is_counted_and_fails_the_gate(self):
        def policy(case, truth):
            row = perfect(case, truth)
            if truth["expectedClass"] == "DEFECT":
                row["findings"][0]["quote"] = "invented text that is not on the line"
            return row
        result = self.trial(policy)
        self.assertEqual(result["unsupportedVerifiedFindings"], 10)
        self.assertFalse(result["pilotGate"]["unsupportedVerifiedIsZero"])

    def test_technical_stop_is_not_a_wrong_judgment(self):
        def policy(case, truth):
            if case == next(iter(ORACLE)):
                return {"case": case, "technicalStop": "TIMEOUT"}
            return perfect(case, truth)
        result = self.trial(policy)
        self.assertEqual(result["technicalStops"], 1)
        self.assertEqual(result["falseBlockersOnSoundPlans"]["count"], 0)
        self.assertLess(result["pairDiscrimination"]["of"], 12)

    def test_repeatability_across_trials(self):
        first = respond(perfect)
        second = [dict(r, trial=2) for r in respond(perfect)]
        second[0] = dict(respond(approve_everything)[0], trial=2)
        result = sc.score([dict(r, trial=1) for r in first] + second)
        self.assertEqual(result["repeatability"]["of"], 24)
        self.assertLess(result["repeatability"]["count"], 24)

    def test_invalid_input_is_refused(self):
        with self.assertRaises(sc.Invalid):
            sc.score([{"case": "P-000000", "assessment": "NO_BLOCKERS_FOUND"}])
        row = respond(perfect)[0]
        with self.assertRaises(sc.Invalid):
            sc.score([row, row])
        with self.assertRaises(sc.Invalid):
            sc.score([dict(row, assessment="LOOKS_GOOD")])

    def test_committed_pilot1_score_still_reproduces_on_every_original_key(self):
        res = HERE / "results/pilot1-claude-opus-5-5-high"
        rows = [json.loads(line) for n in (1, 2) for line in (res / f"trial{n}/responses.jsonl").read_text().splitlines()]
        new, old = sc.score(rows), json.loads((res / "score.json").read_text())
        added = {"pairOrderedCalibrated", "hedgedOnSoundPlans", "pairOrderedCalibratedByDifficulty"}
        for trial in ("1", "2"):
            for key, value in old["trials"][trial].items():
                got = new["trials"][trial][key]
                if key == "perFamily":
                    got = {f: {k: v for k, v in e.items() if k != "pairsOrderedCalibrated"} for f, e in got.items()}
                self.assertEqual(got, value, (trial, key))
            self.assertTrue(added <= set(new["trials"][trial]))
        for key in ("kind", "corpusManifestSha256", "casesInCorpus", "repeatability"):
            self.assertEqual(new[key], old[key], key)

    def test_ordinal_metric_requires_stricter_changed_verdict_and_calibrated_uncertainty(self):
        def policy(case, truth):
            row = perfect(case, truth)
            if truth["expectedClass"] == "UNCERTAIN":  # overclaims a verified blocker: ordered, but not calibrated
                row = {"case": case, "completeness": "COMPLETE", "assessment": "BLOCKERS_FOUND",
                       "findings": [finding(case, "BLOCKER", "VERIFIED")]}
            return row
        trial = sc.score(respond(policy))["trials"]["1"]
        self.assertEqual(trial["pairOrderedCalibrated"]["count"], 10)
        self.assertEqual(trial["perFamily"]["runtime_budget"]["pairsOrderedCalibrated"], "0/2")
        self.assertEqual(trial["perFamily"]["output_bytes"]["pairsOrderedCalibrated"], "2/2")

    def test_wilson_interval_is_wide_for_small_n(self):
        low, high = sc.wilson(12, 12)
        self.assertLess(low, 0.8)
        self.assertEqual(high, 1.0)
        self.assertEqual(sc.wilson(0, 0), None)


if __name__ == "__main__":
    unittest.main()
