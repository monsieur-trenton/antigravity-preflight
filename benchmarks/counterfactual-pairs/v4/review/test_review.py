"""Offline tests of the v4 reviewer prompts and request builders; no model calls."""
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
sys.path.insert(0, str(HERE))
import review_requests as rr  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s4 = load("t_review_score_v4", V4 / "score_v4.py")
pv = load("t_review_parse_v4", V4 / "parse_v4.py")
DEV = s4.Corpus(V4 / "dev")
FORBIDDEN_WORDS = ("twin", "oracle", "benchmark", "counterfactual", "test case", "decisive", "omitted", "sound plan", "mechanism")


def sources_of(case):
    return {r["id"]: DEV.lines(case, r["id"]) for r in DEV.oracle[case]["sources"]}


class PromptFileTests(unittest.TestCase):
    def test_the_reviewer_files_name_no_class_kind_or_corpus_word(self):
        for name in ("prompt.txt", "format-suffix.txt", "bare-request.txt", "bare-reference-lead.txt"):
            text = (HERE / name).read_text(encoding="utf-8").lower()
            for word in FORBIDDEN_WORDS:
                self.assertNotIn(word, text, (name, word))

    def test_the_skill_prompt_keeps_the_v3_contract_sentences_that_the_earlier_results_depend_on(self):
        v3 = (V4.parent / "v3" / "prompt.txt").read_text(encoding="utf-8")
        v4 = (HERE / "prompt.txt").read_text(encoding="utf-8")
        for sentence in ("Do not report a blocker the supplied text does not support, and do not\ntreat missing evidence as a proven defect.",
                         "Follow the review contract exactly: a read-only advisory review"):
            self.assertIn(sentence, v3)
            self.assertIn(sentence, v4)
        for needle in ("source S01", "reference excerpt S02", "conflicts between the plan and the reference excerpt", "the source id and line number"):
            self.assertIn(needle, v4)

    def test_the_format_asks_for_source_qualified_lines_in_the_form_the_parser_reads(self):
        text = (HERE / "format-suffix.txt").read_text(encoding="utf-8")
        self.assertIn("S01:12 or S02:5", text)
        self.assertIn("{SOURCES}", text)
        self.assertEqual(text.count("MACHINE SUMMARY"), 1)

    def test_the_manifest_matches_the_files(self):
        done = subprocess.run([sys.executable, "-B", "-I", str(HERE / "build_manifest.py"), "--check"], capture_output=True, text=True, check=False)
        self.assertEqual((done.returncode, json.loads(done.stdout)["status"]), (0, "PASS"))


class RequestTests(unittest.TestCase):
    def test_every_dev_request_is_deterministic_numbered_and_free_of_corpus_words(self):
        for case, record in DEV.oracle.items():
            sources = sources_of(case)
            for arm in rr.ARMS:
                request = rr.build(arm, sources)
                self.assertEqual(request, rr.build(arm, sources))
                text = request.decode("utf-8")
                low = text.lower()
                for word in FORBIDDEN_WORDS + (case.lower(), record["pair"].lower(), record["family"], record["kind"], record["domain"]):
                    self.assertNotIn(word, low, (case, arm, word))
                self.assertLess(len(request), 131072)
                if arm != "bare":
                    for source, lines in sources.items():
                        for n, line in enumerate(lines, 1):
                            self.assertIn(f"[{source}:{n}] {line}\n", text)
                    self.assertEqual("[S02:" in text, len(sources) == 2)
                    self.assertIn("sources S01 and S02" if len(sources) == 2 else "source S01.", text.split("Write one FINDING line")[1].split("Copy quotations")[0] + "source S01.")
                else:
                    self.assertTrue(text.endswith("VERDICT: NO_GO\n"))
                    self.assertNotIn("MACHINE SUMMARY", text)
                    self.assertNotIn("[S01:", text)
                    self.assertEqual("reference excerpt" in text, len(sources) == 2)

    def test_the_worst_case_fits_the_runtime_prompt_cap(self):
        longest = {"S01": ["x" * 220] * 80, "S02": ["y" * 220] * 25}
        for arm in rr.ARMS:
            self.assertLess(len(rr.build(arm, longest)), 131072)

    def test_skill_go_differs_from_skill_by_exactly_the_pinned_sentence(self):
        sources = sources_of(next(c for c, r in DEV.oracle.items() if len(r["sources"]) == 2))
        plain, plus = rr.build("skill", sources).decode().splitlines(), rr.build("skill-go", sources).decode().splitlines()
        sentence = rr.skill_go_sentence()
        self.assertEqual([line for line in plus if line not in plain], [sentence])
        self.assertEqual(len(plus), len(plain) + 1)
        self.assertEqual(plus.index(sentence), len((HERE / "prompt.txt").read_text(encoding="utf-8").splitlines()))
        self.assertIn("Optional suggestions", sentence)

    def test_a_source_set_other_than_the_plan_with_or_without_one_reference_is_refused(self):
        for bad in ({}, {"S02": ["a"]}, {"S01": ["a"], "S03": ["b"]}, {"S01": ["a"], "S02": ["b"], "S03": ["c"]}):
            with self.assertRaises(ValueError):
                rr.build("skill", bad)
        with self.assertRaises(ValueError):
            rr.build("defined", {"S01": ["a"]})


class ParseTests(unittest.TestCase):
    def test_a_skill_report_citing_the_reference_is_parsed_and_supported_by_the_scorer(self):
        case = next(c for c, r in DEV.oracle.items() if r["role"] == "changed" and r["kind"] == "cross_source_defect")
        ref = DEV.oracle[case]["citeAnyOf"][-1]
        quote = DEV.lines(case, ref["source"])[ref["line"] - 1][:30]
        report = f"A rationale.\n\nMACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: BLOCKERS_FOUND\nFINDING: BLOCKER | VERIFIED | {ref['source']}:{ref['line']} | {quote}\n"
        parsed = pv.parse_report(report)
        row = dict(parsed, case=case, trial=1, arm="skill")
        trial = s4.score([row], V4 / "dev")["trials"]["1"]
        self.assertEqual(trial["unsupportedVerifiedFindings"], 0)
        self.assertEqual(s4.grade(row, DEV.oracle[case], DEV)[0], "CORRECT")

    def test_the_bare_parser(self):
        self.assertEqual(rr.parse_bare("Fine.\n\nVERDICT: GO_WITH_CHANGES\n")["assessment"], "CHANGES_RECOMMENDED")
        self.assertEqual(rr.parse_bare("x\n**VERDICT: NO_GO**")["assessment"], "BLOCKERS_FOUND")
        self.assertEqual(rr.parse_bare("VERDICT: GO\n")["assessment"], "NO_BLOCKERS_FOUND")
        for bad in ("", "VERDICT: GO\nand a last word", "VERDICT: MAYBE", "Verdict: go"):
            with self.assertRaises(ValueError):
                rr.parse_bare(bad)

    def test_the_bare_arm_name_is_the_one_the_scorer_treats_as_verdict_only(self):
        self.assertIn("bare", s4.VERDICT_ONLY_ARMS)
        self.assertNotIn("skill", s4.VERDICT_ONLY_ARMS)
        self.assertNotIn("skill-go", s4.VERDICT_ONLY_ARMS)


if __name__ == "__main__":
    unittest.main()
