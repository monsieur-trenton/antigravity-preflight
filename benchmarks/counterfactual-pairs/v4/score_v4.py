"""Score saved reviewer responses against the hidden oracle of any corpus (v1 to v3 or v4); no model or provider calls.

This generalises score.py, which it imports and leaves untouched, in three ways: the unit of a pair is a `pair` id (an instance, shared by its wordings) rather
than a family, so a family may hold many instances; citations are source-qualified (a finding's optional `source`, default S01, and its line, checked against
that source's own lines); and it adds the v4 metrics (by kind and by family, decoy discipline, citations, mechanism judgments, wording B).
Every key score.py computes for a trial is computed here by the same rules and, on v1 to v3 corpora, is equal (the gate of test_score_v4.py); the one rename is
`perFamily`, which is `perPair` here because on v1 to v3 the pair id is the family.

Responses: a list of observations or the .jsonl ledger of a driver, as for score.py; a finding may carry `"source": "S02"`.
Mechanism judgments (optional): a list of {"arm", "trial", "case", "namesMechanism": true|false} written by a reader blind to the arm.

Usage: score_v4.py --corpus DIR [--adjudication FILE] [--judgments FILE] RESPONSES [OUTPUT_JSON]
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sc = load("v4_score", HERE.parent / "score.py")
cfam = load("v4_check_families", HERE / "check_families.py")
Invalid, require, rate = sc.Invalid, sc.require, sc.rate
RANK, VERDICT_ONLY_ARMS = sc.SEVERITY_RANK, sc.VERDICT_ONLY_ARMS


class Corpus:
    """A frozen corpus behind one interface: normalised oracle records and the numbered lines of each source of each case."""

    def __init__(self, path):
        self.path = Path(path)
        self.manifest = json.loads((self.path / "manifest.json").read_bytes())
        for name, expected in self.manifest["pins"].items():
            require((self.path / name).is_file() and hashlib.sha256((self.path / name).read_bytes()).hexdigest() == expected, "CORPUS_PIN_MISMATCH:" + name)
        records = json.loads((self.path / "oracle/oracle.json").read_bytes())["cases"]
        self.legacy = not any("pair" in r for r in records)
        self.oracle = {}
        for record in records:
            self.oracle[record["case"]] = self.normalise(record)
            if not self.legacy:
                require(not cfam.check_oracle(record), "ORACLE_SCHEMA:" + record["case"])

    def normalise(self, record):
        if not self.legacy:
            return record
        accepted = record.get("citeAnyOf", [record.get("decisiveLine")])
        return dict(record, pair=record["family"], kind=None, citeAnyOf=[{"source": "S01", "line": n} for n in accepted if isinstance(n, int)],
                    decoyLines=[], difficulty=record.get("difficulty"))

    def lines(self, case, source="S01"):
        if self.legacy:
            require(source == "S01", "UNKNOWN_SOURCE")
            return (self.path / "packets" / (case + ".txt")).read_text(encoding="utf-8").split("\n")[:-1]
        path = self.path / "packets" / case / (source + ".txt")
        require(path.is_file(), "UNKNOWN_SOURCE")
        return path.read_text(encoding="utf-8").split("\n")[:-1]


def validate(row, oracle):
    require(isinstance(row, dict) and row.get("case") in oracle, "UNKNOWN_CASE")
    require(type(row.get("trial", 1)) is int and row.get("trial", 1) > 0, "INVALID_TRIAL")
    if row.get("technicalStop"):
        return
    require(row.get("assessment") in sc.ASSESSMENTS, "INVALID_ASSESSMENT")
    require(row.get("completeness") in {"COMPLETE", "INCOMPLETE"}, "INVALID_COMPLETENESS")
    require(isinstance(row.get("findings"), list), "INVALID_FINDINGS")
    for finding in row["findings"]:
        require(finding.get("severity") in sc.SEVERITIES and finding.get("evidence") in sc.EVIDENCE, "INVALID_FINDING")
        require(type(finding.get("line")) is int and isinstance(finding.get("quote"), str), "INVALID_FINDING")
        require(finding.get("source", "S01") in ("S01", "S02"), "INVALID_FINDING")


def supported(corpus, case, finding):
    source = finding.get("source", "S01")
    try:
        lines = corpus.lines(case, source)
    except (Invalid, OSError):
        return False
    line = finding["line"]
    return 1 <= line <= len(lines) and bool(finding["quote"].strip()) and finding["quote"] in lines[line - 1]


def located(finding):
    return (finding.get("source", "S01"), finding["line"])


def grade(row, truth, corpus):
    """(outcome, detail) for one observation, by the rules of score.grade with source-qualified citations."""
    if row.get("technicalStop"):
        return "STOPPED", {}
    if row.get("arm") in VERDICT_ONLY_ARMS:
        severity = RANK[row["assessment"]]
        detail = {"unsupportedVerified": 0, "mechanismCited": None, "incomplete": False, "severity": severity, "verifiedBlocker": severity == 2, "verdictOnly": True}
        expected = truth["expectedClass"]
        if expected == "SOUND":
            return ("FALSE_BLOCKER" if severity == 2 else "CORRECT" if severity == 0 else "HEDGED"), detail
        if expected == "DEFECT":
            return ("CORRECT" if severity == 2 else "MISSED"), detail
        return ("OVERCLAIMED" if severity == 2 else "MISSED" if severity == 0 else "CORRECT"), detail
    findings = row["findings"]
    blockers = [f for f in findings if f["severity"] == "BLOCKER"]
    verified_blockers = [f for f in blockers if f["evidence"] == "VERIFIED"]
    unsupported = sum(1 for f in findings if f["evidence"] == "VERIFIED" and not supported(corpus, row["case"], f))
    accepted = {(r["source"], r["line"]) for r in truth["citeAnyOf"]}
    cited = any(located(f) in accepted and supported(corpus, row["case"], f) for f in verified_blockers)
    detail = {"unsupportedVerified": unsupported, "mechanismCited": cited, "incomplete": row["completeness"] == "INCOMPLETE",
              "severity": RANK[row["assessment"]], "verifiedBlocker": bool(verified_blockers)}
    assessment = row["assessment"]
    expected = truth["expectedClass"]
    if expected == "SOUND":
        if blockers or assessment == "BLOCKERS_FOUND":
            return "FALSE_BLOCKER", detail
        return ("CORRECT" if assessment == "NO_BLOCKERS_FOUND" else "HEDGED"), detail
    if expected == "DEFECT":
        if assessment == "BLOCKERS_FOUND" and verified_blockers:
            return ("CORRECT" if cited else "DETECTED_WITHOUT_DECISIVE_CITATION"), detail
        return "MISSED", detail
    if verified_blockers:
        return "OVERCLAIMED", detail
    return ("MISSED" if assessment == "NO_BLOCKERS_FOUND" else "CORRECT"), detail


def verdict_only(rows, oracle):
    verdicts = {}
    for row in rows:
        if not row.get("technicalStop"):
            verdicts[row["case"]] = RANK[row["assessment"]]
    sound = {"n": 0, "clean": 0, "blocked": 0, "hedged": 0}
    changed = {"n": 0, "correct": 0}
    by_pair = {}
    for case, severity in verdicts.items():
        truth = oracle[case]
        by_pair.setdefault((truth["pair"], truth["wording"]), {})[truth["role"]] = (severity, truth["expectedClass"])
        if truth["role"] == "sound":
            sound["n"] += 1
            sound["clean"] += severity == 0
            sound["blocked"] += severity == 2
            sound["hedged"] += severity == 1
        else:
            changed["n"] += 1
            changed["correct"] += severity == (2 if truth["expectedClass"] == "DEFECT" else 1)
    strict = ordinal = pairs = 0
    for pair in by_pair.values():
        if "sound" in pair and "changed" in pair:
            pairs += 1
            (s_sev, _), (c_sev, c_class) = pair["sound"], pair["changed"]
            ok_twin = c_sev == (2 if c_class == "DEFECT" else 1)
            strict += s_sev == 0 and ok_twin
            ordinal += c_sev > s_sev and not (c_class == "UNCERTAIN" and c_sev == 2)
    return {"soundClean": rate(sound["clean"], sound["n"]), "soundBlocked": rate(sound["blocked"], sound["n"]),
            "soundHedged": rate(sound["hedged"], sound["n"]), "changedVerdictCorrect": rate(changed["correct"], changed["n"]),
            "pairStrictVerdictOnly": rate(strict, pairs), "pairOrderedVerdictOnly": rate(ordinal, pairs),
            "note": "Verdict-only definitions identical for every arm: defect twin = BLOCKERS_FOUND, uncertainty twin = CHANGES_RECOMMENDED."}


def aggregate(units, members):
    """The per-group block of the v4 metrics: `units` are (sound, changed) outcome tuples for one pair-wording, `members` are (role, truth, outcome, detail)."""
    strict = sum(1 for s, c in units if s[0] == "CORRECT" and c[0] == "CORRECT")
    ordered = sum(1 for s, c in units if c[1]["severity"] > s[1]["severity"] and not (c[2] == "UNCERTAIN" and c[1]["verifiedBlocker"]))
    sound = [m for m in members if m[0] == "sound"]
    twins = [m for m in members if m[0] == "changed"]
    gap = [m for m in twins if m[1]["expectedClass"] == "UNCERTAIN"]
    defect = [m for m in twins if m[1]["expectedClass"] == "DEFECT"]
    return {"units": len(units), "strictPairs": rate(strict, len(units)), "orderedPairs": rate(ordered, len(units)),
            "soundClean": rate(sum(1 for m in sound if m[2] == "CORRECT"), len(sound)),
            "soundHedged": rate(sum(1 for m in sound if m[2] == "HEDGED"), len(sound)),
            "soundBlocked": rate(sum(1 for m in sound if m[2] == "FALSE_BLOCKER"), len(sound)),
            "twinCorrect": rate(sum(1 for m in twins if m[2] == "CORRECT"), len(twins)),
            "gapTwinsOverclaimed": rate(sum(1 for m in gap if m[2] == "OVERCLAIMED"), len(gap)),
            "gapTwinsWavedThrough": rate(sum(1 for m in gap if m[2] == "MISSED"), len(gap)),
            "defectTwinsMissed": rate(sum(1 for m in defect if m[2] == "MISSED"), len(defect)),
            "defectTwinsWithoutDecisiveCitation": rate(sum(1 for m in defect if m[2] == "DETECTED_WITHOUT_DECISIVE_CITATION"), len(defect))}


def score_trial(rows, corpus, judgments=None):
    oracle = corpus.oracle
    graded = {row["case"]: grade(row, oracle[row["case"]], corpus) for row in rows}
    by_row = {row["case"]: row for row in rows}
    pairs = {}
    for case, (outcome, detail) in graded.items():
        truth = oracle[case]
        pairs.setdefault(truth["pair"], {})[(truth["wording"], truth["role"])] = (outcome, detail)
    per_pair, pair_ok, pair_n = {}, 0, 0
    ordinal_ok = ordinal_n = sound_hedged = 0
    by_difficulty = {}
    sound_total = sound_false = changed_total = changed_correct = unsupported = stopped = 0
    for name, bucket in sorted(pairs.items()):
        entry = {"outcomes": {f"{w}/{r}": o for (w, r), (o, _) in sorted(bucket.items())}}
        pair_results = []
        for wording in ("A", "B"):
            sound, changed = bucket.get((wording, "sound")), bucket.get((wording, "changed"))
            if sound and changed and "STOPPED" not in (sound[0], changed[0]):
                pair_results.append(sound[0] == "CORRECT" and changed[0] == "CORRECT")
        entry["pairsDiscriminated"] = f"{sum(pair_results)}/{len(pair_results)}"
        ordered = []
        for wording in ("A", "B"):
            sound, changed = bucket.get((wording, "sound")), bucket.get((wording, "changed"))
            if sound and changed and "STOPPED" not in (sound[0], changed[0]):
                twin = next(oracle[c] for c, (o, d) in graded.items()
                            if oracle[c]["pair"] == name and oracle[c]["wording"] == wording and oracle[c]["role"] == "changed")
                calibrated = not (twin["expectedClass"] == "UNCERTAIN" and changed[1]["verifiedBlocker"])
                ok = changed[1]["severity"] > sound[1]["severity"] and calibrated
                ordered.append(ok)
                level = by_difficulty.setdefault(twin.get("difficulty") or "unspecified", [0, 0])
                level[0] += ok
                level[1] += 1
        entry["pairsOrderedCalibrated"] = f"{sum(ordered)}/{len(ordered)}"
        ordinal_ok += sum(ordered)
        ordinal_n += len(ordered)
        pair_ok += sum(pair_results)
        pair_n += len(pair_results)
        roles = {}
        for (wording, role), (outcome, _) in bucket.items():
            roles.setdefault(role, set()).add(outcome)
        entry["wordingConsistent"] = {role: len(outcomes) == 1 for role, outcomes in sorted(roles.items())
                                      if sum(1 for k in bucket if k[1] == role) == 2}
        per_pair[name] = entry
        for (_, role), (outcome, detail) in bucket.items():
            if outcome == "STOPPED":
                stopped += 1
                continue
            unsupported += detail["unsupportedVerified"]
            if role == "sound":
                sound_total += 1
                sound_false += outcome == "FALSE_BLOCKER"
                sound_hedged += outcome == "HEDGED"
            else:
                changed_total += 1
                changed_correct += outcome == "CORRECT"
    result = {
        "observations": len(graded), "technicalStops": stopped, "perPair": per_pair,
        "pairDiscrimination": rate(pair_ok, pair_n),
        "pairOrderedCalibrated": rate(ordinal_ok, ordinal_n),
        "hedgedOnSoundPlans": rate(sound_hedged, sound_total),
        "pairOrderedCalibratedByDifficulty": {k: rate(v[0], v[1]) for k, v in sorted(by_difficulty.items())},
        "verdictOnly": verdict_only(rows, oracle),
        "falseBlockersOnSoundPlans": rate(sound_false, sound_total),
        "changedPlansJudgedCorrectly": rate(changed_correct, changed_total),
        "unsupportedVerifiedFindings": unsupported,
        "pilotGate": {"unsupportedVerifiedIsZero": unsupported == 0,
                      "note": "Also requires complete source/question coverage and human adjudication of every mechanism."},
    }
    result.update(v4_metrics(graded, by_row, corpus, judgments))
    return result


def v4_metrics(graded, by_row, corpus, judgments):
    """The blocks that score.py has no counterpart for. On a v1 to v3 corpus (no kinds) the by-kind block is empty."""
    oracle = corpus.oracle
    members = {case: (oracle[case]["role"], detail, outcome, oracle[case]) for case, (outcome, detail) in graded.items() if outcome != "STOPPED"}
    twins_of = {}
    for case, (role, _, _, truth) in members.items():
        twins_of.setdefault((truth["pair"], truth["wording"]), {})[role] = case
    complete = [(cases["sound"], cases["changed"]) for cases in twins_of.values() if "sound" in cases and "changed" in cases]
    shaped = {}
    for dimension, name_of in (("kind", lambda t: t.get("kind")), ("family", lambda t: t["family"])):
        keys = sorted({name_of(t) for _, _, _, t in members.values() if name_of(t) is not None})
        shaped[dimension] = {}
        for key in keys:
            units = []
            for sound, changed in complete:
                twin = oracle[changed]
                if name_of(twin) == key:
                    units.append(((members[sound][2], members[sound][1]), (members[changed][2], members[changed][1], twin["expectedClass"])))
            rows = [(role, dict(detail, expectedClass=truth["expectedClass"]), outcome) for role, detail, outcome, truth in members.values() if name_of(truth) == key]
            shaped[dimension][key] = aggregate(units, rows)
    decoy_members = [(case, m) for case, m in members.items() if m[3].get("kind") == "decoy_pair" and m[0] == "sound"]
    blocked_on_decoy = flagged_on_decoy = 0
    for case, m in decoy_members:
        decoys = {(r["source"], r["line"]) for r in m[3]["decoyLines"]}
        findings = by_row[case].get("findings", [])
        blocked_on_decoy += any(f["severity"] == "BLOCKER" and located(f) in decoys for f in findings)
        flagged_on_decoy += any(located(f) in decoys for f in findings)
    defect_blocked = [(case, m) for case, m in members.items() if m[0] == "changed" and m[3]["expectedClass"] == "DEFECT" and m[2] in ("CORRECT", "DETECTED_WITHOUT_DECISIVE_CITATION")]
    gap_correct = [(case, m) for case, m in members.items() if m[0] == "changed" and m[3]["expectedClass"] == "UNCERTAIN" and m[2] == "CORRECT"]
    gap_cited = 0
    for case, m in gap_correct:
        accepted = {(r["source"], r["line"]) for r in m[3]["citeAnyOf"]}
        gap_cited += any(located(f) in accepted and supported(corpus, case, f) for f in by_row[case].get("findings", []))
    named = pending = judged_n = 0
    wanted = {(by_row[case].get("arm", "skill"), by_row[case].get("trial", 1), case) for case, _ in defect_blocked}
    table = {(j["arm"], j["trial"], j["case"]): j["namesMechanism"] for j in (judgments or [])}
    for key in wanted:
        if key in table:
            judged_n += 1
            named += bool(table[key])
        else:
            pending += 1
    wording_b = {}
    for role in ("sound", "changed"):
        both = 0
        same = 0
        by_pair_wording = {}
        for case, m in members.items():
            if m[0] == role:
                by_pair_wording.setdefault(m[3]["pair"], {})[m[3]["wording"]] = m[1]["severity"]
        for severities in by_pair_wording.values():
            if "A" in severities and "B" in severities:
                both += 1
                same += severities["A"] == severities["B"]
        wording_b[role] = rate(same, both)
    return {
        "byKind": shaped["kind"], "byFamily": shaped["family"],
        "decoyDiscipline": {"decoySoundMembers": len(decoy_members), "judgedClean": rate(sum(1 for _, m in decoy_members if m[2] == "CORRECT"), len(decoy_members)),
                            "blockerOnDecoyLine": blocked_on_decoy, "anyFindingOnDecoyLine": flagged_on_decoy},
        "citations": {"defectTwinsBlockedAndCited": rate(sum(1 for _, m in defect_blocked if m[2] == "CORRECT"), len(defect_blocked)),
                      "gapTwinsCorrectAndCitedAcceptedLine": rate(gap_cited, len(gap_correct))},
        "mechanismJudgments": {"defectTwinsBlocked": len(defect_blocked), "judged": judged_n, "namesMechanism": named, "pending": pending},
        "wordingBConsistency": wording_b,
    }


def score(responses, corpus, adjudication=None, judgments=None):
    corpus = corpus if isinstance(corpus, Corpus) else Corpus(corpus)
    oracle = corpus.oracle
    require(isinstance(responses, list), "INVALID_RESPONSES")
    responses = sc.apply_reclassification(responses, adjudication)
    trials = {}
    for row in responses:
        validate(row, oracle)
        trial = row.get("trial", 1)
        require(row["case"] not in {r["case"] for r in trials.get(trial, [])}, "DUPLICATE_OBSERVATION")
        trials.setdefault(trial, []).append(row)
    result = {
        "kind": "COUNTERFACTUAL_PAIR_SCORE_V4_NOT_A_GENERAL_ACCURACY_RATE",
        "corpusManifestSha256": hashlib.sha256((corpus.path / "manifest.json").read_bytes()).hexdigest(),
        "casesInCorpus": corpus.manifest["cases"],
        "trials": {str(t): score_trial(rows, corpus, judgments) for t, rows in sorted(trials.items())},
        "providerCalls": 0,
    }
    for t, rows in trials.items():
        block = result["trials"][str(t)]
        block["arms"] = sorted({str(r.get("arm", "skill")) for r in rows})
        block["routes"] = sorted({str(r.get("route", "unspecified")) for r in rows})
        block["requestedModels"] = sorted({str(r.get("requestedModel", "unrecorded")) for r in rows})
        block["servedModelsReported"] = sorted({m for r in rows for m in r.get("servedModels", [])})
        block["casesNotObserved"] = sorted(set(oracle) - {r["case"] for r in rows})
    if adjudication is not None and adjudication.get("invalidPairs"):
        excluded = invalid_pairs(adjudication)
        keep = lambda r: (oracle[r["case"]]["pair"], oracle[r["case"]]["wording"]) not in excluded
        result["adjusted"] = {
            "excludedPairs": sorted(f"{p}/{w}" for p, w in excluded),
            "note": "Shown beside the all-pairs result, never instead of it; exclusions follow the preregistered rule.",
            "trials": {str(t): score_trial([r for r in rows if keep(r)], corpus, judgments) for t, rows in sorted(trials.items())},
        }
    if len(trials) > 1:
        outcomes = {t: {r["case"]: grade(r, oracle[r["case"]], corpus)[0] for r in rows} for t, rows in trials.items()}
        shared = set.intersection(*(set(o) for o in outcomes.values()))
        same = sum(1 for c in shared if len({o[c] for o in outcomes.values()}) == 1)
        result["repeatability"] = rate(same, len(shared))
    return result


def invalid_pairs(adjudication):
    """(pair, wording) pairs an adjudication marks invalid; an entry names its pair as `pair` (v4) or `family` (v1 to v3, where they coincide)."""
    require(isinstance(adjudication, dict) and isinstance(adjudication.get("invalidPairs", []), list), "INVALID_ADJUDICATION")
    out = set()
    for entry in adjudication.get("invalidPairs", []):
        name = entry.get("pair") or entry.get("family")
        require(isinstance(name, str) and isinstance(entry.get("wordings"), list) and isinstance(entry.get("reason"), str) and entry["reason"].strip(), "INVALID_ADJUDICATION")
        out.update((name, w) for w in entry["wordings"])
    return out


def main(argv):
    options = {}
    for flag in ("--adjudication", "--judgments", "--corpus"):
        if flag in argv:
            index = argv.index(flag)
            options[flag] = argv[index + 1]
            argv = argv[:index] + argv[index + 2:]
    if not argv or "--corpus" not in options:
        print("usage: score_v4.py --corpus DIR [--adjudication FILE] [--judgments FILE] RESPONSES [OUTPUT_JSON]", file=sys.stderr)
        return 2
    try:
        adjudication = json.loads(Path(options["--adjudication"]).read_text(encoding="utf-8")) if "--adjudication" in options else None
        judgments = json.loads(Path(options["--judgments"]).read_text(encoding="utf-8")) if "--judgments" in options else None
        raw = Path(argv[0]).read_text(encoding="utf-8")
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()] if argv[0].endswith(".jsonl") else json.loads(raw)
        result = score(rows, Path(options["--corpus"]).resolve(), adjudication, judgments)
    except (Invalid, OSError, json.JSONDecodeError, KeyError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, Invalid) else type(error).__name__}))
        return 1
    text = json.dumps(result, indent=2) + "\n"
    if len(argv) > 1:
        Path(argv[1]).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
