"""Offline tests for reparse_lenient.py. No model calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("reparse_lenient", HERE / "reparse_lenient.py")
rl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rl)

REPORT = ("### Rationale\nYes.\n\nMACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: BLOCKERS_FOUND\n"
          "FINDING: BLOCKER | VERIFIED | {field} | The job lists directories older than 7 days and deletes all of them.\n")


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def row(case, text, code="UNPARSEABLE_REPORT:MALFORMED_FINDING"):
    return {"case": case, "trial": 1, "reportSha256": sha(text), "technicalStop": code, "wallSeconds": 1.5}


class LenientTests(unittest.TestCase):
    def run_rows(self, reports):
        with tempfile.TemporaryDirectory() as tmp:
            for case, text in reports.items():
                (Path(tmp) / (case + ".md")).write_text(text, encoding="utf-8")
            rows = [row(c, t) for c, t in reports.items()]
            return rl.reparse(rows, tmp)

    def test_a_snapshot_label_is_read_as_the_line_number_and_the_hash_is_kept(self):
        text = REPORT.format(field="S01:3")
        out, changed = self.run_rows({"P-a": text})
        self.assertEqual(changed, ["P-a"])
        self.assertEqual((out[0]["assessment"], out[0]["findings"][0]["line"], out[0]["reparsedFrom"]), ("BLOCKERS_FOUND", 3, "UNPARSEABLE_REPORT:MALFORMED_FINDING"))
        self.assertEqual(out[0]["reportSha256"], sha(text))
        self.assertNotIn("technicalStop", out[0])

    def test_only_that_one_relaxation_is_allowed(self):
        for field in ("three", "S01-3", "S01:", "line 3", "[S01:3]", "S01:3x", "3:S01"):
            out, changed = self.run_rows({"P-a": REPORT.format(field=field)})
            self.assertEqual(changed, [], field)
            self.assertEqual(out[0]["technicalStop"], "UNPARSEABLE_REPORT:MALFORMED_FINDING", field)
            self.assertIn("reparseRefused", out[0])

    def test_other_format_errors_stay_stops_even_with_a_label(self):
        text = REPORT.format(field="S01:3").replace("COMPLETENESS: COMPLETE", "COMPLETENESS: DONE")
        out, changed = self.run_rows({"P-a": text})
        self.assertEqual(changed, [])
        self.assertEqual(out[0]["reparseRefused"], "INVALID_COMPLETENESS")

    def test_a_report_that_does_not_match_its_hash_is_refused_and_other_rows_pass_through(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = REPORT.format(field="S01:3")
            (Path(tmp) / "P-a.md").write_text(text + "tampered\n", encoding="utf-8")
            kept = {"case": "P-b", "trial": 1, "assessment": "NO_BLOCKERS_FOUND", "completeness": "COMPLETE", "findings": []}
            stop = {"case": "P-c", "trial": 1, "technicalStop": "UNPARSEABLE_REPORT:NO_MACHINE_SUMMARY", "reportSha256": "0"}
            out, changed = rl.reparse([row("P-a", text), kept, stop], tmp)
            self.assertEqual((changed, out[0]["reparseRefused"], out[1], out[2]), ([], "REPORT_HASH_MISMATCH", kept, stop))

    def test_the_command_line_writes_a_new_file_and_leaves_the_ledger_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            reports = Path(tmp) / "reports"
            reports.mkdir()
            text = REPORT.format(field="S01:3")
            (reports / "P-a.md").write_text(text, encoding="utf-8")
            ledger = Path(tmp) / "ledger.jsonl"
            ledger.write_text(json.dumps(row("P-a", text)) + "\n", encoding="utf-8")
            before = ledger.read_bytes()
            out = Path(tmp) / "out.jsonl"
            self.assertEqual(rl.main([str(ledger), str(reports), str(out)]), 0)
            self.assertEqual(ledger.read_bytes(), before)
            self.assertEqual(json.loads(out.read_text())["assessment"], "BLOCKERS_FOUND")


if __name__ == "__main__":
    unittest.main()
