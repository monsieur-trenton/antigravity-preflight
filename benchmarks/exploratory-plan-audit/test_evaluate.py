"""Regression tests for historical scorer failures; no provider/model calls."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("retrospective_evaluator", ROOT / "evaluate.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class VerdictTests(unittest.TestCase):
    def test_explicit_labels(self):
        rows = {
            "Verdict: GO": "GO",
            "### Verdict: **GO** (Safe to proceed)": "GO",
            "### Verdict\n**NO-GO** (Fatal tripwire detected)": "NO-GO",
            "**Verdict:** **NO-GO** (Fatal tripwire detected)": "NO-GO",
            "### Audit Verdict\n**NO-GO** (Fatal tripwire detected)": "NO-GO",
            "Final verdict: NO GO": "NO-GO",
            "GO": "GO",
            "This assessment is ongoing.": "UNCLEAR",
            "NO_BLOCKERS_FOUND": "UNCLEAR",
            "Verdict: NO_BLOCKERS_FOUND": "UNCLEAR",
            "Verdict: CHANGES_RECOMMENDED": "UNCLEAR",
            "Please choose GO or NO-GO.": "UNCLEAR",
            "Verdict: GO\nVerdict: NO-GO": "UNCLEAR",
            "> Verdict: GO": "UNCLEAR",
            "```\nVerdict: NO-GO\n```\nVerdict: GO": "GO",
            "~~~markdown\nVerdict: GO\n~~~": "UNCLEAR",
            "Verdict: GO\nThe old NO-GO report has been superseded.": "GO",
            "Verdict: GO\nVerdict: GO": "GO",
            "Verdict: NOT GO": "UNCLEAR",
            "Verdict: GOING": "UNCLEAR",
            "Verdict: UNVERIFIABLE\nFinal verdict: GO": "UNCLEAR",
            "Verdict: GO\nVerdict: UNKNOWN": "UNCLEAR",
        }
        for text, expected in rows.items():
            with self.subTest(text=text):
                self.assertEqual(module.extract_verdict(text), expected)

    def test_process_failure_cannot_match(self):
        case = dict(id="test", ground_truth=dict(expected_verdict="GO", key_identifiers=["GO"]))
        for changes in [dict(exit_code=1), dict(exit_code=True), dict(error="timeout"), dict(stdout="")]:
            raw = dict(stdout="Verdict: GO", exit_code=0, error=None)
            raw.update(changes)
            result = module.score(raw, case)
            self.assertFalse(result["originalLabelMatch"])
            self.assertEqual(result["extractedLabel"], "UNADMITTED")

    def test_keywords_do_not_award_semantic_credit(self):
        case = dict(id="test", ground_truth=dict(expected_verdict="NO-GO", key_identifiers=["1500"]))
        result = module.score(dict(stdout="Verdict: NO-GO\n1500", exit_code=0, error=None), case)
        self.assertEqual(result["keywordHints"], ["1500"])
        self.assertFalse(result["keywordHintsAreSemanticCredit"])
        self.assertEqual(result["semanticGrade"], "REQUIRES_SEPARATE_ADJUDICATION")

    def test_retained_observations_remain_label_matches_only(self):
        result = module.evaluate()
        self.assertEqual(result["observations"], 4)
        self.assertEqual(result["originalLabelMatches"], 4)
        self.assertEqual(result["newModelCalls"], 0)
        self.assertNotIn("recall", result)
        self.assertTrue(all(r["semanticGrade"] == "REQUIRES_SEPARATE_ADJUDICATION" for r in result["results"]))
        self.assertEqual(result, json.loads((ROOT / "retrospective-labels.json").read_bytes()))

    def test_original_clean_control_has_unbounded_pointer(self):
        # A path beneath typical filesystem length limits can still exceed the
        # output cap. No files are created and no historical snippet is executed.
        target = ("/" + "segment" * 14) * 16 + "/metadata-full.json"
        pointer = json.dumps(dict(status="OUTPUT_WRITTEN_TO_FILE", path=target,
                                  bytes=1501, sha256="0" * 64)).encode()
        self.assertEqual(len(target), 1603)
        self.assertEqual(len(pointer), 1744)
        self.assertGreater(len(pointer), 1500)


if __name__ == "__main__":
    unittest.main()
