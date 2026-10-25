"""Pin the fifth-arm sentence (the skill-style prompt plus one sentence on optional suggestions) and the skill-style system prompt; no model calls.

The arm's request is the skill-style request of pilots 1 and 2 with exactly one line added after the corpus prompt, so it is bound to a
corpus only through a run manifest (v3-run-skill-go/), which the driver and verifier require for this arm.

Usage: build_manifest.py [--check]
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
BASE = HERE.parent.parent
OWN = ("skill-go-sentence.txt",)


def skill_system_prompt():
    spec = importlib.util.spec_from_file_location("run_pilot_claude_for_skill_go", BASE / "run_pilot_claude.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.SYSTEM_PROMPT


def build():
    sha = lambda data: hashlib.sha256(data).hexdigest()
    manifest = {
        "kind": "ABLATION_SKILL_GO_ARM_FROZEN",
        "differsFromSkillArmBy": "one line, the pinned sentence, inserted after the corpus prompt and before the snapshot",
        "pins": {name: sha((HERE / name).read_bytes()) for name in OWN},
        "systemPromptSha256": sha(skill_system_prompt().encode("utf-8")),
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
