"""Offline tests for the v4 blind audit: requests, answer parsing, the driver with a stub claude, the report against the oracle and the owner's spot check. No model calls."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import stat
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
REPO = V4.parent.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(V4 / "author"))
import audit  # noqa: E402
import audit_parse as ap  # noqa: E402
import audit_prompts as apr  # noqa: E402
import audit_report as ar  # noqa: E402
import build_corpus as bc  # noqa: E402
import prompts as author_prompts  # noqa: E402
import support as su  # noqa: E402

s4 = audit.s4
DEV = json.loads((V4 / "author" / "assignments-dev.json").read_bytes())
MODEL = "claude-test-model"

MEMBER = """Reasoning first.
AUDIT-BEGIN
CLASS: SOUND
REASON: Nothing is contradicted.
DECISIVE_FACT: none
REQUIREMENT_LINE: S01:3
REQUIREMENT_DECIDES: YES
OTHER_PROBLEMS: none
AUDIT-END
"""
PAIR = "AUDIT-BEGIN\nNEEDS_CHANGE: Y\nWHY: Y breaks the limit.\nONE_EDIT: YES\nDIFFERENCE: One number differs.\nAUDIT-END\n"
CLAIM = "AUDIT-BEGIN\nCLAIM_HOLDS: YES\nCONTRADICTING_LINES: none\nAUDIT-END\n"


def build_dev(directory):
    accepted = Path(directory) / "accepted"
    accepted.mkdir()
    for r in DEV["instances"]:
        text, _ = su.case_report(r, author_prompts.family_of(r))
        (accepted / f"{r['pair']}.A.md").write_text(text, encoding="utf-8")
    out = Path(directory) / "corpus"
    bc.build("dev", accepted, out)
    return out


class ParseTests(unittest.TestCase):
    def test_valid_answers(self):
        self.assertEqual(ap.parse(MEMBER, "member")["OTHER_PROBLEMS"], [])
        self.assertEqual(ap.parse(MEMBER.replace("OTHER_PROBLEMS: none", "OTHER_PROBLEMS: S01:7; S02:3"), "member")["OTHER_PROBLEMS"], ["S01:7", "S02:3"])
        self.assertEqual(ap.parse(PAIR, "pair")["NEEDS_CHANGE"], "Y")
        self.assertEqual(ap.parse(CLAIM.replace("none", "S01:7; S01:12"), "claim")["CONTRADICTING_LINES"], ["S01:7", "S01:12"])

    def test_every_failure_is_named(self):
        cases = [(MEMBER.replace("AUDIT-END\n", ""), "member", "MARKERS"), (MEMBER + "Thanks.\n", "member", "TEXT_AFTER_AUDIT_END"),
                 (MEMBER.replace("CLASS: SOUND", "CLASS: FINE"), "member", "BAD_VALUE:CLASS"), (MEMBER.replace("REQUIREMENT_LINE: S01:3", "REQUIREMENT_LINE: line 3"), "member", "BAD_VALUE:REQUIREMENT_LINE"),
                 (MEMBER.replace("OTHER_PROBLEMS: none", "OTHER_PROBLEMS: S01:0"), "member", "BAD_REFS"), (MEMBER.replace("OTHER_PROBLEMS: none\n", ""), "member", "MISSING_FIELDS"),
                 (MEMBER.replace("CLASS: SOUND\n", "CLASS: SOUND\nCLASS: SOUND\n"), "member", "BAD_FIELD:CLASS"), (MEMBER.replace("REASON:", "WHATEVER:"), "member", "BAD_FIELD:WHATEVER"),
                 (PAIR.replace("ONE_EDIT: YES", "ONE_EDIT: MAYBE"), "pair", "BAD_VALUE:ONE_EDIT"), (CLAIM.replace("YES", ""), "claim", "BAD_FIELD:CLAIM_HOLDS"),
                 ("no block at all", "claim", "MARKERS")]
        for text, call, reason in cases:
            with self.subTest(reason=reason):
                with self.assertRaises(ap.AuditParseError) as caught:
                    ap.parse(text, call)
                self.assertEqual(str(caught.exception), reason)


class RequestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_dev(cls.tmp.name)
        cls.corpus = s4.Corpus(cls.out)
        cls.calls = audit.schedule(cls.corpus)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_a_claim_check_is_scheduled_only_for_a_deleted_gap(self):
        claims = [c for c in self.calls if c[1] == "claim"]
        self.assertTrue(all(self.corpus.oracle[c[2]]["changed"]["type"] == "deleted" and self.corpus.oracle[c[2]]["kind"] == "omitted_unknown" for c in claims))
        edits = [r for r in self.corpus.oracle.values() if r["kind"] == "decoy_pair" and r["role"] == "changed"]
        self.assertEqual(len(edits), 8)
        self.assertFalse({c[2] for c in claims} & {r["case"] for r in edits})

    def test_the_schedule_covers_every_member_pair_and_gap_claim_once(self):
        by_type = {}
        for call_id, call_type, subject, request in self.calls:
            by_type.setdefault(call_type, []).append(call_id)
        self.assertEqual({k: len(v) for k, v in by_type.items()}, {"member": 48, "pair": 24, "claim": 8})
        self.assertEqual(len({c[0] for c in self.calls}), len(self.calls))

    def test_the_order_does_not_follow_the_class_or_the_kind(self):
        kinds = [self.corpus.oracle[c[2]]["kind"] if c[1] != "pair" else None for c in self.calls[:30] if c[1] == "member"]
        self.assertGreater(len(set(kinds)), 1)
        self.assertNotEqual([c[0] for c in self.calls], sorted(c[0] for c in self.calls))

    def test_no_request_carries_an_identifier_a_class_a_kind_or_a_mechanism(self):
        oracle = self.corpus.oracle
        forbidden = set()
        for r in oracle.values():
            forbidden |= {r["case"], r["pair"], r["family"], r["kind"], r["domain"], r["expectedVerdict"]}
            if r["mechanism"]:
                forbidden.add(r["mechanism"])
        for call_id, call_type, subject, request in self.calls:
            for word in forbidden:
                self.assertNotIn(word, request, (call_id, word))
            self.assertNotIn("benchmark", request.lower())
            self.assertNotIn("twin", request.lower())

    def test_requests_number_every_source_line_and_show_the_reference_only_when_present(self):
        cross = next(c for c in self.calls if c[1] == "member" and self.corpus.oracle[c[2]]["kind"] == "cross_source_defect")
        self.assertIn("[S02:1]", cross[3])
        self.assertIn("=== S02 (the reference excerpt) ===", cross[3])
        single = next(c for c in self.calls if c[1] == "member" and self.corpus.oracle[c[2]]["kind"] == "omitted_unknown")
        self.assertNotIn("=== S02", single[3])
        lines = self.corpus.lines(single[2])
        self.assertIn(f"[S01:{len(lines)}] {lines[-1]}", single[3])

    def test_the_claim_check_shows_the_authors_sentence_against_the_changed_plan_only(self):
        claim = next(c for c in self.calls if c[1] == "claim")
        twin = self.corpus.oracle[claim[2]]
        self.assertIn(twin["whyNoFallback"], claim[3])
        self.assertEqual(twin["role"], "changed")
        self.assertNotIn("Plan X", claim[3])

    def test_the_pair_order_is_a_fixed_coin_per_pair_and_both_orders_occur(self):
        seed = self.corpus.manifest["authoring"]["seedSha256"]
        coins = {apr.x_is_sound(seed, p["pair"]) for p in DEV["instances"]}
        self.assertEqual(coins, {True, False})
        self.assertEqual(apr.x_is_sound(seed, DEV["instances"][0]["pair"]), apr.x_is_sound(seed, DEV["instances"][0]["pair"]))

    def test_the_templates_name_the_questions_of_the_specification(self):
        member, pair, claim = (apr.template(n) for n in ("member-request.txt", "pair-request.txt", "claim-request.txt"))
        for needle in ("HAS_A_DEFECT", "HAS_AN_UNESTABLISHED_FACT", "DECISIVE_FACT", "REQUIREMENT_DECIDES", "OTHER_PROBLEMS"):
            self.assertIn(needle, member)
        for needle in ("NEEDS_CHANGE", "ONE_EDIT", "exactly one edit"):
            self.assertIn(needle, pair)
        for needle in ("CLAIM_HOLDS", "CONTRADICTING_LINES", "{CLAIM}"):
            self.assertIn(needle, claim)
        self.assertIn("untrusted", apr.system_prompt())


STUB_CLAUDE = r'''#!/usr/bin/env python3
import json, sys
from pathlib import Path
here = Path(__file__).resolve().parent
config = json.loads((here / "stub-claude.json").read_text())
if "--version" in sys.argv:
    print("9.9.9 (stub)")
    sys.exit(0)
request = sys.stdin.read()
counter = here / "stub-count"
n = int(counter.read_text()) if counter.exists() else 0
counter.write_text(str(n + 1))
kind = "pair" if "PLAN X" in request else "claim" if "author makes this claim" in request else "member"
mode = config["mode"][min(n, len(config["mode"]) - 1)]
if mode == "error":
    print(json.dumps({"is_error": True, "terminal_reason": "boom"}))
    sys.exit(1)
text = config["answers"]["garbage" if mode == "garbage" else "ok" if kind == "member" else kind]
payload = {"result": text, "total_cost_usd": 0.02, "num_turns": 1, "modelUsage": {config["served"]: {}}, "is_error": False}
if mode == "safety":
    payload["safety_stops"] = 1
print(json.dumps(payload))
'''


class DriverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_dev(cls.tmp.name)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def stub(self, tmp, modes=("ok",), served=MODEL):
        binary = Path(tmp) / "claude"
        binary.write_text(STUB_CLAUDE)
        binary.chmod(binary.stat().st_mode | stat.S_IEXEC)
        (Path(tmp) / "stub-claude.json").write_text(json.dumps({"mode": list(modes), "served": served, "answers": {"ok": MEMBER, "garbage": "I think it is fine.", "pair": PAIR, "claim": CLAIM}}))
        return binary

    def run_audit(self, tmp, binary, *extra, work="work"):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = audit.main(["--claude-bin", str(binary), "--model", MODEL, "--effort", "high", "--corpus", str(self.out), "--workdir", str(Path(tmp) / work), *extra])
        return code, json.loads(out.getvalue().strip().splitlines()[-1])

    def test_a_dry_run_writes_every_request_and_calls_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, summary = self.run_audit(tmp, self.stub(tmp))
            self.assertEqual((code, summary["status"], summary["callsScheduled"], summary["prepared"], summary["providerCalls"]), (0, "DRY_RUN_PREPARED_ONLY", 80, 80, 0))
            self.assertEqual(len(list((Path(tmp) / "work/dry-requests").iterdir())), 80)
            self.assertFalse((Path(tmp) / "stub-count").exists())

    def test_calls_are_recorded_parsed_and_bounded_by_max_calls(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = self.stub(tmp)
            code, summary = self.run_audit(tmp, binary, "--execute", "--max-calls", "5")
            self.assertEqual((code, summary["executed"], summary["stopped"]), (0, 5, 0))
            rows = [json.loads(l) for l in (Path(tmp) / "work/audit-answers.jsonl").read_text().splitlines()]
            self.assertEqual(len(rows), 5)
            self.assertTrue(all("answer" in r and r["route"] == "claude-cli-audit" and r["requestedModel"] == MODEL and r["servedModels"] == [MODEL] for r in rows))
            self.assertEqual(rows[0]["requestSha256"], hashlib.sha256((Path(tmp) / "work/attempts" / rows[0]["call"].replace(":", "_") / "request.txt").read_bytes()).hexdigest())
            code, summary = self.run_audit(tmp, binary, "--execute", "--max-calls", "5")
            self.assertEqual((summary["executed"], summary["alreadyRecorded"]), (5, 5))                    # resumes, never repeats a recorded call

    def test_unparseable_errors_safety_and_model_mismatch_are_stops_not_retries(self):
        for modes, served, expected in ((("garbage",), MODEL, "UNPARSEABLE_ANSWER:MARKERS"), (("error",), MODEL, "CLAUDE_ERROR:boom"), (("safety",), MODEL, "SAFETY_INTERRUPTED:1"),
                                        (("ok",), "another-model", "MODEL_MISMATCH")):
            with self.subTest(expected=expected), tempfile.TemporaryDirectory() as tmp:
                code, summary = self.run_audit(tmp, self.stub(tmp, modes, served), "--execute", "--max-calls", "1")
                self.assertEqual(summary["stopped"], 1)
                row = json.loads((Path(tmp) / "work/audit-answers.jsonl").read_text().splitlines()[0])
                self.assertTrue(row["technicalStop"].startswith(expected.split(":")[0]) and row["technicalStop"].startswith(expected))
                self.assertNotIn("answer", row)

    def test_consecutive_stops_halt_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, summary = self.run_audit(tmp, self.stub(tmp, ("garbage",)), "--execute", "--max-consecutive-stops", "2")
            self.assertEqual((summary["executed"], summary.get("halted")), (2, "CONSECUTIVE_STOPS"))

    def test_an_attempt_directory_without_a_row_is_an_interrupted_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = self.stub(tmp)
            first = audit.schedule(s4.Corpus(self.out))[0][0]
            (Path(tmp) / "work/attempts" / first.replace(":", "_")).mkdir(parents=True)
            code, summary = self.run_audit(tmp, binary, "--execute", "--max-calls", "1")
            row = json.loads((Path(tmp) / "work/audit-answers.jsonl").read_text().splitlines()[0])
            self.assertEqual((row["call"], row["technicalStop"]), (first, "INTERRUPTED_UNKNOWN_STATE"))
            self.assertFalse((Path(tmp) / "stub-count").exists())

    def test_the_claude_command_is_tool_free_and_isolated(self):
        class Args:
            claude_bin, model, effort, max_budget_usd = "/x/claude", MODEL, "high", 1.0
        command = audit.rpc.claude_command(Args, "/tmp/empty.json", apr.system_prompt())
        for flag in ("--tools", "--safe-mode", "--no-session-persistence", "--strict-mcp-config", "--disable-slash-commands"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--tools") + 1], "")

    def test_refusals(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = self.stub(tmp)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = audit.main(["--claude-bin", str(binary), "--model", MODEL, "--effort", "high", "--corpus", str(self.out), "--workdir", str(REPO / "audit-workdir-must-not-exist")])
            self.assertEqual((code, json.loads(out.getvalue())["reason"]), (1, "WORKDIR_INSIDE_REPOSITORY"))
            self.assertFalse((REPO / "audit-workdir-must-not-exist").exists())
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = audit.main(["--claude-bin", "claude", "--model", MODEL, "--effort", "high", "--corpus", str(self.out), "--workdir", str(Path(tmp) / "w")])
            self.assertEqual((code, json.loads(out.getvalue())["reason"]), (1, "CLAUDE_BIN_INVALID"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = audit.main(["--claude-bin", str(binary), "--model", MODEL, "--effort", "high", "--corpus", str(V4.parent), "--workdir", str(Path(tmp) / "w")])
            self.assertEqual((code, json.loads(out.getvalue())["reason"]), (1, "NOT_A_V4_CORPUS"))


def perfect_ledger(corpus):
    """Ledger rows from an auditor that agrees with the oracle on everything."""
    seed = corpus.manifest["authoring"]["seedSha256"]
    rows = {}
    for call_id, call_type, subject, request in audit.schedule(corpus):
        if call_type == "member":
            klass = ar.EXPECTED[corpus.oracle[subject]["expectedClass"]]
            answer = ap.parse(MEMBER.replace("CLASS: SOUND", f"CLASS: {klass}"), "member")
        elif call_type == "pair":
            answer = ap.parse(PAIR.replace("NEEDS_CHANGE: Y", "NEEDS_CHANGE: " + ("Y" if apr.x_is_sound(seed, subject) else "X")), "pair")
        else:
            answer = ap.parse(CLAIM, "claim")
        rows[call_id] = {"call": call_id, "type": call_type, "subject": subject, "answer": answer}
    return rows


class ReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_dev(cls.tmp.name)
        cls.corpus = s4.Corpus(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def pairs(self, kind):
        return [p for p, c in ar.pairs_of(self.corpus).items() if self.corpus.oracle[c["changed"]]["kind"] == kind]

    def test_an_auditor_that_agrees_gives_pass_for_every_pair(self):
        report = ar.analyse(self.corpus, perfect_ledger(self.corpus))
        self.assertEqual(report["decisions"], {"PASS": 24, "PASS_WITH_READ": 0, "REVIEW": 0, "INCOMPLETE": 0})
        self.assertEqual((report["memberClassRecovered"]["count"], report["memberClassRecovered"]["of"]), (48, 48))
        self.assertEqual(report["firstPassAgreement"]["count"], 24)
        self.assertEqual(report["needsAPersonsRead"], [])
        self.assertEqual(sorted(report["byKind"]), ["cross_source_defect", "decoy_pair", "omitted_unknown"])

    def test_each_disagreement_is_a_review_with_its_reason(self):
        pair = self.pairs("omitted_unknown")[0]
        cases = ar.pairs_of(self.corpus)[pair]

        def with_change(change):
            rows = copy.deepcopy(perfect_ledger(self.corpus))
            change(rows)
            return ar.analyse(self.corpus, rows)["perPair"][pair]

        sound_wrong = with_change(lambda r: r[f"member:{cases['sound']}"]["answer"].update(CLASS="HAS_A_DEFECT"))
        self.assertEqual((sound_wrong["decision"], sound_wrong["reasons"]), ("REVIEW", ["SOUND_MEMBER_NOT_RECOVERED:HAS_A_DEFECT"]))
        twin_wrong = with_change(lambda r: r[f"member:{cases['changed']}"]["answer"].update(CLASS="SOUND"))
        self.assertEqual(twin_wrong["reasons"], ["TWIN_NOT_RECOVERED:SOUND"])
        wrong_kind_of_problem = with_change(lambda r: r[f"member:{cases['changed']}"]["answer"].update(CLASS="HAS_A_DEFECT"))
        self.assertEqual(wrong_kind_of_problem["reasons"], ["TWIN_NOT_RECOVERED:HAS_A_DEFECT"])
        choice = with_change(lambda r: r[f"pair:{pair}"]["answer"].update(NEEDS_CHANGE="NEITHER"))
        self.assertEqual(choice["reasons"], ["PAIR_CHOICE:NEITHER"])
        edit = with_change(lambda r: r[f"pair:{pair}"]["answer"].update(ONE_EDIT="NO"))
        self.assertEqual(edit["reasons"], ["NOT_ONE_EDIT"])
        claim = with_change(lambda r: r[f"claim:{cases['changed']}"]["answer"].update(CLAIM_HOLDS="NO", CONTRADICTING_LINES=["S01:4"]))
        self.assertEqual(claim["reasons"], ["CLAIM_CONTRADICTED:S01:4"])

    def test_flags_make_pass_with_read_and_do_not_fail_a_pair(self):
        pair = self.pairs("cross_source_defect")[0]
        cases = ar.pairs_of(self.corpus)[pair]
        rows = perfect_ledger(self.corpus)
        rows[f"member:{cases['sound']}"]["answer"]["OTHER_PROBLEMS"] = ["S02:3"]
        rows[f"member:{cases['changed']}"]["answer"]["REQUIREMENT_DECIDES"] = "NO"
        entry = ar.analyse(self.corpus, rows)["perPair"][pair]
        self.assertEqual(entry["decision"], "PASS_WITH_READ")
        self.assertEqual(entry["flags"], ["SOUND_OTHER_PROBLEMS:S02:3", "TWIN_REQUIREMENT_DOES_NOT_DECIDE"])
        self.assertIn(pair, ar.analyse(self.corpus, rows)["needsAPersonsRead"])

    def test_missing_or_stopped_calls_make_a_pair_incomplete_not_a_pass(self):
        pair = self.pairs("omitted_unknown")[0]
        cases = ar.pairs_of(self.corpus)[pair]
        rows = perfect_ledger(self.corpus)
        del rows[f"claim:{cases['changed']}"]
        rows[f"pair:{pair}"] = {"call": f"pair:{pair}", "technicalStop": "UNPARSEABLE_ANSWER:MARKERS"}
        report = ar.analyse(self.corpus, rows)
        self.assertEqual((report["perPair"][pair]["decision"], report["perPair"][pair]["incompleteCalls"]), ("INCOMPLETE", ["pair", "claim"]))
        self.assertEqual(report["decisions"]["INCOMPLETE"], 1)
        self.assertEqual(report["firstPassAgreement"]["of"], 23)

    def test_a_defect_pair_needs_no_claim_check(self):
        pair = self.pairs("cross_source_defect")[0]
        self.assertNotIn("claim:" + ar.pairs_of(self.corpus)[pair]["changed"], perfect_ledger(self.corpus))
        self.assertEqual(ar.analyse(self.corpus, perfect_ledger(self.corpus))["perPair"][pair]["decision"], "PASS")

    def test_the_command_line_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Path(tmp) / "answers.jsonl"
            ledger.write_text("\n".join(json.dumps(r) for r in perfect_ledger(self.corpus).values()) + "\n", encoding="utf-8")
            out = Path(tmp) / "report.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(ar.main(["report", "--corpus", str(self.out), "--answers", str(ledger), "--out", str(out)]), 0)
                self.assertEqual(ar.main(["report", "--corpus", str(self.out), "--answers", str(ledger) + ".missing"]), 1)
                self.assertEqual(ar.main([]), 2)
            self.assertEqual(json.loads(out.read_text())["decisions"]["PASS"], 24)


class SpotCheckTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.out = build_dev(cls.tmp.name)
        cls.corpus = s4.Corpus(cls.out)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_sample_is_at_least_a_fifth_stratified_and_reproducible(self):
        sample = ar.spot_sample(self.corpus)
        self.assertGreaterEqual(len(sample), 5)
        self.assertEqual(sample, ar.spot_sample(self.corpus))
        kinds = {self.corpus.oracle[ar.pairs_of(self.corpus)[p]["changed"]]["kind"] for p in sample}
        self.assertEqual(kinds, {"omitted_unknown", "cross_source_defect", "decoy_pair"})
        self.assertEqual(len(sample), len(set(sample)))
        for fraction in (0.2, 0.5):
            self.assertGreaterEqual(len(ar.spot_sample(self.corpus, fraction)), 24 * fraction)

    def test_the_files_hold_unlabelled_plans_and_only_the_index_knows_the_answer(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "spot"
            index = ar.write_spot(self.corpus, out)
            files = sorted(p.name for p in out.glob("*.txt"))
            self.assertEqual(files, [f"{n:02d}.txt" for n in range(1, len(index) + 1)])
            oracle = self.corpus.oracle
            for number, key in index.items():
                text = (out / f"{number}.txt").read_text(encoding="utf-8")
                for word in ("twin", "sound plan", "kind", "mechanism", key["pair"], oracle[ar.pairs_of(self.corpus)[key["pair"]]["changed"]]["family"]):
                    self.assertNotIn(word, text)
                self.assertIn("PLAN X", text)
                self.assertIn("PLAN Y", text)
                self.assertIn("QUESTIONS FOR THE OWNER", text)
                self.assertNotIn("{X}", text)
            self.assertTrue({k["twin"] for k in index.values()} <= {"X", "Y"})
            with self.assertRaises(FileExistsError):
                ar.write_spot(self.corpus, out)

    def test_scoring_the_owners_answers(self):
        with tempfile.TemporaryDirectory() as tmp:
            index = ar.write_spot(self.corpus, Path(tmp) / "spot")
            problem = {"DEFECT": "DEFECT", "UNCERTAIN": "UNESTABLISHED"}
            right = {n: {"needsChange": k["twin"], "oneEdit": True, "problem": problem[k["twinClass"]]} for n, k in index.items()}
            self.assertTrue(ar.score_spot(index, right)["clean"])
            wrong = dict(right)
            first = sorted(index)[0]
            wrong[first] = {"needsChange": "X" if index[first]["twin"] == "Y" else "Y", "oneEdit": True, "problem": right[first]["problem"]}
            result = ar.score_spot(index, wrong)
            self.assertFalse(result["clean"])
            self.assertEqual([d["file"] for d in result["disagreements"]], [first])
            partial = {first: right[first]}
            self.assertFalse(ar.score_spot(index, partial)["clean"])
            not_one = dict(right)
            not_one[first] = {"needsChange": index[first]["twin"], "oneEdit": False, "problem": right[first]["problem"]}
            self.assertFalse(ar.score_spot(index, not_one)["clean"])
            other = dict(right)
            other[first] = dict(right[first], problem="UNESTABLISHED" if right[first]["problem"] == "DEFECT" else "DEFECT")
            result = ar.score_spot(index, other)
            self.assertEqual((result["clean"], result["problemKindMatchesOracle"]["count"], result["disagreements"][0]["oracleProblem"]),
                             (False, len(index) - 1, right[first]["problem"]))
            self.assertEqual(result["needsChangeMatchesOracle"]["count"], len(index))

    def test_the_command_line_spot_and_spot_score(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ar.main(["spot", "--corpus", str(self.out), "--out", str(Path(tmp) / "spot")]), 0)
                index = json.loads((Path(tmp) / "spot/spot-index.json").read_text())
                answers = Path(tmp) / "answers.json"
                answers.write_text(json.dumps({n: {"needsChange": k["twin"], "oneEdit": True, "problem": {"DEFECT": "DEFECT", "UNCERTAIN": "UNESTABLISHED"}[k["twinClass"]]} for n, k in index.items()}))
                self.assertEqual(ar.main(["spot-score", "--corpus", str(self.out), "--index", str(Path(tmp) / "spot/spot-index.json"), "--answers", str(answers)]), 0)
            self.assertTrue(json.loads(out.getvalue().split("\n", 1)[1])["clean"])


class RunScriptTests(unittest.TestCase):
    SCRIPT = HERE / "run.sh"

    def sh(self, *args, env_extra=None):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ, ROOT=str(Path(tmp) / "root"), CLAUDE="/nonexistent/claude", **(env_extra or {}))
            env.pop("CORPUS", None)
            env.pop("CORPUS_SHA", None)
            env.update(env_extra or {})
            done = subprocess.run(["bash", str(self.SCRIPT), *args], capture_output=True, text=True, env=env, cwd=REPO, check=False, timeout=300)
            return done.returncode, done.stdout, done.stderr

    def test_the_pinned_template_hashes_match_the_repository(self):
        text = self.SCRIPT.read_text(encoding="utf-8")
        for name, flag in (("system-prompt.txt", "EXPECT_SYSTEM_SHA"), ("member-request.txt", "EXPECT_MEMBER_SHA"), ("pair-request.txt", "EXPECT_PAIR_SHA"),
                           ("claim-request.txt", "EXPECT_CLAIM_SHA")):
            self.assertIn(f"{flag}={hashlib.sha256((HERE / name).read_bytes()).hexdigest()}", text)
        self.assertNotIn("@", "".join(l for l in text.splitlines() if l.startswith("EXPECT_")))
        self.assertTrue(self.SCRIPT.stat().st_mode & 0o111)

    def test_the_corpus_and_its_hash_are_required_and_live_needs_the_go_flag(self):
        for args in (("checks",), ("dry",), ("live", "2", "--go")):
            with self.subTest(args=args):
                code, out, err = self.sh(*args)
                self.assertEqual((code, "CORPUS_AND_CORPUS_SHA_REQUIRED" in err), (2, True), err)
        code, out, err = self.sh("live", "2")
        self.assertEqual((code, "REFUSED" in err), (2, True))
        code, out, err = self.sh("live", "x", "--go")
        self.assertEqual((code, "N_MUST_BE_A_NUMBER" in err), (2, True))
        self.assertEqual(self.sh()[0], 2)

    def test_a_wrong_corpus_hash_stops_before_anything_else(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / "manifest.json").write_text("{}")
            code, out, err = self.sh("dry", env_extra={"CORPUS": tmp, "CORPUS_SHA": "0" * 64})
            self.assertEqual((code, "MISMATCH:corpus-manifest" in err), (1, True))

    def test_bundle_needs_a_run(self):
        self.assertEqual(self.sh("bundle")[0], 1)

    def test_the_brief_names_the_rules_and_the_commands(self):
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for needle in ("stop and send the exact output", "Do not open `oracle/`", "`live N --go`", "never retries", "$B bundle", "CORPUS_SHA", "audit_report.py spot"):
            self.assertIn(needle, brief)


if __name__ == "__main__":
    unittest.main()
