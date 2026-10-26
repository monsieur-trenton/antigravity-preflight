"""Parse the three audit answers (member, pair, claim); strict, no model calls.

Each answer ends with one AUDIT block of `KEY: value` lines; free text may precede it. Anything else after AUDIT-END, a missing, repeated or unknown key, or a value outside
its set is a parse failure, recorded as a stop and never repaired.
"""
import re
import sys

sys.dont_write_bytecode = True

SPECS = {
    "member": {"CLASS": ("SOUND", "HAS_A_DEFECT", "HAS_AN_UNESTABLISHED_FACT", "CANNOT_TELL"), "REASON": None, "DECISIVE_FACT": None, "REQUIREMENT_LINE": "ref-or-none",
               "REQUIREMENT_DECIDES": ("YES", "NO"), "OTHER_PROBLEMS": "refs-or-none"},
    "pair": {"NEEDS_CHANGE": ("X", "Y", "BOTH", "NEITHER"), "WHY": None, "ONE_EDIT": ("YES", "NO"), "DIFFERENCE": None},
    "claim": {"CLAIM_HOLDS": ("YES", "NO"), "CONTRADICTING_LINES": "refs-or-none"},
}
REF = re.compile(r"^S0[12]:[1-9][0-9]*$")


class AuditParseError(Exception):
    pass


def parse_refs(value):
    if value.strip().lower() == "none":
        return []
    parts = [p.strip() for p in value.split(";")]
    if not all(REF.match(p) for p in parts):
        raise AuditParseError("BAD_REFS")
    return parts


def parse(text, call):
    spec = SPECS[call]
    lines = text.replace("\r\n", "\n").split("\n")
    begin = [i for i, line in enumerate(lines) if line.strip() == "AUDIT-BEGIN"]
    end = [i for i, line in enumerate(lines) if line.strip() == "AUDIT-END"]
    if len(begin) != 1 or len(end) != 1 or begin[0] > end[0]:
        raise AuditParseError("MARKERS")
    if any(line.strip() for line in lines[end[0] + 1:]):
        raise AuditParseError("TEXT_AFTER_AUDIT_END")
    fields = {}
    for line in lines[begin[0] + 1:end[0]]:
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        key, value = key.strip(), value.strip()
        if not separator or key not in spec or key in fields or not value:
            raise AuditParseError("BAD_FIELD:" + key)
        allowed = spec[key]
        if isinstance(allowed, tuple):
            if value not in allowed:
                raise AuditParseError("BAD_VALUE:" + key)
        elif allowed == "ref-or-none":
            if value.lower() != "none" and not REF.match(value):
                raise AuditParseError("BAD_VALUE:" + key)
        elif allowed == "refs-or-none":
            fields[key] = parse_refs(value)
            continue
        fields[key] = value
    if set(fields) != set(spec):
        raise AuditParseError("MISSING_FIELDS")
    return fields
