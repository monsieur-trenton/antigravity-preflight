"""Assign the instances of corpus v4 from a committed seed: pair ids, domains, plan lengths, position buckets and which test pairs get wording B; no model calls.

SPEC.md leaves these to the builder, not the author (rules 6 and 7). Everything is a pure function of the seed, the families and the domain pool: ordering uses a SHA-256
sort key rather than a random-number generator, so the result does not depend on the interpreter. `--check` re-derives an assignment file and compares it with the committed one.

Usage: assign.py --split dev|test (--write | --check)    (files: assignments-dev.json, assignments-test.json beside this script; seeds in seeds.json)
"""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
BUCKETS = ("early", "middle", "late")
MAX_PER_DOMAIN_SPLIT, MAX_PER_DOMAIN_FAMILY = 4, 2
WORDING_B_PER_KIND = 3


class AssignmentError(Exception):
    pass


def key(seed, *parts):
    return hashlib.sha256("|".join((seed,) + tuple(str(p) for p in parts)).encode("utf-8")).hexdigest()


def ordered(seed, label, items):
    """Items in a seed-determined order (stable for equal keys by position)."""
    return [item for _, _, item in sorted((key(seed, label, i, item if isinstance(item, (str, int)) else i), i, item) for i, item in enumerate(items))]


def balanced(seed, label, count):
    """`count` buckets with each of the three used floor(count/3) or ceil(count/3) times, in a seed-determined order."""
    start = int(key(seed, label, "start")[:8], 16) % 3
    return ordered(seed, label, [BUCKETS[(start + i) % 3] for i in range(count)])


def pick_length(seed, label, bounds):
    low, high = bounds
    return low + int(key(seed, label, "length")[:8], 16) % (high - low + 1)


def derive(seed, split, families_doc, domains_doc):
    families = [f for f in families_doc["families"] if f["split"] == split]
    domains = [d for d in domains_doc["domains"] if split == "dev" or not d["devOnly"]]
    instances = []
    for family in families:
        n = family["instances"]
        decoy = family["kind"] == "decoy_pair"
        cross = family["kind"] == "cross_source_defect"
        requirement = balanced(seed, family["id"] + "|requirement", n)
        changed = balanced(seed, family["id"] + "|changed", n)
        decoys = balanced(seed, family["id"] + "|decoy", n) if decoy else [None] * n
        sources = ordered(seed, family["id"] + "|source", (["S01", "S02"] * n)[:n]) if cross else None  # half the edits in each source
        for i in range(n):
            pair = "N-" + key(seed, "pair", family["id"], i)[:6]
            plan = pick_length(seed, pair + "|plan", family["sources"][0]["lines"])
            reference = pick_length(seed, pair + "|reference", family["sources"][1]["lines"]) if cross else None
            instances.append({"pair": pair, "family": family["id"], "kind": family["kind"], "index": i, "domain": None, "planLines": plan, "referenceLines": reference,
                              "buckets": {"requirement": requirement[i], "changed": changed[i], "decoy": decoys[i]}, "changedSource": sources[i] if cross else "S01",
                              "wordingB": False})
    if len({i["pair"] for i in instances}) != len(instances):
        raise AssignmentError("PAIR_ID_COLLISION")
    used, per_family = {}, {}
    for instance in ordered(seed, "domain-order", [i["pair"] for i in instances]):
        row = next(i for i in instances if i["pair"] == instance)
        eligible = [d["id"] for d in domains if used.get(d["id"], 0) < MAX_PER_DOMAIN_SPLIT and per_family.get((row["family"], d["id"]), 0) < MAX_PER_DOMAIN_FAMILY]
        if not eligible:
            raise AssignmentError("NO_ELIGIBLE_DOMAIN:" + row["pair"])
        chosen = sorted(eligible, key=lambda d: (used.get(d, 0), key(seed, "domain", row["pair"], d)))[0]
        row["domain"] = chosen
        used[chosen] = used.get(chosen, 0) + 1
        per_family[(row["family"], chosen)] = per_family.get((row["family"], chosen), 0) + 1
    wanted = families_doc["targets"][split]["wordingBPairs"]
    if wanted:
        if wanted != 4 * WORDING_B_PER_KIND:
            raise AssignmentError("WORDING_B_TARGET")
        for kind in sorted({i["kind"] for i in instances}):
            of_kind = [i for i in instances if i["kind"] == kind]
            for row in sorted(of_kind, key=lambda r: key(seed, "wording-b", r["pair"]))[:WORDING_B_PER_KIND]:
                row["wordingB"] = True
    return instances


def document(seed, split, families_doc, domains_doc):
    return {"schemaVersion": 1, "split": split, "seedSha256": hashlib.sha256(seed.encode("utf-8")).hexdigest(),
            "instances": derive(seed, split, families_doc, domains_doc)}


def problems(doc, families_doc, domains_doc):
    """Constraint violations of an assignment document (SPEC.md rules 6 and 7); independent of how it was derived."""
    out = []
    split = doc.get("split")
    families = {f["id"]: f for f in families_doc["families"] if f["split"] == split}
    domain_ok = {d["id"]: d for d in domains_doc["domains"]}
    rows = doc.get("instances", [])
    if len(rows) != sum(f["instances"] for f in families.values()):
        out.append("INSTANCE_COUNT")
    if len({r["pair"] for r in rows}) != len(rows):
        out.append("PAIR_IDS")
    by_domain, by_family_domain = {}, {}
    for r in rows:
        by_domain[r["domain"]] = by_domain.get(r["domain"], 0) + 1
        by_family_domain[(r["family"], r["domain"])] = by_family_domain.get((r["family"], r["domain"]), 0) + 1
        if r["domain"] not in domain_ok or (split == "test" and domain_ok[r["domain"]]["devOnly"]):
            out.append("DOMAIN:" + r["pair"])
        family = families.get(r["family"])
        if family is None:
            out.append("FAMILY:" + r["pair"])
            continue
        low, high = family["sources"][0]["lines"]
        if not low <= r["planLines"] <= high:
            out.append("PLAN_LENGTH:" + r["pair"])
        if len(family["sources"]) == 2 and not family["sources"][1]["lines"][0] <= r["referenceLines"] <= family["sources"][1]["lines"][1]:
            out.append("REFERENCE_LENGTH:" + r["pair"])
        if (r["buckets"]["decoy"] is None) == (family["kind"] == "decoy_pair"):
            out.append("DECOY_BUCKET:" + r["pair"])
    if any(c > MAX_PER_DOMAIN_SPLIT for c in by_domain.values()):
        out.append("DOMAIN_SPLIT_CAP")
    if any(c > MAX_PER_DOMAIN_FAMILY for c in by_family_domain.values()):
        out.append("DOMAIN_FAMILY_CAP")
    for fid, family in families.items():
        own = [r for r in rows if r["family"] == fid]
        n = len(own)
        for role in ("requirement", "changed", "decoy"):
            if role == "decoy" and family["kind"] != "decoy_pair":
                continue
            counts = [sum(1 for r in own if r["buckets"][role] == b) for b in BUCKETS]
            if sum(counts) != n or min(counts) < n // 3 or max(counts) > n // 3 + 1:
                out.append(f"BUCKETS:{fid}:{role}")
        if family["kind"] == "cross_source_defect":
            edits = [sum(1 for r in own if r["changedSource"] == s) for s in ("S01", "S02")]
            if abs(edits[0] - edits[1]) > 1:
                out.append("CHANGED_SOURCE:" + fid)
    flagged = {}
    for r in rows:
        if r["wordingB"]:
            flagged[r["kind"]] = flagged.get(r["kind"], 0) + 1
    want = families_doc["targets"][split]["wordingBPairs"]
    if sum(flagged.values()) != want or any(c != WORDING_B_PER_KIND for c in flagged.values()) or (want and len(flagged) != 4):
        out.append("WORDING_B")
    return out


def load():
    seeds = json.loads((HERE / "seeds.json").read_bytes())
    return seeds, json.loads((V4 / "families.json").read_bytes()), json.loads((V4 / "domains.json").read_bytes())


def bucket_range(lines, bucket):
    """First and last line number (inclusive, from 1) of the early, middle or late third of a source of `lines` lines."""
    low = lines // 3
    high = 2 * lines // 3
    return {"early": (1, low), "middle": (low + 1, high), "late": (high + 1, lines)}[bucket]


def bucket_of(line, lines):
    return next(b for b in BUCKETS if bucket_range(lines, b)[0] <= line <= bucket_range(lines, b)[1])


def main(argv):
    if len(argv) != 3 or argv[0] != "--split" or argv[1] not in ("dev", "test") or argv[2] not in ("--write", "--check"):
        print("usage: assign.py --split dev|test (--write | --check)", file=sys.stderr)
        return 2
    split = argv[1]
    seeds, families_doc, domains_doc = load()
    seed = seeds[split]["seed"]
    if hashlib.sha256(seed.encode("utf-8")).hexdigest() != seeds[split]["sha256"]:
        print(json.dumps({"status": "STOPPED", "reason": "SEED_HASH_MISMATCH"}))
        return 1
    try:
        doc = document(seed, split, families_doc, domains_doc)
    except AssignmentError as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error)}))
        return 1
    bad = problems(doc, families_doc, domains_doc)
    path = HERE / f"assignments-{split}.json"
    text = json.dumps(doc, indent=1) + "\n"
    if argv[2] == "--write":
        if bad:
            print(json.dumps({"status": "STOPPED", "reason": "CONSTRAINTS", "problems": bad}))
            return 1
        path.write_text(text, encoding="utf-8")
        print(json.dumps({"status": "WRITTEN", "split": split, "instances": len(doc["instances"])}))
        return 0
    same = path.is_file() and path.read_text(encoding="utf-8") == text
    print(json.dumps({"status": "PASS" if same and not bad else "FAIL", "split": split, "matchesSeed": same, "problems": bad, "instances": len(doc["instances"])}))
    return 0 if same and not bad else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
