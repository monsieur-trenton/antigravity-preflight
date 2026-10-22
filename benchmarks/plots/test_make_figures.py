"""Offline tests for the SVG figure generator; no model or provider calls."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("make_figures", HERE / "make_figures.py")
mf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mf)

RESULTS = {
    "summary": {"mechanicalFaults": 1, "mechanicalStopped": 1, "semanticFaults": 1,
                "semanticPassedThroughToManualCheck": 1, "notExercised": 1},
    "faults": [
        {"id": "a", "description": "Tag <b> & \"quote\"", "kind": "MECHANICAL", "observedReason": "QUOTE_MISMATCH",
         "layer": "LINE_AND_QUOTE"},
        {"id": "b", "description": "Semantic", "kind": "SEMANTIC", "observedReason": None, "layer": None},
        {"id": "c", "description": "Manual", "kind": "MANUAL", "observedReason": None, "layer": None, "owner": "Codex"},
    ],
}
INPUTS = {
    "results": RESULTS, "utilityChecks": 45, "utilityCases": 8, "citationScenarios": 50,
    "mechanicalStopped": 1, "mechanicalFaults": 1, "argonTotal": 20, "argonRuns": 2, "argonPerRun": 10,
    "argonSuites": [("alpha", 6), ("beta", 4)],
}


class FigureTests(unittest.TestCase):
    def test_every_figure_is_well_formed_and_deterministic(self):
        first, second = mf.build(INPUTS), mf.build(INPUTS)
        self.assertEqual(first, second)
        for name, svg in first.items():
            root = ET.fromstring(svg)
            self.assertTrue(root.tag.endswith("svg"), name)
            self.assertIn("prefers-color-scheme: dark", svg)

    def test_text_is_escaped(self):
        svg = mf.build(INPUTS)["fault-gate-matrix.svg"]
        self.assertIn("Tag &lt;b&gt; &amp; \"quote\"", svg)
        self.assertNotIn("<b>", svg)

    def test_overlong_label_is_refused_not_clipped(self):
        broken = json.loads(json.dumps(RESULTS))
        broken["faults"][0]["description"] = "x" * 200
        with self.assertRaises(ValueError):
            mf.fault_matrix(broken)

    def test_each_state_has_a_distinct_shape_not_only_a_colour(self):
        svg = mf.build(INPUTS)["fault-gate-matrix.svg"]
        self.assertIn("<polyline", svg)      # stopped: check mark
        self.assertIn("<circle", svg)        # passes through: exclamation mark
        self.assertIn("stroke-dasharray", svg)  # not exercised: dashed outline

    def test_pair_matrix_is_well_formed_labelled_and_counts_ordinally(self):
        order = ["NO_BLOCKERS_FOUND", "CHANGES_RECOMMENDED", "BLOCKERS_FOUND"]
        rows = {}
        for family in mf.FAMILY_LABEL:
            for wording in ("A", "B"):
                for trial in (1, 2):
                    rows[(family, wording, "sound", trial)] = order[0]
                    rows[(family, wording, "changed", trial)] = order[0] if family == "output_bytes" else order[2]
        svg = mf.pair_matrix({"rows": rows, "model": "m", "effort": "high", "strict": [9, 8], "invalidFamilies": ["output_bytes"]})
        ET.fromstring(svg)
        self.assertIn("20 of 20", svg)
        self.assertIn("9/12 and 8/12", svg)
        self.assertIn("0/4 judged stricter", svg)
        self.assertIn("corpus defect", svg)
        self.assertIn("Blockers", svg)  # every state carries a text label, not colour alone

    def test_pair_matrix_accepts_a_custom_family_set_footer_and_flag(self):
        order = ["NO_BLOCKERS_FOUND", "CHANGES_RECOMMENDED", "BLOCKERS_FOUND"]
        families = {"alpha": "Alpha", "beta": "Beta"}
        rows = {}
        for family in families:
            for wording in ("A", "B"):
                for trial in (1, 2):
                    rows[(family, wording, "sound", trial)] = order[1] if family == "beta" else order[0]
                    rows[(family, wording, "changed", trial)] = order[2]
        svg = mf.pair_matrix({"rows": rows, "model": "m", "effort": "high", "families": families, "invalidFamilies": ["beta"],
                              "flagNote": "adjudicated gap in sound plan", "subLabels": {"alpha": "needs inference across lines"},
                              "subtitle3": "Custom subtitle.", "title": "Custom title",
                              "footer": [("First footer line.", "small"), ("Second footer line.", "small muted")]})
        ET.fromstring(svg)
        for text in ("Custom title", "Custom subtitle.", "First footer line.", "Second footer line.", "adjudicated gap in sound plan",
                     "needs inference across lines", "8 cases"):
            self.assertIn(text, svg)
        self.assertIn("stroke-dasharray", svg)  # the flagged family is dashed
        self.assertEqual(svg.count("4/4 judged stricter"), 2)

    def test_ablation_figure_is_built_from_committed_data_and_labels_every_state(self):
        data = mf.load_ablation()
        svg = mf.ablation_figure(data)
        ET.fromstring(svg)
        self.assertEqual(data["mix"]["bare"]["sound"], {"NO_BLOCKERS_FOUND": 7, "CHANGES_RECOMMENDED": 32, "BLOCKERS_FOUND": 0})
        self.assertEqual(data["perFamily"]["output_bytes"]["bareLost"], 3)
        for text in ("Bare prompt against skill-style prompt", "Blockers 36", "Changes 32", "Clean 24", "bare 21/37", "skill 40/40",
                     "3 bare pairs lost to platform interruptions", "Human reading", "stroke-dasharray"):
            self.assertIn(text, svg)
        self.assertIn("<polygon", svg)  # bare marks are diamonds, skill marks circles: not colour alone
        self.assertIn("<circle", svg)

    def test_ablation_figure_refuses_a_stale_analysis(self):
        import json, shutil
        results = mf.ROOT / "benchmarks/counterfactual-pairs/results/ablation-bare-opus-5-5-high"
        original = (results / "analysis.json").read_bytes()
        try:
            stale = json.loads(original)
            stale["allPairs"]["primaryOrdinalPairDiscrimination"]["bare"]["count"] += 1
            (results / "analysis.json").write_text(json.dumps(stale), encoding="utf-8")
            with self.assertRaises(SystemExit):
                mf.load_ablation()
        finally:
            (results / "analysis.json").write_bytes(original)

    def test_three_arm_figure_is_built_from_committed_data_and_labels_every_state(self):
        data = mf.load_three_arms()
        svg = mf.three_arm_figure(data)
        ET.fromstring(svg)
        self.assertEqual(data["mix"]["defined"]["sound"], {"NO_BLOCKERS_FOUND": 8, "CHANGES_RECOMMENDED": 32, "BLOCKERS_FOUND": 0})
        self.assertEqual(data["mix"]["defined"]["defect"]["BLOCKERS_FOUND"], 35)
        self.assertEqual(data["primary"]["defined"]["count"], 35)
        self.assertEqual(data["onlySkillFamilies"], ["runtime_budget"])
        for text in ("Clean 24", "Changes 32", "Blockers 35", "pairs lost to stops: 3 bare, 1 defined",
                     "defined 35/39", "Preregistered label: partly closes the gap", "Runtime budget evidence",
                     "p = 0.0005", "Bare + defined verdicts"):
            self.assertIn(text, svg)
        self.assertIn("<polygon", svg)  # diamonds for bare, circles for skill-style, squares for defined: not colour alone
        self.assertIn("<circle", svg)
        self.assertIn("<rect x=", svg)

    def test_three_arm_figure_refuses_a_stale_analysis(self):
        results = mf.ROOT / "benchmarks/counterfactual-pairs/results/ablation-defined-opus-5-5-high"
        original = (results / "analysis-vs-bare.json").read_bytes()
        try:
            stale = json.loads(original)
            stale["allPairs"]["primaryOrdinalPairDiscrimination"]["defined"]["count"] += 1
            (results / "analysis-vs-bare.json").write_text(json.dumps(stale), encoding="utf-8")
            with self.assertRaises(SystemExit):
                mf.load_three_arms()
        finally:
            (results / "analysis-vs-bare.json").write_bytes(original)

    def test_four_arm_figure_is_built_from_committed_data_and_states_the_cost(self):
        data = mf.load_four_arms()
        svg = mf.four_arm_figure(data)
        ET.fromstring(svg)
        self.assertEqual(data["mix"]["defined-go"]["sound"], {"NO_BLOCKERS_FOUND": 40, "CHANGES_RECOMMENDED": 0, "BLOCKERS_FOUND": 0})
        self.assertEqual(data["mix"]["defined-go"]["uncertain"], {"NO_BLOCKERS_FOUND": 3, "CHANGES_RECOMMENDED": 1, "BLOCKERS_FOUND": 0})
        self.assertEqual(data["lostFamilies"], ["runtime_budget"])
        self.assertEqual((data["strict"]["defined-go"]["count"], data["strict"]["skill"]["count"], data["strict"]["bare"]["count"]), (37, 24, 2))
        for text in ("Clean 40", "Blockers 36", "Clean 3", "Preregistered label: costs detection", "37/40",
                     "Runtime budget evidence", "not out-of-sample evidence", "Defined + optional sentence"):
            self.assertIn(text, svg)
        self.assertIn("<polygon", svg)   # diamonds and triangles, circles and squares: four shapes, not colour alone
        self.assertIn("<circle", svg)
        self.assertEqual(mf.build({"fourArms": data, **{k: INPUTS[k] for k in INPUTS}}).get("ablation-four-arms.svg"), svg)

    def test_four_arm_label_matches_the_analysis_function(self):
        spec = importlib.util.spec_from_file_location("analyze_for_label", mf.ROOT / "benchmarks/counterfactual-pairs/ablation/analyze.py")
        analyze = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(analyze)
        results = mf.RESULTS_V2 / mf.ARM_DIRS["defined-go"]
        vs_defined = json.loads((results / "analysis-vs-defined.json").read_bytes())
        vs_skill = json.loads((results / "analysis-vs-skill.json").read_bytes())
        self.assertEqual(mf.fourth_arm_label(mf.load_four_arms()), analyze.fourth_arm_label(vs_defined, vs_skill))
        for lost, clean, skill_only in ((0, (0, 14), 3), (0, (0, 14), 6), (2, (0, 14), 0), (0, (1, 5), 0), (0, (9, 0), 0), (3, (0, 14), 0)):
            wrap = lambda c, l, s: {"soundCleanDefinedVsGo": {"onlyFirst": c[0], "onlySecond": c[1], "exactTwoSidedSignTestP": analyze.sign_test(*c)},
                                    "twinCorrectDefinedVsGo": {"onlyFirst": l}, "soundCleanSkillVsGo": {"onlyFirst": s}}
            blocks = lambda c, l, s: {"allPairs": {"soundCleanPaired": {"onlyFirst": c[0], "onlySecond": c[1], "exactTwoSidedSignTestP": analyze.sign_test(*c)},
                                                  "changedTwinCorrectPaired": {"onlyFirst": l, "onlySecond": 0}}}
            self.assertEqual(mf.fourth_arm_label(wrap(clean, lost, skill_only)),
                             analyze.fourth_arm_label(blocks(clean, lost, 0), {"allPairs": {"soundCleanPaired": {"onlyFirst": skill_only, "onlySecond": 0,
                                                                                                                   "exactTwoSidedSignTestP": 1.0}}}))

    def test_four_arm_figure_refuses_a_stale_analysis(self):
        results = mf.RESULTS_V2 / mf.ARM_DIRS["defined-go"]
        original = (results / "analysis-vs-defined.json").read_bytes()
        try:
            stale = json.loads(original)
            stale["allPairs"]["strictPairDiscrimination"]["defined-go"]["count"] -= 1
            (results / "analysis-vs-defined.json").write_text(json.dumps(stale), encoding="utf-8")
            with self.assertRaises(SystemExit):
                mf.load_four_arms()
        finally:
            (results / "analysis-vs-defined.json").write_bytes(original)

    def test_stale_figure_is_detected(self):
        figures = mf.build(INPUTS)
        with tempfile.TemporaryDirectory() as raw:
            out = Path(raw)
            for name, svg in figures.items():
                (out / name).write_text(svg, encoding="utf-8")
            stale = [n for n, svg in figures.items() if (out / n).read_text(encoding="utf-8") != svg]
            self.assertEqual(stale, [])
            (out / "offline-evidence.svg").write_text("tampered", encoding="utf-8")
            stale = [n for n, svg in figures.items() if (out / n).read_text(encoding="utf-8") != svg]
            self.assertEqual(stale, ["offline-evidence.svg"])


if __name__ == "__main__":
    unittest.main()
