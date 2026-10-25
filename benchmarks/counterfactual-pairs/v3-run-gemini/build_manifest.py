"""Pin the Gemini v3 run preregistration and tie it to the corpus v3 manifest, the flash-high runtime package and the agy binary; no model calls.

The driver (run_gemini_v3.py) and verifier (verify_gemini_run.py) load this manifest with --run-manifest. The binary hash is the one every receipt of the
Gemini 3.8 Flash High pilot recorded (results/pilot-flash-high); a different binary is a different run and needs a new manifest.

Usage: build_manifest.py [--check]
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
BASE = HERE.parent
ROOT = BASE.parent.parent
CORPUS = BASE / "v3" / "manifest.json"
RUNTIME = ROOT / "runtime" / "flash-high"
OWN = ("PREREGISTRATION.md",)
BINARY_SHA256 = "16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508"
BINARY_VERSION = "1.4.1"


def tree_sha(directory):
    spec = importlib.util.spec_from_file_location("run_gemini_v3_for_manifest", BASE / "run_gemini_v3.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.runtime_tree_sha(directory)


def build():
    manifest = {
        "kind": "V3_GEMINI_RUN_FROZEN",
        "corpus": {"path": "benchmarks/counterfactual-pairs/v3", "manifestSha256": hashlib.sha256(CORPUS.read_bytes()).hexdigest()},
        "runtime": {"dir": "runtime/flash-high", "profile": None, "model": "gemini-3.8-flash-high", "effort": "high", "treeSha256": tree_sha(RUNTIME)},
        "binary": {"sha256": BINARY_SHA256, "versionContains": BINARY_VERSION},
        "parser": "snapshot-label-tolerant",
        "pins": {name: hashlib.sha256((HERE / name).read_bytes()).hexdigest() for name in OWN},
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
    print(json.dumps({"status": "PASS", "pins": len(OWN), "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
