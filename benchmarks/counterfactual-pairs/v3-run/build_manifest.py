"""Pin the v3 run preregistration, tie it to the corpus v3 manifest, the arms' own manifests and the skill-style system prompt; no model calls.

The arms' manifests name corpus v2, and the evidence recorded against them is verified with them as they are, so they are never
edited. A run on corpus v3 is bound instead by this manifest, which the driver and verifier load with --run-manifest.

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
ARM_MANIFESTS = {"defined": BASE / "ablation" / "defined" / "manifest.json", "defined-go": BASE / "ablation" / "defined-go" / "manifest.json"}
OWN = ("PREREGISTRATION.md",)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def skill_system_prompt():
    spec = importlib.util.spec_from_file_location("run_pilot_claude_for_manifest", BASE / "run_pilot_claude.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SYSTEM_PROMPT


def build():
    manifest = {
        "kind": "V3_RUN_FROZEN",
        "corpus": {"path": "benchmarks/counterfactual-pairs/v3", "manifestSha256": sha(CORPUS.read_bytes())},
        "arms": {
            "skill": {"manifest": None, "systemPromptSha256": sha(skill_system_prompt().encode("utf-8"))},
            **{name: {"manifest": str(path.relative_to(ROOT)), "manifestSha256": sha(path.read_bytes())} for name, path in ARM_MANIFESTS.items()},
        },
        "pins": {name: sha((HERE / name).read_bytes()) for name in OWN},
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
    print(json.dumps({"status": "PASS", "arms": 3, "pins": len(OWN), "providerCalls": 0}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
