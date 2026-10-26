"""Build the authoring and rewording prompts of corpus v4 from the pinned templates, a family specification, a domain and an assignment; no model calls.

The prompt for an instance is a pure function of the template files, families.json, domains.json and the instance's assignment, so it can be rebuilt and hashed.
"""
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
sys.path.insert(0, str(HERE))
import check_author as ca  # noqa: E402

THIRDS = {"early": "first third", "middle": "middle third", "late": "last third"}


def third(lines, bucket):
    first, last = ca.assign.bucket_range(lines, bucket)
    return f"the {THIRDS[bucket]}, lines {first} to {last}"


def format_block(instance, with_oracle=True):
    out = ["CASE-BEGIN"]
    for member, label in (("SOUND", "the sound plan"), ("TWIN", "the twin")):
        for source in ca.sources_of(instance):
            noun = "reference excerpt" if source == "S02" else "plan"
            out += [f"{member}-{source}-BEGIN", f"<{label}, {noun} {source}, one sentence per line>", f"{member}-{source}-END"]
    if with_oracle:
        out += ["ORACLE-BEGIN"] + [f"{k}: <...>" for k in ca.ORACLE_KEYS] + ["ORACLE-END"]
    return "\n".join(out + ["CASE-END"])


def assignment_block(instance, family, domain):
    cross = instance["kind"] == "cross_source_defect"
    plan = instance["planLines"]
    lines = [f"Domain: {domain['description']}. Entities you may use: {domain['entities']}.",
             f"Family: {family['title']}.",
             f"The requirement the plan states, to be written as one testable sentence in the plan's own words: {family['requirement']}",
             f"What the SOUND plan contains: {family['soundHas']}",
             f"What the TWIN does: {family['twinDiffers']}",
             f"The line that states the requirement goes in {third(plan, instance['buckets']['requirement'])} of the plan.",
             f"The change goes in {third(plan if instance['changedSource'] == 'S01' else instance['referenceLines'], instance['buckets']['changed'])} "
             f"of {'the plan (S01)' if instance['changedSource'] == 'S01' else 'the reference excerpt (S02)'}"
             + (" (the lines to delete, counted in the sound plan)." if ca.deleting(family) else " (the one line to edit)."),
             f"Length: the plan (S01) has {plan} lines" + (f" and the reference excerpt (S02) has {instance['referenceLines']} lines, one entry per line, "
                                                           "an excerpt of a settings file, contract, policy or schema that the plan is subject to." if cross else "."),
             "Citation rule (for cite_lines): " + family["citeRule"]]
    if instance["kind"] == "decoy_pair":
        lines.append(f"Open-item lines (decoy_lines): the plan contains the open item the family describes, flagged as pending or unconfirmed, in "
                     f"{third(plan, instance['buckets']['decoy'])} of the plan, at least five lines from the change. These are the only lines that may say something is open, "
                     "and the plan has exactly one open item.")
        if family["twinClass"] == "UNCERTAIN":
            lines.append("why_no_fallback must say why nothing else in the plan settles the open item.")
        else:
            lines.append("In the twin, the change must make the plan contradict its own stated requirement from its own lines, with no outside fact needed; why_no_fallback is none.")
    elif instance["kind"] == "omitted_unknown":
        lines.append("No line of either plan says that anything is unknown or unmeasured; the twin simply never mentions the missing fact. decoy_lines is none. "
                     "why_no_fallback must say why nothing else in the twin bounds or establishes it.")
    else:
        lines.append("No line of either plan says that anything is unknown or open; decoy_lines is none and why_no_fallback is none.")
    lines.append("Things to keep out of the case:")
    lines += [f"- {h}" for h in family["hazards"]]
    lines.append("Concrete choices for you to make and keep consistent: " + "; ".join(family["slots"]) + ".")
    return "\n".join(lines)


def author_prompt(instance, family, domain):
    template = (HERE / "author-template.txt").read_text(encoding="utf-8")
    return template.replace("{ASSIGNMENT}", assignment_block(instance, family, domain)).replace("{FORMAT}", format_block(instance))


def pair_text(parsed, instance):
    out = ["CASE-BEGIN"]
    for member in ("sound", "twin"):
        for source in ca.sources_of(instance):
            out += [f"{member.upper()}-{source}-BEGIN", *parsed[member][source], f"{member.upper()}-{source}-END"]
    return "\n".join(out + ["CASE-END"])


def reword_prompt(instance, parsed):
    template = (HERE / "reword-template.txt").read_text(encoding="utf-8")
    return template.replace("{FORMAT}", format_block(instance, with_oracle=False)).replace("{PAIR}", pair_text(parsed, instance))


def domain_of(instance):
    return next(d for d in json.loads((V4 / "domains.json").read_bytes())["domains"] if d["id"] == instance["domain"])


def family_of(instance):
    return next(f for f in json.loads((V4 / "families.json").read_bytes())["families"] if f["id"] == instance["family"])
