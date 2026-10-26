"""Tests of parse_v4.py and score_v4.py; offline, no model calls.

The gate: on every committed ledger of the v1 to v3 runs, score_v4 returns exactly what score.py returns (with `perFamily` named `perPair` and the v4-only
blocks set aside), and where score.py itself reproduces a committed score file, score_v4 reproduces that file. Then the v4 features on a synthetic corpus.
"""
import contextlib
import copy
import io
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import parse_v4 as pv  # noqa: E402
import score_v4 as s4  # noqa: E402

PAIRS = HERE.parent
RES = PAIRS / "results"
V4_ONLY = ("byKind", "byFamily", "decoyDiscipline", "citations", "mechanismJudgments", "wordingBConsistency")


def ledger(*paths):
    out = []
    for path in paths:
        out += [json.loads(line) for line in (PAIRS / path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return out


def two(directory, name="responses.jsonl"):
    return [f"results/{directory}/trial1/{name}", f"results/{directory}/trial2/{name}"]


# name: (ledger files, corpus directory relative to PAIRS, adjudication, committed score file or None)
RUNS = {
    "pilot-flash as run": (two("pilot-flash-high"), ".", "results/pilot-flash-high/adjudication.json", "results/pilot-flash-high/score-as-run.json"),
    "pilot-flash documented rule": (two("pilot-flash-high", "responses-documented-rule.jsonl"), ".", "results/pilot-flash-high/adjudication.json",
                                    "results/pilot-flash-high/score-documented-rule.json"),
    "pilot1 claude": (two("pilot1-claude-opus-5-5-high"), ".", None, None),
    "pilot2 claude v2": (two("pilot2-v2-claude-opus-5-5-high"), "v2", "results/pilot2-v2-claude-opus-5-5-high/adjudication.json", None),
    "ablation bare as run": (two("ablation-bare-opus-5-5-high"), "v2", None, "results/ablation-bare-opus-5-5-high/score-as-run.json"),
    "ablation bare documented rule": (two("ablation-bare-opus-5-5-high"), "v2", "results/ablation-bare-opus-5-5-high/adjudication.json",
                                      "results/ablation-bare-opus-5-5-high/score-documented-rule.json"),
    "ablation defined": (two("ablation-defined-opus-5-5-high"), "v2", "results/ablation-defined-opus-5-5-high/adjudication.json", None),
    "ablation defined-go": (two("ablation-defined-go-opus-5-5-high"), "v2", "results/ablation-defined-go-opus-5-5-high/adjudication.json", None),
    "v3 claude skill": (two("v3-claude-opus-5-5-high/skill"), "v3", "results/v3-claude-opus-5-5-high/adjudication.json", "results/v3-claude-opus-5-5-high/score-skill.json"),
    "v3 claude defined": (two("v3-claude-opus-5-5-high/defined"), "v3", "results/v3-claude-opus-5-5-high/adjudication.json", None),
    "v3 claude defined-go": (two("v3-claude-opus-5-5-high/defined-go"), "v3", "results/v3-claude-opus-5-5-high/adjudication.json", None),
    "v3 gemini": (two("v3-gemini-flash-high"), "v3", "results/v3-gemini-flash-high/adjudication.json", "results/v3-gemini-flash-high/score.json"),
    "v3 skill-go run, skill arm": (two("v3-skill-go-opus-5-5-high/skill"), "v3", "results/v3-skill-go-opus-5-5-high/adjudication.json",
                                   "results/v3-skill-go-opus-5-5-high/score-skill.json"),
    "v3 skill-go run, skill-go arm": (two("v3-skill-go-opus-5-5-high/skill-go"), "v3", "results/v3-skill-go-opus-5-5-high/adjudication.json",
                                      "results/v3-skill-go-opus-5-5-high/score-skill-go.json"),
}


def renamed(value):
    return json.loads(json.dumps(value).replace('"perFamily"', '"perPair"'))


def without_v4_blocks(result):
    result = copy.deepcopy(result)
    result["kind"] = None
    for block in list(result["trials"].values()) + (list(result["adjusted"]["trials"].values()) if "adjusted" in result else []):
        for key in V4_ONLY:
            block.pop(key, None)
    return result


class GateAgainstEarlierScorer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sc = s4.sc

    def corpus(self, name):
        return PAIRS if name == "." else PAIRS / name

    def test_every_committed_ledger_scores_identically(self):
        for name, (ledgers, corpus, adjudication, _) in RUNS.items():
            with self.subTest(run=name):
                rows = ledger(*ledgers)
                adj = json.loads((PAIRS / adjudication).read_text(encoding="utf-8")) if adjudication else None
                old = self.sc.score(copy.deepcopy(rows), self.corpus(corpus), copy.deepcopy(adj))
                new = s4.score(copy.deepcopy(rows), self.corpus(corpus), copy.deepcopy(adj))
                old["kind"] = None
                self.assertEqual(without_v4_blocks(new), renamed(old))

    def test_committed_score_files_are_reproduced(self):
        checked = 0
        for name, (ledgers, corpus, adjudication, committed) in RUNS.items():
            if committed is None:
                continue
            with self.subTest(run=name):
                adj = json.loads((PAIRS / adjudication).read_text(encoding="utf-8")) if adjudication else None
                expected = json.loads((PAIRS / committed).read_text(encoding="utf-8"))
                got = s4.score(ledger(*ledgers), self.corpus(corpus), adj)
                expected["kind"] = None
                self.assertEqual(without_v4_blocks(got), renamed(expected))
                checked += 1
        self.assertEqual(checked, 8)

    def test_the_gate_covers_every_earlier_corpus(self):
        corpora = {corpus for _, corpus, _, _ in RUNS.values()}
        self.assertEqual(corpora, {".", "v2", "v3"})

    def test_legacy_corpora_have_no_kinds_and_the_pair_is_the_family(self):
        for name in (".", "v2", "v3"):
            corpus = s4.Corpus(self.corpus(name))
            self.assertTrue(corpus.legacy)
            self.assertTrue(all(r["pair"] == r["family"] and r["kind"] is None for r in corpus.oracle.values()))
            self.assertTrue(all(r["citeAnyOf"] and all(c["source"] == "S01" for c in r["citeAnyOf"]) for r in corpus.oracle.values() if r["role"] == "changed"))

    def test_v3_by_family_matches_the_families_of_the_corpus(self):
        rows = ledger(*RUNS["v3 gemini"][0])
        result = s4.score(rows, PAIRS / "v3")
        trial = result["trials"]["1"]
        self.assertEqual(trial["byKind"], {})
        self.assertEqual(set(trial["byFamily"]), {r["family"] for r in s4.Corpus(PAIRS / "v3").oracle.values()})
        paired = sum(int(e["pairsDiscriminated"].split("/")[1]) for e in trial["perPair"].values())
        self.assertEqual(sum(b["units"] for b in trial["byFamily"].values()), paired)


# ---------------------------------------------------------------------------------------------------------------------------------------------------
# a synthetic v4 corpus

S01 = ["alpha plan", "beta step", "gamma rollout", "delta check", "epsilon close"]
S02 = ["spec header", "spec limit is 50", "spec footer"]


def ref(source, line):
    return {"source": source, "line": line}


def record(case, pair, family, kind, wording, role, *, cite=None, decoys=(), cross=False, changed_type="edited"):
    sound = role == "sound"
    twin_class = {"omitted_unknown": "UNCERTAIN", "decoy_pair": "UNCERTAIN"}.get(kind, "DEFECT")
    verdict = {"UNCERTAIN": "GO_WITH_CHANGES", "DEFECT": "NO_GO"}[twin_class]
    sources = [{"id": "S01", "lines": len(S01)}] + ([{"id": "S02", "lines": len(S02)}] if cross else [])
    return {
        "case": case, "pair": pair, "family": family, "kind": kind, "domain": "billing", "wording": wording, "role": role,
        "expectedClass": "SOUND" if sound else twin_class, "expectedVerdict": "GO" if sound else verdict,
        "difficulty": {"omitted_unknown": "omission", "decoy_pair": "decoy"}.get(kind, "direct"), "sources": sources, "requirement": ref("S01", 1),
        "citeAnyOf": [] if sound else cite, "changed": {"type": "deleted" if kind == "omitted_unknown" else changed_type, "source": "S01", "positionBucket": "middle", "lines": [2]},
        "decoyLines": [ref("S01", n) for n in decoys], "mechanism": None if sound else "the planted mechanism",
        "whyNoFallback": "nothing bounds it" if (not sound and kind in ("omitted_unknown", "decoy_pair")) else None, "baitNotes": ["a bait"], "rubricKeywords": [["limit"]],
    }


CASES = [
    # pair X1: a cross-source defect in two wordings
    record("Q-a00001", "X1", "xsrc", "cross_source_defect", "A", "sound", cross=True),
    record("Q-a00002", "X1", "xsrc", "cross_source_defect", "A", "changed", cite=[ref("S02", 2)], cross=True),
    record("Q-a00003", "X1", "xsrc", "cross_source_defect", "B", "sound", cross=True),
    record("Q-a00004", "X1", "xsrc", "cross_source_defect", "B", "changed", cite=[ref("S02", 2)], cross=True),
    # pair D1: a decoy pair, the decoy at S01:3 and the decisive line at S01:4 in the twin
    record("Q-b00001", "D1", "decoy", "decoy_pair", "A", "sound", decoys=(3,)),
    record("Q-b00002", "D1", "decoy", "decoy_pair", "A", "changed", cite=[ref("S01", 3)], decoys=(3,)),
    # pair O1: an omitted unknown
    record("Q-c00001", "O1", "omit", "omitted_unknown", "A", "sound"),
    record("Q-c00002", "O1", "omit", "omitted_unknown", "A", "changed", cite=[ref("S01", 2)]),
]


def write_corpus(root, cases=CASES):
    root = Path(root)
    (root / "oracle").mkdir(parents=True)
    (root / "oracle" / "oracle.json").write_text(json.dumps({"cases": cases}), encoding="utf-8")
    for r in cases:
        folder = root / "packets" / r["case"]
        folder.mkdir(parents=True)
        (folder / "S01.txt").write_text("\n".join(S01) + "\n", encoding="utf-8")
        if len(r["sources"]) == 2:
            (folder / "S02.txt").write_text("\n".join(S02) + "\n", encoding="utf-8")
    pins = {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob("*")) if p.is_file()}
    (root / "manifest.json").write_text(json.dumps({"cases": len(cases), "pins": pins}), encoding="utf-8")


def finding(severity, evidence, line, quote, source=None):
    out = {"severity": severity, "evidence": evidence, "line": line, "quote": quote}
    if source:
        out["source"] = source
    return out


def row(case, assessment, findings=(), **extra):
    return dict({"case": case, "trial": 1, "arm": "skill", "assessment": assessment, "completeness": "COMPLETE", "findings": list(findings)}, **extra)


SPEC_BLOCK = finding("BLOCKER", "VERIFIED", 2, "limit is 50", "S02")
CLEAN = "NO_BLOCKERS_FOUND"
BLOCK = "BLOCKERS_FOUND"
CHANGES = "CHANGES_RECOMMENDED"


class V4Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.root = Path(self.tmp) / "corpus"
        write_corpus(self.root)

    def score(self, rows, **kw):
        return s4.score(rows, self.root, **kw)

    def grade(self, case, r):
        corpus = s4.Corpus(self.root)
        return s4.grade(r, corpus.oracle[case], corpus)


class SourceQualifiedCitations(V4Fixture):
    def test_a_second_source_citation_is_decisive(self):
        outcome, detail = self.grade("Q-a00002", row("Q-a00002", BLOCK, [SPEC_BLOCK]))
        self.assertEqual((outcome, detail["mechanismCited"], detail["unsupportedVerified"]), ("CORRECT", True, 0))

    def test_the_same_line_number_in_the_wrong_source_is_not_decisive(self):
        wrong = finding("BLOCKER", "VERIFIED", 2, "beta step", "S01")
        outcome, detail = self.grade("Q-a00002", row("Q-a00002", BLOCK, [wrong]))
        self.assertEqual((outcome, detail["mechanismCited"], detail["unsupportedVerified"]), ("DETECTED_WITHOUT_DECISIVE_CITATION", False, 0))

    def test_a_bare_line_means_the_first_source(self):
        bare = finding("BLOCKER", "VERIFIED", 2, "beta step")
        self.assertEqual(s4.located(bare), ("S01", 2))

    def test_a_quote_from_one_source_cited_to_the_other_is_unsupported(self):
        crossed = finding("BLOCKER", "VERIFIED", 2, "beta step", "S02")
        outcome, detail = self.grade("Q-a00002", row("Q-a00002", BLOCK, [crossed]))
        self.assertEqual(detail["unsupportedVerified"], 1)
        self.assertEqual(outcome, "DETECTED_WITHOUT_DECISIVE_CITATION")

    def test_a_single_source_case_has_no_second_source(self):
        ghost = finding("RISK", "VERIFIED", 1, "spec header", "S02")
        outcome, detail = self.grade("Q-c00001", row("Q-c00001", CHANGES, [ghost]))
        self.assertEqual(detail["unsupportedVerified"], 1)

    def test_line_out_of_range_and_empty_quote_are_unsupported(self):
        for line, quote in ((9, "limit"), (0, "limit"), (2, "  ")):
            with self.subTest(line=line):
                _, detail = self.grade("Q-a00002", row("Q-a00002", BLOCK, [finding("RISK", "VERIFIED", line, quote, "S02")]))
                self.assertEqual(detail["unsupportedVerified"], 1)

    def test_unverified_findings_are_not_counted_unsupported(self):
        _, detail = self.grade("Q-a00002", row("Q-a00002", BLOCK, [finding("RISK", "UNVERIFIED", 9, "nothing", "S02")]))
        self.assertEqual(detail["unsupportedVerified"], 0)

    def test_validation_rejects_a_third_source_and_missing_cases(self):
        corpus = s4.Corpus(self.root)
        with self.assertRaises(s4.Invalid):
            s4.validate(row("Q-a00002", BLOCK, [finding("RISK", "VERIFIED", 1, "x", "S03")]), corpus.oracle)
        with self.assertRaises(s4.Invalid):
            s4.validate(row("Q-zzzzzz", BLOCK), corpus.oracle)

    def test_a_twin_with_only_the_unsourced_accepted_line_is_not_cited(self):
        # the accepted line is S02:2; the S01 line 2 must not satisfy it even with a perfect quote
        outcome, _ = self.grade("Q-a00002", row("Q-a00002", BLOCK, [finding("BLOCKER", "VERIFIED", 2, "beta step")]))
        self.assertEqual(outcome, "DETECTED_WITHOUT_DECISIVE_CITATION")


class GradingRules(V4Fixture):
    def test_sound_plans(self):
        self.assertEqual(self.grade("Q-a00001", row("Q-a00001", CLEAN))[0], "CORRECT")
        self.assertEqual(self.grade("Q-a00001", row("Q-a00001", CHANGES))[0], "HEDGED")
        self.assertEqual(self.grade("Q-a00001", row("Q-a00001", BLOCK, [SPEC_BLOCK]))[0], "FALSE_BLOCKER")

    def test_gap_twin(self):
        self.assertEqual(self.grade("Q-c00002", row("Q-c00002", CHANGES))[0], "CORRECT")
        self.assertEqual(self.grade("Q-c00002", row("Q-c00002", CLEAN))[0], "MISSED")
        self.assertEqual(self.grade("Q-c00002", row("Q-c00002", BLOCK, [finding("BLOCKER", "VERIFIED", 2, "beta step")]))[0], "OVERCLAIMED")

    def test_defect_twin_missed_without_a_verified_blocker(self):
        self.assertEqual(self.grade("Q-a00002", row("Q-a00002", BLOCK, [finding("BLOCKER", "UNVERIFIED", 2, "limit is 50", "S02")]))[0], "MISSED")

    def test_technical_stop(self):
        self.assertEqual(self.grade("Q-a00002", {"case": "Q-a00002", "technicalStop": True})[0], "STOPPED")

    def test_verdict_only_arms_use_the_verdict(self):
        arm = next(iter(s4.VERDICT_ONLY_ARMS))
        self.assertEqual(self.grade("Q-a00002", row("Q-a00002", BLOCK, arm=arm))[0], "CORRECT")
        self.assertEqual(self.grade("Q-c00002", row("Q-c00002", BLOCK, arm=arm))[0], "OVERCLAIMED")


def full_run(**overrides):
    """A reviewer that is right on every case of the synthetic corpus."""
    rows = {
        "Q-a00001": row("Q-a00001", CLEAN), "Q-a00002": row("Q-a00002", BLOCK, [SPEC_BLOCK]),
        "Q-a00003": row("Q-a00003", CLEAN), "Q-a00004": row("Q-a00004", BLOCK, [SPEC_BLOCK]),
        "Q-b00001": row("Q-b00001", CLEAN), "Q-b00002": row("Q-b00002", CHANGES, [finding("RISK", "VERIFIED", 3, "gamma rollout")]),
        "Q-c00001": row("Q-c00001", CLEAN), "Q-c00002": row("Q-c00002", CHANGES, [finding("RISK", "VERIFIED", 2, "beta step")]),
    }
    rows.update(overrides)
    return list(rows.values())


class V4Metrics(V4Fixture):
    def trial(self, rows, **kw):
        return self.score(rows, **kw)["trials"]["1"]

    def test_perfect_run(self):
        t = self.trial(full_run())
        self.assertEqual((t["pairDiscrimination"]["count"], t["pairDiscrimination"]["of"]), (4, 4))
        self.assertEqual(t["unsupportedVerifiedFindings"], 0)
        self.assertEqual(sorted(t["perPair"]), ["D1", "O1", "X1"])
        self.assertEqual(sorted(t["byKind"]), ["cross_source_defect", "decoy_pair", "omitted_unknown"])
        self.assertEqual(sorted(t["byFamily"]), ["decoy", "omit", "xsrc"])
        self.assertEqual(t["byKind"]["cross_source_defect"]["units"], 2)
        self.assertEqual((t["byKind"]["cross_source_defect"]["strictPairs"]["count"], t["byKind"]["cross_source_defect"]["strictPairs"]["of"]), (2, 2))

    def test_by_kind_separates_the_failures(self):
        t = self.trial(full_run(**{"Q-a00002": row("Q-a00002", CLEAN), "Q-c00002": row("Q-c00002", BLOCK, [finding("BLOCKER", "VERIFIED", 2, "beta step")])}))
        self.assertEqual(t["byKind"]["cross_source_defect"]["defectTwinsMissed"]["count"], 1)
        self.assertEqual(t["byKind"]["cross_source_defect"]["strictPairs"]["count"], 1)
        self.assertEqual(t["byKind"]["omitted_unknown"]["gapTwinsOverclaimed"]["count"], 1)
        self.assertEqual(t["byKind"]["omitted_unknown"]["strictPairs"]["count"], 0)
        self.assertEqual(t["byKind"]["decoy_pair"]["strictPairs"]["count"], 1)

    def test_decoy_discipline(self):
        quiet = self.trial(full_run())["decoyDiscipline"]
        self.assertEqual((quiet["decoySoundMembers"], quiet["judgedClean"]["count"], quiet["blockerOnDecoyLine"], quiet["anyFindingOnDecoyLine"]), (1, 1, 0, 0))
        noted = self.trial(full_run(**{"Q-b00001": row("Q-b00001", CLEAN, [finding("NOTE", "VERIFIED", 3, "gamma rollout")])}))["decoyDiscipline"]
        self.assertEqual((noted["judgedClean"]["count"], noted["blockerOnDecoyLine"], noted["anyFindingOnDecoyLine"]), (1, 0, 1))
        blocked = self.trial(full_run(**{"Q-b00001": row("Q-b00001", BLOCK, [finding("BLOCKER", "VERIFIED", 3, "gamma rollout")])}))["decoyDiscipline"]
        self.assertEqual((blocked["judgedClean"]["count"], blocked["blockerOnDecoyLine"], blocked["anyFindingOnDecoyLine"]), (0, 1, 1))

    def test_decoy_discipline_counts_only_decoy_pairs(self):
        self.assertEqual(self.trial(full_run())["decoyDiscipline"]["decoySoundMembers"], 1)

    def test_citation_rates(self):
        t = self.trial(full_run(**{"Q-a00004": row("Q-a00004", BLOCK, [finding("BLOCKER", "VERIFIED", 2, "beta step", "S01")]),
                                   "Q-c00002": row("Q-c00002", CHANGES, [finding("RISK", "VERIFIED", 4, "delta check")])}))["citations"]
        self.assertEqual((t["defectTwinsBlockedAndCited"]["count"], t["defectTwinsBlockedAndCited"]["of"]), (1, 2))
        self.assertEqual((t["gapTwinsCorrectAndCitedAcceptedLine"]["count"], t["gapTwinsCorrectAndCitedAcceptedLine"]["of"]), (1, 2))

    def test_mechanism_judgments_are_pending_until_given(self):
        t = self.trial(full_run())["mechanismJudgments"]
        self.assertEqual(t, {"defectTwinsBlocked": 2, "judged": 0, "namesMechanism": 0, "pending": 2})
        judgments = [{"arm": "skill", "trial": 1, "case": "Q-a00002", "namesMechanism": True}, {"arm": "skill", "trial": 1, "case": "Q-a00004", "namesMechanism": False}]
        t = self.trial(full_run(), judgments=judgments)["mechanismJudgments"]
        self.assertEqual(t, {"defectTwinsBlocked": 2, "judged": 2, "namesMechanism": 1, "pending": 0})

    def test_judgments_of_other_cases_or_arms_are_ignored(self):
        judgments = [{"arm": "bare", "trial": 1, "case": "Q-a00002", "namesMechanism": True}, {"arm": "skill", "trial": 2, "case": "Q-a00002", "namesMechanism": True}]
        self.assertEqual(self.trial(full_run(), judgments=judgments)["mechanismJudgments"]["judged"], 0)

    def test_wording_b_consistency(self):
        same = self.trial(full_run())["wordingBConsistency"]
        self.assertEqual((same["sound"]["count"], same["sound"]["of"], same["changed"]["count"], same["changed"]["of"]), (1, 1, 1, 1))
        split = self.trial(full_run(**{"Q-a00003": row("Q-a00003", CHANGES)}))["wordingBConsistency"]
        self.assertEqual((split["sound"]["count"], split["sound"]["of"]), (0, 1))

    def test_stops_drop_out_of_units_but_are_counted(self):
        t = self.trial(full_run(**{"Q-a00002": {"case": "Q-a00002", "technicalStop": True, "trial": 1}}))
        self.assertEqual(t["technicalStops"], 1)
        self.assertEqual(t["byKind"]["cross_source_defect"]["units"], 1)

    def test_unsupported_verified_across_sources_is_the_gate(self):
        t = self.trial(full_run(**{"Q-a00004": row("Q-a00004", BLOCK, [SPEC_BLOCK, finding("RISK", "VERIFIED", 3, "beta step", "S02")])}))
        self.assertEqual(t["unsupportedVerifiedFindings"], 1)
        self.assertFalse(t["pilotGate"]["unsupportedVerifiedIsZero"])

    def test_two_trials_and_repeatability(self):
        rows = full_run() + [dict(r, trial=2) for r in full_run(**{"Q-c00001": row("Q-c00001", CHANGES)})]
        result = self.score(rows)
        self.assertEqual(sorted(result["trials"]), ["1", "2"])
        self.assertEqual((result["repeatability"]["count"], result["repeatability"]["of"]), (7, 8))

    def test_invalid_pairs_by_pair_name(self):
        adjudication = {"invalidPairs": [{"pair": "X1", "wordings": ["A"], "reason": "the sound plan was unsound"}]}
        result = self.score(full_run(), adjudication=adjudication)
        self.assertEqual(result["adjusted"]["excludedPairs"], ["X1/A"])
        self.assertEqual(result["adjusted"]["trials"]["1"]["observations"], 6)
        self.assertEqual(result["trials"]["1"]["observations"], 8)

    def test_invalid_pairs_accept_the_family_key_of_earlier_adjudications(self):
        self.assertEqual(s4.invalid_pairs({"invalidPairs": [{"family": "F", "wordings": ["A", "B"], "reason": "r"}]}), {("F", "A"), ("F", "B")})
        for bad in ({"invalidPairs": [{"pair": "X1", "wordings": ["A"], "reason": " "}]}, {"invalidPairs": [{"wordings": ["A"], "reason": "r"}]}, []):
            with self.assertRaises(s4.Invalid):
                s4.invalid_pairs(bad)

    def test_duplicate_observation_and_unknown_case_stop(self):
        with self.assertRaises(s4.Invalid):
            self.score(full_run() + [row("Q-a00001", CLEAN)])
        with self.assertRaises(s4.Invalid):
            self.score([row("Q-zzzzzz", CLEAN)])

    def test_cases_not_observed_are_listed(self):
        t = self.trial(full_run()[:-1])
        self.assertEqual(t["observations"], 7)

    def test_no_provider_calls_and_kind(self):
        result = self.score(full_run())
        self.assertEqual(result["providerCalls"], 0)
        self.assertEqual(result["kind"], "COUNTERFACTUAL_PAIR_SCORE_V4_NOT_A_GENERAL_ACCURACY_RATE")


class CorpusLoading(V4Fixture):
    def test_a_modified_pinned_file_stops(self):
        (self.root / "packets" / "Q-a00001" / "S02.txt").write_text("changed\n", encoding="utf-8")
        with self.assertRaises(s4.Invalid):
            s4.Corpus(self.root)

    def test_a_malformed_oracle_record_stops(self):
        bad = copy.deepcopy(CASES)
        bad[1]["citeAnyOf"] = [ref("S02", 99)]
        root = Path(self.tmp) / "bad"
        write_corpus(root, bad)
        with self.assertRaises(s4.Invalid):
            s4.Corpus(root)

    def test_lines_of_each_source(self):
        corpus = s4.Corpus(self.root)
        self.assertEqual(corpus.lines("Q-a00002", "S02"), S02)
        self.assertEqual(corpus.lines("Q-a00002"), S01)
        with self.assertRaises(s4.Invalid):
            corpus.lines("Q-c00001", "S02")

    def test_a_v4_corpus_is_not_legacy(self):
        self.assertFalse(s4.Corpus(self.root).legacy)


class CommandLine(V4Fixture):
    def test_main_writes_the_score(self):
        responses = Path(self.tmp) / "responses.jsonl"
        responses.write_text("\n".join(json.dumps(r) for r in full_run()) + "\n", encoding="utf-8")
        out = Path(self.tmp) / "out.json"
        self.assertEqual(s4.main(["--corpus", str(self.root), str(responses), str(out)]), 0)
        self.assertEqual(json.loads(out.read_text(encoding="utf-8"))["trials"]["1"]["observations"], 8)

    def test_main_stops_on_bad_input(self):
        responses = Path(self.tmp) / "responses.json"
        responses.write_text(json.dumps([row("Q-zzzzzz", CLEAN)]), encoding="utf-8")
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(s4.main(["--corpus", str(self.root), str(responses)]), 1)
            self.assertEqual(s4.main([str(responses)]), 2)


REPORT = """Review text.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | S02:5 | the limit is 50
FINDING: RISK | UNVERIFIED | 12 | some quote
FINDING: NOTE | UNVERIFIED | - | -
"""


class ParserTests(unittest.TestCase):
    def test_a_report_with_source_qualified_lines(self):
        parsed = pv.parse_report(REPORT)
        self.assertEqual((parsed["completeness"], parsed["assessment"]), ("COMPLETE", "BLOCKERS_FOUND"))
        self.assertEqual([(f["source"], f["line"]) for f in parsed["findings"]], [("S02", 5), ("S01", 12), ("S01", 0)])
        self.assertEqual(parsed["findings"][0]["quote"], "the limit is 50")
        self.assertEqual(parsed["findings"][2]["quote"], "")

    def test_the_quote_may_contain_pipes_and_colons(self):
        parsed = pv.parse_report(REPORT.replace("the limit is 50", "a | b: c"))
        self.assertEqual(parsed["findings"][0]["quote"], "a | b: c")

    def test_line_fields(self):
        self.assertEqual(pv.parse_line_field("S03:7"), ("S03", 7))
        self.assertEqual(pv.parse_line_field(" 4 "), ("S01", 4))
        for bad in ("S1:4", "S01:0", "0", "S01:", "S01:S02:4", "4-5", "line 4", "", "-1", "s01:4"):
            with self.subTest(field=bad):
                self.assertIsNone(pv.parse_line_field(bad))

    def test_malformed_reports_stop(self):
        cases = {
            "NO_MACHINE_SUMMARY": "no summary here",
            "MALFORMED_FINDING": REPORT.replace("S02:5", "S02:0"),
            "UNEXPECTED_LINE_AFTER_SUMMARY": REPORT + "trailing prose\n",
            "DUPLICATE_ASSESSMENT": REPORT + "ASSESSMENT: NO_BLOCKERS_FOUND\n",
            "DUPLICATE_COMPLETENESS": REPORT + "COMPLETENESS: COMPLETE\n",
            "INVALID_ASSESSMENT": REPORT.replace("BLOCKERS_FOUND", "MAYBE"),
            "INVALID_COMPLETENESS": REPORT.replace("COMPLETENESS: COMPLETE", "COMPLETENESS: ALMOST"),
        }
        for reason, text in cases.items():
            with self.subTest(reason=reason):
                with self.assertRaises(pv.Stop) as caught:
                    pv.parse_report(text)
                self.assertEqual(str(caught.exception), reason)

    def test_unsupported_severity_or_evidence_is_malformed(self):
        for text in (REPORT.replace("BLOCKER | VERIFIED", "SEVERE | VERIFIED"), REPORT.replace("BLOCKER | VERIFIED", "BLOCKER | PROVEN"), REPORT.replace("| the limit is 50", "")):
            with self.assertRaises(pv.Stop):
                pv.parse_report(text)

    def test_the_last_summary_marker_counts(self):
        text = "MACHINE SUMMARY\nCOMPLETENESS: INCOMPLETE\n\n" + REPORT
        self.assertEqual(pv.parse_report(text)["completeness"], "COMPLETE")

    def test_parsed_findings_score(self):
        parsed = pv.parse_report(REPORT)
        for f in parsed["findings"]:
            self.assertEqual(set(f), {"severity", "evidence", "source", "line", "quote"})


if __name__ == "__main__":
    unittest.main()
