"""Synthetic authored cases for the tests of this directory: a generator that writes, for any assignment, a report that satisfies every mechanical check.

Used only by the tests (and by nothing that reads a model). The lines are generic filler; what is faithful is the structure: the assigned lengths, thirds, edit
relation, open-item lines, citations and oracle fields, so a test can break exactly one thing at a time.
"""
import sys

sys.dont_write_bytecode = True
from pathlib import Path  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_author as ca  # noqa: E402

SWAPS = (("platform team", "infrastructure group"), ("completes", "finishes"), ("records", "writes down"), ("outcome", "result"), ("before the window", "ahead of the window"))


def filler(source, i):
    return f"The platform team completes task {source.lower()}{i:02d} on gateway-{i:02d} before the window and records the outcome in the change log."


def reword_line(line):
    for old, new in SWAPS:
        line = line.replace(old, new)
    return line


def positions(instance, sound_len, ref_len):
    """(requirement, edit lines, decoy or None) as sound-plan line numbers inside the assigned thirds, the decoy far from the edit and the requirement on neither."""
    first = lambda bucket, n: ca.assign.bucket_range(n, bucket)
    chg_n = sound_len if instance["changedSource"] == "S01" else ref_len
    chg_lo, chg_hi = first(instance["buckets"]["changed"], chg_n)
    edit = (chg_hi, chg_hi - 1)
    taken = set(edit) if instance["changedSource"] == "S01" else set()
    dec = None
    if instance["kind"] == "decoy_pair":
        lo, hi = first(instance["buckets"]["decoy"], sound_len)
        dec = max((lo, hi), key=lambda d: min(abs(d - e) for e in edit)) if instance["changedSource"] == "S01" else lo
        taken.add(dec)
    lo, hi = first(instance["buckets"]["requirement"], sound_len)
    req = next(n for n in (lo, lo + 2, hi, hi - 2) if n not in taken)
    return req, edit, dec


def case_report(instance, family, mutate=None):
    """(report text, facts) for a clean pair; `mutate(facts)` may change the plan lines or oracle fields before rendering."""
    n = instance["planLines"]
    cross = instance["kind"] == "cross_source_defect"
    ref_n = instance["referenceLines"] if cross else 0
    req, edit, dec = positions(instance, n, ref_n)
    sound = {"S01": [filler("a", i) for i in range(1, n + 1)]}
    if cross:
        sound["S02"] = [f"Setting s{i:02d} of gateway-{i:02d} permits at most {i * 10} units per window and is changed only by the platform team through review." for i in range(1, ref_n + 1)]
    sound["S01"][req - 1] = f"The platform team requires that task r{req:02d} finishes within 4 hours, and then records the outcome in the change log."
    if dec is not None:
        sound["S01"][dec - 1] = f"The platform team completes task d{dec:02d} on gateway-{dec:02d} while one item stays pending and records the outcome in the change log."
    twin = {s: list(lines) for s, lines in sound.items()}
    source = instance["changedSource"]
    from_edit = None
    if ca.deleting(family):
        count = 1 if family["kind"] == "decoy_pair" else 2
        lines = sorted(edit[:count])
        twin[source] = [line for j, line in enumerate(sound[source], 1) if j not in lines]
        changed = lines
    else:
        j = edit[0]
        twin[source][j - 1] = sound[source][j - 1].replace("task", "step").replace("gateway-", "gateway-9") if source == "S01" else sound[source][j - 1].replace("at most", "at least")
        changed = [j]
        from_edit = j
    cite = [(source, j) for j in changed] if from_edit else [("S01", req)]
    if cross and from_edit:
        other = "S02" if source == "S01" else "S01"
        cite.append((other, 2 if other == "S02" else req))
    facts = {"sound": sound, "twin": twin, "requirement": req, "cite": cite, "decoys": [("S01", dec)] if dec else [], "changed": changed, "source": source,
             "mechanism": "The twin changes the one thing that the requirement depends on, so the requirement can no longer be shown to hold.",
             "why": "Nothing else in the plan bounds or establishes it, so the requirement stays unsupported." if instance["kind"] in ("omitted_unknown", "decoy_pair") else "none",
             "bait": "no rehearsal | one alert channel", "rubric": "platform, task ; gateway"}
    if mutate:
        mutate(facts)
    return render(instance, facts), facts


def render(instance, facts):
    parts = ["CASE-BEGIN"]
    for member in ("sound", "twin"):
        for source in ca.sources_of(instance):
            parts += [f"{member.upper()}-{source}-BEGIN", *facts[member][source], f"{member.upper()}-{source}-END"]
    fmt = lambda refs: ", ".join(f"{s}:{n}" for s, n in refs) if refs else "none"
    parts += ["ORACLE-BEGIN", f"requirement_line: {facts['requirement']}", f"cite_lines: {fmt(facts['cite'])}", f"decoy_lines: {fmt(facts['decoys'])}",
              f"mechanism: {facts['mechanism']}", f"why_no_fallback: {facts['why']}", f"bait_notes: {facts['bait']}", f"rubric_keywords: {facts['rubric']}", "ORACLE-END", "CASE-END"]
    return "\n".join(parts) + "\n"


def reword_report(instance, facts):
    parts = ["CASE-BEGIN"]
    for member in ("sound", "twin"):
        for source in ca.sources_of(instance):
            parts += [f"{member.upper()}-{source}-BEGIN", *[reword_line(line) for line in facts[member][source]], f"{member.upper()}-{source}-END"]
    return "\n".join(parts + ["CASE-END"]) + "\n"
