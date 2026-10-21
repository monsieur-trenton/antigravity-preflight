"""Pin the defined-verdicts request and preregistration, borrow the bare system prompt and rubric by hash, and tie
them to one corpus v2 manifest; no model calls.

Usage: build_manifest.py [--check]
"""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
ABLATION = HERE.parent
CORPUS_MANIFEST = ABLATION.parent / "v2" / "manifest.json"
OWN = ("PREREGISTRATION.md", "defined-request.txt")
BORROWED = ("bare-system.txt", "rubric.json")  # live in ablation/, pinned by the bare arm's manifest


def build():
    sha = lambda data: hashlib.sha256(data).hexdigest()
    manifest = {
        "kind": "ABLATION_DEFINED_VERDICTS_ARM_FROZEN",
        "corpus": {"path": "benchmarks/counterfactual-pairs/v2", "manifestSha256": sha(CORPUS_MANIFEST.read_bytes())},
        "pins": {name: sha((HERE / name).read_bytes()) for name in OWN},
        "borrowed": {name: sha((ABLATION / name).read_bytes()) for name in BORROWED},
        "providerCalls": 0,
    }
    return (json.dumps(manifest, indent=2) + "\n").encode("utf-8")


def main(argv):
    data = build()
    target = HERE / "manifest.json"
    if "--check" in argv:
        if not target.is_file() or target.read_bytes() != data:
            print(json.dumps({"status": "STALE_MANIFEST"}))
            return 1
    else:
        target.write_bytes(data)
    print(json.dumps({"status": "PASS", "pins": len(OWN), "borrowed": len(BORROWED), "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
