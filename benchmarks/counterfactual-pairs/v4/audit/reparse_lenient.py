"""Re-read, under one stated relaxation, the audit answers that were recorded as unparseable because of commentary in a reference list; no model call.

An audit answer whose OTHER_PROBLEMS or CONTRADICTING_LINES carries prose in parentheses after a reference (`S01:15 (16 shard primaries ...)`) is recorded by audit.py as a technical stop
(`UNPARSEABLE_ANSWER:BAD_REFS`), as it should be: the driver never repairs. The answer is otherwise well-formed. This tool re-reads the held ANSWER.md of each such call, checks its hash against
the ledger row, accepts parenthetical commentary after a reference and a comma as a separator, and nothing else, and writes the re-read rows to a supplemental ledger. The original ledger is
never modified; audit_report.py reads the two together (`--answers ORIGINAL,SUPPLEMENT`) and a row of the supplement replaces the same call.

Usage: reparse_lenient.py LEDGER ATTEMPTS_DIR OUTPUT_LEDGER
"""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import audit_parse  # noqa: E402

REASON = "UNPARSEABLE_ANSWER:BAD_REFS"


def reparse(rows, attempts):
    out, refused = [], []
    for row in rows:
        if row.get("technicalStop") != REASON:
            continue
        path = Path(attempts) / row["call"].replace(":", "_") / "ANSWER.md"
        text = path.read_text(encoding="utf-8") if path.is_file() else None
        if text is None or hashlib.sha256(text.encode("utf-8")).hexdigest() != row.get("reportSha256"):
            refused.append({"call": row["call"], "why": "ANSWER_MISSING_OR_HASH_MISMATCH"})
            continue
        try:
            answer = audit_parse.parse(text, row["type"], lenient=True)
        except audit_parse.AuditParseError as error:
            refused.append({"call": row["call"], "why": str(error)})
            continue
        new = {k: v for k, v in row.items() if k != "technicalStop"}
        new.update(answer=answer, lenientReparse=True, originalStop=REASON)
        out.append(new)
    return out, refused


def main(argv):
    if len(argv) != 3:
        print(json.dumps({"status": "STOPPED", "reason": "USAGE"}))
        return 2
    rows = [json.loads(line) for line in Path(argv[0]).read_text(encoding="utf-8").splitlines() if line.strip()]
    out, refused = reparse(rows, argv[1])
    Path(argv[2]).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in out), encoding="utf-8")
    print(json.dumps({"status": "WRITTEN", "stopsConsidered": sum(1 for r in rows if r.get("technicalStop") == REASON), "reRead": len(out), "refused": refused, "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
