"""Read the answers of the blind audit against the oracle, draw the owner's spot-check sample and score the owner's answers; no model calls.

`report` joins the audit ledger (audit.py) with the corpus oracle and gives, for every pair, a decision of PASS, PASS_WITH_READ (all questions agree with the oracle but the
auditor flagged something a person should read), REVIEW (an answer disagrees with the oracle: rewrite or drop the pair) or INCOMPLETE (a call has no clean answer). It never
drops anything: the drop list is a person's decision, written to a file that build_corpus.py reads.

`spot` writes the unlabelled members of a stratified sample of at least one fifth of the pairs, one file per pair with the two members in a seed-determined order and the
questions for the owner; `spot-score` compares the owner's answers with the oracle.

Usage: audit_report.py report --corpus DIR --answers FILE [--out FILE]
       audit_report.py spot --corpus DIR --out DIR
       audit_report.py spot-score --corpus DIR --index FILE --answers FILE
"""
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_prompts  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s4 = load("audit_report_score_v4", HERE.parent / "score_v4.py")
EXPECTED = {"SOUND": "SOUND", "DEFECT": "HAS_A_DEFECT", "UNCERTAIN": "HAS_AN_UNESTABLISHED_FACT"}
GAP_KINDS = ("omitted_unknown", "decoy_pair")
SPOT_FRACTION = 0.2


def rate(k, n):
    return s4.rate(k, n)


def read_ledger(path):
    """The rows of a ledger by call id; `path` may name several ledgers, comma-separated, and a call in a later one replaces the same call in an earlier one (a re-audit)."""
    rows = {}
    for one in str(path).split(","):
        for line in Path(one).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["call"]] = row
    return rows


def clean(row):
    return row is not None and not row.get("technicalStop") and "answer" in row


def pairs_of(corpus):
    pairs = {}
    for case, record in corpus.oracle.items():
        if record["wording"] == "A":
            pairs.setdefault(record["pair"], {})[record["role"]] = case
    return pairs


def analyse(corpus, rows):
    seed = corpus.manifest["authoring"]["seedSha256"]
    oracle = corpus.oracle
    per_pair, member_total, member_right = {}, 0, 0
    by_kind = {}
    reads = []
    for pair, cases in sorted(pairs_of(corpus).items()):
        sound, twin = cases["sound"], cases["changed"]
        kind = oracle[twin]["kind"]
        reasons, flags, incomplete = [], [], []
        answers = {"sound": rows.get(f"member:{sound}"), "twin": rows.get(f"member:{twin}"), "pair": rows.get(f"pair:{pair}"), "claim": rows.get(f"claim:{twin}")}
        needed = ["sound", "twin", "pair"] + (["claim"] if kind in GAP_KINDS and oracle[twin]["changed"]["type"] == "deleted" else [])
        for name in needed:
            if not clean(answers[name]):
                incomplete.append(name)
        if "sound" not in incomplete:
            member_total += 1
            if answers["sound"]["answer"]["CLASS"] == "SOUND":
                member_right += 1
            else:
                reasons.append("SOUND_MEMBER_NOT_RECOVERED:" + answers["sound"]["answer"]["CLASS"])
        if "twin" not in incomplete:
            member_total += 1
            if answers["twin"]["answer"]["CLASS"] == EXPECTED[oracle[twin]["expectedClass"]]:
                member_right += 1
            else:
                reasons.append("TWIN_NOT_RECOVERED:" + answers["twin"]["answer"]["CLASS"])
        for name in ("sound", "twin"):
            if name not in incomplete:
                a = answers[name]["answer"]
                if a["OTHER_PROBLEMS"]:
                    flags.append(f"{name.upper()}_OTHER_PROBLEMS:" + ",".join(a["OTHER_PROBLEMS"]))
                if a["REQUIREMENT_DECIDES"] == "NO":
                    flags.append(f"{name.upper()}_REQUIREMENT_DOES_NOT_DECIDE")
        if "pair" not in incomplete:
            a = answers["pair"]["answer"]
            twin_label = "Y" if audit_prompts.x_is_sound(seed, pair) else "X"
            if a["NEEDS_CHANGE"] != twin_label:
                reasons.append("PAIR_CHOICE:" + a["NEEDS_CHANGE"])
            if a["ONE_EDIT"] != "YES":
                reasons.append("NOT_ONE_EDIT")
        if "claim" in needed and "claim" not in incomplete:
            a = answers["claim"]["answer"]
            if a["CLAIM_HOLDS"] != "YES":
                reasons.append("CLAIM_CONTRADICTED:" + ",".join(a["CONTRADICTING_LINES"]))
        decision = "INCOMPLETE" if incomplete else "REVIEW" if reasons else "PASS_WITH_READ" if flags else "PASS"
        per_pair[pair] = {"kind": kind, "family": oracle[twin]["family"], "decision": decision, "reasons": reasons, "flags": flags, "incompleteCalls": incomplete}
        by_kind.setdefault(kind, []).append(decision)
        if flags or reasons:
            reads.append(pair)
    decisions = [p["decision"] for p in per_pair.values()]
    complete = [d for d in decisions if d != "INCOMPLETE"]
    return {"kind": "V4_BLIND_AUDIT_REPORT", "pairs": len(per_pair), "memberClassRecovered": rate(member_right, member_total),
            "firstPassAgreement": rate(sum(1 for d in complete if d in ("PASS", "PASS_WITH_READ")), len(complete)),
            "decisions": {d: decisions.count(d) for d in ("PASS", "PASS_WITH_READ", "REVIEW", "INCOMPLETE")},
            "byKind": {k: {d: v.count(d) for d in sorted(set(v))} for k, v in sorted(by_kind.items())},
            "needsAPersonsRead": sorted(reads), "perPair": per_pair, "providerCalls": 0,
            "note": "A decision of REVIEW means the auditor disagreed with the oracle; the pair is rewritten or dropped by a person, and a drop is recorded with its reason."}


def spot_sample(corpus, fraction=SPOT_FRACTION):
    """At least `fraction` of the pairs, stratified by kind (at least one per kind), chosen by a seed-determined hash order."""
    seed = corpus.manifest["authoring"]["seedSha256"]
    by_kind = {}
    for pair, cases in pairs_of(corpus).items():
        by_kind.setdefault(corpus.oracle[cases["changed"]]["kind"], []).append(pair)
    chosen = []
    for kind, pairs in sorted(by_kind.items()):
        ordered = sorted(pairs, key=lambda p: hashlib.sha256(f"{seed}|spot|{p}".encode()).hexdigest())
        chosen += ordered[:max(1, math.ceil(len(pairs) * fraction))]
    return sorted(chosen, key=lambda p: hashlib.sha256(f"{seed}|spot-order|{p}".encode()).hexdigest())


SPOT_QUESTIONS = """QUESTIONS FOR THE OWNER (answer in spot-answers.json under this file's number)
needsChange: "X", "Y", "BOTH" or "NEITHER", the plan that cannot be carried out as written, or neither
problem: for the plan you named, "DEFECT" if its text contradicts itself or the reference (a line, or a number, breaks what another line says), or "UNESTABLISHED" if nothing is contradicted but a fact that the plan's own requirement needs is not established anywhere in the text; "NONE" if you named neither
why: one sentence
oneEdit: true if one plan is the other with exactly one edit (one line edited in place, or one to three lines deleted) and nothing else, otherwise false
otherProblems: lines, if any, that are unknown or contradictory for some other reason
"""


def write_spot(corpus, out_dir):
    seed = corpus.manifest["authoring"]["seedSha256"]
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=False)
    index = {}
    for number, pair in enumerate(spot_sample(corpus), 1):
        cases = pairs_of(corpus)[pair]
        sources_of = lambda case: {r["id"]: corpus.lines(case, r["id"]) for r in corpus.oracle[case]["sources"]}
        text = audit_prompts.template("pair-request.txt").split("End your answer")[0]
        x_sound = int(hashlib.sha256(f"{seed}|spot-xy|{pair}".encode()).hexdigest()[:8], 16) % 2 == 0
        x, y = (cases["sound"], cases["changed"]) if x_sound else (cases["changed"], cases["sound"])
        body = text.replace("{X}", audit_prompts.numbered(sources_of(x))).replace("{Y}", audit_prompts.numbered(sources_of(y)))
        (out / f"{number:02d}.txt").write_text(body.rstrip() + "\n\n" + SPOT_QUESTIONS, encoding="utf-8")
        index[f"{number:02d}"] = {"pair": pair, "twin": "Y" if x_sound else "X", "twinClass": corpus.oracle[cases["changed"]]["expectedClass"]}
    (out / "spot-index.json").write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    return index


PROBLEM = {"DEFECT": "DEFECT", "UNCERTAIN": "UNESTABLISHED"}


def score_spot(index, answers):
    right_choice = one_edit = right_problem = total = 0
    disagree = []
    for number, key in sorted(index.items()):
        a = answers.get(number)
        if a is None:
            continue
        total += 1
        ok_choice = a.get("needsChange") == key["twin"]
        ok_edit = a.get("oneEdit") is True
        ok_problem = ok_choice and a.get("problem") == PROBLEM[key["twinClass"]]
        right_choice += ok_choice
        one_edit += ok_edit
        right_problem += ok_problem
        if not (ok_choice and ok_edit and ok_problem):
            disagree.append({"file": number, "pair": key["pair"], "needsChange": a.get("needsChange"), "oneEdit": a.get("oneEdit"), "problem": a.get("problem"),
                             "oracleProblem": PROBLEM[key["twinClass"]]})
    return {"kind": "V4_OWNER_SPOT_CHECK", "sampled": len(index), "answered": total, "needsChangeMatchesOracle": rate(right_choice, total), "oneEditConfirmed": rate(one_edit, total),
            "problemKindMatchesOracle": rate(right_problem, total), "disagreements": disagree, "clean": total == len(index) and not disagree}


def main(argv):
    if not argv or argv[0] not in ("report", "spot", "spot-score"):
        print("usage: audit_report.py report|spot|spot-score ...", file=sys.stderr)
        return 2
    opts = dict(zip(argv[1::2], argv[2::2]))
    try:
        corpus = s4.Corpus(Path(opts["--corpus"]).resolve())
        if argv[0] == "report":
            result = analyse(corpus, read_ledger(opts["--answers"]))
            text = json.dumps(result, indent=1) + "\n"
            if "--out" in opts:
                Path(opts["--out"]).write_text(text, encoding="utf-8")
            else:
                print(text, end="")
        elif argv[0] == "spot":
            index = write_spot(corpus, opts["--out"])
            print(json.dumps({"status": "WRITTEN", "files": len(index), "pairs": len(pairs_of(corpus))}))
        else:
            result = score_spot(json.loads(Path(opts["--index"]).read_text(encoding="utf-8")), json.loads(Path(opts["--answers"]).read_text(encoding="utf-8")))
            print(json.dumps(result, indent=1))
    except (KeyError, OSError, ValueError, s4.Invalid) as error:
        print(json.dumps({"status": "STOPPED", "reason": type(error).__name__ + ":" + str(error)[:80]}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
