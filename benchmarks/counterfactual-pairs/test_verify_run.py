"""Offline tests for verify_run.py using the stub Claude executable. No provider calls."""
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
V2 = HERE / "v2"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


vr = load("verify_run", HERE / "verify_run.py")
claude_tests = load("vr_claude_tests", HERE / "test_run_pilot_claude.py")
MODEL = claude_tests.MODEL


def run_and_verify(tmp, corpus, mode="ok", trials=(1,)):
    h = claude_tests.Harness(tmp, mode)
    for t in trials:
        h.run("--corpus", str(corpus), "--execute", "--trial", str(t), "--max-consecutive-stops", "99")
    return h, vr.verify(corpus, h.work, MODEL, "high", list(trials))


class VerifyTests(unittest.TestCase):
    def test_clean_run_verifies_on_both_corpora(self):
        for corpus, n in ((HERE, 24), (V2, 40)):
            with tempfile.TemporaryDirectory() as tmp:
                _, report = run_and_verify(tmp, corpus)
                self.assertEqual(report["failures"], [], corpus)
                self.assertEqual(report["trials"]["1"]["observations"], n)
                self.assertEqual(report["servedModelsReported"], [MODEL])
                self.assertEqual(report["providerCalls"], 0)

    def test_two_trials_and_cost_are_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, report = run_and_verify(tmp, V2, trials=(1, 2))
            self.assertEqual(report["failures"], [])
            self.assertEqual(sorted(report["trials"]), ["1", "2"])
            self.assertAlmostEqual(report["totalCostUsd"], 0.01 * 80, places=4)

    def test_technical_stops_are_reported_not_failures(self):
        with tempfile.TemporaryDirectory() as tmp:
            _, report = run_and_verify(tmp, V2, mode="garbage")
            self.assertEqual(report["failures"], [])
            self.assertEqual(report["trials"]["1"]["technicalStops"], {"NO_JSON_OUTPUT": 40})

    def test_tampered_request_report_or_hash_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _ = run_and_verify(tmp, V2)
            case = json.loads((h.work / "responses-trial1.jsonl").read_text().splitlines()[0])["case"]
            attempt = h.work / "trial1/attempts" / case
            (attempt / "request.txt").write_text("changed", encoding="utf-8")
            self.assertIn(f"REQUEST_MISMATCH:trial1:{case}", vr.verify(V2, h.work, MODEL, "high", [1])["failures"])
        with tempfile.TemporaryDirectory() as tmp:
            h, _ = run_and_verify(tmp, V2)
            case = json.loads((h.work / "responses-trial1.jsonl").read_text().splitlines()[0])["case"]
            (h.work / "trial1/attempts" / case / "REVIEW.md").write_text("edited report", encoding="utf-8")
            failures = vr.verify(V2, h.work, MODEL, "high", [1])["failures"]
            self.assertIn(f"REPORT_HASH_MISMATCH:trial1:{case}", failures)
            self.assertIn(f"REPORT_NOT_CLI_RESULT:trial1:{case}", failures)

    def test_a_ledger_row_that_differs_from_its_saved_report_is_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _ = run_and_verify(tmp, V2)
            ledger = h.work / "responses-trial1.jsonl"
            rows = [json.loads(line) for line in ledger.read_text().splitlines()]
            case = rows[0]["case"]
            rows[0]["assessment"] = "BLOCKERS_FOUND" if rows[0]["assessment"] != "BLOCKERS_FOUND" else "NO_BLOCKERS_FOUND"
            ledger.write_text("\n".join(json.dumps(r) for r in rows) + "\n")
            self.assertIn(f"LEDGER_DIFFERS_FROM_REPARSE:trial1:{case}", vr.verify(V2, h.work, MODEL, "high", [1])["failures"])

    def test_a_saved_report_that_no_longer_parses_is_caught_on_a_row_recorded_as_a_verdict(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _ = run_and_verify(tmp, V2)
            case = json.loads((h.work / "responses-trial1.jsonl").read_text().splitlines()[0])["case"]
            attempt = h.work / "trial1/attempts" / case
            (attempt / "REVIEW.md").write_text("no summary here", encoding="utf-8")
            output = json.loads((attempt / "claude-output.json").read_text())
            output["result"] = "no summary here"
            (attempt / "claude-output.json").write_text(json.dumps(output), encoding="utf-8")
            row = json.loads((h.work / "responses-trial1.jsonl").read_text().splitlines()[0])
            row["reportSha256"] = vr.sha(b"no summary here")
            lines = (h.work / "responses-trial1.jsonl").read_text().splitlines()
            (h.work / "responses-trial1.jsonl").write_text("\n".join([json.dumps(row)] + lines[1:]) + "\n")
            self.assertIn(f"REPORT_DOES_NOT_REPARSE:trial1:{case}", vr.verify(V2, h.work, MODEL, "high", [1])["failures"])

    def test_every_committed_non_stop_ledger_row_reparses_to_its_saved_report(self):
        rc = load("vr_rc", HERE / "run_pilot_claude.py")
        rg = load("vr_rg", HERE / "run_gemini_v3.py")
        checked = 0
        for ledger in sorted((HERE / "results").glob("**/responses.jsonl")):
            for line in ledger.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                if row.get("technicalStop"):
                    continue
                text = (ledger.parent / "reports" / (row["case"] + ".md")).read_text(encoding="utf-8")
                if "v3-gemini" in str(ledger):
                    parsed = rg.tolerant_parse(text)
                elif row.get("arm") in rc.VERDICT_ONLY_ARMS:
                    parsed = rc.parse_bare(text)
                else:
                    parsed = rc.rp.parse_report(text)
                for key in ("assessment", "completeness", "findings", "verdictRaw"):
                    if key in parsed or key in row:
                        self.assertEqual(parsed.get(key), row.get(key), (str(ledger), row["case"], key))
                checked += 1
        self.assertGreater(checked, 1100)

    def test_missing_duplicate_and_wrong_arguments_are_caught(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _ = run_and_verify(tmp, V2)
            ledger = h.work / "responses-trial1.jsonl"
            lines = ledger.read_text().splitlines()
            ledger.write_text("\n".join(lines[:-1] + [lines[0]]) + "\n")
            failures = vr.verify(V2, h.work, MODEL, "high", [1])["failures"]
            self.assertTrue(any(f.startswith("DUPLICATE_CASES") for f in failures))
            self.assertTrue(any(f.startswith("CASE_SET_MISMATCH") for f in failures))
            ledger.write_text("\n".join(lines) + "\n")
            self.assertTrue(any(f.startswith("STAMP_MISMATCH") for f in vr.verify(V2, h.work, MODEL, "low", [1])["failures"]))
            self.assertIn("LEDGER_MISSING:trial2", vr.verify(V2, h.work, MODEL, "high", [1, 2])["failures"])

    def test_corpus_edit_is_caught(self):
        import shutil
        with tempfile.TemporaryDirectory() as tmp:
            h, _ = run_and_verify(tmp, V2)
            copy = Path(tmp) / "corpus"
            shutil.copytree(V2, copy, ignore=shutil.ignore_patterns("__pycache__"))
            (copy / "PREREGISTRATION.md").write_text("edited", encoding="utf-8")
            failures = vr.verify(copy, h.work, MODEL, "high", [1])["failures"]
            self.assertIn("CORPUS_PIN_MISMATCH:PREREGISTRATION.md", failures)

    def test_verifier_never_reads_the_oracle(self):
        self.assertNotIn("oracle", (HERE / "verify_run.py").read_text().replace("oracle.json", "").lower().replace("the oracle", ""))


if __name__ == "__main__":
    unittest.main()
