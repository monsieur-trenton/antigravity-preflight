"""Offline tests for the v3 corpus and its scoring. Simulated reviewers only; no provider calls."""
import importlib.util
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


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


bc = load("v3_build_corpus", HERE / "build_corpus.py")
sc = load("v3_score", PARENT / "score.py")
claude_tests = load("v3_claude_tests", PARENT / "test_run_pilot_claude.py")
ORACLE = {c["case"]: c for c in json.loads((HERE / "oracle/oracle.json").read_bytes())["cases"]}
V2_ORACLE = {c["case"] for c in json.loads((PARENT / "v2/oracle/oracle.json").read_bytes())["cases"]}
RUBRIC = json.loads((HERE / "rubric.json").read_bytes())["families"]
FAMILIES = json.loads((HERE / "families.json").read_bytes())["families"]
NOT_ESTABLISHED = re.compile(r"\b(has not|have not|not been|nobody|none of|no write|unknown|unchecked|not known|not measured|unconfirmed|not confirmed|no figure)\b", re.I)


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
    """Hedges on every sound plan with an unverified risk, never blocks one; catches every defect and flags every gap."""
    if truth["expectedClass"] == "SOUND":
        return row(case, "CHANGES_RECOMMENDED", [finding(case, "RISK", "UNVERIFIED", line=1)])
    return perfect(case, truth)


def waves_through_gaps(case, truth):
    """Clean on sound plans, blocks every defect, and files every unverified gap as optional (a clean verdict)."""
    if truth["expectedClass"] == "UNCERTAIN":
        return row(case, "NO_BLOCKERS_FOUND")
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
            if name not in bc.SOURCES:
                self.assertEqual((HERE / name).read_bytes(), data, name)

    def test_shape_and_difficulty_mix(self):
        self.assertEqual(len(ORACLE), 64)
        families = {t["family"] for t in ORACLE.values()}
        self.assertEqual(len(families), 16)
        kind = {f: next(t["expectedClass"] for t in ORACLE.values() if t["family"] == f and t["role"] == "changed") for f in families}
        self.assertEqual((sum(v == "DEFECT" for v in kind.values()), sum(v == "UNCERTAIN" for v in kind.values())), (8, 8))
        difficulty = {f: next(t["difficulty"] for t in ORACLE.values() if t["family"] == f) for f in families}
        self.assertEqual(sorted(difficulty.values()), ["direct"] * 3 + ["evidence_gap"] * 8 + ["inference"] * 5)
        self.assertTrue(all((difficulty[f] == "evidence_gap") == (kind[f] == "UNCERTAIN") for f in families))
        for family in families:
            group = [t for t in ORACLE.values() if t["family"] == family]
            self.assertEqual(sorted((t["wording"], t["role"]) for t in group),
                             [("A", "changed"), ("A", "sound"), ("B", "changed"), ("B", "sound")])
        for truth in ORACLE.values():
            self.assertIn(truth["decisiveLine"], truth["citeAnyOf"])

    def test_case_ids_are_new_and_unique(self):
        self.assertEqual(len(ORACLE), len(set(ORACLE)))
        self.assertTrue(all(re.fullmatch(r"Q-[0-9a-f]{6}", c) for c in ORACLE))
        self.assertFalse(set(ORACLE) & V2_ORACLE)

    def test_authored_families_pass_every_structural_check(self):
        self.assertEqual(bc.problems(), [])
        self.assertEqual(sorted(f["author"] for f in FAMILIES), sorted(["d1"] * 4 + ["d2"] * 4 + ["u1"] * 4 + ["u2"] * 4))

    def test_twin_differs_from_sound_in_exactly_the_decisive_line(self):
        for family, spec in bc.FAMILIES.items():
            for wording in ("A", "B"):
                sound, twin = bc.plan_lines(family, wording, "sound"), bc.plan_lines(family, wording, "twin")
                self.assertEqual([i + 1 for i, (a, b) in enumerate(zip(sound, twin)) if a != b], [spec["line"]], (family, wording))
                self.assertEqual(len(sound), len(twin))

    def test_wordings_differ_on_every_line(self):
        for family in bc.FAMILIES:
            a, b = bc.plan_lines(family, "A", "sound"), bc.plan_lines(family, "B", "sound")
            self.assertTrue(all(x != y for x, y in zip(a, b)), family)

    def test_evidence_gap_twins_say_so_and_sound_plans_do_not(self):
        for family, spec in bc.FAMILIES.items():
            if spec["twin"] != "UNCERTAIN":
                continue
            for wording in ("A", "B"):
                sound, twin = bc.plan_lines(family, wording, "sound"), bc.plan_lines(family, wording, "twin")
                self.assertRegex(twin[spec["line"] - 1], NOT_ESTABLISHED, (family, wording))
                self.assertNotRegex(sound[spec["line"] - 1], NOT_ESTABLISHED, (family, wording))

    def test_packets_leak_no_labels_and_manifest_hides_the_oracle_and_preregistration(self):
        words = list(bc.FAMILIES) + [  # family ids; their spaced forms are ordinary domain terms (for example "unique constraint")
            
            "DEFECT", "UNCERTAIN", "oracle", "inference", "evidence_gap", "evidence gap", "distractor", "counterfactual"]
        for path in (HERE / "packets").glob("*.txt"):
            text = path.read_text(encoding="utf-8").lower()
            for word in words:
                self.assertNotIn(word.lower(), text, (path.name, word))
        manifest = json.loads((HERE / "manifest.json").read_bytes())
        visible = " ".join(manifest["reviewerVisible"])
        self.assertNotIn("oracle", visible)
        self.assertNotIn("PREREGISTRATION", visible)
        self.assertEqual(sorted(manifest["pins"]), sorted(
            ["PREREGISTRATION.md", "families.json", "rubric.json", "audit/README.md", "audit/author-brief.txt", "audit/judgments.json", "audit/classification.json",
             "oracle/oracle.json", "prompt.txt"] + [n for n in manifest["reviewerVisible"] if n.startswith("packets/")]))
        self.assertEqual(len(manifest["submissionOrder"]), 64)
        self.assertEqual(sorted(manifest["submissionOrder"]), sorted(ORACLE))

    def test_prompt_is_identical_to_v1_so_routes_stay_comparable(self):
        self.assertEqual((HERE / "prompt.txt").read_bytes(), (PARENT / "prompt.txt").read_bytes())

    def test_frozen_files_cannot_be_edited_unnoticed(self):
        with tempfile.TemporaryDirectory() as raw:
            copy = Path(raw) / "corpus"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            self.assertTrue(sc.load_frozen(copy))
            for name in ("PREREGISTRATION.md", "rubric.json", "families.json", "audit/classification.json"):
                original = (copy / name).read_bytes()
                (copy / name).write_text("edited", encoding="utf-8")
                with self.assertRaises(sc.Invalid, msg=name):
                    sc.load_frozen(copy)
                (copy / name).write_bytes(original)

    def test_a_forbidden_word_or_number_mismatch_is_refused(self):
        broken = json.loads(json.dumps(bc.FAMILIES))
        name = next(iter(broken))
        broken[name]["A"]["sound"][0] += " This is a defect."
        self.assertTrue(any("forbidden word" in p for p in bc.problems(broken)))
        broken = json.loads(json.dumps(bc.FAMILIES))
        broken[name]["B"]["sound"][0] += " It takes 99 minutes."
        self.assertTrue(any("numbers differ" in p for p in bc.problems(broken)))
        broken = json.loads(json.dumps(bc.FAMILIES))
        broken[name]["A"]["twin"]["1"] = broken[name]["A"]["sound"][0]
        self.assertTrue(bc.problems(broken))


class RubricTests(unittest.TestCase):
    def matches(self, text, family):
        return all(any(re.search(p, text, re.I) for p in group) for group in RUBRIC[family])

    def test_rubric_covers_exactly_the_families(self):
        self.assertEqual(set(RUBRIC), set(bc.FAMILIES))

    def test_each_authors_sample_report_matches_its_own_rubric_and_no_other(self):
        for f in FAMILIES:
            self.assertTrue(self.matches(f["sampleReport"], f["family"]), f["family"])
            self.assertEqual([k for k in RUBRIC if k != f["family"] and self.matches(f["sampleReport"], k)], [], f["family"])

    def test_a_report_that_misses_the_point_does_not_match(self):
        for family in RUBRIC:
            self.assertFalse(self.matches("The plan is reasonable. Nothing needs to change.", family), family)


class MetricTests(unittest.TestCase):
    def test_perfect_reviewer(self):
        t = score(perfect)
        self.assertEqual((t["pairDiscrimination"]["count"], t["pairOrderedCalibrated"]["count"]), (32, 32))
        self.assertEqual(t["falseBlockersOnSoundPlans"]["count"], 0)
        self.assertEqual(t["unsupportedVerifiedFindings"], 0)
        self.assertEqual(set(t["pairOrderedCalibratedByDifficulty"]), {"direct", "evidence_gap", "inference"})

    def test_cautious_reviewer_hedging_on_sound_plans_cannot_order_the_evidence_gap_pairs(self):
        t = score(cautious)
        self.assertEqual(t["pairDiscrimination"]["count"], 0)
        self.assertEqual(t["pairOrderedCalibrated"]["count"], 16)       # the 16 defect pairs; the 16 evidence-gap pairs leave nothing to order
        self.assertEqual(t["hedgedOnSoundPlans"]["count"], 32)

    def test_a_reviewer_that_waves_gaps_through_scores_half_the_pairs_and_is_clean_on_sound_plans(self):
        t = score(waves_through_gaps)
        self.assertEqual(t["pairOrderedCalibrated"]["count"], 16)
        self.assertEqual(t["falseBlockersOnSoundPlans"]["count"], 0)
        self.assertEqual(t["hedgedOnSoundPlans"]["count"], 0)
        self.assertEqual(t["pairOrderedCalibratedByDifficulty"]["evidence_gap"]["count"], 0)
        self.assertEqual(t["pairOrderedCalibratedByDifficulty"]["inference"]["count"], 10)

    def test_degenerate_reviewers_earn_no_primary_credit(self):
        self.assertEqual(score(reject_everything)["pairOrderedCalibrated"]["count"], 0)
        self.assertEqual(score(approve_everything)["pairOrderedCalibrated"]["count"], 0)
        self.assertEqual(score(reject_everything)["falseBlockersOnSoundPlans"]["count"], 32)

    def test_overclaiming_the_evidence_gap_fails_calibration(self):
        def policy(case, truth):
            return reject_everything(case, truth) if truth["expectedClass"] == "UNCERTAIN" else perfect(case, truth)
        t = score(policy)
        self.assertEqual(t["pairOrderedCalibrated"]["count"], 16)

    def test_verdict_only_metrics_separate_the_three_behaviours(self):
        verdict_only = lambda policy: score(policy)["verdictOnly"] if "verdictOnly" in score(policy) else None
        rows = lambda policy: [dict(policy(case, truth), arm="defined-go", route="claude-cli") for case, truth in ORACLE.items()]
        vo = sc.verdict_only(rows(waves_through_gaps), ORACLE)
        self.assertEqual((vo["soundClean"]["count"], vo["changedVerdictCorrect"]["count"], vo["pairStrictVerdictOnly"]["count"]), (32, 16, 16))
        vo = sc.verdict_only(rows(cautious), ORACLE)
        self.assertEqual((vo["soundClean"]["count"], vo["changedVerdictCorrect"]["count"], vo["pairStrictVerdictOnly"]["count"]), (0, 32, 0))
        vo = sc.verdict_only(rows(perfect), ORACLE)
        self.assertEqual((vo["soundClean"]["count"], vo["changedVerdictCorrect"]["count"], vo["pairStrictVerdictOnly"]["count"]), (32, 32, 32))

    def test_any_listed_supporting_line_counts_as_the_mechanism(self):
        truth = next(t for t in ORACLE.values() if t["family"] == "payment_idempotency_key" and t["role"] == "changed")
        other = next(line for line in truth["citeAnyOf"] if line != truth["decisiveLine"])
        case = truth["case"]
        outcome, detail = sc.grade(row(case, "BLOCKERS_FOUND", [finding(case, "BLOCKER", "VERIFIED", line=other)]), truth, HERE)
        self.assertEqual((outcome, detail["mechanismCited"]), ("CORRECT", True))
        outcome, _ = sc.grade(row(case, "BLOCKERS_FOUND", [finding(case, "BLOCKER", "VERIFIED", line=1)]), truth, HERE)
        self.assertEqual(outcome, "DETECTED_WITHOUT_DECISIVE_CITATION")

    def test_unsupported_verified_quote_fails_the_gate(self):
        def policy(case, truth):
            r = perfect(case, truth)
            if truth["expectedClass"] == "DEFECT":
                r["findings"][0]["quote"] = "invented text"
            return r
        t = score(policy)
        self.assertEqual(t["unsupportedVerifiedFindings"], 16)
        self.assertFalse(t["pilotGate"]["unsupportedVerifiedIsZero"])


class DriverTests(unittest.TestCase):
    def test_claude_driver_runs_the_v3_corpus_and_the_scorer_accepts_the_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp)
            code, out = h.run("--corpus", str(HERE), "--execute")
            self.assertEqual((code, out["executed"], out["stopped"]), (0, 64, 0))
            calls = h.calls()
            self.assertEqual(len(calls), 64)
            self.assertTrue(all("expectedClass" not in c["stdin"] and "oracle" not in c["stdin"].lower() for c in calls))
            result = sc.score(h.ledger(), HERE)
            self.assertEqual(result["trials"]["1"]["observations"], 64)
            self.assertEqual(result["casesInCorpus"], 64)

    def test_default_corpus_is_still_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            h = claude_tests.Harness(tmp)
            code, out = h.run()
            self.assertEqual((code, out["prepared"]), (0, 24))


if __name__ == "__main__":
    unittest.main()
