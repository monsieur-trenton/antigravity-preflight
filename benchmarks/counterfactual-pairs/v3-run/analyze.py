"""Analyse a preregistered corpus v3 run as v3-run/PREREGISTRATION.md fixes it; no model calls.

Each arm directory holds trial1/, trial2/, ..., each with responses.jsonl and reports/<case>.md, as in ablation/analyze.py,
whose loaders and statistics this reuses. Verdict-only metrics are computed identically for every arm: the three primary
rates (sound plans judged GO, defect twins judged NO_GO, evidence-gap twins judged GO_WITH_CHANGES), strict and ordinal pair
discrimination, the secondary rates, a per-family table, every pairwise paired comparison on matched (case, trial) units with
an exact two-sided sign test, and the preregistered labels. It reads the oracle only to map cases to families, roles and classes.

Usage: analyze.py --corpus DIR --rubric FILE --arm NAME=DIR [--arm NAME=DIR ...]   (one arm gives the rates and no comparisons) [--exclude FAMILY ...] [--adjudication FILE] [--out FILE]
"""
import argparse
import importlib.util
import itertools
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


ab = load("v3run_ablation_analyze", PARENT / "ablation" / "analyze.py")
sc = ab.sc
GO, GWC, NOGO = 0, 1, 2  # severity ranks of NO_BLOCKERS_FOUND, CHANGES_RECOMMENDED, BLOCKERS_FOUND
CORRECT = {"DEFECT": NOGO, "UNCERTAIN": GWC}


def report_text(row):
    return row["_report"].split("MACHINE SUMMARY")[0]


def matches(text, groups):
    return all(any(re.search(p, text, re.I) for p in group) for group in groups)


def observations(trials, oracle, excluded):
    """(case, trial) -> (severity, row) for observations with a verdict, outside the excluded families."""
    found = {}
    for trial, rows in trials.items():
        for row in rows:
            if row.get("technicalStop") or oracle[row["case"]]["family"] in excluded:
                continue
            found[(row["case"], trial)] = (ab.SEVERITY[row["assessment"]], row)
    return found


def unit_sets(obs, oracle):
    """Boolean outcome per matched unit, keyed so the same unit in two arms is the same key."""
    sound_go, defect_nogo, gap_correct = {}, {}, {}
    for (case, trial), (severity, _) in obs.items():
        truth = oracle[case]
        if truth["role"] == "sound":
            sound_go[(case, trial)] = severity == GO
        elif truth["expectedClass"] == "DEFECT":
            defect_nogo[(case, trial)] = severity == NOGO
        else:
            gap_correct[(case, trial)] = severity == GWC
    return {"soundGo": sound_go, "defectNoGo": defect_nogo, "gapGwc": gap_correct}


def per_family(obs, oracle):
    table = {}
    for (case, trial), (severity, _) in obs.items():
        truth = oracle[case]
        entry = table.setdefault(truth["family"], {"kind": truth["expectedClass"] if truth["role"] == "changed" else None,
                                                   "soundGo": [0, 0], "changedCorrect": [0, 0], "changedVerdicts": {"GO": 0, "GO_WITH_CHANGES": 0, "NO_GO": 0}})
        if truth["role"] == "sound":
            entry["soundGo"][1] += 1
            entry["soundGo"][0] += severity == GO
        else:
            entry["kind"] = truth["expectedClass"]
            entry["changedCorrect"][1] += 1
            entry["changedCorrect"][0] += severity == CORRECT[truth["expectedClass"]]
            entry["changedVerdicts"][("GO", "GO_WITH_CHANGES", "NO_GO")[severity]] += 1
    return {family: dict(entry, soundGo=ab.rate(*entry["soundGo"]), changedCorrect=ab.rate(*entry["changedCorrect"])) for family, entry in sorted(table.items())}


def arm_block(name, trials, oracle, corpus, rubric, excluded):
    obs = observations(trials, oracle, excluded)
    trials = {t: [r for r in rows if oracle[r["case"]]["family"] not in excluded] for t, rows in trials.items()}
    severity = {key: value[0] for key, value in obs.items()}
    units = unit_sets(obs, oracle)
    ordinal = ab.ordinal_units(severity, oracle, set())
    strict = ab.strict_units(severity, oracle, set())
    sound = [s for (c, _), (s, _) in obs.items() if oracle[c]["role"] == "sound"]
    gap = [(c, t, s, r) for (c, t), (s, r) in obs.items() if oracle[c]["role"] == "changed" and oracle[c]["expectedClass"] == "UNCERTAIN"]
    gap_go = [(c, t, r) for c, t, s, r in gap if s == GO]
    named = sum(matches(report_text(r), rubric[oracle[c]["family"]]) for c, t, r in gap_go)
    named_any = sum(matches(report_text(r), rubric[oracle[c]["family"]]) for c, t, s, r in gap)
    stops, total = {}, 0
    for rows in trials.values():
        for row in rows:
            total += 1
            if row.get("technicalStop"):
                code = row["technicalStop"].split(":")[0]
                stops[code] = stops.get(code, 0) + 1
    runs = {row.get("runManifestSha256") for rows in trials.values() for row in rows}
    by_case = {}
    for (case, trial), (s, _) in obs.items():
        by_case.setdefault(case, {})[trial] = s
    pairs = [v for v in by_case.values() if len(v) >= 2]
    first = ab.rate(sum(1 for v in pairs if len(set(v.values())) == 1), len(pairs))
    return {
        "arm": name, "observations": total, "technicalStops": stops,
        "stamps": sorted({(str(r.get("requestedModel")), str(r.get("effort")), str(r.get("claudeVersion"))) for rows in trials.values() for r in rows}),
        "servedModels": sorted({m for rows in trials.values() for r in rows for m in r.get("servedModels", [])}),
        "runManifestSha256": sorted(map(str, runs)),
        "costUsd": round(sum((r.get("costUsd") or 0) for rows in trials.values() for r in rows), 4),
        "primary": {
            "soundPlansGo": ab.rate(sum(units["soundGo"].values()), len(units["soundGo"])),
            "defectTwinsNoGo": ab.rate(sum(units["defectNoGo"].values()), len(units["defectNoGo"])),
            "evidenceGapTwinsGoWithChanges": ab.rate(sum(units["gapGwc"].values()), len(units["gapGwc"])),
        },
        "summary": {"strictPairDiscrimination": ab.rate(sum(strict.values()), len(strict)),
                    "orderedPairDiscrimination": ab.rate(sum(ordinal.values()), len(ordinal))},
        "secondary": {
            "soundPlansBlocked": ab.rate(sum(1 for s in sound if s == NOGO), len(sound)),
            "soundPlansHedged": ab.rate(sum(1 for s in sound if s == GWC), len(sound)),
            "evidenceGapTwinsNoGo": ab.rate(sum(1 for _, _, s, _ in gap if s == NOGO), len(gap)),
            "evidenceGapTwinsGo": ab.rate(len(gap_go), len(gap)),
            "gapNamedButDismissed": ab.rate(named, len(gap_go)),
            "gapNamedAmongAllEvidenceGapTwins": ab.rate(named_any, len(gap)),
            "verdictFollowsFinding": ab.verdict_follows_finding(trials, oracle, rubric, severity),
            "verdictIdenticalAcrossTrials": first,
            "snapshotLabelRead": sum(1 for rows in trials.values() for r in rows if r.get("snapshotLabelRead")),
        },
        "perFamily": per_family(obs, oracle),
    }, units, strict, ordinal


COMPARISONS = (("soundGo", "soundPlansGo"), ("defectNoGo", "defectTwinsNoGo"), ("gapGwc", "evidenceGapTwinsGoWithChanges"))


def compare(names, units, strict, ordinal):
    out = {}
    for first, second in itertools.combinations(names, 2):
        block = {key: {"first": first, "second": second, **ab.paired(units[first][key], units[second][key])} for key, _ in COMPARISONS}
        block["strict"] = {"first": first, "second": second, **ab.paired(strict[first], strict[second])}
        block["ordered"] = {"first": first, "second": second, **ab.paired(ordinal[first], ordinal[second])}
        out[f"{first}__{second}"] = block
    return out


def direction(paired, higher_is_better_second=True):
    """'second', 'first' or None: which arm the matched units favour, at p < 0.05."""
    if paired["exactTwoSidedSignTestP"] >= 0.05 or paired["onlyFirst"] == paired["onlySecond"]:
        return None
    return "second" if paired["onlySecond"] > paired["onlyFirst"] else "first"


def labels(comparisons, first="defined", second="defined-go", skill="skill"):
    """The preregistered labels for the sentence arm (second) against the defined arm (first); None when an arm is absent."""
    key = f"{first}__{second}"
    if key not in comparisons:
        return None
    block = comparisons[key]
    gain = direction(block["soundGo"])
    cost = direction(block["gapGwc"])
    lost = block["defectNoGo"]["onlyFirst"]
    result = {
        "soundPlanGain": {"second": "replicated", "first": "reversed", None: "not replicated"}[gain],
        "evidenceGapCost": {"first": "confirmed", "second": "reversed (the sentence arm is better)", None: "not detected"}[cost],
        "defectTwins": "lost" if lost >= 3 else "held",
        "rule": "gain: sound-plan GO paired p < 0.05 favouring the sentence arm; cost: evidence-gap GO_WITH_CHANGES paired p < 0.05 favouring the defined arm; "
                "defect twins lost if 3 or more matched units were NO_GO under the defined arm and are not under the sentence arm.",
    }
    for other, tag in ((skill, "skillStyleVsSentenceArm"),):
        pair = f"{other}__{second}"
        if pair in comparisons:
            b = comparisons[pair]
            result[tag] = {"evidenceGapGoWithChanges": {"first": "skill-style better", "second": "sentence arm better", None: "no significant difference"}[direction(b["gapGwc"])],
                           "soundPlansGo": {"first": "skill-style better", "second": "sentence arm better", None: "no significant difference"}[direction(b["soundGo"])]}
    return result


def analyze(corpus, arms, rubric, excluded=(), adjudication=None):
    corpus = Path(corpus)
    loaded = {name: ab.load_arm(directory) for name, directory in arms.items()}
    result = _analyze(corpus, loaded, rubric, set(excluded))
    if adjudication and adjudication.get("technicalStops"):
        reclassified = {name: {t: sc.apply_reclassification(rows, adjudication) for t, rows in trials.items()} for name, trials in loaded.items()}
        view = _analyze(corpus, reclassified, rubric, set(excluded))
        view["reclassified"] = [{k: e[k] for k in ("arm", "trial", "case", "code")} for e in adjudication["technicalStops"]]
        result["documentedRuleView"] = view
    return result


def _analyze(corpus, loaded, rubric, excluded):
    manifest, oracle = sc.load_frozen(corpus)
    names = list(loaded)
    blocks, units, strict, ordinal = {}, {}, {}, {}
    for name, trials in loaded.items():
        blocks[name], units[name], strict[name], ordinal[name] = arm_block(name, trials, oracle, corpus, rubric, excluded)
    comparisons = compare(names, units, strict, ordinal)
    return {
        "kind": "V3_RUN_ARM_COMPARISON_NOT_A_GENERAL_ACCURACY_RATE",
        "corpusManifestSha256": sc.hashlib.sha256((corpus / "manifest.json").read_bytes()).hexdigest(),
        "excludedFamilies": sorted(excluded),
        "arms": blocks,
        "comparability": {"sameModelEffortAndCliVersion": len({tuple(map(tuple, blocks[n]["stamps"])) for n in names}) == 1,
                          "note": "A mismatch means the arms differ in more than the prompt bundle."},
        "comparisons": comparisons,
        "labels": labels(comparisons),
        "providerCalls": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--rubric", required=True, help="the corpus's rubric.json (v3/rubric.json)")
    parser.add_argument("--arm", action="append", required=True, metavar="NAME=DIR")
    parser.add_argument("--exclude", action="append", default=[], help="family to exclude (repeatable); the all-pairs run is a separate call")
    parser.add_argument("--adjudication", help="adjudication JSON; its technicalStops add a documented-rule view beside the as-run one")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        arms = dict(item.split("=", 1) for item in args.arm)
        sc.require(len(arms) >= 1, "AT_LEAST_ONE_ARM_REQUIRED")
        rubric = json.loads(Path(args.rubric).read_bytes())["families"]
        adjudication = json.loads(Path(args.adjudication).read_text(encoding="utf-8")) if args.adjudication else None
        result = analyze(args.corpus, arms, rubric, args.exclude, adjudication)
    except (sc.Invalid, OSError, ValueError, KeyError) as error:
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
