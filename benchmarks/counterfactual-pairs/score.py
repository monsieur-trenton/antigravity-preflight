"""Score saved reviewer responses against the hidden oracle; no model or provider calls.

Responses JSON: a list of observations
  {"case": "P-xxxxxx", "trial": 1, "technicalStop": null,
   "completeness": "COMPLETE|INCOMPLETE", "assessment": "BLOCKERS_FOUND|CHANGES_RECOMMENDED|NO_BLOCKERS_FOUND",
   "findings": [{"severity": "BLOCKER|RISK|NOTE", "evidence": "VERIFIED|UNVERIFIED|CANNOT_CHECK",
                 "line": 4, "quote": "exact text from that line"}]}

The mechanical outcome is a proxy: a human must still adjudicate each mechanism and any extra claim.
This pilot reports counts with intervals, not a general accuracy rate.

RESPONSES may be a JSON list or the .jsonl ledger written by run_pilot.py (extra keys are ignored).

Usage: score.py [--corpus DIR] [--adjudication FILE] RESPONSES_JSON_OR_JSONL [OUTPUT_JSON]   (DIR defaults to this directory, corpus v1)
"""
import hashlib
import json
from math import sqrt
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ASSESSMENTS = {"BLOCKERS_FOUND", "CHANGES_RECOMMENDED", "NO_BLOCKERS_FOUND"}
SEVERITIES = {"BLOCKER", "RISK", "NOTE"}
EVIDENCE = {"VERIFIED", "UNVERIFIED", "CANNOT_CHECK"}


class Invalid(ValueError):
    pass


def require(condition, label):
    if not condition:
        raise Invalid(label)


def wilson(k, n, z=1.96):
    if n == 0:
        return None
    p = k / n
    denominator = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denominator
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return [round(max(0.0, centre - half), 3), round(min(1.0, centre + half), 3)]


def rate(k, n):
    return {"count": k, "of": n, "wilson95": wilson(k, n)}


def load_frozen(corpus=HERE):
    corpus = Path(corpus)
    manifest = json.loads((corpus / "manifest.json").read_bytes())
    for name, expected in manifest["pins"].items():
        require((corpus / name).is_file() and hashlib.sha256((corpus / name).read_bytes()).hexdigest() == expected,
                "CORPUS_PIN_MISMATCH:" + name)
    oracle = json.loads((corpus / "oracle/oracle.json").read_bytes())
    return manifest, {c["case"]: c for c in oracle["cases"]}


def packet_lines(case, corpus=HERE):
    return (Path(corpus) / "packets" / (case + ".txt")).read_text(encoding="utf-8").split("\n")[:-1]


def validate(row, oracle):
    require(isinstance(row, dict) and row.get("case") in oracle, "UNKNOWN_CASE")
    require(type(row.get("trial", 1)) is int and row.get("trial", 1) > 0, "INVALID_TRIAL")
    if row.get("technicalStop"):
        return
    require(row.get("assessment") in ASSESSMENTS, "INVALID_ASSESSMENT")
    require(row.get("completeness") in {"COMPLETE", "INCOMPLETE"}, "INVALID_COMPLETENESS")
    require(isinstance(row.get("findings"), list), "INVALID_FINDINGS")
    for finding in row["findings"]:
        require(finding.get("severity") in SEVERITIES and finding.get("evidence") in EVIDENCE, "INVALID_FINDING")
        require(type(finding.get("line")) is int and isinstance(finding.get("quote"), str), "INVALID_FINDING")


def supported(case, finding, corpus=HERE):
    lines = packet_lines(case, corpus)
    line = finding["line"]
    return 1 <= line <= len(lines) and bool(finding["quote"].strip()) and finding["quote"] in lines[line - 1]


SEVERITY_RANK = {"NO_BLOCKERS_FOUND": 0, "CHANGES_RECOMMENDED": 1, "BLOCKERS_FOUND": 2}
VERDICT_ONLY_ARMS = ("bare", "defined", "defined-go")  # arms whose reports carry a verdict line and no checkable findings


def grade(row, truth, corpus=HERE):
    """Return (outcome, detail) for one observation."""
    if row.get("technicalStop"):
        return "STOPPED", {}
    if row.get("arm") in VERDICT_ONLY_ARMS:  # verdict only: no findings or quotations exist to check
        severity = SEVERITY_RANK[row["assessment"]]
        detail = {"unsupportedVerified": 0, "mechanismCited": None, "incomplete": False, "severity": severity,
                  "verifiedBlocker": severity == 2, "verdictOnly": True}
        expected = truth["expectedClass"]
        if expected == "SOUND":
            return ("FALSE_BLOCKER" if severity == 2 else "CORRECT" if severity == 0 else "HEDGED"), detail
        if expected == "DEFECT":
            return ("CORRECT" if severity == 2 else "MISSED"), detail
        return ("OVERCLAIMED" if severity == 2 else "MISSED" if severity == 0 else "CORRECT"), detail
    findings = row["findings"]
    blockers = [f for f in findings if f["severity"] == "BLOCKER"]
    verified_blockers = [f for f in blockers if f["evidence"] == "VERIFIED"]
    unsupported = sum(1 for f in findings if f["evidence"] == "VERIFIED" and not supported(row["case"], f, corpus))
    accepted = truth.get("citeAnyOf", [truth["decisiveLine"]])
    cited = any(f["line"] in accepted and supported(row["case"], f, corpus) for f in verified_blockers)
    detail = {"unsupportedVerified": unsupported, "mechanismCited": cited, "incomplete": row["completeness"] == "INCOMPLETE",
              "severity": SEVERITY_RANK[row["assessment"]], "verifiedBlocker": bool(verified_blockers)}
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
    if verified_blockers:  # UNCERTAIN: evidence is absent, not contradictory
        return "OVERCLAIMED", detail
    return ("MISSED" if assessment == "NO_BLOCKERS_FOUND" else "CORRECT"), detail


def verdict_only(rows, oracle):
    """Metrics computed from the verdict alone, so they mean the same for every arm."""
    verdicts = {}
    for row in rows:
        if not row.get("technicalStop"):
            verdicts[row["case"]] = SEVERITY_RANK[row["assessment"]]
    sound = {"n": 0, "clean": 0, "blocked": 0, "hedged": 0}
    changed = {"n": 0, "correct": 0}
    by_pair = {}
    for case, severity in verdicts.items():
        truth = oracle[case]
        by_pair.setdefault((truth["family"], truth["wording"]), {})[truth["role"]] = (severity, truth["expectedClass"])
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


def score_trial(rows, oracle, corpus=HERE):
    graded = {}
    for row in rows:
        graded[row["case"]] = grade(row, oracle[row["case"]], corpus)
    families = {}
    for case, (outcome, detail) in graded.items():
        truth = oracle[case]
        bucket = families.setdefault(truth["family"], {})
        bucket[(truth["wording"], truth["role"])] = (outcome, detail)
    per_family, pair_ok, pair_n = {}, 0, 0
    ordinal_ok = ordinal_n = sound_hedged = 0
    by_difficulty = {}
    sound_total = sound_false = changed_total = changed_correct = unsupported = stopped = 0
    for name, bucket in sorted(families.items()):
        entry = {"outcomes": {f"{w}/{r}": o for (w, r), (o, _) in sorted(bucket.items())}}
        pairs = []
        for wording in ("A", "B"):
            sound, changed = bucket.get((wording, "sound")), bucket.get((wording, "changed"))
            if sound and changed and "STOPPED" not in (sound[0], changed[0]):
                pairs.append(sound[0] == "CORRECT" and changed[0] == "CORRECT")
        entry["pairsDiscriminated"] = f"{sum(pairs)}/{len(pairs)}"
        ordered = []
        for wording in ("A", "B"):
            sound, changed = bucket.get((wording, "sound")), bucket.get((wording, "changed"))
            if sound and changed and "STOPPED" not in (sound[0], changed[0]):
                twin = next(oracle[c] for c, (o, d) in graded.items()
                            if oracle[c]["family"] == name and oracle[c]["wording"] == wording and oracle[c]["role"] == "changed")
                calibrated = not (twin["expectedClass"] == "UNCERTAIN" and changed[1]["verifiedBlocker"])
                ok = changed[1]["severity"] > sound[1]["severity"] and calibrated
                ordered.append(ok)
                level = by_difficulty.setdefault(twin.get("difficulty", "unspecified"), [0, 0])
                level[0] += ok
                level[1] += 1
        entry["pairsOrderedCalibrated"] = f"{sum(ordered)}/{len(ordered)}"
        ordinal_ok += sum(ordered)
        ordinal_n += len(ordered)
        pair_ok += sum(pairs)
        pair_n += len(pairs)
        roles = {}
        for (wording, role), (outcome, _) in bucket.items():
            roles.setdefault(role, set()).add(outcome)
        entry["wordingConsistent"] = {role: len(outcomes) == 1 for role, outcomes in sorted(roles.items())
                                      if sum(1 for k in bucket if k[1] == role) == 2}
        per_family[name] = entry
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
    return {
        "observations": len(graded), "technicalStops": stopped, "perFamily": per_family,
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


def apply_reclassification(rows, adjudication):
    """Turn the observations an adjudication names into technical stops; each entry names its arm, trial and case."""
    entries = (adjudication or {}).get("technicalStops", [])
    require(isinstance(entries, list), "INVALID_ADJUDICATION")
    named = {}
    for entry in entries:
        require(isinstance(entry.get("arm"), str) and type(entry.get("trial")) is int and isinstance(entry.get("case"), str)
                and isinstance(entry.get("reason"), str) and entry["reason"].strip(), "INVALID_ADJUDICATION")
        named[(entry["arm"], entry["trial"], entry["case"])] = entry.get("code", "RECLASSIFIED")
    if not named:
        return rows
    out = []
    for row in rows:
        code = named.get((row.get("arm", "skill"), row.get("trial", 1), row.get("case")))
        if code:
            keep = {k: row[k] for k in ("case", "trial", "arm", "route", "requestedModel", "effort", "servedModels", "costUsd") if k in row}
            row = dict(keep, technicalStop="RECLASSIFIED:" + code)
        out.append(row)
    return out


def invalid_pairs(adjudication):
    """(family, wording) pairs an adjudication file marks invalid under the preregistered rule."""
    require(isinstance(adjudication, dict) and isinstance(adjudication.get("invalidPairs", []), list), "INVALID_ADJUDICATION")
    pairs = set()
    for entry in adjudication.get("invalidPairs", []):
        require(isinstance(entry.get("family"), str) and isinstance(entry.get("wordings"), list)
                and isinstance(entry.get("reason"), str) and entry["reason"].strip(), "INVALID_ADJUDICATION")
        pairs.update((entry["family"], w) for w in entry["wordings"])
    return pairs


def score(responses, corpus=HERE, adjudication=None):
    manifest, oracle = load_frozen(corpus)
    require(isinstance(responses, list), "INVALID_RESPONSES")
    responses = apply_reclassification(responses, adjudication)
    trials = {}
    for row in responses:
        validate(row, oracle)
        trial = row.get("trial", 1)
        require(row["case"] not in {r["case"] for r in trials.get(trial, [])}, "DUPLICATE_OBSERVATION")
        trials.setdefault(trial, []).append(row)
    result = {
        "kind": "COUNTERFACTUAL_PAIR_PILOT_SCORE_NOT_A_GENERAL_ACCURACY_RATE",
        "corpusManifestSha256": hashlib.sha256((Path(corpus) / "manifest.json").read_bytes()).hexdigest(),
        "casesInCorpus": manifest["cases"],
        "trials": {str(t): score_trial(rows, oracle, corpus) for t, rows in sorted(trials.items())},
        "providerCalls": 0,
    }
    for t, rows in trials.items():
        result["trials"][str(t)]["arms"] = sorted({str(r.get("arm", "skill")) for r in rows})
        result["trials"][str(t)]["routes"] = sorted({str(r.get("route", "unspecified")) for r in rows})
        result["trials"][str(t)]["requestedModels"] = sorted({str(r.get("requestedModel", "unrecorded")) for r in rows})
        result["trials"][str(t)]["servedModelsReported"] = sorted({m for r in rows for m in r.get("servedModels", [])})
        result["trials"][str(t)]["casesNotObserved"] = sorted(set(oracle) - {r["case"] for r in rows})
    if adjudication is not None and adjudication.get("invalidPairs"):
        excluded = invalid_pairs(adjudication)
        keep = lambda r: (oracle[r["case"]]["family"], oracle[r["case"]]["wording"]) not in excluded
        result["adjusted"] = {
            "excludedPairs": sorted(f"{f}/{w}" for f, w in excluded),
            "note": "Shown beside the all-pairs result, never instead of it; exclusions follow the preregistered rule.",
            "trials": {str(t): score_trial([r for r in rows if keep(r)], oracle, corpus) for t, rows in sorted(trials.items())},
        }
    if len(trials) > 1:
        outcomes = {t: {r["case"]: grade(r, oracle[r["case"]], corpus)[0] for r in rows} for t, rows in trials.items()}
        shared = set.intersection(*(set(o) for o in outcomes.values()))
        same = sum(1 for c in shared if len({o[c] for o in outcomes.values()}) == 1)
        result["repeatability"] = rate(same, len(shared))
    return result


def main(argv):
    corpus, adjudication = HERE, None
    if "--adjudication" in argv:
        index = argv.index("--adjudication")
        try:
            adjudication = json.loads(Path(argv[index + 1]).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            print(json.dumps({"status": "STOPPED", "reason": "ADJUDICATION_UNREADABLE"}))
            return 1
        argv = argv[:index] + argv[index + 2:]
    if "--corpus" in argv:
        index = argv.index("--corpus")
        corpus = Path(argv[index + 1]).resolve()
        argv = argv[:index] + argv[index + 2:]
    if not argv:
        print("usage: score.py [--corpus DIR] [--adjudication FILE] RESPONSES_JSON [OUTPUT_JSON]", file=sys.stderr)
        return 2
    try:
        raw = Path(argv[0]).read_text(encoding="utf-8")
        rows = [json.loads(line) for line in raw.splitlines() if line.strip()] if argv[0].endswith(".jsonl") else json.loads(raw)
        result = score(rows, corpus, adjudication)
    except (Invalid, OSError, json.JSONDecodeError) as error:
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
