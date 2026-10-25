"""Build the frozen v3 counterfactual-pair corpus from families.json; no model or provider calls.

Sixteen families (eight whose twin is a defect, eight whose twin leaves one decisive fact unestablished), each a sound plan
and a changed twin differing in exactly one line, in two equivalent wordings (A and B): 64 cases. Differences from v2 are
in PREREGISTRATION.md. The family texts in families.json were written by four independent model authors from a
construction specification (see audit/README.md); this script only validates and assembles them.
Reviewer-visible packets carry random identifiers and no labels. The oracle lives in oracle/ and must never be sent to a reviewer.

Usage: build_corpus.py [--check]
"""
import hashlib
import json
from pathlib import Path
import random
import re
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
SEED = 20261023
SOUND, DEFECT, UNCERTAIN = "SOUND", "DEFECT", "UNCERTAIN"
PREREGISTRATION = "PREREGISTRATION.md"
SOURCES = (PREREGISTRATION, "families.json", "rubric.json", "audit/README.md", "audit/author-brief.txt", "audit/judgments.json", "audit/classification.json")
FORBIDDEN = ("defect", "bug", "flaw", "sound", "uncertain", "blocker", "evidence", "unverified", "verified", "test case",
             "counterfactual", "reviewer", "review", "oracle", "distractor")
MIN_LINES, MAX_LINES, MAX_LENGTH = 5, 8, 260
DIFFICULTY = {DEFECT: ("direct", "inference"), UNCERTAIN: ("evidence_gap",)}

PROMPT = (HERE.parent / "prompt.txt").read_text(encoding="utf-8")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def load_families():
    data = json.loads((HERE / "families.json").read_bytes())
    return {f["family"]: f for f in data["families"]}


FAMILIES = load_families()


def plan_lines(family, wording, role):
    spec = FAMILIES[family][wording]
    lines = list(spec["sound"])
    if role == "twin":
        for number, text in spec["twin"].items():
            lines[int(number) - 1] = text
    return lines


def problems(families=None):
    """Structural problems in the authored families; empty when the corpus may be built."""
    found = []
    for name, spec in (families or FAMILIES).items():
        kind = spec["twin"]
        if kind not in DIFFICULTY or spec["difficulty"] not in DIFFICULTY[kind]:
            found.append(f"{name}: kind/difficulty {kind}/{spec['difficulty']}")
        sizes = {w: len(spec[w]["sound"]) for w in "AB"}
        if sizes["A"] != sizes["B"] or not MIN_LINES <= sizes["A"] <= MAX_LINES:
            found.append(f"{name}: line counts {sizes}")
            continue
        n = sizes["A"]
        if not (1 <= spec["line"] <= n and spec["line"] in spec["cite"] and all(1 <= c <= n for c in spec["cite"])):
            found.append(f"{name}: line/cite out of range")
        for w in "AB":
            twin = spec[w]["twin"]
            if list(twin) != [str(spec["line"])]:
                found.append(f"{name}/{w}: twin must replace exactly line {spec['line']}")
            elif twin[str(spec["line"])] == spec[w]["sound"][spec["line"] - 1]:
                found.append(f"{name}/{w}: twin line equals sound line")
            for text in spec[w]["sound"] + list(twin.values()):
                low = text.lower()
                if "\n" in text or len(text) > MAX_LENGTH or not text.strip():
                    found.append(f"{name}/{w}: bad line {text[:40]!r}")
                for word in FORBIDDEN:
                    if re.search(r"\b" + re.escape(word), low):
                        found.append(f"{name}/{w}: forbidden word {word!r}")
        for i in range(n):
            nums = [sorted(re.findall(r"\d[\d,.]*\d|\d", (spec[w]["twin"].get(str(i + 1)) or spec[w]["sound"][i]))) for w in "AB"]
            sound = [sorted(re.findall(r"\d[\d,.]*\d|\d", spec[w]["sound"][i])) for w in "AB"]
            if sound[0] != sound[1] or nums[0] != nums[1]:
                found.append(f"{name}: numbers differ between wordings on line {i + 1}")
        if spec["A"]["sound"] == spec["B"]["sound"]:
            found.append(f"{name}: wordings identical")
    return found


def cases_and_packets():
    """Case records and reviewer-visible packets, deterministic from the seed; needs no frozen source files."""
    bad = problems()
    if bad:
        raise SystemExit("INVALID_FAMILIES:" + "; ".join(bad))
    rng = random.Random(SEED)
    used = set()

    def new_id():
        while True:
            value = "Q-" + "".join(rng.choice("0123456789abcdef") for _ in range(6))
            if value not in used:
                used.add(value)
                return value

    packets, cases = {}, []
    for family, spec in FAMILIES.items():
        for wording in ("A", "B"):
            for role in ("sound", "twin"):
                case = new_id()
                packets["packets/" + case + ".txt"] = ("\n".join(plan_lines(family, wording, role)) + "\n").encode("utf-8")
                cases.append({
                    "case": case, "family": family, "wording": wording,
                    "role": "sound" if role == "sound" else "changed",
                    "expectedClass": SOUND if role == "sound" else spec["twin"],
                    "difficulty": spec["difficulty"], "decisiveLine": spec["line"], "citeAnyOf": spec["cite"],
                    "mechanism": None if role == "sound" else spec["mechanism"],
                })
    cases.sort(key=lambda c: (c["family"], c["wording"], c["role"]))
    order = [c["case"] for c in cases]
    rng.shuffle(order)
    return cases, packets, order


def build():
    cases, files, order = cases_and_packets()
    oracle = {"kind": "COUNTERFACTUAL_ORACLE_NEVER_SEND_TO_REVIEWER", "corpus": "v3", "seed": SEED, "cases": cases}
    files["oracle/oracle.json"] = (json.dumps(oracle, indent=2) + "\n").encode("utf-8")
    files["prompt.txt"] = PROMPT.encode("utf-8")
    for name in SOURCES:
        files[name] = (HERE / name).read_bytes()
    manifest = {
        "kind": "COUNTERFACTUAL_PAIR_CORPUS_V3_FROZEN",
        "cases": len(cases), "families": len(FAMILIES), "submissionOrder": order,
        "reviewerVisible": sorted(n for n in files if n.startswith("packets/")) + ["prompt.txt"],
        "pins": {name: sha(data) for name, data in sorted(files.items())},
        "providerCalls": 0,
    }
    files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
    return files


def main(argv):
    files = build()
    generated = {n: d for n, d in files.items() if n not in SOURCES}
    if "--check" in argv:
        stale = [n for n, data in generated.items() if not (HERE / n).is_file() or (HERE / n).read_bytes() != data]
        extra = sorted(p.name for p in (HERE / "packets").glob("*") if "packets/" + p.name not in files) \
            if (HERE / "packets").is_dir() else []
        if stale or extra:
            print(json.dumps({"status": "STALE_CORPUS", "files": stale, "unexpected": extra}))
            return 1
    else:
        for name, data in generated.items():
            path = HERE / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
    print(json.dumps({"status": "PASS", "cases": len(FAMILIES) * 4, "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
