"""Offline tests for the skill-go run: the one-line difference from the skill-style arm, manifest binding, the driver and verifier under a stub CLI, and the labels. No provider calls."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
PARENT = HERE.parent
REPO = PARENT.parent.parent
V3 = PARENT / "v3"
V2 = PARENT / "v2"
RUN_MANIFEST = HERE / "manifest.json"
ARM_DIR = PARENT / "ablation" / "skill-go"


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rc = load("sg_driver", PARENT / "run_pilot_claude.py")
vr = load("sg_verify", PARENT / "verify_run.py")
an = load("sg_analyze", HERE / "analyze.py")
bm = load("sg_build_manifest", HERE / "build_manifest.py")
arm_bm = load("sg_arm_build_manifest", ARM_DIR / "build_manifest.py")
v3_tests = load("sg_v3_run_tests", PARENT / "v3-run" / "test_run.py")
claude_tests = v3_tests.claude_tests
MODEL = claude_tests.MODEL
ORACLE = v3_tests.ORACLE
RUBRIC = json.loads((V3 / "rubric.json").read_bytes())["families"]
SENTENCE = "Optional suggestions that only make a working plan more robust are not changes it needs; if that is all you have, the assessment is NO_BLOCKERS_FOUND."


class FrozenFilesTests(unittest.TestCase):
    def test_the_manifests_are_current_and_tie_the_run_to_the_corpus_the_arm_and_the_prompt(self):
        self.assertEqual(RUN_MANIFEST.read_bytes(), bm.build())
        self.assertEqual((ARM_DIR / "manifest.json").read_bytes(), arm_bm.build())
        manifest = json.loads(RUN_MANIFEST.read_bytes())
        self.assertEqual(manifest["corpus"]["manifestSha256"], rc.rp.sha((V3 / "manifest.json").read_bytes()))
        self.assertEqual(sorted(manifest["arms"]), ["skill", "skill-go"])
        self.assertEqual(manifest["arms"]["skill"]["systemPromptSha256"], rc.rp.sha(rc.SYSTEM_PROMPT.encode("utf-8")))
        self.assertEqual(manifest["arms"]["skill-go"]["manifestSha256"], rc.rp.sha((ARM_DIR / "manifest.json").read_bytes()))
        self.assertEqual(json.loads((ARM_DIR / "manifest.json").read_bytes())["systemPromptSha256"], rc.rp.sha(rc.SYSTEM_PROMPT.encode("utf-8")))
        self.assertEqual(sorted(manifest["pins"]), ["PREREGISTRATION.md"])

    def test_the_sentence_is_the_defined_go_sentence_with_only_the_verdict_word_changed(self):
        defined = (PARENT / "ablation/defined-go/defined-go-request.txt").read_text(encoding="utf-8")
        original = [line for line in defined.splitlines() if line.startswith("Optional suggestions")]
        self.assertEqual(len(original), 1)
        self.assertEqual(original[0].replace("the verdict is GO", "the assessment is NO_BLOCKERS_FOUND"), SENTENCE)
        self.assertEqual((ARM_DIR / "skill-go-sentence.txt").read_text(encoding="utf-8"), SENTENCE + "\n")

    def test_every_request_is_the_skill_style_request_plus_exactly_the_sentence_line(self):
        skill, skill_go = rc.load_arm("skill"), rc.load_arm("skill-go")
        prompt = (V3 / "prompt.txt").read_text(encoding="utf-8")
        for packet in sorted((V3 / "packets").glob("*.txt")):
            lines = packet.read_text(encoding="utf-8").split("\n")[:-1]
            base = skill["build"](prompt, lines).decode("utf-8").split("\n")
            added = skill_go["build"](prompt, lines).decode("utf-8").split("\n")
            self.assertEqual(len(added), len(base) + 1)
            index = added.index(SENTENCE)
            self.assertEqual(added[:index] + added[index + 1:], base)
            self.assertEqual(index, len(prompt.rstrip("\n").split("\n")))     # directly after the corpus prompt, before the snapshot
        self.assertEqual((skill_go["system"], skill_go["parse"]), (skill["system"], skill["parse"]))

    def test_the_brief_names_the_current_hashes(self):
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for path in (RUN_MANIFEST, V3 / "manifest.json", ARM_DIR / "manifest.json"):
            self.assertIn(rc.rp.sha(path.read_bytes()), brief, str(path))

    def test_the_earlier_run_manifest_and_arm_manifests_are_untouched(self):
        self.assertEqual(rc.rp.sha((PARENT / "v3-run/manifest.json").read_bytes()), "3751f9acabeb2d60acfd6dd132db8079cc66c7b4ffc14a0ed7a4628d8e4d2f6a")
        self.assertEqual(rc.rp.sha((PARENT / "ablation/defined-go/manifest.json").read_bytes()), "b628683f9140c2c20c4f583c672244b15a99fd4a3c007efc348bb7ee68b0f356")

    def test_the_arm_refuses_a_changed_sentence_or_system_prompt(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "skill-go"
            shutil.copytree(ARM_DIR, copy, ignore=shutil.ignore_patterns("__pycache__"))
            original = rc.SKILL_GO
            try:
                rc.SKILL_GO = copy
                self.assertEqual(rc.load_arm("skill-go")["name"], "skill-go")
                (copy / "skill-go-sentence.txt").write_text(SENTENCE.replace("more robust", "more rigid") + "\n", encoding="utf-8")
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_arm("skill-go")
                self.assertEqual(str(raised.exception), "ABLATION_PIN_MISMATCH:skill-go-sentence.txt")
                shutil.copy(ARM_DIR / "skill-go-sentence.txt", copy / "skill-go-sentence.txt")
                manifest = json.loads((copy / "manifest.json").read_bytes())
                manifest["systemPromptSha256"] = "0" * 64
                (copy / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_arm("skill-go")
                self.assertEqual(str(raised.exception), "ABLATION_SYSTEM_PROMPT_MISMATCH")
            finally:
                rc.SKILL_GO = original

    def test_load_run_refuses_a_tampered_manifest_or_arm_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            copy = Path(tmp) / "run"
            shutil.copytree(HERE, copy, ignore=shutil.ignore_patterns("__pycache__"))
            self.assertTrue(rc.load_run(copy / "manifest.json")["sha256"])
            manifest = json.loads((copy / "manifest.json").read_bytes())
            for edit, expected in ((lambda m: m["arms"]["skill-go"].update(manifestSha256="0" * 64), "RUN_ARM_MANIFEST_MISMATCH:skill-go"),
                                   (lambda m: m["pins"].update({"PREREGISTRATION.md": "0" * 64}), "RUN_PIN_MISMATCH:PREREGISTRATION.md")):
                tampered = json.loads(json.dumps(manifest))
                edit(tampered)
                (copy / "manifest.json").write_text(json.dumps(tampered), encoding="utf-8")
                with self.assertRaises(rc.rp.Stop) as raised:
                    rc.load_run(copy / "manifest.json")
                self.assertEqual(str(raised.exception), expected)


class BindingTests(unittest.TestCase):
    def run_arm(self, tmp, arm, *extra, corpus=V3, manifest=RUN_MANIFEST):
        h = claude_tests.Harness(tmp)
        (h.bin.parent / "stub-config.json").write_text(json.dumps({"mode": "ok", "log": str(h.log), "model": MODEL, "verdict": "GO"}))
        args = ["--arm", arm, "--corpus", str(corpus)] + (["--run-manifest", str(manifest)] if manifest else []) + list(extra)
        code, out = h.run(*args)
        return h, code, out

    def test_both_arms_run_the_v3_corpus_under_the_run_manifest_and_verify(self):
        run_sha = rc.rp.sha(RUN_MANIFEST.read_bytes())
        for arm in ("skill-go", "skill"):
            with tempfile.TemporaryDirectory() as tmp:
                h, code, out = self.run_arm(tmp, arm, "--execute")
                self.assertEqual((code, out["executed"], out["arm"], out["runManifestSha256"]), (0, 64, arm, run_sha), arm)
                rows = h.ledger()
                self.assertTrue(all(r["runManifestSha256"] == run_sha and r["arm"] == arm for r in rows))
                if arm == "skill-go":
                    self.assertTrue(all(r["armManifestSha256"] == rc.rp.sha((ARM_DIR / "manifest.json").read_bytes()) for r in rows))
                self.assertEqual(vr.verify(V3, h.work, MODEL, "high", [1], arm, RUN_MANIFEST)["failures"], [], arm)

    def test_the_saved_request_carries_the_sentence_and_the_verifier_catches_one_without_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _, _ = self.run_arm(tmp, "skill-go", "--execute")
            case = h.ledger()[0]["case"]
            request = h.work / "trial1/attempts" / case / "request.txt"
            self.assertIn(SENTENCE, request.read_text(encoding="utf-8"))
            request.write_text(request.read_text(encoding="utf-8").replace(SENTENCE + "\n", ""), encoding="utf-8")
            self.assertIn(f"REQUEST_MISMATCH:trial1:{case}", vr.verify(V3, h.work, MODEL, "high", [1], "skill-go", RUN_MANIFEST)["failures"])

    def test_the_arm_cannot_run_without_a_run_manifest_or_on_another_corpus_or_under_another_runs_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_arm(tmp, "skill-go", manifest=None)
            self.assertEqual((code, out["reason"]), (1, "RUN_MANIFEST_REQUIRED"))
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_arm(tmp, "skill-go", corpus=V2)
            self.assertEqual((code, out["reason"]), (1, "RUN_CORPUS_MISMATCH"))
        with tempfile.TemporaryDirectory() as tmp:
            h, code, out = self.run_arm(tmp, "skill-go", manifest=PARENT / "v3-run/manifest.json")
            self.assertEqual((code, out["reason"]), (1, "RUN_ARM_NOT_BOUND"))

    def test_the_verifier_catches_a_wrong_arm_or_a_missing_run_binding(self):
        with tempfile.TemporaryDirectory() as tmp:
            h, _, _ = self.run_arm(tmp, "skill-go", "--execute")
            self.assertTrue(vr.verify(V3, h.work, MODEL, "high", [1], "skill", RUN_MANIFEST)["failures"])
            self.assertIn("RUN_MANIFEST_REQUIRED", vr.verify(V3, h.work, MODEL, "high", [1], "skill-go")["failures"])   # the arm names no corpus of its own


def ideal_with_noise(overrides):
    def policy(truth):
        return overrides.get(truth["expectedClass"], v3_tests.ideal(truth))
    return policy


class AnalysisTests(unittest.TestCase):
    def run_analysis(self, policies, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            arms = {}
            for name, policy in policies.items():
                directory = Path(tmp) / name
                v3_tests.write_arm(directory, policy)
                arms[name] = directory
            return an.analyze(V3, arms, RUBRIC, **kw)

    def test_the_sentence_that_cures_hedging_and_keeps_everything_else_is_labelled_so(self):
        result = self.run_analysis({"skill": v3_tests.hedger, "skill-go": v3_tests.ideal})
        labels = result["labels"]
        self.assertEqual((labels["soundPlanHedging"], labels["defectTwins"], labels["wavedThrough"]), ("reduced", "held", "does not wave gaps through"))
        self.assertEqual((labels["evidenceGapGoWithChanges"], labels["overclaiming"]), ("no significant difference", "not detected"))
        block = result["comparisons"]["skill__skill-go"]
        self.assertEqual((block["soundGo"]["onlyFirst"], block["soundGo"]["onlySecond"]), (0, 64))

    def test_a_sentence_that_waves_gaps_through_is_labelled_with_the_cost(self):
        result = self.run_analysis({"skill": v3_tests.ideal, "skill-go": v3_tests.waves_through_gaps})
        labels = result["labels"]
        self.assertEqual((labels["wavedThrough"], labels["evidenceGapGoWithChanges"]), ("waves gaps through", "skill better"))
        self.assertEqual(result["arms"]["skill-go"]["secondary"]["evidenceGapTwinsGo"]["count"], 32)

    def test_a_sentence_that_softens_defects_loses_them(self):
        result = self.run_analysis({"skill": v3_tests.ideal, "skill-go": v3_tests.softens_defects})
        self.assertEqual(result["labels"]["defectTwins"], "lost")

    def test_overclaiming_is_read_in_both_directions(self):
        overclaims = ideal_with_noise({"UNCERTAIN": "BLOCKERS_FOUND"})
        reduced = self.run_analysis({"skill": overclaims, "skill-go": v3_tests.ideal})
        self.assertEqual((reduced["labels"]["overclaiming"], reduced["overclaimPaired"]["onlyFirst"], reduced["overclaimPaired"]["onlySecond"]), ("reduced", 32, 0))
        increased = self.run_analysis({"skill": v3_tests.ideal, "skill-go": overclaims})
        self.assertEqual(increased["labels"]["overclaiming"], "increased")

    def test_the_comparison_with_the_plain_request_sentence_arm_is_labelled_and_the_arm_order_does_not_matter(self):
        policies = {"defined-go": v3_tests.waves_through_gaps, "skill-go": v3_tests.ideal, "skill": v3_tests.hedger}
        result = self.run_analysis(policies)
        self.assertEqual(result["labels"]["againstdefined-go"], {"evidenceGapGoWithChanges": "skill-go better", "soundPlansGo": "no significant difference"})
        self.assertEqual(result["labels"]["soundPlanHedging"], "reduced")

    def test_skill_go_and_skill_are_both_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            v3_tests.write_arm(Path(tmp) / "skill-go", v3_tests.ideal)
            with self.assertRaises(an.sc.Invalid):
                an.analyze(V3, {"skill-go": Path(tmp) / "skill-go"}, RUBRIC)


class RunScriptTests(unittest.TestCase):
    """The gated helper script: its pinned expectations match the repository, it refuses ungated live runs, and its dry run makes no model call."""
    SCRIPT = HERE / "run.sh"

    def sh(self, *args, claude_version="2.1.306 (Claude Code)", root=None):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            stub = Path(tmp) / "claude"
            stub.write_text(f'#!/bin/sh\necho "{claude_version}"\n', encoding="utf-8")
            stub.chmod(0o755)
            env = dict(os.environ, CLAUDE=str(stub), ROOT=str(root or Path(tmp) / "root"))
            done = subprocess.run(["bash", str(self.SCRIPT), *args], capture_output=True, text=True, env=env, cwd=REPO, check=False, timeout=300)
            return done.returncode, done.stdout, done.stderr

    def test_the_pinned_expectations_match_the_repository(self):
        text = self.SCRIPT.read_text(encoding="utf-8")
        for name, path in (("EXPECT_CORPUS_SHA", V3 / "manifest.json"), ("EXPECT_RUN_SHA", RUN_MANIFEST), ("EXPECT_ARM_SHA", ARM_DIR / "manifest.json")):
            self.assertIn(f"{name}={rc.rp.sha(path.read_bytes())}", text)
        self.assertIn("EXPECT_CLAUDE_SHA=520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe", text)
        self.assertTrue(self.SCRIPT.stat().st_mode & 0o111)

    def test_a_live_run_needs_the_go_flag_and_a_valid_run_number(self):
        code, out, err = self.sh("live", "1")
        self.assertEqual(code, 2)
        self.assertIn("REFUSED", err)
        code, out, err = self.sh("live", "5", "--go")
        self.assertEqual(code, 2)
        self.assertIn("RUN_MUST_BE_1_TO_4", err)
        code, out, err = self.sh()
        self.assertEqual(code, 2)

    def test_the_checks_stop_on_a_wrong_claude_version_before_anything_else(self):
        code, out, err = self.sh("checks", claude_version="9.9.9")
        self.assertEqual(code, 1)
        self.assertIn("MISMATCH:claude-version", err)

    def test_the_dry_run_prepares_both_arms_and_shows_only_the_sentence_as_the_difference(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.sh("dry", root=Path(tmp) / "r")
            self.assertEqual(code, 0, err)
            self.assertEqual(out.count("DRY_RUN_PREPARED_ONLY"), 2)
            diff = [line for line in out.split("--- the only difference")[1].splitlines() if line.startswith(("<", ">"))]
            self.assertEqual(diff, ["< " + SENTENCE])
            self.assertEqual(len(list((Path(tmp) / "r/work-skill-go/trial1/dry-requests").iterdir())), 64)
            self.assertFalse((Path(tmp) / "r/work-skill-go/responses-trial1.jsonl").exists())

    def test_bundling_without_any_run_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out, err = self.sh("bundle", root=Path(tmp) / "empty")
            self.assertEqual(code, 1)
            self.assertIn("NOTHING_TO_BUNDLE", err)


if __name__ == "__main__":
    unittest.main()
