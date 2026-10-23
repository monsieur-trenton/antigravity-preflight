"""Pack the evidence of one run_gemini_v3.py trial into a small archive that verify_gemini_run.py accepts; no model calls, no oracle.

A trial's working directory is tens of gigabytes because every seed and attempt carries a copy of the runtime and the native binary. The
evidence that the verifier and the scorer need is a few megabytes: the ledger, each case's report and receipt, and the prompt the model was
sent with its snapshot. This copies exactly that allowlist, keeps the same relative layout (so the verifier runs unchanged on the extracted
archive), and records in BUNDLE-MANIFEST.json the SHA-256 of every included file and, for everything left out, only file counts and sizes.
Nothing in the working directory is modified, moved or deleted.

Usage: bundle_gemini_evidence.py --workdir DIR --trial N --out FILE.tar.gz [--hash-omitted]
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import tarfile

sys.dont_write_bytecode = True

ATTEMPT_FILES = ("GEMINI-REVIEW.md", "CLI-RECEIPT.json", "CLI-INIT.json")
PACKET_FILES = ("prompt.txt", "PACKET.json", "snapshots/S01.txt")
MAX_INCLUDED_BYTES = 8 * 1024 * 1024


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def included_files(workdir, trial):
    """Relative paths (under the workdir) of everything the verifier and the scorer read."""
    wanted = [Path(f"responses-trial{trial}.jsonl")]
    base = Path(f"trial{trial}")
    for kind, names in (("attempts", ATTEMPT_FILES), ("packets", PACKET_FILES)):
        root = workdir / base / kind
        if root.is_dir():
            for case in sorted(p.name for p in root.iterdir() if p.is_dir()):
                wanted += [base / kind / case / name for name in names]
    return [p for p in wanted if (workdir / p).is_file()]


def bundle(workdir, trial, out, hash_omitted=False):
    workdir = Path(workdir).resolve()
    keep = included_files(workdir, trial)
    kept = {str(p) for p in keep}
    for p in keep:
        if (workdir / p).stat().st_size > MAX_INCLUDED_BYTES:
            raise SystemExit("INCLUDED_FILE_TOO_LARGE:" + str(p))
    omitted = {"files": 0, "bytes": 0, "byTopLevel": {}}
    omitted_rows = []
    for path in sorted(workdir.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        rel = path.relative_to(workdir)
        if str(rel) in kept:
            continue
        size = path.stat().st_size
        top = "/".join(rel.parts[:3]) if rel.parts[0] == f"trial{trial}" else rel.parts[0]
        row = omitted["byTopLevel"].setdefault(top, {"files": 0, "bytes": 0})
        row["files"] += 1
        row["bytes"] += size
        omitted["files"] += 1
        omitted["bytes"] += size
        if hash_omitted:
            omitted_rows.append({"path": str(rel), "bytes": size, "sha256": sha(path)})
    manifest = {"kind": "GEMINI_V3_EVIDENCE_BUNDLE", "trial": trial,
                "included": [{"path": str(p), "bytes": (workdir / p).stat().st_size, "sha256": sha(workdir / p)} for p in keep],
                "omitted": omitted, "omittedFiles": omitted_rows or None,
                "note": "Only the allowlisted evidence is included; the omitted files are runtime copies, seeds and scratch. The working directory was not modified."}
    manifest_bytes = (json.dumps(manifest, indent=1) + "\n").encode("utf-8")
    out = Path(out)
    with tarfile.open(out, "w:gz") as archive:
        info = tarfile.TarInfo(f"live{trial}/BUNDLE-MANIFEST.json")
        info.size = len(manifest_bytes)
        info.mtime = 0
        archive.addfile(info, __import__("io").BytesIO(manifest_bytes))
        for p in keep:
            info = archive.gettarinfo(str(workdir / p), arcname=f"live{trial}/{p}")
            info.uid = info.gid = 0
            info.uname = info.gname = ""
            info.mtime = 0
            with (workdir / p).open("rb") as stream:
                archive.addfile(info, stream)
    return {"status": "PASS", "included": len(keep), "includedBytes": sum((workdir / p).stat().st_size for p in keep),
            "omittedFiles": omitted["files"], "omittedBytes": omitted["bytes"], "archive": str(out), "archiveBytes": out.stat().st_size, "providerCalls": 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--trial", type=int, required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--hash-omitted", action="store_true", help="also record the SHA-256 of every omitted file (reads all of it; slow on tens of gigabytes)")
    args = parser.parse_args(argv)
    out = Path(args.out).resolve()
    if out.exists():
        print(json.dumps({"status": "STOPPED", "reason": "OUTPUT_EXISTS"}))
        return 1
    if Path(args.workdir).resolve() in out.parents:
        print(json.dumps({"status": "STOPPED", "reason": "OUTPUT_INSIDE_WORKDIR"}))
        return 1
    print(json.dumps(bundle(args.workdir, args.trial, out, args.hash_omitted)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
