"""Write or check the manifest of the v4 reviewer files: the pinned prompts, the request builder and the files it depends on; no model calls.

Usage: build_manifest.py (--write | --check)
"""
import hashlib
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
PAIRS = V4.parent
OWN = ("prompt.txt", "format-suffix.txt", "bare-request.txt", "bare-reference-lead.txt", "review_requests.py")
BORROWED = {"ablation/skill-go/skill-go-sentence.txt": PAIRS, "ablation/bare-system.txt": PAIRS, "v4/parse_v4.py": PAIRS, "v4/score_v4.py": PAIRS, "v4/families.json": PAIRS,
            "run_pilot.py": PAIRS, "score.py": PAIRS}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build():
    spec = __import__("importlib.util").util.spec_from_file_location("rp_for_manifest", PAIRS / "run_pilot_claude.py")
    module = __import__("importlib.util").util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return {"kind": "V4_REVIEWER_FILES_PINNED", "arms": ["skill", "skill-go", "bare"],
            "pins": {name: sha(HERE / name) for name in OWN},
            "borrowed": {name: sha(root / name) for name, root in BORROWED.items()},
            "claudeSkillSystemPromptSha256": hashlib.sha256(module.SYSTEM_PROMPT.encode("utf-8")).hexdigest(),
            "note": "Pins the reviewer-visible wording of corpus v4. Not a run manifest: the corpus, the drivers and the preregistration are bound to it separately, and nothing here has been run."}


def main(argv):
    if argv not in (["--write"], ["--check"]):
        print("usage: build_manifest.py (--write | --check)", file=sys.stderr)
        return 2
    manifest = build()
    text = json.dumps(manifest, indent=2) + "\n"
    path = HERE / "manifest.json"
    if argv == ["--write"]:
        path.write_text(text, encoding="utf-8")
        print(json.dumps({"status": "WRITTEN", "pins": len(manifest["pins"]) + len(manifest["borrowed"])}))
        return 0
    same = path.is_file() and path.read_text(encoding="utf-8") == text
    print(json.dumps({"status": "PASS" if same else "FAIL", "providerCalls": 0}))
    return 0 if same else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
