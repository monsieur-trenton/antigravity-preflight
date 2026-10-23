"""The documented-rule view of a run_pilot.py ledger: re-read the saved reports of MALFORMED_FINDING stops, accepting one relaxation only.

A FINDING line whose line field is the snapshot label 'S01:<n>' (the numbered snapshot labels each line [S01:n]) is read as line <n>.
Nothing else is relaxed: the quotation must still appear verbatim on that line (the scorer checks it) and every other format rule of
run_pilot.parse_report applies. The report must match the hash in the ledger row. The original ledger is never modified; the result
is written to a new file, and a stop that still does not parse stays a stop. No model calls, no oracle.

Usage: reparse_lenient.py LEDGER_JSONL REPORTS_DIR OUT_JSONL
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("run_pilot", HERE / "run_pilot.py")
rp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(rp)

LABELLED_LINE = re.compile(r"^(\s*FINDING:[^|]*\|[^|]*\|\s*)S\d+:(\d+)(\s*\|)", re.M)


def lenient_text(text):
    marker = text.rfind("MACHINE SUMMARY")
    if marker < 0:
        return text
    return text[:marker] + LABELLED_LINE.sub(r"\g<1>\g<2>\g<3>", text[marker:])


def reparse(rows, reports_dir):
    """Rows with MALFORMED_FINDING stops that now parse are replaced by parsed rows marked reparsedFrom; all others are returned as they were."""
    out, changed = [], []
    for row in rows:
        code = row.get("technicalStop") or ""
        if not code.endswith("MALFORMED_FINDING"):
            out.append(row)
            continue
        path = Path(reports_dir) / (row["case"] + ".md")
        data = path.read_bytes() if path.is_file() else b""
        if hashlib.sha256(data).hexdigest() != row.get("reportSha256"):
            out.append(dict(row, reparseRefused="REPORT_HASH_MISMATCH"))
            continue
        try:
            parsed = rp.parse_report(lenient_text(data.decode("utf-8")))
        except rp.Stop as error:
            out.append(dict(row, reparseRefused=str(error)))
            continue
        keep = {k: row[k] for k in ("case", "trial", "reportSha256", "wallSeconds") if k in row}
        out.append(dict(keep, **parsed, reparsedFrom=code))
        changed.append(row["case"])
    return out, changed


def main(argv):
    if len(argv) != 3:
        print("usage: reparse_lenient.py LEDGER_JSONL REPORTS_DIR OUT_JSONL", file=sys.stderr)
        return 2
    rows = [json.loads(line) for line in Path(argv[0]).read_text(encoding="utf-8").splitlines() if line.strip()]
    out, changed = reparse(rows, argv[1])
    Path(argv[2]).write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in out), encoding="utf-8")
    print(json.dumps({"status": "PASS", "rows": len(out), "reparsed": changed, "stillStopped": [r["case"] for r in out if r.get("technicalStop")], "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
