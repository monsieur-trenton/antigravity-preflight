"""Mechanical checks of one authored v4 pair and of its wording-B rewording; no model calls.

Reads an author's report, parses the CASE block of author-template.txt and decides, for each rule of SPEC.md that a program can decide, whether it holds against the
instance's assignment (assignments-*.json) and the family specification. It never judges realism, coherence or whether the twin is a fair test: the audit and the
owner's reading do that. Rule numbers refer to SPEC.md.

Library use: analyse(text, instance, family) -> (result, parsed or None); analyse_reword(text, parsed_a, instance) -> (result, parsed or None).
Command line: check_author.py PAIR_ID (dev|test) REPORT.md   (prints one JSON object; the exit status is 0 whether or not every check passes)
"""
from collections import Counter
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


assign = load("author_assign", HERE / "assign.py")
META_WORDS = ("twin", "sound", "benchmark", "oracle", "decisive", "counterfactual", "test case", "omitted")
ADMISSIONS = ("unknown", "unmeasured", "unconfirmed", "unverified", "pending", "tbd", "to be decided", "to be confirmed", "not yet", "not measured",
              "not been measured", "not final", "undecided", "open item", "open question")
ORACLE_KEYS = ("requirement_line", "cite_lines", "decoy_lines", "mechanism", "why_no_fallback", "bait_notes", "rubric_keywords")
LINE_CHARS = (60, 220)
LENGTH_SLACK = {"S01": 3, "S02": 2}
ABSOLUTE = {"S01": (25, 80), "S02": (8, 25)}
CALL_BYTES_MAX = 28000
REF = re.compile(r"^(S0[12]):([1-9][0-9]*)$")
PROTECTED_CHARS = set("_/\\:=@#")


def deleting(family):
    """True when the family's twin is made by deleting lines (its `twinDiffers` begins with Delete), false when by editing one in place."""
    return family["twinDiffers"].startswith("Delete")


def sources_of(instance):
    return ["S01", "S02"] if instance["kind"] == "cross_source_defect" else ["S01"]


def markers(instance, with_oracle=True):
    names = ["CASE-BEGIN"]
    for member in ("SOUND", "TWIN"):
        for source in sources_of(instance):
            names += [f"{member}-{source}-BEGIN", f"{member}-{source}-END"]
    if with_oracle:
        names += ["ORACLE-BEGIN", "ORACLE-END"]
    return names + ["CASE-END"]


def split_blocks(text, instance, with_oracle=True):
    """{(member, source): lines, "oracle": lines, "before": [...], "after": [...]} or None when the markers are not each present once and in order."""
    lines = text.replace("\r\n", "\n").split("\n")
    names = markers(instance, with_oracle)
    where = []
    for name in names:
        found = [i for i, line in enumerate(lines) if line.strip() == name]
        if len(found) != 1:
            return None
        where.append(found[0])
    if where != sorted(where):
        return None
    at = dict(zip(names, where))
    out = {}
    for member in ("SOUND", "TWIN"):
        for source in sources_of(instance):
            out[(member.lower(), source)] = lines[at[f"{member}-{source}-BEGIN"] + 1:at[f"{member}-{source}-END"]]
    if with_oracle:
        out["oracle"] = lines[at["ORACLE-BEGIN"] + 1:at["ORACLE-END"]]
    out["before"] = [line for line in lines[:at["CASE-BEGIN"]] if line.strip()]
    out["after"] = [line for line in lines[at["CASE-END"] + 1:] if line.strip()]
    return out


def parse_refs(value, allow_none=False):
    if allow_none and value.strip().lower() == "none":
        return []
    parts = [p.strip() for p in value.split(",")]
    refs = []
    for part in parts:
        match = REF.match(part)
        if not match:
            return None
        refs.append((match.group(1), int(match.group(2))))
    return refs if refs and len(set(refs)) == len(refs) else None


def parse_oracle(lines):
    fields = {}
    for line in lines:
        if not line.strip():
            continue
        name, separator, value = line.partition(":")
        if not separator or name.strip() not in ORACLE_KEYS or name.strip() in fields:
            return None
        fields[name.strip()] = value.strip()
    return fields if set(fields) == set(ORACLE_KEYS) and all(fields.values()) else None


def keyword_groups(value):
    groups = [[w.strip().lower() for w in group.split(",") if w.strip()] for group in value.split(";")]
    return groups if 1 <= len(groups) <= 3 and all(groups) else None


def edit_relation(sound, twin, family, instance):
    """(kind, changed line numbers in the sound plan) for the twin's one edit, or (None, reason). `sound` and `twin` map source to lines."""
    source = instance["changedSource"]
    for other in sources_of(instance):
        if other != source and sound[other] != twin[other]:
            return None, "OTHER_SOURCE_DIFFERS"
    s, t = sound[source], twin[source]
    if deleting(family):
        limit = 1 if family["kind"] == "decoy_pair" else 3
        gone = len(s) - len(t)
        if not 1 <= gone <= limit:
            return None, "DELETED_COUNT"
        kept, i = [], 0
        for j, line in enumerate(s, 1):
            if i < len(t) and t[i] == line:
                i += 1
            else:
                kept.append(j)
        if i != len(t) or len(kept) != gone:
            return None, "NOT_A_DELETION"
        return "deleted", kept
    if len(s) != len(t):
        return None, "LENGTH_CHANGED"
    differing = [i for i, (a, b) in enumerate(zip(s, t), 1) if a != b]
    if len(differing) != 1:
        return None, "NOT_ONE_LINE"
    return "edited", differing


def shape_problems(lines):
    return [i for i, line in enumerate(lines, 1) if not line.strip() or line != line.strip() or not LINE_CHARS[0] <= len(line) <= LINE_CHARS[1]
            or re.match(r"^(\d+[.)]|[-*•]\s|\[|#)", line)]


def admits(line):
    low = line.lower()
    return any(a in low for a in ADMISSIONS)


def analyse(text, instance, family):
    """(result, parsed): result is {"allPassed", "checks", "details"}; parsed is the case dict when the markers and the oracle block parse, else None."""
    checks, details = {}, {}
    blocks = split_blocks(text, instance)
    checks["BLOCKS_IN_ORDER"] = blocks is not None
    if blocks is None:
        return {"allPassed": False, "checks": checks, "details": {"reason": "the markers are not each present once and in order"}}, None
    checks["CALL_BYTES"] = len(text.encode("utf-8")) <= CALL_BYTES_MAX
    checks["NOTHING_OUTSIDE_THE_CASE"] = not blocks["before"] and not blocks["after"]
    sources = sources_of(instance)
    sound = {s: blocks[("sound", s)] for s in sources}
    twin = {s: blocks[("twin", s)] for s in sources}
    want = {"S01": instance["planLines"], "S02": instance["referenceLines"]}
    lengths_ok = True
    for s in sources:
        low, high = ABSOLUTE[s]
        lengths_ok &= abs(len(sound[s]) - want[s]) <= LENGTH_SLACK[s] and low <= len(sound[s]) <= high
    checks["LENGTHS_AS_ASSIGNED"] = lengths_ok
    details["soundLines"] = {s: len(sound[s]) for s in sources}
    details["twinLines"] = {s: len(twin[s]) for s in sources}
    bad = {f"{m}:{s}": shape_problems(lines)[:10] for m, group in (("sound", sound), ("twin", twin)) for s, lines in group.items() if shape_problems(lines)}
    checks["LINE_SHAPE"] = not bad
    details["badShapeLines"] = bad
    checks["NO_DUPLICATE_LINES"] = all(len(set(lines)) == len(lines) for lines in sound.values())
    kind, changed = edit_relation(sound, twin, family, instance)
    checks["ONE_EDIT_AS_SPECIFIED"] = kind is not None
    details["edit"] = {"type": kind, "lines": changed} if kind else {"reason": changed}
    oracle = parse_oracle(blocks["oracle"])
    checks["ORACLE_FIELDS"] = oracle is not None
    requirement = decoys = cites = groups = None
    if oracle:
        requirement = int(oracle["requirement_line"]) if oracle["requirement_line"].isdigit() else None
        decoys = parse_refs(oracle["decoy_lines"], allow_none=True)
        cites = parse_refs(oracle["cite_lines"])
        groups = keyword_groups(oracle["rubric_keywords"])
        baits = [b.strip() for b in oracle["bait_notes"].split("|") if b.strip()]
        needs_fallback = instance["kind"] in ("omitted_unknown", "decoy_pair")
        checks["ORACLE_CONTENT"] = (len(oracle["mechanism"]) >= 20 and groups is not None and 2 <= len(baits) <= 3
                                    and (len(oracle["why_no_fallback"]) >= 20 if needs_fallback else oracle["why_no_fallback"].lower() == "none"))
        checks["CLAIM_SENTENCE_NEUTRAL"] = not any(re.search(r"\b" + re.escape(w) + r"\b", oracle["why_no_fallback"].lower()) for w in META_WORDS if w != "decisive")
    else:
        checks["ORACLE_CONTENT"] = False
    in_range = lambda refs: refs is not None and all(s in sound and 1 <= n <= len(sound[s]) for s, n in refs)
    checks["ORACLE_REFS_IN_RANGE"] = requirement is not None and 1 <= requirement <= len(sound["S01"]) and in_range(cites) and in_range(decoys)
    if kind and checks["ORACLE_REFS_IN_RANGE"]:
        source = instance["changedSource"]
        mine = [(source, n) for n in changed]
        checks["CITES_SURVIVE_AND_COVER_THE_EDIT"] = (len(cites) <= 4 and not (kind == "deleted" and set(cites) & set(mine))
                                                      and (kind == "deleted" or set(mine) <= set(cites)))
        checks["REQUIREMENT_NOT_AN_EDITED_LINE"] = not (source == "S01" and requirement in changed)
        low_high = lambda b, s: assign.bucket_range(len(sound[s]), b)
        first, last = low_high(instance["buckets"]["changed"], source)
        checks["EDIT_IN_ASSIGNED_THIRD"] = all(first <= n <= last for n in changed)
        first, last = low_high(instance["buckets"]["requirement"], "S01")
        checks["REQUIREMENT_IN_ASSIGNED_THIRD"] = first <= requirement <= last
        decoy_lines = [n for s, n in decoys if s == "S01"]
        if instance["kind"] == "decoy_pair":
            first, last = low_high(instance["buckets"]["decoy"], "S01")
            checks["DECOY_IN_ASSIGNED_THIRD"] = bool(decoy_lines) and len(decoy_lines) == len(decoys) and all(first <= n <= last for n in decoy_lines)
            checks["DECOY_APART_FROM_EDIT"] = source != "S01" or all(abs(d - c) >= 5 for d in decoy_lines for c in changed)
            checks["DECOY_LINES_ADMIT_SOMETHING"] = bool(decoy_lines) and all(admits(sound["S01"][n - 1]) for n in decoy_lines)
        else:
            checks["NO_DECOY_LINES"] = not decoys
    plan_text = "\n".join(line for group in (sound, twin) for lines in group.values() for line in lines).lower()
    leaked = [w for w in META_WORDS if re.search(r"\b" + re.escape(w) + r"\b", plan_text)]
    checks["NO_META_WORDS"] = not leaked
    details["metaWordsFound"] = leaked
    allowed = {(s, n) for s, n in (decoys or [])}
    admitted = [f"{s}:{i}" for s in sources for i, line in enumerate(sound[s], 1) if (s, i) not in allowed and admits(line)]
    if kind == "edited" and instance["kind"] != "decoy_pair":
        i = changed[0]
        if admits(twin[instance["changedSource"]][i - 1]):
            admitted.append(f"twin {instance['changedSource']}:{i}")
    checks["NO_ADMISSIONS_OUTSIDE_OPEN_ITEMS"] = not admitted
    details["admissionLines"] = admitted
    if groups:
        sound_text = "\n".join(line for lines in sound.values() for line in lines).lower()
        checks["RUBRIC_GROUNDED_IN_THE_PLAN"] = all(any(w in sound_text for w in group) for group in groups)
    parsed = None
    if oracle and kind:
        parsed = {"sound": sound, "twin": twin, "edit": {"type": kind, "source": instance["changedSource"], "lines": changed},
                  "oracle": {"requirement": requirement, "cite": cites, "decoys": decoys, "mechanism": oracle["mechanism"],
                             "whyNoFallback": None if oracle["why_no_fallback"].lower() == "none" else oracle["why_no_fallback"],
                             "baitNotes": [b.strip() for b in oracle["bait_notes"].split("|") if b.strip()], "rubricKeywords": groups}}
    return {"allPassed": all(checks.values()), "checks": checks, "details": details}, parsed


def protected(line):
    """Counter of the tokens a rewording must keep: those with a digit or one of _ / \\ : = @ #, words in capitals, and capitalised words that are not the first."""
    tokens = []
    for index, raw in enumerate(line.split()):
        token = raw.strip(".,;()[]\"'`!?")
        if not token:
            continue
        if (any(c.isdigit() for c in token) or PROTECTED_CHARS & set(token) or (len(token) >= 2 and token.isalpha() and token.isupper())
                or (index > 0 and token[0].isupper())):
            tokens.append(token)
    return Counter(tokens)


def analyse_reword(text, accepted, instance, family):
    """(result, parsed) for a wording-B rewording of an accepted pair `accepted` (the parsed case of analyse)."""
    checks, details = {}, {}
    blocks = split_blocks(text, instance, with_oracle=False)
    checks["BLOCKS_IN_ORDER"] = blocks is not None
    if blocks is None:
        return {"allPassed": False, "checks": checks, "details": {"reason": "the markers are not each present once and in order"}}, None
    checks["CALL_BYTES"] = len(text.encode("utf-8")) <= CALL_BYTES_MAX
    checks["NOTHING_OUTSIDE_THE_CASE"] = not blocks["before"] and not blocks["after"]
    sources = sources_of(instance)
    sound = {s: blocks[("sound", s)] for s in sources}
    twin = {s: blocks[("twin", s)] for s in sources}
    checks["SAME_LINE_COUNTS"] = all(len(sound[s]) == len(accepted["sound"][s]) and len(twin[s]) == len(accepted["twin"][s]) for s in sources)
    bad = {f"{m}:{s}": shape_problems(lines)[:10] for m, group in (("sound", sound), ("twin", twin)) for s, lines in group.items() if shape_problems(lines)}
    checks["LINE_SHAPE"] = not bad
    details["badShapeLines"] = bad
    checks["NO_DUPLICATE_LINES"] = all(len(set(lines)) == len(lines) for lines in sound.values())
    if checks["SAME_LINE_COUNTS"]:
        kind, changed = edit_relation(sound, twin, family, instance)
        checks["SAME_EDIT_AS_WORDING_A"] = kind == accepted["edit"]["type"] and changed == accepted["edit"]["lines"]
        mismatched = []
        for s in sources:
            for i, (a, b) in enumerate(zip(accepted["sound"][s], sound[s]), 1):
                if protected(a) != protected(b):
                    mismatched.append(f"sound {s}:{i}")
        if kind == "edited":
            source, line = accepted["edit"]["source"], accepted["edit"]["lines"][0]
            if protected(accepted["twin"][source][line - 1]) != protected(twin[source][line - 1]):
                mismatched.append(f"twin {source}:{line}")
        checks["PROTECTED_TOKENS_KEPT"] = not mismatched
        details["protectedTokenMismatches"] = mismatched[:10]
        differing = sum(1 for s in sources for a, b in zip(accepted["sound"][s], sound[s]) if a != b)
        total = sum(len(accepted["sound"][s]) for s in sources)
        checks["IS_A_REWORDING"] = differing * 2 >= total
        details["linesReworded"] = f"{differing}/{total}"
    plan_text = "\n".join(line for group in (sound, twin) for lines in group.values() for line in lines).lower()
    leaked = [w for w in META_WORDS if re.search(r"\b" + re.escape(w) + r"\b", plan_text)]
    checks["NO_META_WORDS"] = not leaked
    allowed = {(s, n) for s, n in accepted["oracle"]["decoys"]}
    admitted = [f"{s}:{i}" for s in sources for i, line in enumerate(sound[s], 1) if (s, i) not in allowed and admits(line)]
    checks["NO_ADMISSIONS_OUTSIDE_OPEN_ITEMS"] = not admitted
    if instance["kind"] == "decoy_pair":
        checks["DECOY_LINES_ADMIT_SOMETHING"] = all(admits(sound[s][n - 1]) for s, n in accepted["oracle"]["decoys"])
    parsed = {"sound": sound, "twin": twin} if all(checks.values()) else None
    return {"allPassed": all(checks.values()), "checks": checks, "details": details}, parsed


def load_instance(pair, split):
    doc = json.loads((HERE / f"assignments-{split}.json").read_bytes())
    families = {f["id"]: f for f in json.loads((V4 / "families.json").read_bytes())["families"]}
    instance = next(i for i in doc["instances"] if i["pair"] == pair)
    return instance, families[instance["family"]]


def main(argv):
    if len(argv) != 3 or argv[1] not in ("dev", "test"):
        print(json.dumps({"status": "STOPPED", "reason": "USAGE"}))
        return 2
    try:
        instance, family = load_instance(argv[0], argv[1])
        text = Path(argv[2]).read_text(encoding="utf-8")
    except (OSError, UnicodeError, StopIteration):
        print(json.dumps({"status": "STOPPED", "reason": "INPUT_UNREADABLE"}))
        return 2
    print(json.dumps(analyse(text, instance, family)[0], indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
