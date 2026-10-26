"""Build the requests of the blind audit from a built v4 corpus; no model calls.

The auditor sees only packet text, numbered as a reviewer would see it, and case ids are never put in a request. The oracle is read here for scheduling only (which cases are
gap twins, which pairs exist) and, for the claim check, for the author's own `whyNoFallback` sentence; no request contains a class, a kind, a line number of the oracle or a
mechanism.
"""
import hashlib
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def template(name):
    return (HERE / name).read_text(encoding="utf-8")


def numbered(sources):
    """The plan text as a reviewer sees it: [S01:n] before every line."""
    parts = []
    for source_id in sorted(sources):
        title = "S01 (the plan)" if source_id == "S01" else "S02 (the reference excerpt)"
        parts.append(f"=== {title} ===")
        parts += [f"[{source_id}:{n}] {line}" for n, line in enumerate(sources[source_id], 1)]
    return "\n".join(parts)


def member_request(sources):
    return template("member-request.txt").replace("{PLAN}", numbered(sources))


def x_is_sound(seed, pair):
    """Which member is shown as X: a fixed, seed-determined coin per pair, so the order carries no information."""
    return int(hashlib.sha256(f"{seed}|audit-order|{pair}".encode()).hexdigest()[:8], 16) % 2 == 0


def pair_request(seed, pair, sound_sources, twin_sources):
    x, y = (sound_sources, twin_sources) if x_is_sound(seed, pair) else (twin_sources, sound_sources)
    return template("pair-request.txt").replace("{X}", numbered(x)).replace("{Y}", numbered(y))


def claim_request(sources, claim):
    return template("claim-request.txt").replace("{CLAIM}", claim.replace('"', "'")).replace("{PLAN}", numbered(sources))


def system_prompt():
    return template("system-prompt.txt").strip()
