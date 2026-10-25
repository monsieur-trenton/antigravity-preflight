"""Mechanical checks of one authored case pair (the probe's output); no model calls.

Reads the author's report text, finds the CASE block and reports, for each rule of author-prompt.txt that a program can decide, whether it holds. It never
judges realism, coherence or whether the twin is a fair test: those are read by a person.

Usage: check_probe_output.py REPORT.md   (prints one JSON object; the exit status is 0 whether or not every check passes)
"""
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

MARKERS = ("CASE-BEGIN", "SOUND-BEGIN", "SOUND-END", "TWIN-BEGIN", "TWIN-END", "ORACLE-BEGIN", "ORACLE-END", "CASE-END")
ORACLE_KEYS = ("requirement_line", "sound_fact_lines", "decoy_lines", "decisive_fact", "why_no_fallback", "tempting_alternative")
META_WORDS = ("twin", "sound", "benchmark", "oracle", "decisive", "counterfactual", "test case", "omitted")
ADMISSIONS = ("unknown", "unmeasured", "unconfirmed", "unverified", "pending", "tbd", "to be decided", "to be confirmed", "not yet", "not measured",
              "not been measured", "not final", "undecided")
SOUND_LINES = (32, 44)
LINE_CHARS = (60, 220)


def blocks(text):
    """The five block bodies as lists of non-trailing lines, or None when the markers are not exactly once each and in order."""
    lines = text.replace("\r\n", "\n").split("\n")
    positions = []
    for marker in MARKERS:
        found = [i for i, line in enumerate(lines) if line.strip() == marker]
        if len(found) != 1:
            return None
        positions.append(found[0])
    if positions != sorted(positions):
        return None
    where = dict(zip(MARKERS, positions))
    body = lambda a, b: [line for line in lines[where[a] + 1:where[b]]]
    return {"sound": body("SOUND-BEGIN", "SOUND-END"), "twin": body("TWIN-BEGIN", "TWIN-END"), "oracle": body("ORACLE-BEGIN", "ORACLE-END"),
            "before": [line for line in lines[:where["CASE-BEGIN"]] if line.strip()], "after": [line for line in lines[where["CASE-END"] + 1:] if line.strip()]}


def number_list(value):
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return [int(p) for p in parts] if parts and all(p.isdigit() for p in parts) else None


def parse_oracle(lines):
    fields = {}
    for line in lines:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        if not separator or key.strip() not in ORACLE_KEYS or key.strip() in fields:
            return None
        fields[key.strip()] = value.strip()
    return fields if set(fields) == set(ORACLE_KEYS) and all(fields.values()) else None


def check(text):
    results, details = {}, {}
    found = blocks(text)
    results["BLOCKS_IN_ORDER"] = found is not None
    if found is None:
        return {"allPassed": False, "checks": results, "details": {"reason": "the eight markers are not each present once and in order"}}
    sound, twin = found["sound"], found["twin"]
    results["NOTHING_OUTSIDE_THE_CASE"] = not found["before"] and not found["after"]
    oracle = parse_oracle(found["oracle"])
    results["ORACLE_FIELDS"] = oracle is not None
    fact = number_list(oracle["sound_fact_lines"]) if oracle else None
    decoys = number_list(oracle["decoy_lines"]) if oracle else None
    requirement = int(oracle["requirement_line"]) if oracle and oracle["requirement_line"].isdigit() else None
    results["ORACLE_NUMBERS"] = fact is not None and decoys is not None and requirement is not None
    in_range = lambda numbers: numbers is not None and all(1 <= n <= len(sound) for n in numbers)
    results["ORACLE_NUMBERS_IN_RANGE"] = in_range(fact) and in_range(decoys) and in_range([requirement] if requirement else None)
    results["FACT_LINES_1_TO_3"] = fact is not None and 1 <= len(set(fact)) <= 3 and len(set(fact)) == len(fact)
    results["DECOY_PRESENT_AND_APART_FROM_FACT"] = bool(decoys) and not (set(decoys) & set(fact or []))
    results["REQUIREMENT_NOT_A_FACT_LINE"] = requirement is not None and requirement not in (fact or [])
    results["SOUND_LENGTH"] = SOUND_LINES[0] <= len(sound) <= SOUND_LINES[1]
    details["soundLines"], details["twinLines"] = len(sound), len(twin)
    bad_shape = [i + 1 for i, line in enumerate(sound + twin) if not line.strip() or not LINE_CHARS[0] <= len(line.strip()) <= LINE_CHARS[1]
                 or re.match(r"^\s*(\d+[.)]|[-*•]\s|\[)", line)]
    results["LINE_SHAPE"] = not bad_shape
    details["badShapeLineIndexes"] = bad_shape[:10]
    expected_twin = [line for i, line in enumerate(sound, 1) if i not in set(fact or [])]
    results["TWIN_IS_SOUND_MINUS_FACT_LINES"] = bool(fact) and twin == expected_twin
    plan_text = "\n".join(sound + twin).lower()
    leaked = [w for w in META_WORDS if re.search(r"\b" + re.escape(w) + r"\b", plan_text)]
    results["NO_META_WORDS"] = not leaked
    details["metaWordsFound"] = leaked
    decoy_set = set(decoys or [])
    admitted = [i for i, line in enumerate(sound, 1) if i not in decoy_set and any(a in line.lower() for a in ADMISSIONS)]
    results["NO_ADMISSIONS_OUTSIDE_DECOY"] = not admitted
    details["admissionLinesOutsideDecoy"] = admitted
    results["DECOY_LINE_ADMITS_SOMETHING"] = bool(decoy_set) and all(any(a in sound[i - 1].lower() for a in ADMISSIONS) for i in decoy_set if i <= len(sound))
    return {"allPassed": all(results.values()), "checks": results, "details": details}


def main(argv):
    if len(argv) != 1:
        print(json.dumps({"status": "STOPPED", "reason": "USAGE"}))
        return 2
    try:
        text = Path(argv[0]).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        print(json.dumps({"status": "STOPPED", "reason": "REPORT_UNREADABLE"}))
        return 2
    print(json.dumps(check(text), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
