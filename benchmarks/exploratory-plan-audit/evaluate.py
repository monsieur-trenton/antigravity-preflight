"""Offline retrospective label extraction; no model execution or semantic grading."""
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parent
LABEL = re.compile(r"^(NO-GO|NO GO|GO)(?:\s*\([^\r\n]*\))?\s*[.!]?\s*$", re.I)
HEADING = re.compile(r"^(?:(?:FINAL|AUDIT)\s+)?VERDICT\s*(?::\s*|$)(.*)$", re.I)


def extract_verdict(text):
    """Accept explicit GO/NO-GO verdict declarations, refusing conflicts.

    Ignore fenced code and blockquotes. A bare label is accepted only as the
    first content row or following a standalone Verdict heading. This parser
    serves the original binary prompt; skill assessments never grant readiness.
    """
    found = []
    fence = None
    awaiting_label = False
    unsupported_declaration = False
    content_rows = 0
    for raw in text.splitlines():
        row = raw.strip()
        marker = re.match(r"^(`{3,}|~{3,})", row)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence):
                fence = None
            continue
        if fence or not row or row.startswith(">"):
            continue
        row = re.sub(r"^#{1,6}\s+", "", row)
        row = row.replace("**", "").replace("`", "").strip()
        heading = HEADING.fullmatch(row)
        candidate = None
        if heading:
            remainder = heading[1].strip()
            if remainder:
                candidate = remainder
                awaiting_label = False
            else:
                awaiting_label = True
        else:
            if awaiting_label or content_rows == 0:
                candidate = row
            if awaiting_label and not LABEL.fullmatch(row):
                unsupported_declaration = True
            awaiting_label = False
        content_rows += 1
        if candidate is not None:
            match = LABEL.fullmatch(candidate)
            if match:
                found.append(match[1].upper().replace(" ", "-"))
            elif heading:
                unsupported_declaration = True
    return found[0] if found and len(set(found)) == 1 and not unsupported_declaration and not awaiting_label else "UNCLEAR"


def score(raw, case):
    output = raw.get("stdout")
    valid_output = isinstance(output, str) and bool(output.strip())
    process_ok = type(raw.get("exit_code")) is int and raw["exit_code"] == 0 and raw.get("error") is None
    verdict = extract_verdict(output) if valid_output and process_ok else "UNADMITTED"
    expected = case["ground_truth"]["expected_verdict"]
    hints = [word for word in case["ground_truth"]["key_identifiers"]
             if valid_output and word.casefold() in output.casefold()]
    return dict(case_id=case["id"], recordedConfiguredModel=raw.get("model"),
                processOutcomeAdmitted=process_ok and valid_output,
                originalExpectedLabel=expected, extractedLabel=verdict,
                originalLabelMatch=process_ok and valid_output and verdict == expected,
                keywordHints=hints, keywordHintsAreSemanticCredit=False,
                reportedCliWallSeconds=raw.get("elapsed_seconds"),
                semanticGrade="REQUIRES_SEPARATE_ADJUDICATION")


def evaluate():
    raw = json.loads((ROOT / "historical/responses.json").read_bytes())
    cases = {c["id"]: c for c in (json.loads(p.read_bytes())
             for p in sorted((ROOT / "historical/corpus").glob("case_*.json")))}
    if len(raw) != len(cases) or len({r["case_id"] for r in raw}) != len(cases):
        raise ValueError("MISSING_OR_DUPLICATE_CASE_RESULT")
    if {r["case_id"] for r in raw} != set(cases):
        raise ValueError("CASE_SET_MISMATCH")
    scored = [score(r, cases[r["case_id"]]) for r in raw]
    return dict(kind="RETROSPECTIVE_LABEL_EXTRACTION_NOT_SEMANTIC_BENCHMARK",
                observations=len(scored), originalLabelMatches=sum(r["originalLabelMatch"] for r in scored),
                newModelCalls=0, results=scored,
                limits="Original labels include an unproven timeout oracle and an invalid clean control; label matches are not correctness or recall estimates.")


if __name__ == "__main__":
    # Stdout only: never overwrite retained experimental results.
    json.dump(evaluate(), sys.stdout, indent=2)
    sys.stdout.write("\n")
