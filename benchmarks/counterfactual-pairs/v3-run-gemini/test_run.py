"""Offline tests for the Gemini v3 run tooling: manifest binding, the driver and its parser relaxation, and the verifier. A stub runtime stands in for the native CLI; no provider calls."""
import contextlib
import hashlib
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
REPO = PARENT.parent.parent
V3 = PARENT / "v3"
V2 = PARENT / "v2"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rg = load("t_run_gemini_v3", PARENT / "run_gemini_v3.py")
vg = load("t_verify_gemini_run", PARENT / "verify_gemini_run.py")
bg = load("t_bundle_gemini_evidence", PARENT / "bundle_gemini_evidence.py")
bm = load("t_gemini_build_manifest", HERE / "build_manifest.py")
sc = load("t_score", PARENT / "score.py")
rp = rg.rp
MANIFEST = HERE / "manifest.json"
RUN = json.loads(MANIFEST.read_bytes())
BINARY = RUN["binary"]["sha256"]
ORACLE = {c["case"]: c for c in json.loads((V3 / "oracle/oracle.json").read_bytes())["cases"]}

STUB = r'''
import hashlib, json, shutil, sys
from pathlib import Path
here = Path(__file__).resolve().parent
config = json.loads((here / "stub-config.json").read_text())
args = sys.argv[1:]
sha = lambda b: hashlib.sha256(b).hexdigest()
if args[0] == "prepare":
    packet, seed = Path(args[1]), Path(args[3])
    shutil.copytree(packet.parent, seed / "packet")
    (seed / "CLI-PLAN.json").write_text("{}")
elif args[0] == "run":
    attempt = Path(args[1])
    assert "--authorize-live" in args and "--qualification" in args
    snapshot = (attempt / "packet/snapshots/S01.txt").read_text().split("\n")
    prompt = (attempt / "packet/prompt.txt").read_bytes()
    mode = config["mode"]
    head = "Rationale.\n\nMACHINE SUMMARY\nCOMPLETENESS: COMPLETE\n"
    reports = {"approve": head + "ASSESSMENT: NO_BLOCKERS_FOUND\n",
               "label": head + "ASSESSMENT: BLOCKERS_FOUND\nFINDING: BLOCKER | VERIFIED | S01:3 | " + snapshot[2] + "\n",
               "digit": head + "ASSESSMENT: BLOCKERS_FOUND\nFINDING: BLOCKER | VERIFIED | 3 | " + snapshot[2] + "\n",
               "bracket": head + "ASSESSMENT: BLOCKERS_FOUND\nFINDING: BLOCKER | VERIFIED | [S01:3] | " + snapshot[2] + "\n",
               "garbage": "I think it is fine."}
    report = reports[mode].encode("utf-8")
    frame = json.dumps(dict(event="user", message=dict(content=prompt.decode("utf-8")))).encode() + b"\n"
    (attempt / "GEMINI-REVIEW.md").write_bytes(report)
    receipt = {"status": "REPORT_RECEIVED_PENDING_ADJUDICATION", "failure": None, "closingFailures": [],
               "model": "gemini-3.8-flash-high", "effort": "high", "retries": 0, "invocations": {"proxy": 1, "native": 1},
               "processes": {"native": {"spawned": True, "reaped": True}, "proxy": {"spawned": True, "reaped": True}},
               "privateHomeAbsent": True, "socketDirectoryAbsent": True,
               "promptDelivery": {"status": "COMPLETE", "wireBytes": len(frame), "bytesWritten": len(frame)},
               "native": {"sha256": config["binary"], "bytes": 1}, "report": {"sha256": sha(report), "bytes": len(report)}}
    receipt.update(config.get("receipt", {}))
    (attempt / "CLI-RECEIPT.json").write_text(json.dumps(receipt))
'''


class Harness:
    def __init__(self, tmp, mode="approve", runtime_name="flash-high", binary=BINARY, receipt=None, caps=None):
        self.tmp = Path(tmp)
        self.runtime = self.tmp / "rt" / runtime_name
        (self.runtime / "scripts").mkdir(parents=True)
        (self.runtime / "scripts/cli_review.py").write_text(STUB)
        (self.runtime / "scripts/stub-config.json").write_text(json.dumps({"mode": mode, "binary": binary, "receipt": receipt or {}}))
        self.caps = self.tmp / "caps"
        self.caps.mkdir()
        (self.caps / "RESULT.json").write_text(json.dumps(caps or {
            "status": "PASS_METADATA_CAPABILITIES_ONLY", "binaryStable": True, "frozenBinary": {"sha256": BINARY, "bytes": 1},
            "observedVersion": "agy 1.4.1", "model": "gemini-3.8-flash-high", "effort": "high"}))
        (self.tmp / "q.json").write_text("{}")
        self.work = self.tmp / "work"
        self.original_tree = rg.runtime_tree_sha
        rg.runtime_tree_sha = lambda directory: RUN["runtime"]["treeSha256"]  # the stub is not the real runtime package

    def close(self):
        rg.runtime_tree_sha = self.original_tree

    def run(self, *extra, corpus=V3, manifest=MANIFEST, trial=1):
        argv = ["--runtime-dir", str(self.runtime), "--capabilities", str(self.caps), "--qualification", str(self.tmp / "q.json"),
                "--workdir", str(self.work), "--corpus", str(corpus), "--run-manifest", str(manifest), "--trial", str(trial), *extra]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = rg.main(argv)
        return code, json.loads(out.getvalue().strip().splitlines()[-1])

    def ledger(self, trial=1):
        return [json.loads(l) for l in (self.work / f"responses-trial{trial}.jsonl").read_text().splitlines()]

    def verify(self, trial=1, manifest=MANIFEST):
        return vg.verify(V3, manifest, self.work, trial)


class WithHarness(unittest.TestCase):
    def harness(self, **kw):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        h = Harness(tmp.name, **kw)
        self.addCleanup(h.close)
        return h


class FrozenFilesTests(unittest.TestCase):
    def test_manifest_is_current_and_ties_the_run_to_corpus_runtime_and_binary(self):
        self.assertEqual(MANIFEST.read_bytes(), bm.build())
        self.assertEqual(RUN["corpus"]["manifestSha256"], rp.sha((V3 / "manifest.json").read_bytes()))
        self.assertEqual(RUN["runtime"]["treeSha256"], rg.runtime_tree_sha(REPO / "runtime/flash-high"))
        self.assertEqual((RUN["runtime"]["dir"], RUN["runtime"]["profile"], RUN["runtime"]["model"], RUN["runtime"]["effort"]),
                         ("runtime/flash-high", None, "gemini-3.8-flash-high", "high"))
        self.assertEqual(sorted(RUN["pins"]), ["PREREGISTRATION.md"])

    def test_the_frozen_binary_is_the_one_every_receipt_of_the_gemini_pilot_recorded(self):
        receipts = list((PARENT / "results/pilot-flash-high").glob("trial*/receipts/*.json"))
        self.assertEqual(len(receipts), 48)
        self.assertEqual({json.loads(p.read_text())["native"]["sha256"] for p in receipts}, {BINARY})

    def test_the_brief_names_the_current_hashes_and_commands(self):
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for digest in (rp.sha(MANIFEST.read_bytes()), rp.sha((V3 / "manifest.json").read_bytes()), BINARY):
            self.assertIn(digest, brief)
        for text in ("run_gemini_v3.py", "verify_gemini_run.py", "bundle_gemini_evidence.py", "--run-manifest", "go trial N", "Do not commit, push", "do not archive or upload"):
            self.assertIn(text, brief)

    def test_the_pilot_driver_is_imported_not_edited(self):
        # run_pilot.py stays byte-identical, so the pilot's evidence stays tied to unchanged code; the relaxation lives only in the wrapper.
        self.assertNotIn("snapshot-label", (PARENT / "run_pilot.py").read_text())
        self.assertIn("snapshot-label", (PARENT / "run_gemini_v3.py").read_text())

    def test_tree_hash_changes_when_a_runtime_file_changes_and_ignores_bytecode(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "flash-high"
            shutil.copytree(REPO / "runtime/flash-high", copy)
            before = rg.runtime_tree_sha(copy)
            (copy / "scripts/__pycache__").mkdir(exist_ok=True)
            (copy / "scripts/__pycache__/x.pyc").write_bytes(b"x")
            self.assertEqual(rg.runtime_tree_sha(copy), before)
            (copy / "scripts/cli_review.py").write_bytes((copy / "scripts/cli_review.py").read_bytes() + b"\n#")
            self.assertNotEqual(rg.runtime_tree_sha(copy), before)


class PromptDeliveryTests(unittest.TestCase):
    def test_the_framed_prompt_length_matches_every_real_receipt_of_the_gemini_pilot(self):
        # The first live use of the verifier compared wireBytes with the bare prompt and failed on every case: the runtime sends one stream-json frame.
        v1 = PARENT
        prompt = (v1 / "prompt.txt").read_text(encoding="utf-8")
        checked = 0
        for trial in (1, 2):
            for path in sorted((v1 / f"results/pilot-flash-high/trial{trial}/receipts").glob("*.json")):
                snapshot = (v1 / "packets" / (path.stem + ".txt")).read_bytes().decode("utf-8").split("\n")[:-1]
                delivery = json.loads(path.read_text())["promptDelivery"]
                wire = vg.expected_wire_bytes(rp.request_text(prompt, snapshot, True))
                self.assertEqual((delivery["wireBytes"], delivery["bytesWritten"]), (wire, wire), path.name)
                checked += 1
        self.assertEqual(checked, 48)

    def test_a_non_ascii_prompt_is_escaped_in_the_frame_as_the_runtime_does(self):
        self.assertEqual(vg.expected_wire_bytes("caf\u00e9".encode("utf-8")), len(json.dumps(dict(event="user", message=dict(content="caf\u00e9"))).encode()) + 1)


class ParserTests(unittest.TestCase):
    REPORT = "x\n\nMACHINE SUMMARY\nCOMPLETENESS: COMPLETE\nASSESSMENT: BLOCKERS_FOUND\nFINDING: BLOCKER | VERIFIED | {field} | a quote\n"

    def test_only_the_snapshot_label_relaxation_is_admitted(self):
        parsed = rg.tolerant_parse(self.REPORT.format(field="S01:3"))
        self.assertEqual((parsed["findings"][0]["line"], parsed["snapshotLabelRead"]), (3, True))
        self.assertNotIn("snapshotLabelRead", rg.tolerant_parse(self.REPORT.format(field="3")))
        for field in ("[S01:3]", "S01-3", "S02:3", "line 3", "three", "S01:", "3b"):
            with self.assertRaises(rp.Stop, msg=field):
                rg.tolerant_parse(self.REPORT.format(field=field))

    def test_the_strict_parser_still_refuses_the_label(self):
        with self.assertRaises(rp.Stop):
            rg.STRICT_PARSE(self.REPORT.format(field="S01:3"))


class DriverTests(WithHarness):
    def test_dry_run_prepares_all_cases_writes_no_ledger_and_names_the_run(self):
        h = self.harness()
        code, out = h.run()
        self.assertEqual((code, out["status"], out["prepared"], out["route"], out["parser"]), (0, "DRY_RUN_PREPARED_ONLY", 64, rg.ROUTE, rg.PARSER))
        self.assertEqual(out["runManifestSha256"], rp.sha(MANIFEST.read_bytes()))
        self.assertFalse((h.work / "responses-trial1.jsonl").exists())

    def test_live_run_stamps_every_row_and_the_verifier_passes(self):
        h = self.harness()
        code, out = h.run("--execute")
        self.assertEqual((code, out["status"], out["executed"], out["stopped"]), (0, "COMPLETE", 64, 0))
        rows = h.ledger()
        self.assertEqual([r["case"] for r in rows], json.loads((V3 / "manifest.json").read_bytes())["submissionOrder"])
        self.assertTrue(all((r["route"], r["parser"], r["runManifestSha256"], r["binarySha256"]) == (rg.ROUTE, rg.PARSER, rp.sha(MANIFEST.read_bytes()), BINARY) for r in rows))
        report = h.verify()
        self.assertEqual((report["failures"], report["observations"], report["technicalStops"]), ([], 64, {}))

    def test_a_snapshot_label_is_read_flagged_and_verified_and_the_scorer_accepts_the_ledger(self):
        h = self.harness(mode="label")
        code, out = h.run("--execute")
        self.assertEqual((code, out["executed"], out["stopped"]), (0, 64, 0))
        rows = h.ledger()
        self.assertTrue(all(r["snapshotLabelRead"] and r["findings"][0]["line"] == 3 for r in rows))
        report = h.verify()
        self.assertEqual((report["failures"], report["snapshotLabelsRead"]), ([], 64))
        self.assertEqual(sc.score(rows, V3)["trials"]["1"]["observations"], 64)

    def test_a_bare_digit_is_not_flagged(self):
        h = self.harness(mode="digit")
        h.run("--execute")
        self.assertTrue(not any(r.get("snapshotLabelRead") for r in h.ledger()))
        self.assertEqual(h.verify()["failures"], [])

    def test_other_malformed_findings_stay_stops_and_are_listed_not_failures(self):
        h = self.harness(mode="bracket")
        code, out = h.run("--execute", "--max-consecutive-stops", "99")
        self.assertEqual((code, out["stopped"]), (0, 64))
        self.assertTrue(all(r["technicalStop"] == "UNPARSEABLE_REPORT:MALFORMED_FINDING" for r in h.ledger()))
        report = h.verify()
        self.assertEqual((report["failures"], report["technicalStops"]), ([], {"UNPARSEABLE_REPORT": 64}))

    def test_three_consecutive_stops_halt_and_a_resume_skips_what_is_recorded(self):
        h = self.harness(mode="garbage")
        code, out = h.run("--execute")
        self.assertEqual((code, out["status"], out["stopped"]), (1, "HALTED_CONSECUTIVE_STOPS", 3))
        h2 = self.harness(mode="approve")
        h2.run("--execute", "--max-consecutive-stops", "99")
        again = h2.run("--execute")[1]
        self.assertEqual((again["skippedAlreadyRecorded"], again["executed"]), (64, 0))

    def test_an_attempt_without_a_record_is_logged_never_rerun(self):
        h = self.harness()
        first = json.loads((V3 / "manifest.json").read_bytes())["submissionOrder"][0]
        (h.work / "trial1/attempts" / first).mkdir(parents=True)
        h.run("--execute")
        self.assertEqual(h.ledger()[0]["technicalStop"], "INTERRUPTED_UNKNOWN_STATE")

    def test_refusals_before_any_turn(self):
        cases = [("RUN_CORPUS_MISMATCH", dict(), dict(corpus=V2)),
                 ("RUN_BINARY_MISMATCH", dict(caps={"status": "PASS_METADATA_CAPABILITIES_ONLY", "binaryStable": True, "frozenBinary": {"sha256": "0" * 64},
                                                    "observedVersion": "agy 1.4.1", "model": "gemini-3.8-flash-high", "effort": "high"}), dict()),
                 ("RUN_BINARY_VERSION_MISMATCH", dict(caps={"status": "PASS_METADATA_CAPABILITIES_ONLY", "binaryStable": True, "frozenBinary": {"sha256": BINARY},
                                                            "observedVersion": "agy 2.0.0", "model": "gemini-3.8-flash-high", "effort": "high"}), dict()),
                 ("CAPABILITIES_NOT_PASS", dict(caps={"status": "STOPPED"}), dict()),
                 ("RUN_RUNTIME_NOT_FLASH_HIGH", dict(runtime_name="argon-high"), dict())]
        for expected, harness_kw, run_kw in cases:
            h = self.harness(**harness_kw)
            code, out = h.run("--execute", **run_kw)
            self.assertEqual((code, out["reason"]), (1, expected), expected)
            self.assertFalse((h.work / "responses-trial1.jsonl").exists(), expected)

    def test_a_changed_runtime_package_is_refused(self):
        h = self.harness()
        rg.runtime_tree_sha = h.original_tree  # the stub's real hash differs from the frozen one
        code, out = h.run("--execute")
        self.assertEqual((code, out["reason"]), (1, "RUN_RUNTIME_TREE_MISMATCH"))

    def test_a_tampered_run_manifest_is_refused(self):
        h = self.harness()
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "run"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            (copy / "PREREGISTRATION.md").write_text("edited", encoding="utf-8")
            code, out = h.run("--execute", manifest=copy / "manifest.json")
            self.assertEqual((code, out["reason"]), (1, "RUN_PIN_MISMATCH:PREREGISTRATION.md"))


class VerifierTests(WithHarness):
    def finished(self, **kw):
        h = self.harness(**kw)
        h.run("--execute")
        return h

    def first_case(self, h):
        return h.ledger()[0]["case"]

    def test_a_tampered_report_prompt_or_snapshot_is_caught(self):
        h = self.finished()
        case = self.first_case(h)
        attempt, packet = h.work / "trial1/attempts" / case, h.work / "trial1/packets" / case
        review = attempt / "GEMINI-REVIEW.md"
        original = review.read_bytes()
        review.write_bytes(original + b"x")
        self.assertIn(f"REPORT_HASH_MISMATCH:{case}", h.verify()["failures"])
        review.write_bytes(original)
        (packet / "prompt.txt").write_bytes((packet / "prompt.txt").read_bytes() + b" ")
        self.assertIn(f"REQUEST_MISMATCH:{case}", h.verify()["failures"])

    def test_each_receipt_defect_is_named(self):
        faults = {"RECEIPT_RETRIES_OR_INVOCATIONS": {"retries": 1}, "RECEIPT_NOT_CLEAN": {"failure": {"code": "X"}},
                  "PROCESS_NOT_REAPED": {"processes": {"native": {"spawned": True, "reaped": False}}},
                  "SANDBOX_NOT_CLEANED": {"privateHomeAbsent": False}, "NATIVE_BINARY_HASH": {"native": {"sha256": "0" * 64}},
                  "PROMPT_DELIVERY": {"promptDelivery": {"status": "COMPLETE", "wireBytes": 1, "bytesWritten": 1}},
                  "RECEIPT_MODEL_OR_EFFORT": {"model": "other"}}
        for expected, override in faults.items():
            h = self.finished(receipt=override)
            failures = h.verify()["failures"]
            self.assertTrue(any(f.startswith(expected + ":") for f in failures), (expected, failures[:2]))

    def test_ledger_defects_are_named(self):
        h = self.finished()
        path = h.work / "responses-trial1.jsonl"
        rows = h.ledger()
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows[1:]))
        self.assertTrue(any(f.startswith("CASE_SET_MISMATCH") for f in h.verify()["failures"]))
        swapped = [rows[1], rows[0]] + rows[2:]
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in swapped))
        self.assertIn("RECORDED_OUT_OF_ORDER", h.verify()["failures"])
        bad = [dict(rows[0], runManifestSha256="0" * 64)] + rows[1:]
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in bad))
        self.assertIn(f"STAMP_MISMATCH:{rows[0]['case']}", h.verify()["failures"])
        changed = [dict(rows[0], assessment="BLOCKERS_FOUND")] + rows[1:]
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in changed))
        self.assertIn(f"LEDGER_DIFFERS_FROM_REPARSE:{rows[0]['case']}", h.verify()["failures"])
        path.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows) + json.dumps(rows[0]) + "\n")
        self.assertIn("DUPLICATE_CASES", h.verify()["failures"])

    def test_a_stop_that_would_now_parse_and_a_missing_ledger_are_failures(self):
        h = self.finished(mode="label")
        rows = h.ledger()
        rows[0] = {k: rows[0][k] for k in ("case", "trial", "reportSha256", "wallSeconds", "route", "parser", "runManifestSha256", "binarySha256")}
        rows[0]["technicalStop"] = "UNPARSEABLE_REPORT:MALFORMED_FINDING"
        (h.work / "responses-trial1.jsonl").write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        self.assertIn(f"STOP_BUT_REPORT_PARSES:{rows[0]['case']}", h.verify()["failures"])
        self.assertEqual(vg.verify(V3, MANIFEST, h.work, 2)["failures"], ["LEDGER_MISSING"])

    def test_the_command_line_exits_nonzero_on_a_failure(self):
        h = self.finished()
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(vg.main(["--corpus", str(V3), "--run-manifest", str(MANIFEST), "--workdir", str(h.work)]), 0)
            (h.work / "responses-trial1.jsonl").unlink()
            self.assertEqual(vg.main(["--corpus", str(V3), "--run-manifest", str(MANIFEST), "--workdir", str(h.work)]), 1)


class BundleTests(WithHarness):
    def full_run_with_bulk(self):
        h = self.harness()
        h.run("--execute")
        for case in [r["case"] for r in h.ledger()][:3]:
            for bulk in (h.work / "trial1/seeds" / case / "runtime/agy", h.work / "trial1/attempts" / case / "private-home/cache.bin"):
                bulk.parent.mkdir(parents=True, exist_ok=True)
                bulk.write_bytes(b"x" * (2 * 1024 * 1024))
        return h

    def test_the_bundle_is_small_keeps_the_layout_and_verifies_like_the_original(self):
        import tarfile
        h = self.full_run_with_bulk()
        out = h.tmp / "evidence.tar.gz"
        report = bg.bundle(h.work, 1, out)
        self.assertEqual((report["status"], report["included"]), ("PASS", 1 + 64 * 3 + 64 * 2))
        self.assertGreater(report["omittedBytes"], 12 * 1024 * 1024)
        self.assertLess(report["archiveBytes"], 2 * 1024 * 1024)
        extract = h.tmp / "extracted"
        with tarfile.open(out) as archive:
            archive.extractall(extract, filter="data")
        original, bundled = h.verify(), vg.verify(V3, MANIFEST, extract / "live1", 1)
        self.assertEqual((original["failures"], bundled["failures"]), ([], []))
        for key in ("observations", "technicalStops", "snapshotLabelsRead", "meanWallSeconds"):
            self.assertEqual(original[key], bundled[key], key)

    def test_the_manifest_hashes_every_included_file_and_counts_the_rest(self):
        import tarfile
        h = self.full_run_with_bulk()
        out = h.tmp / "evidence.tar.gz"
        bg.bundle(h.work, 1, out)
        with tarfile.open(out) as archive:
            manifest = json.loads(archive.extractfile("live1/BUNDLE-MANIFEST.json").read())
            for row in manifest["included"][:5]:
                self.assertEqual(hashlib.sha256(archive.extractfile("live1/" + row["path"]).read()).hexdigest(), row["sha256"])
            names = archive.getnames()
        self.assertFalse(any("seeds" in n or "private-home" in n for n in names))
        self.assertEqual(manifest["omitted"]["byTopLevel"]["trial1/seeds/" + h.ledger()[0]["case"]]["bytes"] >= 2 * 1024 * 1024, True)
        self.assertEqual(manifest["trial"], 1)

    def test_the_bundler_changes_nothing_and_refuses_unsafe_outputs(self):
        h = self.full_run_with_bulk()
        before = sorted((str(p.relative_to(h.work)), p.stat().st_size) for p in h.work.rglob("*") if p.is_file())
        bg.bundle(h.work, 1, h.tmp / "a.tar.gz", hash_omitted=True)
        self.assertEqual(before, sorted((str(p.relative_to(h.work)), p.stat().st_size) for p in h.work.rglob("*") if p.is_file()))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(bg.main(["--workdir", str(h.work), "--trial", "1", "--out", str(h.tmp / "a.tar.gz")]), 1)
            self.assertEqual(bg.main(["--workdir", str(h.work), "--trial", "1", "--out", str(h.work / "inside.tar.gz")]), 1)
        self.assertIn("OUTPUT_EXISTS", out.getvalue())
        self.assertIn("OUTPUT_INSIDE_WORKDIR", out.getvalue())

    def test_an_oversized_evidence_file_is_refused_rather_than_silently_dropped(self):
        h = self.harness()
        h.run("--execute")
        review = h.work / "trial1/attempts" / h.ledger()[0]["case"] / "CLI-RECEIPT.json"
        review.write_bytes(b"{" + b" " * (9 * 1024 * 1024) + b"}")
        with self.assertRaises(SystemExit):
            bg.bundle(h.work, 1, h.tmp / "big.tar.gz")


if __name__ == "__main__":
    unittest.main()
