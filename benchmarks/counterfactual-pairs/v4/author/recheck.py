"""Re-apply the mechanical checks to the reports a work directory already holds; no model call and no one reads a report.

Acceptance is a function of the report text and check_author.py. When a check is corrected after a batch, a report that failed only the old rule may pass the corrected one;
this accepts it without spending another call, and records that it did in rechecks.jsonl (pair, attempt, report hash, hash of the checker, the checks it failed before).
Only the last attempt of a pair is considered, only if it produced a report, and a pair that is already accepted is left alone. Nothing here changes a ledger row.

Usage: recheck.py --split dev|test --workdir DIR [--apply]    (without --apply it only reports what would be accepted)
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import check_author as ca  # noqa: E402
import prompts  # noqa: E402


def sha(data):
    return hashlib.sha256(data).hexdigest()


def run(split, work, apply=False):
    work = Path(work)
    doc = json.loads((HERE / f"assignments-{split}.json").read_bytes())["instances"]
    by_pair = {i["pair"]: i for i in doc}
    ledger = work / "calls.jsonl"
    rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line.strip()] if ledger.is_file() else []
    last = {}
    for row in rows:
        if row["purpose"] == "author":
            last[row["pair"]] = row
    checker_sha = sha((HERE / "check_author.py").read_bytes())
    summary = {"split": split, "considered": 0, "wouldAccept": [], "accepted": [], "stillFailing": 0, "applied": apply, "checkerSha256": checker_sha, "providerCalls": 0}
    for pair, row in sorted(last.items()):
        target = work / "accepted" / f"{pair}.A.md"
        report = work / "calls" / f"{pair}-author-a{row['attempt']}" / "REPORT.md"
        if row.get("accepted") or target.is_file() or row.get("technicalStop") or not report.is_file():
            continue
        summary["considered"] += 1
        instance = by_pair[pair]
        data = report.read_bytes()
        result, _ = ca.analyse(data.decode("utf-8"), instance, prompts.family_of(instance))
        if not result["allPassed"]:
            summary["stillFailing"] += 1
            continue
        summary["wouldAccept"].append(pair)
        if apply:
            target.write_bytes(data)
            with (work / "rechecks.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"pair": pair, "attempt": row["attempt"], "reportSha256": sha(data), "checkerSha256": checker_sha, "failedBefore": row.get("failedChecks"),
                                         "accepted": True}, sort_keys=True) + "\n")
            summary["accepted"].append(pair)
    return summary


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    print(json.dumps(run(args.split, args.workdir, args.apply)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
