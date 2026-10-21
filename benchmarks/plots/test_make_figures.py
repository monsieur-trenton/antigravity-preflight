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
