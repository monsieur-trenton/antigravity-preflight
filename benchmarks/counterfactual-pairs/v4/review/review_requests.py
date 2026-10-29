"""Build the reviewer requests of corpus v4 for the preregistered arms from the pinned prompt files; no model calls.

A request is a pure function of the arm, the pinned files and the case's sources (a dict from source id to its lines), so it can be rebuilt and hashed. The reviewer sees only packet text:
never an id, a pair, a family, a kind or a class. The skill-style arms get the numbered reading view `[S01:n]` / `[S02:n]` and the machine summary; the bare arm gets the plan as plain
lines and a request to end with a verdict. Parsers: parse_v4.parse_report for the skill-style arms, parse_bare below for the bare arm.
"""
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ABLATION = HERE.parent.parent / "ablation"
SOURCE_TITLES = {"S01": "the plan", "S02": "the reference excerpt the plan is subject to"}
BARE_VERDICTS = {"GO": "NO_BLOCKERS_FOUND", "GO_WITH_CHANGES": "CHANGES_RECOMMENDED", "NO_GO": "BLOCKERS_FOUND"}
ARMS = ("skill", "skill-go", "bare")


def read(path):
    return Path(path).read_text(encoding="utf-8")


def source_ids(sources):
    ids = sorted(sources)
    if ids not in (["S01"], ["S01", "S02"]):
        raise ValueError("SOURCES")
    return ids


def reading_view(sources):
    """The numbered reading view: a header per source, then `[S0n:k] line`."""
    parts = []
    for source in source_ids(sources):
        parts.append(f"SOURCE {source} ({SOURCE_TITLES[source]}; numbered reading view, copy quotations from the row without the prefix)")
        parts += [f"[{source}:{n}] {line}" for n, line in enumerate(sources[source], 1)]
        parts.append("")
    return "\n".join(parts)


def skill_request(sources, sentence=None):
    """Prompt, optional one-sentence addition, numbered view, format suffix; as the v3 skill-style request with two sources possible."""
    ids = source_ids(sources)
    body = read(HERE / "prompt.txt").rstrip("\n") + "\n"
    if sentence is not None:
        body += sentence.rstrip("\n") + "\n"
    body += "\n" + reading_view(sources)
    only = "source S01" if ids == ["S01"] else "sources S01 and S02"
    return (body + read(HERE / "format-suffix.txt").replace("{SOURCES}", only)).encode("utf-8")


def skill_go_sentence():
    return read(ABLATION / "skill-go" / "skill-go-sentence.txt").rstrip("\n")


def bare_request(sources):
    ids = source_ids(sources)
    material = "\n".join(sources["S01"])
    if ids == ["S01", "S02"]:
        material += "\n\n" + read(HERE / "bare-reference-lead.txt").rstrip("\n") + "\n\n" + "\n".join(sources["S02"])
    return read(HERE / "bare-request.txt").replace("{material}", material).encode("utf-8")


def build(arm, sources):
    if arm == "skill":
        return skill_request(sources)
    if arm == "skill-go":
        return skill_request(sources, skill_go_sentence())
    if arm == "bare":
        return bare_request(sources)
    raise ValueError("ARM")


def parse_bare(text):
    """The bare arm's only machine hook: the last non-empty line must be one VERDICT line."""
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        raise ValueError("EMPTY_REPORT")
    match = re.fullmatch(r"VERDICT:\s*(GO_WITH_CHANGES|NO_GO|GO)", lines[-1].strip().strip("*`_ ").strip())
    if match is None:
        raise ValueError("NO_VERDICT_LINE")
    return {"completeness": "COMPLETE", "assessment": BARE_VERDICTS[match.group(1)], "findings": [], "verdictRaw": match.group(1)}
