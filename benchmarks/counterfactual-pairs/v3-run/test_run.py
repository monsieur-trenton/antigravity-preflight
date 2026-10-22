"""Offline tests for the v3 run tooling: run-manifest binding, the analysis and its labels. Stubbed driver and simulated arms; no provider calls."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
V3 = PARENT / "v3"
V2 = PARENT / "v2"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rc = load("v3run_driver", PARENT / "run_pilot_claude.py")
vr = load("v3run_verify", PARENT / "verify_run.py")
an = load("v3run_analyze", HERE / "analyze.py")
bm = load("v3run_build_manifest", HERE / "build_manifest.py")
claude_tests = load("v3run_claude_tests", PARENT / "test_run_pilot_claude.py")
MODEL = claude_tests.MODEL
ORACLE = {c["case"]: c for c in json.loads((V3 / "oracle/oracle.json").read_bytes())["cases"]}
FAMILIES = {f["family"]: f for f in json.loads((V3 / "families.json").read_bytes())["families"]}
RUBRIC_FILE = V3 / "rubric.json"
RUN_MANIFEST = HERE / "manifest.json"


class FrozenFilesTests(unittest.TestCase):
    def test_manifest_is_current_and_ties_the_run_to_corpus_arms_and_prompt(self):
        self.assertEqual(RUN_MANIFEST.read_bytes(), bm.build())
        manifest = json.loads(RUN_MANIFEST.read_bytes())
        self.assertEqual(manifest["corpus"]["manifestSha256"], rc.rp.sha((V3 / "manifest.json").read_bytes()))
        self.assertEqual(sorted(manifest["arms"]), ["defined", "defined-go", "skill"])
        self.assertEqual(manifest["arms"]["skill"]["systemPromptSha256"], rc.rp.sha(rc.SYSTEM_PROMPT.encode("utf-8")))
        for name in ("defined", "defined-go"):
            path = PARENT.parent.parent / manifest["arms"][name]["manifest"]
            self.assertEqual(manifest["arms"][name]["manifestSha256"], rc.rp.sha(path.read_bytes()))
        self.assertEqual(sorted(manifest["pins"]), ["PREREGISTRATION.md"])

    def test_the_brief_names_the_current_hashes(self):
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for path in (RUN_MANIFEST, V3 / "manifest.json", PARENT / "ablation/manifest.json", PARENT / "ablation/defined/manifest.json",
                     PARENT / "ablation/defined-go/manifest.json"):
            self.assertIn(rc.rp.sha(path.read_bytes()), brief, str(path))

    def test_the_earlier_arm_manifests_are_untouched_so_their_v2_evidence_still_verifies(self):
        ablation = PARENT / "ablation"
        self.assertEqual(rc.rp.sha((ablation / "manifest.json").read_bytes()), "35d7ea8dd779078b95b3c854da645f3039f91bec2cec068c8f9355fab4c4dcbb")
        self.assertEqual(rc.rp.sha((ablation / "defined/manifest.json").read_bytes()), "60f9268660ec0fb2fd545d2c835d5997eaa2f1362a798af7e92a43415d817484")
        self.assertEqual(rc.rp.sha((ablation / "defined-go/manifest.json").read_bytes()), "b628683f9140c2c20c4f583c672244b15a99fd4a3c007efc348bb7ee68b0f356")
        self.assertEqual(json.loads((ablation / "defined/manifest.json").read_bytes())["corpus"]["manifestSha256"], rc.rp.sha((V2 / "manifest.json").read_bytes()))

    def test_load_run_refuses_a_tampered_run_manifest_or_arm_hash_or_prompt_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "run"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            self.assertTrue(rc.load_run(copy / "manifest.json")["sha256"])
            manifest = json.loads((copy / "manifest.json").read_bytes())
            for edit, expected in ((lambda m: m["arms"]["defined"].update(manifestSha256="0" * 64), "RUN_ARM_MANIFEST_MISMATCH:defined"),
                                   (lambda m: m["pins"].update({"PREREGISTRATION.md": "0" * 64}), "RUN_PIN_MISMATCH:PREREGISTRATION.md")):
                tampered = json.loads(json.dumps(manifest))
                edit(tampered)
                (copy / "manifest.json").write_text(json.dumps(tampered), encoding="utf-8")
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_run(copy / "manifest.json")
                self.assertEqual(str(raised.exception), expected)
            (copy / "manifest.json").write_text(json.dumps(dict(manifest, kind="OTHER")), encoding="utf-8")
            with self.assertRaises(rc.rp.Stop):
                rc.load_run(copy / "manifest.json")


class BindingTests(unittest.TestCase):
    def run_arm(self, tmp, arm, *extra, corpus=V3, run=True, verdict="GO"):
        h = claude_tests.Harness(tmp)
        (h.bin.parent / "stub-config.json").write_text(json.dumps({"mode": "ok", "log": str(h.log), "model": MODEL, "verdict": verdict}))
        args = ["--arm", arm, "--corpus", str(corpus)] + (["--run-manifest", str(RUN_MANIFEST)] if run else []) + list(extra)
        code, out = h.run(*args)
        return h, code, out

    def test_each_arm_runs_the_v3_corpus_under_the_run_manifest_and_every_row_carries_its_hash(self):
        run_sha = rc.rp.sha(RUN_MANIFEST.read_bytes())
        for arm in ("skill", "defined", "defined-go"):
            with tempfile.TemporaryDirectory() as tmp:
                h, code, out = self.run_arm(tmp, arm, "--execute")
                self.assertEqual((code, out["executed"], out["arm"], out["runManifestSha256"]), (0, 64, arm, run_sha), arm)
                rows = h.ledger()
                self.assertTrue(all(r["runManifestSha256"] == run_sha for r in rows))
                self.assertEqual(vr.verify(V3, h.work, MODEL, "high", [1], arm, RUN_MANIFEST)["failures"], [], arm)

    def test_the_verifier_catches_a_missing_or_wrong_run_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _, _ = self.run_arm(tmp, "defined-go", "--execute")
            self.assertTrue(vr.verify(V3, h.work, MODEL, "high", [1], "defined-go")["failures"])           # rows carry a run hash the verifier was not told about
            self.assertTrue(vr.verify(V3, h.work, MODEL, "high", [1], "defined", RUN_MANIFEST)["failures"])  # the wrong arm

    def test_a_verdict_only_arm_is_still_bound_to_v2_without_a_run_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_arm(tmp, "defined-go", run=False)
            self.assertEqual((code, out["reason"]), (1, "ABLATION_CORPUS_MISMATCH"))

    def test_the_run_manifest_refuses_another_corpus_and_an_arm_it_does_not_bind(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_arm(tmp, "defined-go", corpus=V2)
            self.assertEqual((code, out["reason"]), (1, "RUN_CORPUS_MISMATCH"))
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_arm(tmp, "bare")
            self.assertEqual((code, out["reason"]), (1, "RUN_ARM_NOT_BOUND"))

    def test_an_arm_whose_own_files_changed_is_refused_even_under_a_run_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "ablation"
            shutil.copytree(PARENT / "ablation", copy, ignore=shutil.ignore_patterns("__pycache__"))
            originals = (rc.ABLATION, rc.DEFINED, rc.DEFINED_GO)
            try:
                rc.ABLATION, rc.DEFINED, rc.DEFINED_GO = copy, copy / "defined", copy / "defined-go"
                (copy / "defined-go" / "defined-go-request.txt").write_text("{plan}\nVERDICT: GO\n", encoding="utf-8")
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_arm("defined-go")
                self.assertEqual(str(raised.exception), "ABLATION_PIN_MISMATCH:defined-go-request.txt")
            finally:
                rc.ABLATION, rc.DEFINED, rc.DEFINED_GO = originals


def write_arm(directory, policy, report=lambda truth: "report text", stops=()):
    for trial in (1, 2):
        (directory / f"trial{trial}/reports").mkdir(parents=True)
        lines = []
        for case, truth in ORACLE.items():
            row = {"case": case, "trial": trial, "assessment": policy(truth), "completeness": "COMPLETE", "findings": [],
                   "requestedModel": MODEL, "effort": "high", "claudeVersion": "9.9", "servedModels": [MODEL], "costUsd": 0.01}
            if (case, trial) in stops:
                row = {"case": case, "trial": trial, "technicalStop": "SAFETY_INTERRUPTED:1", "arm": "x"}
            lines.append(json.dumps(row))
            (directory / f"trial{trial}/reports/{case}.md").write_text(report(truth), encoding="utf-8")
        (directory / f"trial{trial}/responses.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def ideal(truth):
    return {"SOUND": "NO_BLOCKERS_FOUND", "DEFECT": "BLOCKERS_FOUND", "UNCERTAIN": "CHANGES_RECOMMENDED"}[truth["expectedClass"]]


def hedger(truth):
    """Hedges on every sound plan; correct on both kinds of twin."""
    return "CHANGES_RECOMMENDED" if truth["expectedClass"] == "SOUND" else ideal(truth)


def waves_through_gaps(truth):
    return "NO_BLOCKERS_FOUND" if truth["expectedClass"] in ("SOUND", "UNCERTAIN") else "BLOCKERS_FOUND"


def softens_defects(truth):
    return "CHANGES_RECOMMENDED" if truth["expectedClass"] in ("DEFECT", "UNCERTAIN") else "NO_BLOCKERS_FOUND"


def sample_report(truth):
    return FAMILIES[truth["family"]]["sampleReport"]


class AnalysisTests(unittest.TestCase):
    def run_analysis(self, policies, excluded=(), adjudication=None, **kw):
        rubric = json.loads(RUBRIC_FILE.read_bytes())["families"]
        with tempfile.TemporaryDirectory() as tmp:
            arms = {}
            for name, policy in policies.items():
                directory = Path(tmp) / name
                stops = kw.get("stops", {}).get(name, ())
                write_arm(directory, policy, kw.get("report", lambda truth: "report text"), stops)
                arms[name] = directory
            return an.analyze(V3, arms, rubric, excluded, adjudication)

    def test_the_sentence_pattern_is_read_as_gain_with_a_cost(self):
        result = self.run_analysis({"skill": hedger, "defined": hedger, "defined-go": waves_through_gaps})
        go, defined = result["arms"]["defined-go"]["primary"], result["arms"]["defined"]["primary"]
        self.assertEqual((go["soundPlansGo"]["count"], go["soundPlansGo"]["of"]), (64, 64))     # 32 sound plans, two trials
        self.assertEqual(go["evidenceGapTwinsGoWithChanges"]["count"], 0)
        self.assertEqual(defined["soundPlansGo"]["count"], 0)
        self.assertEqual((defined["evidenceGapTwinsGoWithChanges"]["count"], defined["evidenceGapTwinsGoWithChanges"]["of"]), (32, 32))
        pair = result["comparisons"]["defined__defined-go"]
        self.assertEqual((pair["soundGo"]["onlyFirst"], pair["soundGo"]["onlySecond"]), (0, 64))
        self.assertEqual((pair["gapGwc"]["onlyFirst"], pair["gapGwc"]["onlySecond"]), (32, 0))
        self.assertEqual(pair["defectNoGo"]["onlyFirst"] + pair["defectNoGo"]["onlySecond"], 0)
        self.assertEqual(result["labels"]["soundPlanGain"], "replicated")
        self.assertEqual(result["labels"]["evidenceGapCost"], "confirmed")
        self.assertEqual(result["labels"]["defectTwins"], "held")
        self.assertEqual(result["labels"]["skillStyleVsSentenceArm"], {"evidenceGapGoWithChanges": "skill-style better", "soundPlansGo": "sentence arm better"})

    def test_strict_and_ordered_pairs_follow_from_the_three_behaviours(self):
        result = self.run_analysis({"defined": hedger, "defined-go": waves_through_gaps, "skill": ideal})
        arms = result["arms"]
        self.assertEqual(arms["skill"]["summary"]["strictPairDiscrimination"]["count"], 64)
        self.assertEqual(arms["defined-go"]["summary"]["strictPairDiscrimination"]["count"], 32)   # the 16 defect pairs, two trials
        self.assertEqual(arms["defined"]["summary"]["strictPairDiscrimination"]["count"], 0)
        self.assertEqual(arms["defined"]["summary"]["orderedPairDiscrimination"]["count"], 32)     # hedging leaves nothing to order on evidence-gap pairs
        self.assertEqual(arms["skill"]["summary"]["orderedPairDiscrimination"]["count"], 64)

    def test_no_difference_reads_as_not_replicated_and_not_detected(self):
        result = self.run_analysis({"defined": ideal, "defined-go": ideal})
        self.assertEqual(result["labels"], {"soundPlanGain": "not replicated", "evidenceGapCost": "not detected", "defectTwins": "held", "rule": result["labels"]["rule"]})

    def test_a_sentence_arm_that_softens_defects_is_labelled_lost_and_the_reverse_direction_is_reported(self):
        result = self.run_analysis({"defined": ideal, "defined-go": softens_defects})
        self.assertEqual(result["labels"]["defectTwins"], "lost")
        better = self.run_analysis({"defined": waves_through_gaps, "defined-go": ideal})
        self.assertEqual(better["labels"]["evidenceGapCost"], "reversed (the sentence arm is better)")
        reversed_gain = self.run_analysis({"defined": ideal, "defined-go": hedger})
        self.assertEqual(reversed_gain["labels"]["soundPlanGain"], "reversed")

    def test_gap_named_but_dismissed_uses_the_corpus_rubric_on_reports_that_ended_clean(self):
        named = self.run_analysis({"defined": ideal, "defined-go": waves_through_gaps}, report=sample_report)["arms"]["defined-go"]["secondary"]
        self.assertEqual((named["gapNamedButDismissed"]["count"], named["gapNamedButDismissed"]["of"]), (32, 32))
        self.assertEqual(named["evidenceGapTwinsGo"]["count"], 32)
        silent = self.run_analysis({"defined": ideal, "defined-go": waves_through_gaps})["arms"]["defined-go"]["secondary"]
        self.assertEqual((silent["gapNamedButDismissed"]["count"], silent["gapNamedButDismissed"]["of"]), (0, 32))
        self.assertEqual(self.run_analysis({"defined": ideal, "defined-go": ideal}, report=sample_report)["arms"]["defined-go"]["secondary"]["gapNamedButDismissed"]["of"], 0)

    def test_verdict_follows_finding_counts_defect_twins_whose_report_names_the_mechanism(self):
        arm = self.run_analysis({"defined": ideal, "defined-go": softens_defects}, report=sample_report)["arms"]
        self.assertEqual((arm["defined"]["secondary"]["verdictFollowsFinding"]["count"], arm["defined"]["secondary"]["verdictFollowsFinding"]["of"]), (32, 32))
        self.assertEqual(arm["defined-go"]["secondary"]["verdictFollowsFinding"]["count"], 0)

    def test_stops_are_removed_not_counted_and_the_documented_rule_view_sits_beside_the_as_run_one(self):
        case = next(c for c, t in ORACLE.items() if t["role"] == "changed" and t["expectedClass"] == "UNCERTAIN")
        result = self.run_analysis({"defined": ideal, "defined-go": waves_through_gaps}, stops={"defined-go": {(case, 1)}})
        self.assertEqual(result["arms"]["defined-go"]["technicalStops"], {"SAFETY_INTERRUPTED": 1})
        self.assertEqual(result["arms"]["defined-go"]["primary"]["evidenceGapTwinsGoWithChanges"]["of"], 31)
        self.assertNotIn("documentedRuleView", result)

    def test_an_adjudication_adds_the_documented_rule_view_without_changing_the_as_run_result(self):
        case = next(c for c, t in ORACLE.items() if t["role"] == "changed" and t["expectedClass"] == "UNCERTAIN")
        adjudication = {"technicalStops": [{"arm": "skill", "trial": 2, "case": case, "code": "MODEL_MISMATCH", "reason": "test"}]}
        result = self.run_analysis({"defined": ideal, "defined-go": waves_through_gaps}, adjudication=adjudication)
        self.assertEqual(result["arms"]["defined-go"]["primary"]["evidenceGapTwinsGoWithChanges"]["of"], 32)
        view = result["documentedRuleView"]
        self.assertEqual(view["arms"]["defined-go"]["primary"]["evidenceGapTwinsGoWithChanges"]["of"], 31)
        self.assertEqual(view["arms"]["defined"]["primary"]["evidenceGapTwinsGoWithChanges"]["of"], 31)
        self.assertEqual(view["reclassified"], [{"arm": "skill", "trial": 2, "case": case, "code": "MODEL_MISMATCH"}])

    def test_excluding_a_family_removes_it_from_every_count(self):
        full = self.run_analysis({"defined": ideal, "defined-go": ideal})
        cut = self.run_analysis({"defined": ideal, "defined-go": ideal}, excluded=["rate_arithmetic", "capacity_headroom"])
        self.assertEqual(full["arms"]["defined"]["primary"]["soundPlansGo"]["of"], 64)
        self.assertEqual(cut["arms"]["defined"]["primary"]["soundPlansGo"]["of"], 56)
        self.assertEqual(cut["arms"]["defined"]["primary"]["evidenceGapTwinsGoWithChanges"]["of"], 28)
        self.assertNotIn("rate_arithmetic", cut["arms"]["defined"]["perFamily"])
        self.assertEqual(cut["excludedFamilies"], ["capacity_headroom", "rate_arithmetic"])

    def test_per_family_table_and_comparability_flag(self):
        result = self.run_analysis({"defined": hedger, "defined-go": waves_through_gaps})
        row = result["arms"]["defined-go"]["perFamily"]["capacity_headroom"]
        self.assertEqual((row["kind"], row["changedVerdicts"]["GO"], row["soundGo"]["count"]), ("UNCERTAIN", 4, 4))
        self.assertTrue(result["comparability"]["sameModelEffortAndCliVersion"])
        self.assertEqual(result["providerCalls"], 0)

    def test_the_command_line_writes_the_analysis_and_refuses_a_single_arm(self):
        rubric = str(RUBRIC_FILE)
        with tempfile.TemporaryDirectory() as tmp:
            a, b, out = Path(tmp) / "a", Path(tmp) / "b", Path(tmp) / "out.json"
            write_arm(a, ideal)
            write_arm(b, waves_through_gaps)
            self.assertEqual(an.main(["--corpus", str(V3), "--rubric", rubric, "--arm", f"defined={a}", "--arm", f"defined-go={b}", "--out", str(out)]), 0)
            self.assertEqual(json.loads(out.read_text())["labels"]["evidenceGapCost"], "confirmed")
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                self.assertEqual(an.main(["--corpus", str(V3), "--rubric", rubric, "--arm", f"defined={a}"]), 1)
            self.assertIn("AT_LEAST_TWO_ARMS_REQUIRED", buffer.getvalue())

    def test_the_analysis_never_reads_a_ledger_it_was_not_given(self):
        self.assertNotIn("results/", (HERE / "analyze.py").read_text())


if __name__ == "__main__":
    unittest.main()
