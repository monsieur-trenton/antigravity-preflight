"""Validate the corpus v4 family specifications, the domain pool and the oracle record schema of SPEC.md; no model calls.

Usage: check_families.py   (prints one JSON object and exits 0 when everything holds, 1 otherwise)
"""
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
KINDS = {
    "omitted_unknown": {"twinClass": "UNCERTAIN", "difficulty": {"omission"}, "twinVerdict": "GO_WITH_CHANGES", "needsReference": False},
    "cross_source_defect": {"twinClass": "DEFECT", "difficulty": {"direct", "inference"}, "twinVerdict": "NO_GO", "needsReference": True},
    "defect": {"twinClass": "DEFECT", "difficulty": {"direct", "inference"}, "twinVerdict": "NO_GO", "needsReference": False},
    "decoy_pair": {"twinClass": "UNCERTAIN", "difficulty": {"decoy"}, "twinVerdict": "GO_WITH_CHANGES", "needsReference": False},
}
FAMILY_FIELDS = ("id", "kind", "split", "instances", "title", "twinClass", "difficulty", "sources", "requirement", "soundHas", "twinDiffers", "expectedVerdict",
                 "citeRule", "hazards", "gapNamedGuidance", "slots")
DEV_FAMILIES = 3
MAX_PER_DOMAIN_SPLIT, MAX_PER_DOMAIN_FAMILY = 4, 2
BUCKETS = ("early", "middle", "late")
ORACLE_FIELDS = ("case", "pair", "family", "kind", "domain", "wording", "role", "expectedClass", "expectedVerdict", "difficulty", "sources", "requirement",
                 "citeAnyOf", "changed", "decoyLines", "mechanism", "whyNoFallback", "baitNotes", "rubricKeywords")


def check_domains(doc):
    problems = []
    domains = doc.get("domains", [])
    ids = [d.get("id") for d in domains]
    if len(set(ids)) != len(ids) or not all(isinstance(i, str) and re.fullmatch(r"[a-z0-9_]+", i) for i in ids):
        problems.append("DOMAIN_IDS")
    if not all(d.get("description") and d.get("entities") and isinstance(d.get("devOnly"), bool) for d in domains):
        problems.append("DOMAIN_FIELDS")
    eligible = [d for d in domains if not d.get("devOnly")]
    if len(eligible) * MAX_PER_DOMAIN_SPLIT < 80:
        problems.append("TEST_DOMAIN_CAPACITY")
    if len(domains) * MAX_PER_DOMAIN_SPLIT < 24:
        problems.append("DEV_DOMAIN_CAPACITY")
    return problems


def check_families(doc, domains):
    problems = []
    families = doc.get("families", [])
    ids = [f.get("id") for f in families]
    if len(set(ids)) != len(ids) or len(families) != 14:
        problems.append("FAMILY_IDS_OR_COUNT")
    limits = doc.get("limits", {})
    for f in families:
        tag = f.get("id", "?")
        missing = [k for k in FAMILY_FIELDS if not f.get(k)]
        if missing:
            problems.append(f"FAMILY_FIELDS:{tag}:{','.join(missing)}")
            continue
        kind = KINDS.get(f["kind"])
        if kind is None or f["split"] not in ("dev", "test"):
            problems.append(f"KIND_OR_SPLIT:{tag}")
            continue
        if f["twinClass"] != kind["twinClass"] or f["difficulty"] not in kind["difficulty"] or f["expectedVerdict"] != {"sound": "GO", "twin": kind["twinVerdict"]}:
            problems.append(f"KIND_MAPPING:{tag}")
        roles = [s.get("role") for s in f["sources"]]
        if roles != (["plan", "reference"] if kind["needsReference"] else ["plan"]) or [s.get("id") for s in f["sources"]] != ["S01", "S02"][:len(roles)]:
            problems.append(f"SOURCES:{tag}")
        for s in f["sources"]:
            lo, hi = s.get("lines", [0, 0])
            bound = limits.get("planLines" if s["role"] == "plan" else "referenceLines", [0, 0])
            if not (bound[0] <= lo <= hi <= bound[1]):
                problems.append(f"LINE_RANGE:{tag}:{s['id']}")
        if not isinstance(f["instances"], int) or f["instances"] < 1 or not isinstance(f["hazards"], list) or not f["hazards"] or not isinstance(f["slots"], list):
            problems.append(f"INSTANCES_OR_LISTS:{tag}")
        if f["instances"] > MAX_PER_DOMAIN_FAMILY * len([d for d in domains["domains"] if not (d["devOnly"] and f["split"] == "test")]):
            problems.append(f"FAMILY_DOMAIN_CAPACITY:{tag}")
    split_counts = {"test": {}, "dev": {}}
    for f in families:
        if f.get("kind") in KINDS and f.get("split") in split_counts:
            split_counts[f["split"]][f["kind"]] = split_counts[f["split"]].get(f["kind"], 0) + f.get("instances", 0)
    targets = doc.get("targets", {})
    for split in ("test", "dev"):
        want = {k: v for k, v in targets.get(split, {}).get("byKind", {}).items() if v}
        if split_counts[split] != want or sum(want.values()) != targets.get(split, {}).get("pairs"):
            problems.append(f"TARGET_COUNTS:{split}")
    dev = [f for f in families if f.get("split") == "dev"]
    if len(dev) != DEV_FAMILIES or sorted(f["kind"] for f in dev) != ["cross_source_defect", "decoy_pair", "omitted_unknown"]:
        problems.append("DEV_FAMILIES")
    if targets.get("test", {}).get("wordingBPairs") != 12 or targets.get("dev", {}).get("wordingBPairs") != 0:
        problems.append("WORDING_B_TARGET")
    cases_a = targets.get("test", {}).get("pairs", 0) * 2
    if cases_a != 160:
        problems.append("TEST_CASE_COUNT")
    if doc.get("verdictMap") != {"GO": "NO_BLOCKERS_FOUND", "GO_WITH_CHANGES": "CHANGES_RECOMMENDED", "NO_GO": "BLOCKERS_FOUND"}:
        problems.append("VERDICT_MAP")
    return problems


def check_oracle(record):
    """Problems with one oracle record (the schema of SPEC.md); an empty list means it is well-formed, not that its content is right."""
    problems = []
    if not isinstance(record, dict) or set(record) != set(ORACLE_FIELDS):
        return ["ORACLE_FIELDS"]
    kind = KINDS.get(record["kind"])
    if kind is None:
        return ["ORACLE_KIND"]
    if record["wording"] not in ("A", "B") or record["role"] not in ("sound", "changed"):
        problems.append("ORACLE_WORDING_OR_ROLE")
    sound = record["role"] == "sound"
    if (record["expectedClass"], record["expectedVerdict"]) != (("SOUND", "GO") if sound else (kind["twinClass"], kind["twinVerdict"])):
        problems.append("ORACLE_CLASS_OR_VERDICT")
    if record["difficulty"] not in kind["difficulty"]:
        problems.append("ORACLE_DIFFICULTY")
    sources = record["sources"]
    ids = [s.get("id") for s in sources] if isinstance(sources, list) else []
    if ids != (["S01", "S02"] if kind["needsReference"] else ["S01"]) or not all(type(s.get("lines")) is int and s["lines"] >= 1 for s in sources):
        problems.append("ORACLE_SOURCES")
        return problems
    size = {s["id"]: s["lines"] for s in sources}

    def valid_ref(ref):
        return isinstance(ref, dict) and set(ref) == {"source", "line"} and ref["source"] in size and type(ref["line"]) is int and 1 <= ref["line"] <= size[ref["source"]]

    if not valid_ref(record["requirement"]):
        problems.append("ORACLE_REQUIREMENT")
    cite = record["citeAnyOf"]
    if not isinstance(cite, list) or not all(valid_ref(r) for r in cite) or bool(cite) == sound:
        problems.append("ORACLE_CITE")
    changed = record["changed"]
    if not (isinstance(changed, dict) and changed.get("type") in ("deleted", "edited") and changed.get("source") in size and changed.get("positionBucket") in BUCKETS
            and isinstance(changed.get("lines"), list) and changed["lines"] and all(type(n) is int and n >= 1 for n in changed["lines"])):
        problems.append("ORACLE_CHANGED")
    elif (record["kind"] == "omitted_unknown" and changed["type"] != "deleted") or (record["kind"] in ("defect", "cross_source_defect") and changed["type"] != "edited"):
        problems.append("ORACLE_CHANGED_TYPE")
    if not isinstance(record["decoyLines"], list) or not all(valid_ref(r) for r in record["decoyLines"]):
        problems.append("ORACLE_DECOYS")
    if record["kind"] == "decoy_pair" and not record["decoyLines"]:
        problems.append("ORACLE_DECOYS_REQUIRED")
    if (record["mechanism"] is None) != sound or (record["mechanism"] is not None and not str(record["mechanism"]).strip()):
        problems.append("ORACLE_MECHANISM")
    needs_no_fallback = record["kind"] in ("omitted_unknown", "decoy_pair") and not sound
    if needs_no_fallback and not (isinstance(record["whyNoFallback"], str) and record["whyNoFallback"].strip()):
        problems.append("ORACLE_WHY_NO_FALLBACK")
    if not needs_no_fallback and record["whyNoFallback"] is not None:
        problems.append("ORACLE_WHY_NO_FALLBACK_UNEXPECTED")
    if not (isinstance(record["baitNotes"], list) and all(isinstance(b, str) and b for b in record["baitNotes"])):
        problems.append("ORACLE_BAIT")
    groups = record["rubricKeywords"]
    if not (isinstance(groups, list) and 1 <= len(groups) <= 3 and all(isinstance(g, list) and g and all(isinstance(w, str) and w for w in g) for g in groups)):
        problems.append("ORACLE_RUBRIC")
    return problems


def run():
    families = json.loads((HERE / "families.json").read_bytes())
    domains = json.loads((HERE / "domains.json").read_bytes())
    problems = check_domains(domains) + check_families(families, domains)
    return {"status": "PASS" if not problems else "FAIL", "families": len(families["families"]), "domains": len(domains["domains"]), "problems": problems, "providerCalls": 0}


def main():
    result = run()
    print(json.dumps(result))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
