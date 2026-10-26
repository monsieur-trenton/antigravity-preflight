"""Parse a v4 reviewer report: the machine summary with source-qualified line numbers; no model calls.

A finding's line field is `S01:12` or `S02:5` (source id and the line of that source, counted from 1), or a bare number, which means S01. The v3 parser
accepted `S01:n` only as a tolerated deviation; here it is the format. Everything else is as strict as run_pilot.parse_report: the same markers, the same enums
(a finding with an unsupported severity or evidence value is malformed), and no text after the summary.

parse_report(text) returns {"completeness", "assessment", "findings": [{"severity", "evidence", "source", "line", "quote"}]} or raises run_pilot.Stop.
"""
import importlib.util
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("v4_run_pilot", HERE.parent / "run_pilot.py")
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)
Stop = rp.Stop
LINE_FIELD = re.compile(r"^(?:(S[0-9]{2}):)?([0-9]+)$")


def parse_line_field(field):
    """(source, line) from `S02:5` or `5`; None when the field is anything else, including a line below 1."""
    match = LINE_FIELD.match(field.strip())
    if not match or int(match.group(2)) < 1:
        return None
    return match.group(1) or "S01", int(match.group(2))


def parse_report(text):
    marker = text.rfind("MACHINE SUMMARY")
    rp.need(marker >= 0, "NO_MACHINE_SUMMARY")
    completeness = assessment = None
    findings = []
    for raw in text[marker:].splitlines()[1:]:
        line = raw.strip()
        if not line:
            continue
        if line.startswith("COMPLETENESS:"):
            rp.need(completeness is None, "DUPLICATE_COMPLETENESS")
            completeness = line.split(":", 1)[1].strip()
        elif line.startswith("ASSESSMENT:"):
            rp.need(assessment is None, "DUPLICATE_ASSESSMENT")
            assessment = line.split(":", 1)[1].strip()
        elif line.startswith("FINDING:"):
            parts = [p.strip() for p in line.split(":", 1)[1].split("|", 3)]
            rp.need(len(parts) == 4, "MALFORMED_FINDING")
            severity, evidence, field, quote = parts
            rp.need(severity in rp.FINDING_SEVERITIES and evidence in rp.FINDING_EVIDENCE, "MALFORMED_FINDING")
            if field == "-":
                source, number, quote = "S01", 0, ""
            else:
                located = parse_line_field(field)
                rp.need(located is not None, "MALFORMED_FINDING")
                source, number = located
            findings.append({"severity": severity, "evidence": evidence, "source": source, "line": number, "quote": "" if quote == "-" else quote})
        else:
            raise Stop("UNEXPECTED_LINE_AFTER_SUMMARY")
    rp.need(completeness in ("COMPLETE", "INCOMPLETE"), "INVALID_COMPLETENESS")
    rp.need(assessment in ("BLOCKERS_FOUND", "CHANGES_RECOMMENDED", "NO_BLOCKERS_FOUND"), "INVALID_ASSESSMENT")
    return {"completeness": completeness, "assessment": assessment, "findings": findings}
