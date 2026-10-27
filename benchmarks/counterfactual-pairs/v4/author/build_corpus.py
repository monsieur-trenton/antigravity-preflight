"""Assemble a v4 corpus directory from the accepted authored reports; no model calls.

Reads the accepted reports of author.py (`accepted/<pair>.A.md`, and `.B.md` for wording-B pairs), the assignments and the families, and writes the layout score_v4.py
reads: packets/<case>/S0n.txt, oracle/oracle.json (one record per case, validated against the schema of SPEC.md) and manifest.json (SHA-256 pins of every file). Case ids are
derived from the seed, so they carry no information and the build is reproducible. Pairs named in --drops are left out of the corpus and recorded in the manifest with
their reasons. For a sealed split give --sealed-manifest as well: it writes a hashes-only document that can be committed while the corpus directory stays private.

Usage: build_corpus.py --split dev|test --accepted DIR[,DIR] --out NEW_DIR [--drops FILE] [--sealed-manifest FILE]
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
sys.path.insert(0, str(HERE))
import check_author as ca  # noqa: E402
import prompts  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cfam = load("build_check_families", V4 / "check_families.py")


class BuildError(Exception):
    pass


def sha(data):
    return hashlib.sha256(data).hexdigest()


def need(condition, reason):
    if not condition:
        raise BuildError(reason)


def mapper(edit):
    """Line number of a sound-plan line in the twin: shifted past the deleted lines of the edited source, unchanged otherwise."""
    gone = edit["lines"] if edit["type"] == "deleted" else []
    return lambda source, line: line - sum(1 for g in gone if g < line) if source == edit["source"] else line


def records_for(instance, family, parsed, wording, seed):
    kind = cfam.KINDS[instance["kind"]]
    edit, oracle = parsed["edit"], parsed["oracle"]
    to_twin = mapper(edit)
    out = {}
    for role in ("sound", "changed"):
        member = "sound" if role == "sound" else "twin"
        sources = [{"id": s, "role": "plan" if s == "S01" else "reference", "lines": len(parsed[member][s])} for s in ca.sources_of(instance)]
        at = (lambda s, n: (s, n)) if role == "sound" else (lambda s, n: (s, to_twin(s, n)))
        ref = lambda s, n: {"source": at(s, n)[0], "line": at(s, n)[1]}
        sound = role == "sound"
        out[role] = {
            "case": "R-" + hashlib.sha256(f"{seed}|case|{instance['pair']}|{wording}|{role}".encode()).hexdigest()[:6],
            "pair": instance["pair"], "family": instance["family"], "kind": instance["kind"], "domain": instance["domain"], "wording": wording, "role": role,
            "expectedClass": "SOUND" if sound else family["twinClass"], "expectedVerdict": "GO" if sound else kind["twins"][family["twinClass"]], "difficulty": family["difficulty"],
            "sources": sources, "requirement": ref("S01", oracle["requirement"]),
            "citeAnyOf": [] if sound else [ref(s, n) for s, n in oracle["cite"]],
            "changed": {"type": edit["type"], "source": edit["source"], "lines": list(edit["lines"]), "positionBucket": instance["buckets"]["changed"]},
            "decoyLines": [ref(s, n) for s, n in oracle["decoys"]],
            "mechanism": None if sound else oracle["mechanism"],
            "whyNoFallback": oracle["whyNoFallback"] if (not sound and instance["kind"] in ("omitted_unknown", "decoy_pair") and family["twinClass"] == "UNCERTAIN") else None,
            "baitNotes": list(oracle["baitNotes"]), "rubricKeywords": [list(g) for g in oracle["rubricKeywords"]],
        }
        problems = cfam.check_oracle(out[role])
        need(not problems, f"ORACLE_SCHEMA:{instance['pair']}:{wording}:{role}:{','.join(problems)}")
    return out


def accepted_file(accepted, name):
    """The accepted report `name` from the last directory that has it; `accepted` is one directory or several (a later batch replaces an earlier report of the same pair)."""
    dirs = [Path(d) for d in (accepted.split(",") if isinstance(accepted, str) else [accepted] if isinstance(accepted, Path) else accepted)]
    for directory in reversed(dirs):
        if (directory / name).is_file():
            return directory / name
    return dirs[-1] / name


def build(split, accepted_dir, out_dir, drops=()):
    seeds = json.loads((HERE / "seeds.json").read_bytes())
    seed = seeds[split]["seed"]
    doc = json.loads((HERE / f"assignments-{split}.json").read_bytes())
    need(doc["seedSha256"] == seeds[split]["sha256"], "SEED_MISMATCH")
    families = {f["id"]: f for f in json.loads((V4 / "families.json").read_bytes())["families"]}
    out_dir = Path(out_dir)
    need(not out_dir.exists() or not any(out_dir.iterdir()), "OUT_DIR_MUST_BE_NEW")
    dropped = {d["pair"]: d["reason"] for d in drops}
    need(all(isinstance(r, str) and r.strip() for r in dropped.values()) and set(dropped) <= {i["pair"] for i in doc["instances"]}, "BAD_DROPS")
    records, packets, authored = [], {}, {}
    for instance in doc["instances"]:
        pair = instance["pair"]
        if pair in dropped:
            continue
        family = families[instance["family"]]
        report_a = accepted_file(accepted_dir, f"{pair}.A.md")
        need(report_a.is_file(), "MISSING_ACCEPTED:" + pair)
        result, parsed_a = ca.analyse(report_a.read_text(encoding="utf-8"), instance, family)
        need(result["allPassed"] and parsed_a, "ACCEPTED_FAILS_CHECKS:" + pair)
        authored[pair] = {"A": sha(report_a.read_bytes())}
        versions = [("A", parsed_a)]
        if instance["wordingB"]:
            report_b = accepted_file(accepted_dir, f"{pair}.B.md")
            need(report_b.is_file(), "MISSING_REWORDING:" + pair)
            result_b, parsed_b = ca.analyse_reword(report_b.read_text(encoding="utf-8"), parsed_a, instance, family)
            need(result_b["allPassed"] and parsed_b, "REWORDING_FAILS_CHECKS:" + pair)
            authored[pair]["B"] = sha(report_b.read_bytes())
            versions.append(("B", dict(parsed_a, sound=parsed_b["sound"], twin=parsed_b["twin"])))
        for wording, text_parsed in versions:
            made = records_for(instance, family, text_parsed, wording, seed)
            for role, member in (("sound", "sound"), ("changed", "twin")):
                records.append(made[role])
                packets[made[role]["case"]] = {s: text_parsed[member][s] for s in ca.sources_of(instance)}
    need(len({r["case"] for r in records}) == len(records), "CASE_ID_COLLISION")
    (out_dir / "oracle").mkdir(parents=True, exist_ok=True)
    order = [c for _, c in sorted((hashlib.sha256(f"{seed}|submission|{r['case']}".encode()).hexdigest(), r["case"]) for r in records)]
    records.sort(key=lambda r: order.index(r["case"]))
    (out_dir / "oracle" / "oracle.json").write_text(json.dumps({"cases": records}, indent=1) + "\n", encoding="utf-8")
    for case, sources in packets.items():
        for source, lines in sources.items():
            path = out_dir / "packets" / case / f"{source}.txt"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    pins = {str(p.relative_to(out_dir)): sha(p.read_bytes()) for p in sorted(out_dir.rglob("*")) if p.is_file()}
    manifest = {"kind": "COUNTERFACTUAL_PAIR_CORPUS_V4", "split": split, "cases": len(records), "pairs": len({r["pair"] for r in records}),
                "families": len({r["family"] for r in records}), "submissionOrder": order,
                "reviewerVisible": sorted(k for k in pins if k.startswith("packets/")), "pins": pins, "providerCalls": 0,
                "authoring": {"seedSha256": seeds[split]["sha256"], "assignmentsSha256": sha((HERE / f"assignments-{split}.json").read_bytes()),
                              "acceptedReportSha256": authored},
                "dropped": [{"pair": p, "reason": r} for p, r in sorted(dropped.items())]}
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8")
    return manifest


def sealed(manifest):
    """The hashes-only view of a manifest: what can be committed while the packets and the oracle stay private."""
    return {"kind": "COUNTERFACTUAL_PAIR_CORPUS_V4_SEALED_HASHES_ONLY", "split": manifest["split"], "cases": manifest["cases"], "pairs": manifest["pairs"],
            "pins": {k: v for k, v in sorted(manifest["pins"].items())}, "authoring": manifest["authoring"], "dropped": manifest["dropped"],
            "manifestSha256": sha((json.dumps(manifest, indent=1) + "\n").encode("utf-8"))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--split", required=True, choices=("dev", "test"))
    parser.add_argument("--accepted", required=True, help="a directory of accepted reports, or several separated by commas (a later one replaces the same pair of an earlier one)")
    parser.add_argument("--out", required=True)
    parser.add_argument("--drops")
    parser.add_argument("--sealed-manifest")
    args = parser.parse_args(argv)
    try:
        drops = json.loads(Path(args.drops).read_text(encoding="utf-8")) if args.drops else []
        manifest = build(args.split, args.accepted, args.out, drops)
        if args.sealed_manifest:
            Path(args.sealed_manifest).write_text(json.dumps(sealed(manifest), indent=1) + "\n", encoding="utf-8")
    except (BuildError, OSError, ValueError, KeyError) as error:
        print(json.dumps({"status": "STOPPED", "reason": str(error) if isinstance(error, BuildError) else type(error).__name__}))
        return 1
    print(json.dumps({"status": "BUILT", "split": args.split, "cases": manifest["cases"], "pairs": manifest["pairs"], "dropped": len(manifest["dropped"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
