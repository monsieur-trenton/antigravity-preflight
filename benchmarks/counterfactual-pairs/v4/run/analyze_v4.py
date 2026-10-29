"""Analyse a v4 run directory as the preregistration fixes it; no model calls. Needs the full corpus (with the oracle), so it runs where the sealed text lives.

Per (route, arm): the v4 scorer (score_v4.score) on each trial's own completed blocks, with the number of blocks and cases that is. Comparisons use only blocks
completed in both arms compared, matched units and an exact two-sided sign test, no correction:
  within a route (skill-go against skill; skill against bare): units are (case, trial) present in both arms
  across routes (Claude against Gemini): trial 1 of the Claude arm against Gemini's only trial, units are cases
Every verdict-based metric uses one definition for every arm: a defect twin is right at `NO_GO`, a gap twin at `GO_WITH_CHANGES`, a sound plan at `GO`; a strict pair is a sound plan
`GO` and its twin right. Subgroup tables (omitted against absorbed gap twins; cross-source against single-source defect twins) are rates with Wilson intervals, not tests.
The headline is the all-pairs result; an adjudication file (written before any metric) can only add the `adjusted` view the scorer produces.

Usage: analyze_v4.py --corpus DIR --run-manifest FILE --workdir DIR [--adjudication FILE] [--judgments FILE] [--include-optional] [OUTPUT_JSON]
"""
import argparse
from math import comb
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rv = load("v4an_run_v4", HERE / "run_v4.py")
sv = load("v4an_score_v4", V4 / "score_v4.py")
rp = rv.rp
SEVERE = {"DEFECT": 2, "UNCERTAIN": 1}
METRICS = ("soundGo", "defectNoGo", "gapGoWithChanges", "gapNoGo", "gapGo")
COMPARISONS = [
    {"id": "H4", "a": ("claude", "skill-go"), "b": ("claude", "skill"), "metrics": ("soundGo", "gapGoWithChanges", "gapNoGo", "defectNoGo"), "units": "case-trial",
     "note": "the optional-suggestions sentence against the same prompt without it"},
    {"id": "H3", "a": ("claude", "skill"), "b": ("gemini", "skill"), "metrics": ("gapNoGo", "gapGoWithChanges"), "units": "case-trial1",
     "note": "Claude trial 1 against Gemini, gap twins overclaimed"},
    {"id": "H5", "a": ("gemini", "skill"), "b": ("gemini", "bare"), "metrics": ("strictPair", "soundGo", "gapGoWithChanges", "defectNoGo"), "units": "case-trial",
     "note": "skill-style against bare, inside the runtime's fixed persona"},
    {"id": "H6", "a": ("claude", "skill"), "b": ("gemini", "skill"), "metrics": ("strictPair", "soundGo", "defectNoGo"), "units": "case-trial1",
     "note": "not interpretable alone: the auditor's filter is a competing explanation"},
]


def sign_test(a_only, b_only):
    """Exact two-sided sign test on the discordant units."""
    n = a_only + b_only
    if n == 0:
        return 1.0
    tail = sum(comb(n, k) for k in range(0, min(a_only, b_only) + 1)) / 2 ** n
    return min(1.0, 2 * tail)


def read_ledgers(work, route):
    out = {}
    for ledger in sorted(work.glob(f"responses-{route}-*-trial*.jsonl")):
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()]
        for row in rows:
            out.setdefault((route, row["arm"], row["trial"]), {})[row["case"]] = row
    return out


def complete_blocks(rows_by_key, schedule, route, arm, trial):
    done = rows_by_key.get((route, arm, trial), {})
    return {b["id"] for b in schedule["blocks"] if all(c in done for c in b["cases"])}


def derived(row, truth):
    """Verdict-based labels of one observation, or None for a stop."""
    if row.get("technicalStop"):
        return None
    severity = sv.RANK[row["assessment"]]
    role, expected = truth["role"], truth["expectedClass"]
    return {"severity": severity, "soundGo": severity == 0 if role == "sound" else None,
            "defectNoGo": severity == 2 if expected == "DEFECT" else None,
            "gapGoWithChanges": severity == 1 if expected == "UNCERTAIN" else None,
            "gapNoGo": severity == 2 if expected == "UNCERTAIN" else None,
            "gapGo": severity == 0 if expected == "UNCERTAIN" else None}


def strict_pairs(rows, oracle):
    """{(pair, wording): bool} for pair-wordings with both members observed."""
    seen = {}
    for case, row in rows.items():
        label = derived(row, oracle[case])
        if label:
            truth = oracle[case]
            seen.setdefault((truth["pair"], truth["wording"]), {})[truth["role"]] = (label["severity"], truth["expectedClass"])
    return {k: v["sound"][0] == 0 and v["changed"][0] == SEVERE[v["changed"][1]] for k, v in seen.items() if "sound" in v and "changed" in v}


def unit_values(rows_by_key, oracle, key, metric, blocks, schedule, trials):
    """{unit: bool} for one arm: the metric's observations in the given blocks and trials."""
    cases = {c for b in schedule["blocks"] if b["id"] in blocks for c in b["cases"]}
    out = {}
    for trial in trials:
        rows = {c: r for c, r in rows_by_key.get(key + (trial,), {}).items() if c in cases}
        if metric == "strictPair":
            for unit, value in strict_pairs(rows, oracle).items():
                out[unit + (trial,)] = value
            continue
        for case, row in rows.items():
            label = derived(row, oracle[case])
            if label and label[metric] is not None:
                out[(case, trial)] = label[metric]
    return out


def compare(spec, rows_by_key, oracle, schedule, trials_of):
    a_key, b_key = spec["a"], spec["b"]
    blocks = None
    for key in (a_key, b_key):
        trials = [1] if spec["units"] == "case-trial1" else trials_of(key)
        have = set.intersection(*[complete_blocks(rows_by_key, schedule, key[0], key[1], t) for t in trials]) if trials else set()
        blocks = have if blocks is None else blocks & have
    cross = spec["units"] == "case-trial1"
    result = {"id": spec["id"], "a": "/".join(a_key), "b": "/".join(b_key), "note": spec["note"], "blocksUsed": len(blocks), "metrics": {}}
    for metric in spec["metrics"]:
        a_trials = (1,) if cross else sorted(set(trials_of(a_key)) & set(trials_of(b_key)))
        b_trials = (1,) if cross else a_trials
        a_vals = unit_values(rows_by_key, oracle, a_key, metric, blocks, schedule, a_trials)
        b_vals = unit_values(rows_by_key, oracle, b_key, metric, blocks, schedule, b_trials)
        matched = sorted(set(a_vals) & set(b_vals)) if not cross else sorted({u[:-1] for u in a_vals} & {u[:-1] for u in b_vals})
        a_ok = lambda u: a_vals[u] if u in a_vals else a_vals[u + (1,)]
        b_ok = lambda u: b_vals[u] if u in b_vals else b_vals[u + (1,)]
        a_only = sum(1 for u in matched if a_ok(u) and not b_ok(u))
        b_only = sum(1 for u in matched if b_ok(u) and not a_ok(u))
        result["metrics"][metric] = {"matchedUnits": len(matched), "aTrue": sum(1 for u in matched if a_ok(u)), "bTrue": sum(1 for u in matched if b_ok(u)),
                                     "aOnly": a_only, "bOnly": b_only, "exactSignTestP": round(sign_test(a_only, b_only), 4)}
    return result


def subgroup_tables(rows_by_key, oracle, schedule):
    """H1 and H2 as rates: for each arm's first trial, over blocks complete in that arm's steps."""
    out = {}
    for (route, arm, trial), rows in sorted(rows_by_key.items()):
        if trial != 1:
            continue
        blocks = complete_blocks(rows_by_key, schedule, route, arm, 1)
        cases = {c for b in schedule["blocks"] if b["id"] in blocks for c in b["cases"]}
        groups = {"gapOmittedUnknown": [0, 0], "gapAbsorbed": [0, 0], "defectCrossSource": [0, 0], "defectSingleSource": [0, 0], "defectDecoy": [0, 0]}
        for case, row in rows.items():
            if case not in cases:
                continue
            label, truth = derived(row, oracle[case]), oracle[case]
            if not label or truth["role"] != "changed":
                continue
            if truth["expectedClass"] == "UNCERTAIN":
                name, hit = ("gapOmittedUnknown" if truth["kind"] == "omitted_unknown" else "gapAbsorbed"), label["gapGoWithChanges"]
            else:
                name = {"cross_source_defect": "defectCrossSource", "decoy_pair": "defectDecoy"}.get(truth["kind"], "defectSingleSource")
                hit = label["defectNoGo"]
            groups[name][0] += bool(hit)
            groups[name][1] += 1
        out[f"{route}/{arm}"] = {k: sv.rate(v[0], v[1]) for k, v in groups.items()}
    return out


def analyze(corpus_dir, run_manifest, workdir, adjudication=None, judgments=None, include_optional=False):
    work = Path(workdir)
    run = rv.load_run_manifest(run_manifest)
    corpus = sv.Corpus(corpus_dir)
    rp.need(rv.sha((Path(corpus_dir) / "manifest.json").read_bytes()) == run["corpus"]["manifestSha256"], "RUN_CORPUS_MISMATCH")
    schedule = rv.load_schedule(HERE / f"schedule-{run['split']}.json", run, corpus.manifest)
    oracle = corpus.oracle
    rows_by_key = {}
    for route in rv.ARMS:
        rows_by_key.update(read_ledgers(work, route))
    main_trials = {(route, arm): sorted({t for r, a, t in rows_by_key if (r, a) == (route, arm)}) for route, arm, _ in rows_by_key}

    def trials_of(key):
        return main_trials.get(key, [])

    arms = {}
    for (route, arm), trials in sorted(main_trials.items()):
        used = {t: complete_blocks(rows_by_key, schedule, route, arm, t) for t in trials}  # each trial on its own completed blocks
        cases = {t: {c for b in schedule["blocks"] if b["id"] in used[t] for c in b["cases"]} for t in trials}
        rows = [dict(r, trial=t) for t in trials for c, r in sorted(rows_by_key[(route, arm, t)].items()) if c in cases[t]]
        entry = {"blocksComplete": {str(t): len(used[t]) for t in trials}, "blocksTotal": len(schedule["blocks"]), "casesScored": {str(t): len(cases[t]) for t in trials},
                 "casesInCorpus": corpus.manifest["cases"]}
        if rows:
            mine = [j for j in (judgments or []) if j.get("route", route) == route and j["arm"] == arm]
            entry["score"] = sv.score(rows, corpus, adjudication, mine)
        arms[f"{route}/{arm}"] = entry
    comparisons = [compare(spec, rows_by_key, oracle, schedule, trials_of) for spec in COMPARISONS
                   if all(k in main_trials for k in (spec["a"], spec["b"]))]
    return {"kind": "V4_RUN_ANALYSIS_NOT_A_GENERAL_ACCURACY_RATE", "runManifestSha256": run["sha256"], "corpusManifestSha256": run["corpus"]["manifestSha256"],
            "arms": arms, "comparisons": comparisons, "subgroups": subgroup_tables(rows_by_key, oracle, schedule), "providerCalls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--run-manifest", required=True)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--adjudication")
    parser.add_argument("--judgments")
    parser.add_argument("--include-optional", action="store_true")
    parser.add_argument("output", nargs="?")
    args = parser.parse_args(argv)
    try:
        adjudication = json.loads(Path(args.adjudication).read_text(encoding="utf-8")) if args.adjudication else None
        judgments = json.loads(Path(args.judgments).read_text(encoding="utf-8")) if args.judgments else None
        result = analyze(args.corpus, args.run_manifest, args.workdir, adjudication, judgments, args.include_optional)
    except (rp.Stop, sv.Invalid, OSError, ValueError, KeyError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, (rp.Stop, sv.Invalid)) else type(error).__name__}))
        return 1
    text = json.dumps(result, indent=1) + "\n"
    if args.output:
        Path(args.output).write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
