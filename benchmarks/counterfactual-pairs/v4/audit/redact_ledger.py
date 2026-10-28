"""Write the committable form of an audit ledger for a sealed split: the enums, references, hashes and costs of every row, with each free-text answer field replaced by its SHA-256; no model call.

The free text of an answer (REASON, DECISIVE_FACT, WHY, DIFFERENCE) quotes or paraphrases the sealed plans, so it stays out of the repository. The request and answer hashes remain, which
bind the redacted ledger to the private attempts directory it came from.

Usage: redact_ledger.py LEDGER [LEDGER ...] > redacted.jsonl     (rows of later ledgers replace rows of the same call, as audit_report.read_ledger does)
"""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

FREE_TEXT = ("REASON", "DECISIVE_FACT", "WHY", "DIFFERENCE")


def redact(row):
    out = dict(row)
    answer = out.get("answer")
    if isinstance(answer, dict):
        out["answer"] = {k: v for k, v in answer.items() if k not in FREE_TEXT}
        out["freeTextSha256"] = {k: hashlib.sha256(answer[k].encode("utf-8")).hexdigest() for k in FREE_TEXT if k in answer}
    return out


def main(argv):
    rows = {}
    for path in argv:
        for line in Path(path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                rows[row["call"]] = row
    for call in sorted(rows):
        print(json.dumps(redact(rows[call]), sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
