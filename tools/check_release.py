"""Validate publication files and exact runtime pins without calling a provider."""
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent


def pin(path):
    body = path.read_bytes()
    return {"sha256": hashlib.sha256(body).hexdigest(), "bytes": len(body)}


def main():
    pins = json.loads((ROOT / "qualification/runtime-pins.json").read_bytes())
    runtime = ROOT / pins["runtimeRoot"]
    assert len(pins["packageFiles"]) == 6
    for name, expected in pins["packageFiles"].items():
        assert pin(runtime / name) == expected, ("RUNTIME_PIN", name)
    provenance = json.loads((ROOT / "qualification/publication-provenance.json").read_bytes())
    for row in provenance["files"]:
        expected = row.get("publishedPin", row["sourcePin"])
        assert pin(ROOT / row["path"]) == expected, ("PUBLICATION_PIN", row["path"])
    paths = [p for p in ROOT.rglob("*") if p.is_file() and ".git" not in p.parts
             and "__pycache__" not in p.parts]
    python_count = 0
    for path in paths:
        assert not path.is_symlink(), ("SYMLINK", str(path.relative_to(ROOT)))
        assert path.stat().st_size < 2_000_000, ("UNEXPECTED_LARGE_FILE", path.name)
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        assert not re.search(r"(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,}|-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----)", text), ("SECRET_PATTERN", path.name)
        private_paths = ("/Documents/" + "Codex/", "/.codex/" + "attachments/")
        assert all(fragment not in text for fragment in private_paths), ("PRIVATE_PATH", path.name)
        if path.suffix == ".py":
            compile(raw, str(path), "exec")
            python_count += 1
        if path.suffix == ".md":
            for target in re.findall(r"\[[^\]\n]+\]\(([^)\s]+)\)", text):
                if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
                    continue
                relative = target.split("#", 1)[0]
                destination = (path.parent / relative).resolve()
                assert destination.is_relative_to(ROOT.resolve()) and destination.exists(), ("BROKEN_LINK", str(path.relative_to(ROOT)), target)
    assert not (ROOT / "skills/antigravity-preflight/references/concordance.md").exists()
    fm = (ROOT / "skills/antigravity-preflight/SKILL.md").read_text()
    assert fm.startswith("---\nname: antigravity-preflight\ndescription:")
    for rel in ["examples/plan/inventory.json", "examples/plan/citations.json"]:
        json.loads((ROOT / rel).read_bytes())
    inventory = json.loads((ROOT / "examples/plan/inventory.json").read_bytes())
    for source in inventory["sources"]:
        assert pin(ROOT / "examples/plan" / source["path"])["sha256"] == source["sha256"]
    print(json.dumps({"status": "PASS", "runtimePins": 6, "publicationPins": len(provenance["files"]),
                      "pythonSourcesSyntaxChecked": python_count, "providerCalls": 0}))


if __name__ == "__main__":
    main()
