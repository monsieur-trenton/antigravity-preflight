"""Compare two arms on the same frozen corpus as preregistered; no model calls.

Each arm directory holds trial1/, trial2/, ..., each with responses.jsonl and reports/<case>.md. The primary
comparison is verdict-only ordinal pair discrimination on matched (pair, trial) units with an exact two-sided sign
test; the secondary comparisons, the keyword rubric on defect twins and the comparability check follow
ablation/PREREGISTRATION.md. It reads the oracle only to map cases to families and roles.

Usage: analyze.py --corpus DIR --arm skill=DIR --arm bare=DIR [--exclude FAMILY ...] [--adjudication FILE] [--out FILE]
"""
import argparse
from math import comb
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sc = load("analyze_score", PARENT / "score.py")
SEVERITY = sc.SEVERITY_RANK


def sign_test(b, c):
    """Exact two-sided sign test on discordant counts b and c."""
    n = b + c
    if n == 0:
        return 1.0
    tail = sum(comb(n, i) for i in range(min(b, c) + 1)) / 2 ** n
    return round(min(1.0, 2 * tail), 4)


def load_arm(directory):
    directory = Path(directory)
    trials = {}
    for trial_dir in sorted(directory.glob("trial*")):
        ledger = trial_dir / "responses.jsonl"
        if not ledger.is_file():
            continue
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            report = trial_dir / "reports" / (row["case"] + ".md")
            row["_report"] = report.read_text(encoding="utf-8") if report.is_file() else ""
        trials[int(trial_dir.name.removeprefix("trial"))] = rows
    sc.require(bool(trials), "ARM_EMPTY:" + str(directory))
    return trials


def verdicts(trials, oracle):
    """(case, trial) -> severity rank for observations that produced a verdict."""
    return {(r["case"], t): SEVERITY[r["assessment"]] for t, rows in trials.items() for r in rows
            if not r.get("technicalStop")}


def ordinal_units(severity_by_case_trial, oracle, excluded):
    """(family, wording, trial) -> counted? for pairs where both twins have a verdict."""
    pairs = {}
    for (case, trial), severity in severity_by_case_trial.items():
        truth = oracle[case]
        if truth["family"] in excluded:
            continue
        pairs.setdefault((truth["family"], truth["wording"], trial), {})[truth["role"]] = (severity, truth["expectedClass"])
    units = {}
    for key, pair in pairs.items():
        if "sound" in pair and "changed" in pair:
            (s_sev, _), (c_sev, c_class) = pair["sound"], pair["changed"]
            units[key] = c_sev > s_sev and not (c_class == "UNCERTAIN" and c_sev == 2)
    return units


def paired(first, second):
    keys = sorted(set(first) & set(second))
    b = sum(1 for k in keys if first[k] and not second[k])
    c = sum(1 for k in keys if second[k] and not first[k])
    return {"matchedUnits": len(keys), "bothCount": sum(1 for k in keys if first[k] and second[k]),
            "onlyFirst": b, "onlySecond": c, "exactTwoSidedSignTestP": sign_test(b, c)}


def strict_units(severity_by_case_trial, oracle, excluded):
    """(family, wording, trial) -> sound twin judged clean and changed twin judged correctly, where both have a verdict."""
    pairs = {}
    for (case, trial), severity in severity_by_case_trial.items():
        truth = oracle[case]
        if truth["family"] in excluded:
            continue
        pairs.setdefault((truth["family"], truth["wording"], trial), {})[truth["role"]] = (severity, truth["expectedClass"])
    units = {}
    for key, pair in pairs.items():
        if "sound" in pair and "changed" in pair:
            (s_sev, _), (c_sev, c_class) = pair["sound"], pair["changed"]
            units[key] = s_sev == 0 and c_sev == (2 if c_class == "DEFECT" else 1)
    return units


def rate(k, n):
    return sc.rate(k, n)


def fourth_arm_label(vs_defined, vs_skill):
    """The fourth arm's preregistered outcome label, from the all-pairs blocks of two analyses (first=defined, second=defined-go;
    first=skill, second=defined-go). Fixed in ablation/defined-go/PREREGISTRATION.md before any observation of that arm."""
    clean, lost = vs_defined["allPairs"]["soundCleanPaired"], vs_defined["allPairs"]["changedTwinCorrectPaired"]
    skill = vs_skill["allPairs"]["soundCleanPaired"]
    if lost["onlyFirst"] >= 3:
        return "costs detection"
    if clean["exactTwoSidedSignTestP"] < 0.05 and clean["onlyFirst"] > clean["onlySecond"]:
        return "worse on sound plans"
    if clean["exactTwoSidedSignTestP"] < 0.05:
        return "closes the sound-plan gap" if skill["onlyFirst"] <= 5 else "partly closes the sound-plan gap"
    return "does not close the sound-plan gap"


def mechanism_mentions(trials, oracle, rubric, severity):
    """Among defect twins with a BLOCKERS_FOUND verdict, how many reports match the family rubric."""
    n = hit = 0
    for trial, rows in trials.items():
        for r in rows:
            truth = oracle[r["case"]]
            if r.get("technicalStop") or truth["role"] != "changed" or truth["expectedClass"] != "DEFECT":
                continue
            if severity.get((r["case"], trial)) != 2:
                continue
            text = r["_report"].split("MACHINE SUMMARY")[0]
            n += 1
            hit += all(any(re.search(p, text, re.I) for p in group) for group in rubric[truth["family"]])
    return rate(hit, n)


def verdict_follows_finding(trials, oracle, rubric, severity):
    """Among defect twins with a verdict whose report matches the family rubric, the share that got BLOCKERS_FOUND."""
    n = hit = 0
    for trial, rows in trials.items():
        for r in rows:
            truth = oracle[r["case"]]
            if r.get("technicalStop") or truth["role"] != "changed" or truth["expectedClass"] != "DEFECT":
                continue
            text = r["_report"].split("MACHINE SUMMARY")[0]
            if all(any(re.search(p, text, re.I) for p in group) for group in rubric[truth["family"]]):
                n += 1
                hit += severity.get((r["case"], trial)) == 2
    return rate(hit, n)


def arm_summary(name, trials, oracle, corpus, rubric, excluded):
    severity = verdicts(trials, oracle)
    stamps = {(r.get("requestedModel"), r.get("effort"), r.get("claudeVersion")) for rows in trials.values() for r in rows}
    stops, unparseable, total = {}, 0, 0
    for rows in trials.values():
        for r in rows:
            total += 1
            if r.get("technicalStop"):
                code = r["technicalStop"].split(":")[0]
                stops[code] = stops.get(code, 0) + 1
                unparseable += code in ("UNPARSEABLE_REPORT", "NO_VERDICT_LINE")
    rows_flat = [dict(r, _report=None) for rows in trials.values() for r in rows]
    scored = sc.score([{k: v for k, v in r.items() if k != "_report"} for r in rows_flat], corpus)
    kept = [r for r in rows_flat if oracle[r["case"]]["family"] not in excluded]
    adjusted = sc.score([{k: v for k, v in r.items() if k != "_report"} for r in kept], corpus) if excluded else None
    return {
        "arm": name, "observations": total, "technicalStops": stops, "unparseableOrMissingVerdict": unparseable,
        "stamps": sorted(map(list, ((str(a), str(b), str(c)) for a, b, c in stamps))),
        "servedModels": sorted({m for rows in trials.values() for r in rows for m in r.get("servedModels", [])}),
        "costUsd": round(sum((r.get("costUsd") or 0) for rows in trials.values() for r in rows), 4),
        "perTrial": {str(t): {"verdictOnly": scored["trials"][str(t)]["verdictOnly"]} for t in sorted(trials)},
        "adjustedPerTrial": ({str(t): {"verdictOnly": adjusted["trials"][str(t)]["verdictOnly"]} for t in sorted(trials)}
                             if adjusted else None),
        "repeatability": scored.get("repeatability"),
        "mechanismMentionedAmongBlockedDefectTwins": mechanism_mentions(trials, oracle, rubric, severity),
        "verdictFollowsFinding": verdict_follows_finding(trials, oracle, rubric, severity),
    }, severity


def analyze(corpus, arms, excluded=(), adjudication=None):
    """As-run analysis at the top level; if an adjudication names technical-stop reclassifications, a second view with
    them applied is added beside it as documentedRuleView, never instead of it."""
    corpus = Path(corpus)
    loaded = {name: load_arm(directory) for name, directory in arms.items()}
    result = _analyze(corpus, arms, loaded, excluded)
    if adjudication and adjudication.get("technicalStops"):
        reclassified = {name: {t: sc.apply_reclassification(rows, adjudication) for t, rows in trials.items()}
                        for name, trials in loaded.items()}
        view = _analyze(corpus, arms, reclassified, excluded)
        view["reclassified"] = [{k: e[k] for k in ("arm", "trial", "case", "code")} for e in adjudication["technicalStops"]]
        result["documentedRuleView"] = view
    return result


def _analyze(corpus, arms, loaded, excluded):
    manifest, oracle = sc.load_frozen(corpus)
    rubric = json.loads((HERE / "rubric.json").read_bytes())["families"]
    summaries, severities = {}, {}
    for name, trials in loaded.items():
        summaries[name], severities[name] = arm_summary(name, trials, oracle, corpus, rubric, set(excluded))
    names = list(arms)
    first, second = names[0], names[1]
    result = {
        "kind": "ABLATION_ARM_COMPARISON_NOT_A_GENERAL_ACCURACY_RATE",
        "corpusManifestSha256": sc.hashlib.sha256((corpus / "manifest.json").read_bytes()).hexdigest(),
        "arms": summaries,
        "comparability": {
            "sameModelEffortAndCliVersion": len({tuple(map(tuple, summaries[n]["stamps"])) for n in names}) == 1,
            "note": "A mismatch means the arms differ in more than the prompt bundle; say so wherever the comparison is quoted.",
        },
        "excludedFamilies": sorted(excluded),
        "providerCalls": 0,
    }
    for label, skip in (("allPairs", set()), ("adjusted", set(excluded))):
        if label == "adjusted" and not excluded:
            continue
        ordinal = {n: ordinal_units(severities[n], oracle, skip) for n in names}
        sound = {n: {k: v for k, v in severities[n].items() if oracle[k[0]]["role"] == "sound" and oracle[k[0]]["family"] not in skip}
                 for n in names}
        twin_ok = {n: {k: v == (2 if oracle[k[0]]["expectedClass"] == "DEFECT" else 1)
                       for k, v in severities[n].items() if oracle[k[0]]["role"] == "changed" and oracle[k[0]]["family"] not in skip}
                   for n in names}
        block = {"primaryOrdinalPairDiscrimination": {n: rate(sum(ordinal[n].values()), len(ordinal[n])) for n in names}}
        block["primaryPaired"] = {"first": first, "second": second, **paired(ordinal[first], ordinal[second])}
        not_blocked = {n: {k: v != 2 for k, v in sound[n].items()} for n in names}
        clean = {n: {k: v == 0 for k, v in sound[n].items()} for n in names}
        block["soundPlansBlocked"] = {n: rate(sum(1 for v in sound[n].values() if v == 2), len(sound[n])) for n in names}
        block["soundPlansClean"] = {n: rate(sum(1 for v in sound[n].values() if v == 0), len(sound[n])) for n in names}
        block["soundPlansHedged"] = {n: rate(sum(1 for v in sound[n].values() if v == 1), len(sound[n])) for n in names}
        block["soundNotBlockedPaired"] = {"first": first, "second": second, **paired(not_blocked[first], not_blocked[second])}
        block["soundCleanPaired"] = {"first": first, "second": second, **paired(clean[first], clean[second])}
        block["changedTwinVerdictCorrect"] = {n: rate(sum(twin_ok[n].values()), len(twin_ok[n])) for n in names}
        block["changedTwinCorrectPaired"] = {"first": first, "second": second, **paired(twin_ok[first], twin_ok[second])}
        strict = {n: strict_units(severities[n], oracle, skip) for n in names}
        block["strictPairDiscrimination"] = {n: rate(sum(strict[n].values()), len(strict[n])) for n in names}
        block["strictPaired"] = {"first": first, "second": second, **paired(strict[first], strict[second])}
        defect_blocked = {n: {k: v == 2 for k, v in severities[n].items()
                              if oracle[k[0]]["role"] == "changed" and oracle[k[0]]["expectedClass"] == "DEFECT"
                              and oracle[k[0]]["family"] not in skip} for n in names}
        block["defectTwinsBlocked"] = {n: rate(sum(defect_blocked[n].values()), len(defect_blocked[n])) for n in names}
        block["defectTwinBlockedPaired"] = {"first": first, "second": second, **paired(defect_blocked[first], defect_blocked[second])}
        result[label] = block
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--arm", action="append", required=True, metavar="NAME=DIR")
    parser.add_argument("--exclude", action="append", default=[], help="family to exclude in the adjusted view (repeatable)")
    parser.add_argument("--adjudication", help="adjudication JSON; its technicalStops add a documented-rule view beside the as-run one")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        arms = dict(item.split("=", 1) for item in args.arm)
        sc.require(len(arms) == 2, "TWO_ARMS_REQUIRED")
        adjudication = json.loads(Path(args.adjudication).read_text(encoding="utf-8")) if args.adjudication else None
        result = analyze(args.corpus, arms, args.exclude, adjudication)
    except (sc.Invalid, OSError, ValueError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, sc.Invalid) else type(error).__name__}))
        return 1
    text = json.dumps(result, indent=2) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
