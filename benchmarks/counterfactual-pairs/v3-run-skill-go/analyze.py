"""Analyse the skill-go run as PREREGISTRATION.md fixes it: the v3 analysis of every arm given, plus the preregistered labels for skill-go; no model calls.

Each arm directory holds trial1/, trial2/, ..., each with responses.jsonl and reports/<case>.md, as in v3-run/analyze.py, which this wraps.
The arms `skill-go` and `skill` are required (`skill` is the concurrent control, or the earlier v3 ledgers when no control was run); `defined-go`
and any other arm may be added.

Usage: analyze.py --corpus DIR --rubric FILE --arm skill-go=DIR --arm skill=DIR [--arm defined-go=DIR ...] [--exclude FAMILY ...] [--adjudication FILE] [--out FILE]
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
BASE = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


an = load("skill_go_v3_analyze", BASE / "v3-run" / "analyze.py")
ab, sc = an.ab, an.sc
NOGO, GWC, GO = an.NOGO, an.GWC, an.GO


def oriented(comparisons, first, second):
    """The paired block for (first, second), swapped if the analysis stored it the other way round."""
    if f"{first}__{second}" in comparisons:
        return comparisons[f"{first}__{second}"]
    swapped = comparisons[f"{second}__{first}"]
    return {key: dict(block, first=block["second"], second=block["first"], onlyFirst=block["onlySecond"], onlySecond=block["onlyFirst"])
            for key, block in swapped.items()}


def gap_nogo_units(obs, oracle):
    return {(case, trial): severity == NOGO for (case, trial), (severity, _) in obs.items()
            if oracle[case]["role"] == "changed" and oracle[case]["expectedClass"] == "UNCERTAIN"}


def labels(comparisons, overclaim, waved, arm="skill-go", primary="skill", other="defined-go"):
    """The preregistered labels for `arm` against `primary` (first = primary, second = arm); None when either arm is absent."""
    if f"{primary}__{arm}" not in comparisons and f"{arm}__{primary}" not in comparisons:
        return None
    block = oriented(comparisons, primary, arm)
    hedging = an.direction(block["soundGo"])
    gap = an.direction(block["gapGwc"])
    over = overclaim
    over_direction = None if over["exactTwoSidedSignTestP"] >= 0.05 or over["onlyFirst"] == over["onlySecond"] else ("second" if over["onlySecond"] > over["onlyFirst"] else "first")
    result = {
        "soundPlanHedging": {"second": "reduced", "first": "increased", None: "not detected"}[hedging],
        "defectTwins": "lost" if block["defectNoGo"]["onlyFirst"] >= 3 else "held",
        "evidenceGapGoWithChanges": {"second": f"{arm} better", "first": f"{primary} better", None: "no significant difference"}[gap],
        "wavedThrough": "waves gaps through" if waved >= 3 else "does not wave gaps through",
        # over = units judged NO_GO: more under `primary` and fewer under `arm` is a reduction, so 'first' (primary has more) means reduced
        "overclaiming": {"first": "reduced", "second": "increased", None: "not detected"}[over_direction],
        "rule": "hedging: sound-plan GO paired p < 0.05 for or against the added sentence; defect twins lost if 3 or more matched units were NO_GO under the primary arm "
                "and are not under skill-go; evidence-gap GO_WITH_CHANGES paired p < 0.05; waved through if skill-go judged 3 or more evidence-gap twins GO; "
                "overclaiming: evidence-gap twins judged NO_GO, paired p < 0.05.",
    }
    if f"{other}__{arm}" in comparisons or f"{arm}__{other}" in comparisons:
        b = oriented(comparisons, other, arm)
        word = {"first": f"{other} better", "second": f"{arm} better", None: "no significant difference"}
        result[f"against{other}"] = {"evidenceGapGoWithChanges": word[an.direction(b["gapGwc"])], "soundPlansGo": word[an.direction(b["soundGo"])]}
    return result


def analyze(corpus, arms, rubric, excluded=(), adjudication=None, arm="skill-go", primary="skill"):
    sc.require(arm in arms and primary in arms, "SKILL_GO_AND_SKILL_ARMS_REQUIRED")
    result = an.analyze(corpus, arms, rubric, excluded, adjudication)
    _, oracle = sc.load_frozen(Path(corpus))
    obs = {name: an.observations(ab.load_arm(directory), oracle, set(excluded)) for name, directory in arms.items()}
    overclaim = {"first": primary, "second": arm,
                 **ab.paired(gap_nogo_units(obs[primary], oracle), gap_nogo_units(obs[arm], oracle))}
    waved = result["arms"][arm]["secondary"]["evidenceGapTwinsGo"]["count"]
    result["overclaimPaired"] = overclaim
    result["labels"] = labels(result["comparisons"], overclaim, waved, arm, primary)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--rubric", required=True)
    parser.add_argument("--arm", action="append", required=True, metavar="NAME=DIR")
    parser.add_argument("--exclude", action="append", default=[])
    parser.add_argument("--adjudication")
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    try:
        arms = dict(item.split("=", 1) for item in args.arm)
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
