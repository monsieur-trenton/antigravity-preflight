"""Build and check the block schedule of the v4 reviewer run from public inputs only; no model calls and no oracle.

A case id is a public function of the committed seed, the pair id, the wording and the role (author/build_corpus.py), and the submission order is a hash of the
same seed, so the pair-to-case mapping, the kinds and the order can be rebuilt from `author/assignments-<split>.json`, `author/seeds.json` and the drops list. Nothing here
reads a packet or the oracle, so it can run in a session that must not see sealed text, and `--check` also compares the rebuilt case set with the corpus manifest's pins
(the committed hashes-only manifest for the test split).

A block is a set of pairs (default 6), dealt round-robin over the kinds so every block mixes them; both members of a pair, and its rewording, share a block. A step is one
(block, arm, trial) of a route. Within a route the arms alternate by block (and by trial) so stopping after any step leaves the arms equally far along. The optional repeat
steps (Gemini, trial 2) cover the pairs with the smallest SHA-256 of `pair|v4-repeat`; they run only on the owner's explicit approval.

Usage: schedule.py --split dev|test (--write FILE | --check FILE | --print)
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
PAIRS_PER_BLOCK = 6
REPEAT_PAIRS = 24
ROUTES = {"gemini": {"arms": ["skill", "bare"], "trials": 1}, "claude": {"arms": ["skill", "skill-go"], "trials": 2}}
CORPUS_MANIFEST = {"dev": V4 / "dev" / "manifest.json", "test": V4 / "test-audit-revision" / "sealed-manifest-final.json"}
DROPS = {"dev": V4 / "dev-drops.json", "test": V4 / "test-drops.json"}


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def surviving_pairs(split):
    doc = json.loads((V4 / "author" / f"assignments-{split}.json").read_bytes())
    seeds = json.loads((V4 / "author" / "seeds.json").read_bytes())
    if doc["seedSha256"] != seeds[split]["sha256"]:
        raise ValueError("SEED_MISMATCH")
    dropped = {d["pair"] for d in json.loads(DROPS[split].read_bytes())}
    return seeds[split]["seed"], [i for i in doc["instances"] if i["pair"] not in dropped]


def case_id(seed, pair, wording, role):
    return "R-" + sha(f"{seed}|case|{pair}|{wording}|{role}")[:6]


def cases_of(seed, instance):
    wordings = ("A", "B") if instance["wordingB"] else ("A",)
    return [case_id(seed, instance["pair"], w, role) for w in wordings for role in ("sound", "changed")]


def submission_order(seed, cases):
    return [c for _, c in sorted((sha(f"{seed}|submission|{c}"), c) for c in cases)]


def deal(seed, instances, per_block):
    """Pairs into blocks: ordered by kind, then by a seeded hash inside each kind, dealt round-robin so every block mixes the kinds."""
    ordered = sorted(instances, key=lambda i: (i["kind"], sha(f"{seed}|block|{i['pair']}")))
    count = -(-len(ordered) // per_block)
    blocks = [[] for _ in range(count)]
    for index, instance in enumerate(ordered):
        blocks[index % count].append(instance)
    return blocks


def block_rows(seed, groups, prefix, order):
    rank = {c: n for n, c in enumerate(order)}
    rows = []
    for number, group in enumerate(groups, 1):
        cases = sorted((c for i in group for c in cases_of(seed, i)), key=rank.__getitem__)
        rows.append({"id": f"{prefix}{number:02d}", "pairs": sorted(i["pair"] for i in group), "cases": cases})
    return rows


def arm_order(arms, index, trial):
    """Alternate the arms' order from one block to the next, and shift it by trial, so neither arm is always first."""
    return arms if (index + trial) % 2 == 0 else list(reversed(arms))


def steps_for(block_ids, arms, trials, first_trial=1):
    steps = []
    for trial in range(first_trial, first_trial + trials):
        for index, block in enumerate(block_ids):
            for arm in arm_order(arms, index, trial):
                steps.append({"step": len(steps) + 1, "block": block, "arm": arm, "trial": trial})
    return steps


def build(split, per_block=PAIRS_PER_BLOCK):
    seed, instances = surviving_pairs(split)
    cases = [c for i in instances for c in cases_of(seed, i)]
    order = submission_order(seed, cases)
    blocks = block_rows(seed, deal(seed, instances, per_block), "B", order)
    repeat_pairs = sorted(instances, key=lambda i: sha(i["pair"] + "|v4-repeat"))[:min(REPEAT_PAIRS, len(instances))]
    repeat_groups = [repeat_pairs[n:n + per_block] for n in range(0, len(repeat_pairs), per_block)]
    repeats = block_rows(seed, repeat_groups, "R", order)
    block_ids = [b["id"] for b in blocks]
    routes = {}
    for route, spec in ROUTES.items():
        routes[route] = {"arms": spec["arms"], "trials": spec["trials"], "steps": steps_for(block_ids, spec["arms"], spec["trials"])}
    optional = {"gemini": {"note": "Run only if the owner approves after trial 1; trial 2 of both Gemini arms on the hash-drawn repeat pairs.",
                           "steps": steps_for([b["id"] for b in repeats], ROUTES["gemini"]["arms"], 1, first_trial=2)}}
    return {"kind": "V4_RUN_SCHEDULE", "split": split, "seedSha256": sha(seed), "pairsPerBlock": per_block,
            "pairs": len(instances), "cases": len(cases), "submissionOrder": order,
            "blocks": blocks, "repeatBlocks": repeats, "routes": routes, "optional": optional}


def check_against_manifest(schedule, split):
    """The rebuilt case set must equal the cases the corpus manifest pins (packets/<case>/S01.txt)."""
    manifest = json.loads(CORPUS_MANIFEST[split].read_bytes())
    pinned = {k.split("/")[1] for k in manifest["pins"] if k.startswith("packets/")}
    if pinned != set(schedule["submissionOrder"]):
        raise ValueError("CASE_SET_MISMATCH")
    if manifest.get("submissionOrder") not in (None, schedule["submissionOrder"]):
        raise ValueError("SUBMISSION_ORDER_MISMATCH")


def render(schedule):
    return json.dumps(schedule, indent=1) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--pairs-per-block", type=int, default=PAIRS_PER_BLOCK)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--write")
    group.add_argument("--check")
    group.add_argument("--print", action="store_true")
    args = parser.parse_args(argv)
    try:
        schedule = build(args.split, args.pairs_per_block)
        check_against_manifest(schedule, args.split)
    except (ValueError, OSError, KeyError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error)}))
        return 1
    text = render(schedule)
    if args.write:
        Path(args.write).write_text(text, encoding="utf-8")
    elif args.check:
        if Path(args.check).read_text(encoding="utf-8") != text:
            print(json.dumps({"status": "FAIL", "reason": "SCHEDULE_DIFFERS"}))
            return 1
    else:
        print(text, end="")
        return 0
    print(json.dumps({"status": "PASS", "split": args.split, "pairs": schedule["pairs"], "cases": schedule["cases"], "blocks": len(schedule["blocks"]),
                      "repeatBlocks": len(schedule["repeatBlocks"]), "stepsPerRoute": {r: len(v["steps"]) for r, v in schedule["routes"].items()},
                      "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
