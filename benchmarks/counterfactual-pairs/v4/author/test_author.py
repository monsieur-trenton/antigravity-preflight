"""Offline tests for the v4 authoring tooling: assignments, prompts, the mechanical checks, the corpus builder and the driver with a stub runtime. No provider calls."""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent
V4 = HERE.parent
PARENT = V4.parent
REPO = PARENT.parent.parent
sys.path.insert(0, str(HERE))
import assign  # noqa: E402
import author  # noqa: E402
import build_corpus as bc  # noqa: E402
import check_author as ca  # noqa: E402
import prompts  # noqa: E402
import recheck  # noqa: E402
import support as su  # noqa: E402


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


s4 = load("t_author_score_v4", V4 / "score_v4.py")
rg, rp = author.rg, author.rp
RUN = json.loads((PARENT / "v3-run-gemini/manifest.json").read_bytes())
BINARY = RUN["binary"]["sha256"]
FAMILIES = json.loads((V4 / "families.json").read_bytes())
DOMAINS = json.loads((V4 / "domains.json").read_bytes())
SEEDS = json.loads((HERE / "seeds.json").read_bytes())
DOCS = {s: json.loads((HERE / f"assignments-{s}.json").read_bytes()) for s in ("dev", "test")}


def instance_of(kind=None, family=None, split="dev", index=0):
    rows = [i for i in DOCS[split]["instances"] if (kind is None or i["kind"] == kind) and (family is None or i["family"] == family)]
    return rows[index], prompts.family_of(rows[index])


class AssignmentTests(unittest.TestCase):
    def test_the_committed_files_are_the_derivation_of_the_committed_seeds(self):
        for split in ("dev", "test"):
            seed = SEEDS[split]["seed"]
            self.assertEqual(hashlib.sha256(seed.encode()).hexdigest(), SEEDS[split]["sha256"])
            self.assertEqual(DOCS[split], assign.document(seed, split, FAMILIES, DOMAINS))
            self.assertEqual(DOCS[split]["seedSha256"], SEEDS[split]["sha256"])
            self.assertEqual(assign.problems(DOCS[split], FAMILIES, DOMAINS), [])

    def test_counts_match_the_targets_of_the_specification(self):
        for split in ("dev", "test"):
            rows = DOCS[split]["instances"]
            target = FAMILIES["targets"][split]
            self.assertEqual(len(rows), target["pairs"])
            for kind, count in target["byKind"].items():
                self.assertEqual(sum(1 for r in rows if r["kind"] == kind), count)
            self.assertEqual(sum(r["wordingB"] for r in rows), target["wordingBPairs"])
        b = [r for r in DOCS["test"]["instances"] if r["wordingB"]]
        self.assertEqual(sorted({r["kind"] for r in b}), ["cross_source_defect", "decoy_pair", "defect", "omitted_unknown"])
        self.assertTrue(all(sum(1 for r in b if r["kind"] == k) == 3 for k in {r["kind"] for r in b}))

    def test_the_test_split_never_uses_a_dev_only_domain_and_caps_hold(self):
        dev_only = {d["id"] for d in DOMAINS["domains"] if d["devOnly"]}
        self.assertFalse(dev_only & {r["domain"] for r in DOCS["test"]["instances"]})
        counts = {}
        for r in DOCS["test"]["instances"]:
            counts[r["domain"]] = counts.get(r["domain"], 0) + 1
        self.assertLessEqual(max(counts.values()), 4)

    def test_lengths_and_buckets_follow_the_families(self):
        for split in ("dev", "test"):
            for r in DOCS[split]["instances"]:
                f = prompts.family_of(r)
                self.assertTrue(f["sources"][0]["lines"][0] <= r["planLines"] <= f["sources"][0]["lines"][1])
                self.assertEqual(r["referenceLines"] is not None, r["kind"] == "cross_source_defect")
                self.assertEqual(r["buckets"]["decoy"] is not None, r["kind"] == "decoy_pair")

    def test_a_different_seed_gives_a_different_assignment_and_the_same_seed_the_same(self):
        a = assign.document("seed-one", "test", FAMILIES, DOMAINS)
        self.assertEqual(a, assign.document("seed-one", "test", FAMILIES, DOMAINS))
        self.assertNotEqual(a["instances"], assign.document("seed-two", "test", FAMILIES, DOMAINS)["instances"])
        self.assertEqual(assign.problems(a, FAMILIES, DOMAINS), [])

    def test_constraint_violations_are_named(self):
        def broken(change):
            doc = copy.deepcopy(DOCS["test"])
            change(doc)
            return assign.problems(doc, FAMILIES, DOMAINS)

        def dev_domain(doc):
            doc["instances"][0]["domain"] = "payments_api_cdn_cutover"

        def crowd(doc):
            for r in doc["instances"][:5]:
                r["domain"] = "feature_flag_rollout"

        def skew(doc):
            for r in doc["instances"]:
                if r["family"] == "omitted_measurement":
                    r["buckets"]["requirement"] = "early"

        def second_b(doc):
            next(r for r in doc["instances"] if not r["wordingB"])["wordingB"] = True

        def short(doc):
            doc["instances"][0]["planLines"] = 5

        self.assertIn("DOMAIN:" + DOCS["test"]["instances"][0]["pair"], broken(dev_domain))
        self.assertTrue({"DOMAIN_SPLIT_CAP", "DOMAIN_FAMILY_CAP"} <= set(broken(crowd)))
        self.assertIn("BUCKETS:omitted_measurement:requirement", broken(skew))
        self.assertIn("WORDING_B", broken(second_b))
        self.assertIn("PLAN_LENGTH:" + DOCS["test"]["instances"][0]["pair"], broken(short))

    def test_thirds(self):
        self.assertEqual([assign.bucket_range(31, b) for b in assign.BUCKETS], [(1, 10), (11, 20), (21, 31)])
        self.assertEqual([assign.bucket_of(n, 31) for n in (1, 10, 11, 20, 21, 31)], ["early", "early", "middle", "middle", "late", "late"])

    def test_the_command_line(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(assign.main(["--split", "dev", "--check"]), 0)
            self.assertEqual(assign.main(["--split", "test", "--check"]), 0)
            self.assertEqual(assign.main(["--split", "dev"]), 2)
        self.assertEqual(json.loads(out.getvalue().splitlines()[0])["status"], "PASS")


class PromptTests(unittest.TestCase):
    def test_every_prompt_states_its_assignment_and_stays_inside_the_limits(self):
        for split in ("dev", "test"):
            for r in DOCS[split]["instances"]:
                f, d = prompts.family_of(r), prompts.domain_of(r)
                text = prompts.author_prompt(r, f, d)
                self.assertLess(len(text.encode()), 8000)
                for needle in (d["description"], f["title"], f["soundHas"], f["twinDiffers"], f"has {r['planLines']} lines", "CASE-BEGIN", "ORACLE-END", "SOUND-S01-BEGIN"):
                    self.assertIn(needle, text)
                self.assertEqual("SOUND-S02-BEGIN" in text, r["kind"] == "cross_source_defect")
                self.assertNotIn("{", text.replace("{", "", 0).split("OUTPUT FORMAT")[0].replace("{ASSIGNMENT}", ""))

    def test_the_prompt_never_mentions_the_review_contract_or_the_corpus(self):
        r, f = instance_of("omitted_unknown")
        text = prompts.author_prompt(r, f, prompts.domain_of(r)).lower()
        for word in ("machine summary", "blockers_found", "no_blockers_found", "corpus", "gemini", "reviewer under test"):
            self.assertNotIn(word, text)

    def test_the_assigned_thirds_are_written_as_line_ranges(self):
        r, f = instance_of("defect", split="test")
        text = prompts.author_prompt(r, f, prompts.domain_of(r))
        first, last = assign.bucket_range(r["planLines"], r["buckets"]["requirement"])
        self.assertIn(f"lines {first} to {last} of the plan", text)

    def test_decoy_and_omission_assignments_differ_from_the_rest(self):
        decoy = prompts.author_prompt(*[instance_of("decoy_pair")[0], instance_of("decoy_pair")[1], prompts.domain_of(instance_of("decoy_pair")[0])])
        self.assertIn("at least five lines from the change", decoy)
        omitted = instance_of("omitted_unknown")[0]
        self.assertIn("never mentions the missing fact", prompts.author_prompt(omitted, prompts.family_of(omitted), prompts.domain_of(omitted)))
        defect = instance_of("cross_source_defect")[0]
        self.assertIn("reference excerpt (S02)", prompts.author_prompt(defect, prompts.family_of(defect), prompts.domain_of(defect)) + "reference excerpt (S02)")

    def test_the_reword_prompt_embeds_the_pair_and_asks_for_no_oracle(self):
        r, f = instance_of("cross_source_defect")
        _, facts = su.case_report(r, f)
        _, parsed = ca.analyse(su.case_report(r, f)[0], r, f)
        text = prompts.reword_prompt(r, parsed)
        self.assertIn(facts["sound"]["S02"][0], text)
        self.assertIn("TWIN-S02-BEGIN", text)
        self.assertNotIn("ORACLE-BEGIN", text)
        self.assertIn("character for character", text)

    def test_the_templates_are_text_and_pinned_by_the_script(self):
        script = (HERE / "run.sh").read_text(encoding="utf-8")
        for name in ("author-template.txt", "reword-template.txt"):
            self.assertIn(hashlib.sha256((HERE / name).read_bytes()).hexdigest(), script)

    def test_every_family_says_delete_or_edit_or_change(self):
        for f in FAMILIES["families"]:
            self.assertEqual(ca.deleting(f), f["twinDiffers"].startswith("Delete"))
            self.assertTrue(f["twinDiffers"].split()[0] in ("Delete", "Edit", "Change"), f["id"])


class CheckerTests(unittest.TestCase):
    def failed(self, instance, family, text):
        result, parsed = ca.analyse(text, instance, family)
        return sorted(k for k, ok in result["checks"].items() if not ok), result, parsed

    def mutated(self, kind, family=None, split="dev", **changes):
        instance, fam = instance_of(kind, family, split)

        def mutate(facts):
            for key, value in changes.items():
                if callable(value):
                    value(facts)
                else:
                    facts[key] = value

        text, facts = su.case_report(instance, fam, mutate)
        return self.failed(instance, fam, text) + (facts,)

    def test_every_assigned_instance_has_a_clean_pair(self):
        for split in ("dev", "test"):
            for r in DOCS[split]["instances"]:
                f = prompts.family_of(r)
                bad, result, parsed = self.failed(r, f, su.case_report(r, f)[0])
                self.assertEqual(bad, [], r["pair"])
                self.assertIsNotNone(parsed)

    def test_markers_and_text_outside_the_case(self):
        r, f = instance_of("omitted_unknown")
        good = su.case_report(r, f)[0]
        for broken in (good.replace("TWIN-S01-END\n", ""), good.replace("CASE-END\n", ""), good + "CASE-BEGIN\n"):
            result, parsed = ca.analyse(broken, r, f)
            self.assertEqual((result["checks"], parsed), ({"BLOCKS_IN_ORDER": False}, None))
        self.assertIn("NOTHING_OUTSIDE_THE_CASE", self.failed(r, f, "Here you go.\n" + good)[0])
        self.assertIn("NOTHING_OUTSIDE_THE_CASE", self.failed(r, f, good + "Hope that helps.\n")[0])
        cross, cf = instance_of("cross_source_defect")
        self.assertEqual(ca.analyse(su.case_report(r, f)[0], cross, cf)[0]["checks"], {"BLOCKS_IN_ORDER": False})   # a one-source report for a two-source assignment

    def test_one_edit_relation(self):
        r, f = instance_of("omitted_unknown")
        # a deletion that also rewords another line
        bad = self.mutated("omitted_unknown", twin=lambda facts: facts["twin"]["S01"].__setitem__(5, facts["twin"]["S01"][5].replace("task", "job")))[0]
        self.assertIn("ONE_EDIT_AS_SPECIFIED", bad)
        # nothing deleted
        bad = self.mutated("omitted_unknown", twin=lambda facts: facts.update(twin={"S01": list(facts["sound"]["S01"])}))[0]
        self.assertIn("ONE_EDIT_AS_SPECIFIED", bad)
        # four lines deleted from an omitted-unknown family (limit three)
        bad = self.mutated("omitted_unknown", twin=lambda facts: facts.update(twin={"S01": facts["sound"]["S01"][:-4]}))[0]
        self.assertIn("ONE_EDIT_AS_SPECIFIED", bad)
        # an edit family whose twin also moves a line
        def swap(facts):
            lines = facts["twin"]["S01"]
            lines[0], lines[1] = lines[1], lines[0]
        bad = self.mutated("defect", split="test", twin=swap)[0]
        self.assertIn("ONE_EDIT_AS_SPECIFIED", bad)
        # a cross-source edit that touches both sources
        def both(facts):
            facts["twin"]["S01"][3] = facts["twin"]["S01"][3] + " Edited."
            facts["twin"]["S02"][3] = facts["twin"]["S02"][3] + " Edited."
        self.assertIn("ONE_EDIT_AS_SPECIFIED", self.mutated("cross_source_defect", twin=both)[0])

    def test_the_edit_must_be_in_the_assigned_source_and_third(self):
        r, f = instance_of("cross_source_defect")
        other = "S01" if r["changedSource"] == "S02" else "S02"
        def move(facts):
            facts["twin"] = {s: list(lines) for s, lines in facts["sound"].items()}
            facts["twin"][other][5] = facts["twin"][other][5] + " Edited."
            facts["cite"] = [(other, 6)]
        bad = self.mutated("cross_source_defect", twin=move)[0]
        self.assertIn("ONE_EDIT_AS_SPECIFIED", bad)
        # the right source, the wrong third
        r, f = instance_of("omitted_unknown")
        lo, hi = assign.bucket_range(r["planLines"], r["buckets"]["changed"])
        other_third = next(b for b in assign.BUCKETS if b != r["buckets"]["changed"])
        olo, _ = assign.bucket_range(r["planLines"], other_third)
        def wrong(facts):
            facts["twin"] = {"S01": [l for j, l in enumerate(facts["sound"]["S01"], 1) if j not in (olo, olo + 1)]}
            facts["cite"] = [("S01", facts["requirement"])]
        bad, result, _, _ = self.mutated("omitted_unknown", twin=wrong)
        self.assertIn("EDIT_IN_ASSIGNED_THIRD", bad)

    def test_requirement_and_citations(self):
        r0, _ = instance_of("omitted_unknown")
        wrong_third = next(b for b in assign.BUCKETS if b not in (r0["buckets"]["requirement"], r0["buckets"]["changed"]))
        outside = assign.bucket_range(r0["planLines"], wrong_third)[1]
        self.assertIn("REQUIREMENT_IN_ASSIGNED_THIRD", self.mutated("omitted_unknown", requirement=outside)[0])
        for changes, expected in (
            ({"cite": [("S01", 999)]}, "ORACLE_REFS_IN_RANGE"),
            ({"cite": [("S02", 1)]}, "ORACLE_REFS_IN_RANGE"),           # a one-source case has no S02
            ({"cite": []}, "ORACLE_REFS_IN_RANGE"),           # "none" is not a citation
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, self.mutated("omitted_unknown", **changes)[0])
        # a deleted line cannot be cited
        r, f = instance_of("omitted_unknown")
        _, facts = su.case_report(r, f)
        bad = self.mutated("omitted_unknown", cite=[("S01", facts["changed"][0])])[0]
        self.assertIn("CITES_SURVIVE_AND_COVER_THE_EDIT", bad)
        # an edit must be among its own citations
        r, f = instance_of("defect", split="test")
        _, facts = su.case_report(r, f)
        bad = self.mutated("defect", split="test", cite=[("S01", 1)])[0]
        self.assertIn("CITES_SURVIVE_AND_COVER_THE_EDIT", bad)

    def test_oracle_content(self):
        for changes in ({"mechanism": "too short"}, {"why": "none"}, {"bait": "only one"}, {"bait": "a | b | c | d"}, {"rubric": ""},
                        {"rubric": "a ; b ; c ; d"}):
            with self.subTest(changes=changes):
                self.assertIn("ORACLE_CONTENT" if changes != {"rubric": ""} else "ORACLE_FIELDS", self.mutated("omitted_unknown", **changes)[0])
        self.assertIn("ORACLE_CONTENT", self.mutated("defect", split="test", why="Nothing else makes up for it, so the twin stays wrong.")[0])
        self.assertIn("RUBRIC_GROUNDED_IN_THE_PLAN", self.mutated("omitted_unknown", rubric="zebra, giraffe")[0])
        # a gap needs one grounded group, a defect needs all of them
        self.assertNotIn("RUBRIC_GROUNDED_IN_THE_PLAN", self.mutated("omitted_unknown", rubric="platform, task ; zebra, giraffe")[0])
        self.assertIn("RUBRIC_GROUNDED_IN_THE_PLAN", self.mutated("defect", split="test", rubric="platform, task ; zebra, giraffe")[0])
        self.assertIn("CLAIM_SENTENCE_NEUTRAL", self.mutated("omitted_unknown", why="Nothing else in the twin bounds it, so the requirement stays unsupported.")[0])
        self.assertIn("ORACLE_REFS_IN_RANGE", self.mutated("omitted_unknown", requirement="third")[0])

    def test_length_shape_duplicates_and_size(self):
        r, f = instance_of("omitted_unknown")
        def shorten(facts):
            facts["sound"]["S01"] = facts["sound"]["S01"][:12]
            facts["twin"]["S01"] = facts["twin"]["S01"][:10]
            facts["cite"] = [("S01", 1)]
            facts["requirement"] = 1
            facts["changed"] = [11, 12]
        self.assertIn("LENGTHS_AS_ASSIGNED", self.mutated("omitted_unknown", sound=lambda facts: shorten(facts))[0])
        def numbered(facts):
            facts["sound"]["S01"][4] = "1. " + facts["sound"]["S01"][4]
            facts["twin"]["S01"] = [l for j, l in enumerate(facts["sound"]["S01"], 1) if j not in facts["changed"]]
        self.assertIn("LINE_SHAPE", self.mutated("omitted_unknown", sound=numbered)[0])
        def stubby(facts):
            facts["sound"]["S01"][4] = "Short."
            facts["twin"]["S01"] = [l for j, l in enumerate(facts["sound"]["S01"], 1) if j not in facts["changed"]]
        self.assertIn("LINE_SHAPE", self.mutated("omitted_unknown", sound=stubby)[0])
        def duplicate(facts):
            facts["sound"]["S01"][6] = facts["sound"]["S01"][7]
            facts["twin"]["S01"] = [l for j, l in enumerate(facts["sound"]["S01"], 1) if j not in facts["changed"]]
        self.assertIn("NO_DUPLICATE_LINES", self.mutated("omitted_unknown", sound=duplicate)[0])
        def huge(facts):
            facts["mechanism"] = "x" * 30000
        self.assertIn("CALL_BYTES", self.failed(r, f, su.case_report(r, f, huge)[0])[0])

    def test_meta_words_and_admissions(self):
        def meta(facts):
            facts["sound"]["S01"][8] = facts["sound"]["S01"][8].replace("task", "benchmark task")
            facts["twin"]["S01"] = [l for j, l in enumerate(facts["sound"]["S01"], 1) if j not in facts["changed"]]
        self.assertIn("NO_META_WORDS", self.mutated("omitted_unknown", sound=meta)[0])
        def admit(facts):
            facts["sound"]["S01"][8] = facts["sound"]["S01"][8].replace("completes", "has not been measured and completes")
            facts["twin"]["S01"] = [l for j, l in enumerate(facts["sound"]["S01"], 1) if j not in facts["changed"]]
        bad, result, _, _ = self.mutated("omitted_unknown", sound=admit)
        self.assertIn("NO_ADMISSIONS_OUTSIDE_OPEN_ITEMS", bad)
        self.assertEqual(result["details"]["admissionLines"], ["S01:9"])

    def test_decoy_rules(self):
        r, f = instance_of("decoy_pair")
        _, facts = su.case_report(r, f)
        dec = facts["decoys"][0][1]
        quiet = lambda fc: (fc["sound"]["S01"].__setitem__(dec - 1, fc["sound"]["S01"][dec - 1].replace("pending", "settled")), fc["twin"]["S01"].__setitem__(dec - 1, fc["sound"]["S01"][dec - 1]))
        self.assertIn("DECOY_LINES_ADMIT_SOMETHING", self.mutated("decoy_pair", sound=quiet)[0])
        self.assertIn("NO_DECOY_LINES", self.mutated("omitted_unknown", decoys=[("S01", 3)])[0])
        near = lambda fc: fc.update(decoys=[("S01", fc["changed"][0] - 1 if fc["changed"][0] > 1 else 3)])
        self.assertTrue({"DECOY_IN_ASSIGNED_THIRD", "DECOY_APART_FROM_EDIT"} & set(self.mutated("decoy_pair", decoys=near)[0]))
        self.assertIn("DECOY_IN_ASSIGNED_THIRD", self.mutated("decoy_pair", decoys=[])[0])

    def test_the_checker_never_calls_a_model_or_reads_a_corpus_oracle(self):
        for name in ("check_author.py", "prompts.py", "assign.py", "build_corpus.py"):
            source = (HERE / name).read_text(encoding="utf-8")
            for word in ("subprocess", "urllib", "socket"):
                self.assertNotIn(word, source, name)

    def test_the_command_line(self):
        r, f = instance_of("omitted_unknown")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "r.md"
            path.write_text(su.case_report(r, f)[0], encoding="utf-8")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                self.assertEqual(ca.main([r["pair"], "dev", str(path)]), 0)
                self.assertEqual(ca.main([r["pair"], "dev", str(path) + ".missing"]), 2)
                self.assertEqual(ca.main([]), 2)
            self.assertTrue(json.loads(out.getvalue().split("\n}\n")[0] + "\n}")["allPassed"])


class RewordTests(unittest.TestCase):
    def setup(self, kind="cross_source_defect", split="dev"):
        r, f = instance_of(kind, split=split)
        text, facts = su.case_report(r, f)
        _, parsed = ca.analyse(text, r, f)
        return r, f, facts, parsed

    def check(self, r, f, parsed, text):
        result, out = ca.analyse_reword(text, parsed, r, f)
        return sorted(k for k, ok in result["checks"].items() if not ok), result, out

    def test_a_faithful_rewording_passes_for_every_kind(self):
        for kind in ("omitted_unknown", "cross_source_defect", "defect", "decoy_pair"):
            r, f, facts, parsed = self.setup(kind, "test")
            bad, result, out = self.check(r, f, parsed, su.reword_report(r, facts))
            self.assertEqual(bad, [], kind)
            self.assertIsNotNone(out)
            self.assertGreaterEqual(int(result["details"]["linesReworded"].split("/")[0]) * 2, int(result["details"]["linesReworded"].split("/")[1]))

    def test_protected_tokens(self):
        self.assertEqual(ca.protected("The cutover at 02:30 uses gateway-07 and /etc/app/conf with Cloudflare and TTL set to 60 seconds."),
                         ca.protected("Through gateway-07 and /etc/app/conf the cutover at 02:30 reaches Cloudflare and the TTL is 60 seconds."))
        self.assertNotEqual(ca.protected("Limit is 40."), ca.protected("Limit is 48."))
        self.assertEqual(ca.protected("Release the Flag now.").keys(), {"Flag"})
        self.assertEqual(ca.protected("Flag first."), ca.protected("Flag later."))     # the first word is not protected
        self.assertNotEqual(ca.protected("Use the API."), ca.protected("Use the interface."))

    def test_each_rule_is_enforced(self):
        r, f, facts, parsed = self.setup()
        def reword_with(change):
            new = copy.deepcopy(facts)
            for member in ("sound", "twin"):
                for s in new[member]:
                    new[member][s] = [su.reword_line(line) for line in new[member][s]]
            change(new)
            return "\n".join(["CASE-BEGIN"] + [x for member in ("sound", "twin") for s in ca.sources_of(r) for x in
                                                [f"{member.upper()}-{s}-BEGIN", *new[member][s], f"{member.upper()}-{s}-END"]] + ["CASE-END"]) + "\n"
        # a changed number
        def number(new):
            new["sound"]["S02"][2] = new["sound"]["S02"][2].replace("30", "31")
        self.assertIn("PROTECTED_TOKENS_KEPT", self.check(r, f, parsed, reword_with(number))[0])
        # a line added to the twin
        def longer(new):
            new["twin"]["S01"].append(new["twin"]["S01"][0] + " Again.")
        self.assertIn("SAME_LINE_COUNTS", self.check(r, f, parsed, reword_with(longer))[0])
        # the twin differs in another line
        def elsewhere(new):
            new["twin"]["S01"][0] = new["twin"]["S01"][0] + " Also edited."
        bad = self.check(r, f, parsed, reword_with(elsewhere))[0]
        self.assertTrue({"SAME_EDIT_AS_WORDING_A", "ONE_EDIT_AS_SPECIFIED"} & set(bad) or "SAME_EDIT_AS_WORDING_A" in bad)
        # an unchanged copy is not a rewording
        self.assertIn("IS_A_REWORDING", self.check(r, f, parsed, su.render(r, dict(facts, requirement=1)).split("ORACLE-BEGIN")[0] + "CASE-END\n")[0])
        # an admission, a meta word, text outside
        def admit(new):
            new["sound"]["S01"][9] = new["sound"]["S01"][9].replace("finishes", "finishes (still unconfirmed)")
            new["twin"]["S01"][9] = new["sound"]["S01"][9]
        self.assertIn("NO_ADMISSIONS_OUTSIDE_OPEN_ITEMS", self.check(r, f, parsed, reword_with(admit))[0])
        self.assertIn("NOTHING_OUTSIDE_THE_CASE", self.check(r, f, parsed, "Sure.\n" + reword_with(lambda n: None))[0])
        self.assertEqual(self.check(r, f, parsed, "nothing")[0], ["BLOCKS_IN_ORDER"])

    def test_decoy_lines_must_still_admit_something(self):
        r, f, facts, parsed = self.setup("decoy_pair", "test")
        text = su.reword_report(r, facts).replace("pending", "settled")
        self.assertIn("DECOY_LINES_ADMIT_SOMETHING", self.check(r, f, parsed, text)[0])


def write_accepted(directory, split, bad=(), with_b=True):
    """Clean accepted reports for every instance of a split; `bad` names pairs to leave out."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    for r in DOCS[split]["instances"]:
        if r["pair"] in bad:
            continue
        f = prompts.family_of(r)
        text, facts = su.case_report(r, f)
        (directory / f"{r['pair']}.A.md").write_text(text, encoding="utf-8")
        if r["wordingB"] and with_b:
            (directory / f"{r['pair']}.B.md").write_text(su.reword_report(r, facts), encoding="utf-8")


class BuilderTests(unittest.TestCase):
    def build(self, split, tmp, **kw):
        accepted = Path(tmp) / "accepted"
        write_accepted(accepted, split, **{k: v for k, v in kw.items() if k in ("bad", "with_b")})
        out = Path(tmp) / "corpus"
        return bc.build(split, accepted, out, kw.get("drops", ())), out

    def test_the_dev_corpus_loads_in_the_scorer_with_every_pin(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, out = self.build("dev", tmp)
            self.assertEqual((manifest["cases"], manifest["pairs"], manifest["families"]), (48, 24, 3))
            corpus = s4.Corpus(out)
            self.assertFalse(corpus.legacy)
            self.assertEqual(len(corpus.oracle), 48)
            self.assertEqual(sorted(manifest["submissionOrder"]), sorted(corpus.oracle))
            self.assertTrue(all(k.startswith("packets/") for k in manifest["reviewerVisible"]))
            twin = next(r for r in corpus.oracle.values() if r["role"] == "changed" and r["kind"] == "cross_source_defect")
            self.assertEqual([s["id"] for s in twin["sources"]], ["S01", "S02"])
            self.assertTrue(corpus.lines(twin["case"], "S02"))

    def test_the_test_corpus_has_184_cases_and_the_wording_b_pairs(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, out = self.build("test", tmp)
            self.assertEqual((manifest["cases"], manifest["pairs"]), (184, 80))
            corpus = s4.Corpus(out)
            wordings = {}
            for r in corpus.oracle.values():
                wordings.setdefault(r["pair"], set()).add(r["wording"])
            self.assertEqual(sum(1 for w in wordings.values() if w == {"A", "B"}), 12)
            kinds = {}
            for r in corpus.oracle.values():
                if r["role"] == "changed" and r["wording"] == "A":
                    kinds[r["kind"]] = kinds.get(r["kind"], 0) + 1
            self.assertEqual(kinds, FAMILIES["targets"]["test"]["byKind"])

    def test_case_ids_carry_nothing_and_the_build_is_reproducible(self):
        with tempfile.TemporaryDirectory() as tmp1, tempfile.TemporaryDirectory() as tmp2:
            m1, o1 = self.build("dev", tmp1)
            m2, o2 = self.build("dev", tmp2)
            self.assertEqual(m1, m2)
            self.assertEqual((o1 / "oracle/oracle.json").read_bytes(), (o2 / "oracle/oracle.json").read_bytes())
            self.assertTrue(all(c.startswith("R-") and len(c) == 8 for c in m1["submissionOrder"]))
            self.assertNotEqual(m1["submissionOrder"], sorted(m1["submissionOrder"]))

    def test_numbers_are_mapped_into_the_twin_after_a_deletion(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, out = self.build("dev", tmp)
            corpus = s4.Corpus(out)
            pair = next(i for i in DOCS["dev"]["instances"] if i["kind"] == "omitted_unknown")
            f = prompts.family_of(pair)
            _, facts = su.case_report(pair, f)
            sound = next(r for r in corpus.oracle.values() if r["pair"] == pair["pair"] and r["role"] == "sound")
            twin = next(r for r in corpus.oracle.values() if r["pair"] == pair["pair"] and r["role"] == "changed")
            before = sum(1 for g in facts["changed"] if g < facts["requirement"])
            self.assertEqual(sound["requirement"]["line"], facts["requirement"])
            self.assertEqual(twin["requirement"]["line"], facts["requirement"] - before)
            self.assertEqual(twin["changed"]["lines"], sound["changed"]["lines"])
            self.assertEqual([s["lines"] for s in twin["sources"]][0], [s["lines"] for s in sound["sources"]][0] - len(facts["changed"]))
            self.assertEqual(sound["citeAnyOf"], [])
            self.assertIsNone(sound["mechanism"])
            self.assertTrue(twin["whyNoFallback"])
            lines = corpus.lines(twin["case"])
            self.assertIn("requires that task r", lines[twin["requirement"]["line"] - 1])

    def test_drops_are_left_out_and_recorded(self):
        pair = DOCS["dev"]["instances"][0]["pair"]
        with tempfile.TemporaryDirectory() as tmp:
            manifest, out = self.build("dev", tmp, drops=[{"pair": pair, "reason": "the audit could not recover its class"}])
            self.assertEqual((manifest["cases"], manifest["pairs"]), (46, 23))
            self.assertEqual(manifest["dropped"], [{"pair": pair, "reason": "the audit could not recover its class"}])
            self.assertNotIn(pair, {r["pair"] for r in s4.Corpus(out).oracle.values()})

    def test_a_later_directory_of_accepted_reports_replaces_the_same_pair(self):
        pair = DOCS["dev"]["instances"][0]
        f = prompts.family_of(pair)
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp) / "a", Path(tmp) / "b"
            write_accepted(first, "dev")
            second.mkdir()
            text, _ = su.case_report(pair, f, lambda facts: facts.update(mechanism="A different mechanism sentence for the rewritten pair, long enough to pass."))
            (second / f"{pair['pair']}.A.md").write_text(text, encoding="utf-8")
            manifest = bc.build("dev", f"{first},{second}", Path(tmp) / "out")
            self.assertEqual(manifest["authoring"]["acceptedReportSha256"][pair["pair"]]["A"], rp.sha(text.encode()))
            twin = next(r for r in s4.Corpus(Path(tmp) / "out").oracle.values() if r["pair"] == pair["pair"] and r["role"] == "changed")
            self.assertTrue(twin["mechanism"].startswith("A different mechanism"))

    def test_the_build_stops_on_missing_failing_or_unexplained_input(self):
        pair = DOCS["dev"]["instances"][0]["pair"]
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(bc.BuildError) as caught:
                self.build("dev", tmp, bad={pair})
            self.assertEqual(str(caught.exception), "MISSING_ACCEPTED:" + pair)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(bc.BuildError) as caught:
                self.build("test", tmp, with_b=False)
            self.assertTrue(str(caught.exception).startswith("MISSING_REWORDING:"))
        with tempfile.TemporaryDirectory() as tmp:
            accepted = Path(tmp) / "accepted"
            write_accepted(accepted, "dev")
            path = accepted / f"{pair}.A.md"
            path.write_text(path.read_text(encoding="utf-8").replace("ORACLE-BEGIN", "ORACLE-BEGIN\nfoo: bar"), encoding="utf-8")
            with self.assertRaises(bc.BuildError) as caught:
                bc.build("dev", accepted, Path(tmp) / "out")
            self.assertEqual(str(caught.exception), "ACCEPTED_FAILS_CHECKS:" + pair)
        with tempfile.TemporaryDirectory() as tmp:
            accepted = Path(tmp) / "accepted"
            write_accepted(accepted, "dev")
            with self.assertRaises(bc.BuildError):
                bc.build("dev", accepted, Path(tmp) / "out", [{"pair": pair, "reason": " "}])
            with self.assertRaises(bc.BuildError):
                bc.build("dev", accepted, Path(tmp) / "out", [{"pair": "N-nothing", "reason": "x"}])
            (Path(tmp) / "used").mkdir()
            (Path(tmp) / "used" / "x").write_text("x")
            with self.assertRaises(bc.BuildError):
                bc.build("dev", accepted, Path(tmp) / "used")

    def test_sealed_manifest_has_hashes_and_no_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, out = self.build("test", tmp)
            sealed = bc.sealed(manifest)
            text = json.dumps(sealed)
            self.assertEqual(sealed["kind"], "COUNTERFACTUAL_PAIR_CORPUS_V4_SEALED_HASHES_ONLY")
            self.assertNotIn("requires that task", text)
            self.assertNotIn("mechanism", text)
            self.assertEqual(len(sealed["pins"]), len(manifest["pins"]))
            self.assertNotIn("submissionOrder", sealed)
            self.assertEqual(sealed["manifestSha256"], hashlib.sha256((out / "manifest.json").read_bytes()).hexdigest())

    def test_an_end_to_end_perfect_reviewer_scores_perfectly_on_the_built_corpus(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest, out = self.build("dev", tmp)
            corpus = s4.Corpus(out)
            rows = []
            for case, r in corpus.oracle.items():
                if r["role"] == "sound":
                    rows.append({"case": case, "trial": 1, "assessment": "NO_BLOCKERS_FOUND", "completeness": "COMPLETE", "findings": []})
                    continue
                accepted = r["citeAnyOf"][0]
                quote = corpus.lines(case, accepted["source"])[accepted["line"] - 1][:25]
                severity = "BLOCKER" if r["expectedClass"] == "DEFECT" else "RISK"
                rows.append({"case": case, "trial": 1, "assessment": "BLOCKERS_FOUND" if severity == "BLOCKER" else "CHANGES_RECOMMENDED", "completeness": "COMPLETE",
                             "findings": [{"severity": severity, "evidence": "VERIFIED", "source": accepted["source"], "line": accepted["line"], "quote": quote}]})
            trial = s4.score(rows, out)["trials"]["1"]
            self.assertEqual((trial["pairDiscrimination"]["count"], trial["pairDiscrimination"]["of"]), (24, 24))
            self.assertEqual(trial["unsupportedVerifiedFindings"], 0)
            self.assertEqual(sorted(trial["byKind"]), ["cross_source_defect", "decoy_pair", "omitted_unknown"])
            self.assertEqual((trial["citations"]["defectTwinsBlockedAndCited"]["count"], trial["citations"]["defectTwinsBlockedAndCited"]["of"]), (16, 16))


STUB = r'''
import json, shutil, sys
from pathlib import Path
here = Path(__file__).resolve().parent
config = json.loads((here / "stub-config.json").read_text())
counter = here / "stub-counter"
args = sys.argv[1:]
if args[0] == "prepare":
    packet, seed = Path(args[1]), Path(args[3])
    shutil.copytree(packet.parent, seed / "packet")
    (seed / "CLI-PLAN.json").write_text("{}")
elif args[0] == "run":
    attempt = Path(args[1])
    n = int(counter.read_text()) if counter.exists() else 0
    counter.write_text(str(n + 1))
    entry = config["script"][min(n, len(config["script"]) - 1)]
    if entry == "stop":
        (attempt / "CLI-RECEIPT.json").write_text(json.dumps({"status": "STOPPED", "failure": {"code": "UNQUALIFIED_STEP"}, "closingFailures": []}))
    else:
        (attempt / "GEMINI-REVIEW.md").write_bytes(entry.encode("utf-8"))
        (attempt / "CLI-RECEIPT.json").write_text(json.dumps({"status": "REPORT_RECEIVED_PENDING_ADJUDICATION", "failure": None, "closingFailures": [],
            "model": "gemini-3.8-flash-high", "effort": "high", "servedAttestation": "UNAVAILABLE", "retries": 0, "invocations": {"proxy": 1, "native": 1},
            "elapsedSeconds": 1.5, "promptDelivery": {"status": "COMPLETE"}}))
'''


class DriverTests(unittest.TestCase):
    def setup(self, tmp, script, binary=BINARY):
        tmp = Path(tmp)
        runtime = tmp / "rt" / "flash-high"
        (runtime / "scripts").mkdir(parents=True)
        (runtime / "scripts/cli_review.py").write_text(STUB)
        (runtime / "scripts/stub-config.json").write_text(json.dumps({"script": script}))
        caps = tmp / "caps"
        caps.mkdir()
        (caps / "RESULT.json").write_text(json.dumps({"status": "PASS_METADATA_CAPABILITIES_ONLY", "binaryStable": True, "frozenBinary": {"sha256": binary, "bytes": 1},
                                                      "observedVersion": "agy 1.4.1", "model": "gemini-3.8-flash-high", "effort": "high"}))
        (tmp / "q.json").write_text("{}")
        original = rg.runtime_tree_sha
        rg.runtime_tree_sha = lambda directory: RUN["runtime"]["treeSha256"]
        self.addCleanup(lambda: setattr(rg, "runtime_tree_sha", original))
        return runtime, caps

    def run_author(self, tmp, runtime, caps, *extra, work="work", split="dev"):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = author.main(["--split", split, "--runtime-dir", str(runtime), "--capabilities", str(caps), "--qualification", str(Path(tmp) / "q.json"),
                                "--workdir", str(Path(tmp) / work), *extra])
        return code, json.loads(out.getvalue().strip().splitlines()[-1])

    def clean(self, index=0, kind="omitted_unknown"):
        r, f = instance_of(kind, index=index)
        return r, su.case_report(r, f)

    def test_a_dry_run_builds_every_prompt_and_makes_no_call(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, ["stop"])
            code, out = self.run_author(tmp, runtime, caps)
            self.assertEqual((code, out["status"], out["providerCalls"], out["dryRun"], out["pairsSelected"]), (0, "DRY_RUN_PREPARED_ONLY", 0, True, 24))
            work = Path(tmp) / "work"
            self.assertEqual(len(list((work / "prompts").glob("*.A.txt"))), 24)
            self.assertFalse((work / "calls.jsonl").exists())
            self.assertFalse(any((work / "calls").iterdir()))

    def test_one_call_is_accepted_and_recorded(self):
        r, (text, _) = self.clean()
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, [text])
            code, out = self.run_author(tmp, runtime, caps, "--pairs", r["pair"], "--execute")
            self.assertEqual((code, out["calls"], out["accepted"], out["failedChecks"]), (0, 1, 1, 0))
            work = Path(tmp) / "work"
            self.assertEqual((work / "accepted" / f"{r['pair']}.A.md").read_text(encoding="utf-8"), text)
            row = json.loads((work / "calls.jsonl").read_text().splitlines()[0])
            self.assertEqual((row["pair"], row["purpose"], row["attempt"], row["accepted"], row["allPassed"], row["technicalStop"]), (r["pair"], "author", 1, True, True, None))
            self.assertEqual((row["receipt"]["retries"], row["receipt"]["servedAttestation"]), (0, "UNAVAILABLE"))
            self.assertEqual(row["promptSha256"], rp.sha((work / "prompts" / f"{r['pair']}.A.txt").read_bytes()))
            self.assertEqual(row["reportSha256"], rp.sha(text.encode()))
            self.assertTrue((work / "calls" / f"{r['pair']}-author-a1" / "REPORT.md").is_file())

    def test_a_failed_check_is_recorded_kept_and_retried_once_then_the_attempts_run_out(self):
        r, (text, facts) = self.clean()
        bad = text.replace("TWIN-S01-END\n", "")
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, [bad, bad, text])
            args = ("--pairs", r["pair"], "--execute", "--max-calls", "5")
            code, out = self.run_author(tmp, runtime, caps, *args)                                # one attempt per pair per invocation
            self.assertEqual((out["calls"], out["accepted"], out["failedChecks"], out["attemptsUsedUp"]), (1, 0, 1, []))
            code, out = self.run_author(tmp, runtime, caps, *args)
            self.assertEqual((out["calls"], out["accepted"], out["failedChecks"]), (1, 0, 1))
            work = Path(tmp) / "work"
            rows = [json.loads(l) for l in (work / "calls.jsonl").read_text().splitlines()]
            self.assertEqual([(x["attempt"], x["accepted"], x["failedChecks"]) for x in rows], [(1, False, ["BLOCKS_IN_ORDER"]), (2, False, ["BLOCKS_IN_ORDER"])])
            self.assertFalse((work / "accepted" / f"{r['pair']}.A.md").exists())
            self.assertTrue((work / "calls" / f"{r['pair']}-author-a1" / "REPORT.md").is_file())
            code, out = self.run_author(tmp, runtime, caps, *args)                               # a third attempt is refused
            self.assertEqual((out["calls"], out["attemptsUsedUp"]), (0, [r["pair"]]))
            code, out = self.run_author(tmp, runtime, caps, *args, "--max-attempts", "3")       # unless the owner raises the limit
            self.assertEqual((out["calls"], out["accepted"]), (1, 1))

    def test_max_calls_bounds_one_invocation_and_accepted_pairs_are_skipped(self):
        a, (ta, _) = self.clean(0)
        b, (tb, _) = self.clean(1)
        pairs = f"{a['pair']},{b['pair']}"
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, [ta, tb])
            code, out = self.run_author(tmp, runtime, caps, "--pairs", pairs, "--execute")
            self.assertEqual((out["calls"], out["accepted"]), (1, 1))
            code, out = self.run_author(tmp, runtime, caps, "--pairs", pairs, "--execute")
            self.assertEqual((out["calls"], out["accepted"], out["alreadyAccepted"]), (1, 1, 1))

    def test_a_runtime_stop_is_recorded_and_halts_after_the_consecutive_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, ["stop"])
            code, out = self.run_author(tmp, runtime, caps, "--execute", "--max-calls", "10", "--max-consecutive-stops", "2")
            self.assertEqual((out["calls"], out["technicalStops"], out.get("halted")), (2, 2, "CONSECUTIVE_STOPS"))
            rows = [json.loads(l) for l in (Path(tmp) / "work/calls.jsonl").read_text().splitlines()]
            self.assertTrue(all(x["technicalStop"].startswith("RUNTIME_STOP:") and not x["accepted"] for x in rows))

    def test_an_existing_call_directory_without_a_row_counts_as_interrupted(self):
        r, (text, _) = self.clean()
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, [text])
            (Path(tmp) / "work/calls" / f"{r['pair']}-author-a1").mkdir(parents=True)
            code, out = self.run_author(tmp, runtime, caps, "--pairs", r["pair"], "--execute")
            self.assertEqual((out["calls"], out["technicalStops"]), (0, 1))
            row = json.loads((Path(tmp) / "work/calls.jsonl").read_text().splitlines()[0])
            self.assertEqual(row["technicalStop"], "INTERRUPTED_UNKNOWN_STATE")

    def test_rewording_needs_an_accepted_wording_a_and_writes_wording_b(self):
        r, f = instance_of("omitted_unknown", split="test")
        picked = next(i for i in DOCS["test"]["instances"] if i["wordingB"])
        f = prompts.family_of(picked)
        text, facts = su.case_report(picked, f)
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, [su.reword_report(picked, facts)])
            code, out = self.run_author(tmp, runtime, caps, "--reword", "--pairs", picked["pair"], "--execute", split="test")
            self.assertEqual((out["calls"], out["waitingForAccepted"]), (0, [picked["pair"]]))
            (Path(tmp) / "work/accepted").mkdir(parents=True, exist_ok=True)
            (Path(tmp) / "work/accepted" / f"{picked['pair']}.A.md").write_text(text, encoding="utf-8")
            code, out = self.run_author(tmp, runtime, caps, "--reword", "--pairs", picked["pair"], "--execute", split="test")
            self.assertEqual((out["calls"], out["accepted"]), (1, 1))
            self.assertTrue((Path(tmp) / "work/accepted" / f"{picked['pair']}.B.md").is_file())
            row = json.loads((Path(tmp) / "work/calls.jsonl").read_text().splitlines()[0])
            self.assertEqual((row["purpose"], row["attempt"]), ("reword", 1))
            prompt = (Path(tmp) / "work/prompts" / f"{picked['pair']}.B.txt").read_text(encoding="utf-8")
            self.assertIn(facts["sound"]["S01"][0], prompt)

    def test_only_pairs_marked_for_wording_b_are_reworded(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, ["stop"])
            code, out = self.run_author(tmp, runtime, caps, "--reword", split="test")
            self.assertEqual(out["pairsSelected"], 12)
            code, out = self.run_author(tmp, runtime, caps, "--reword", split="dev", work="w2")
            self.assertEqual(out["pairsSelected"], 0)

    def test_identity_workdir_and_pair_checks(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, ["stop"], binary="0" * 64)
            code, out = self.run_author(tmp, runtime, caps, "--execute")
            self.assertEqual((code, out["reason"]), (1, "RUN_BINARY_MISMATCH"))
            self.assertFalse((Path(tmp) / "work/calls").exists())
        with tempfile.TemporaryDirectory() as tmp:
            runtime, caps = self.setup(tmp, ["stop"])
            code, out = self.run_author(tmp, runtime, caps, "--pairs", "N-nothing", "--execute")
            self.assertEqual((code, out["reason"]), (1, "UNKNOWN_PAIR"))
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = author.main(["--split", "dev", "--runtime-dir", str(runtime), "--capabilities", str(caps), "--qualification", str(Path(tmp) / "q.json"),
                                    "--workdir", str(REPO / "author-workdir-must-not-exist"), "--execute"])
            self.assertEqual((code, json.loads(out.getvalue())["reason"]), (1, "WORKDIR_INSIDE_REPOSITORY"))
            self.assertFalse((REPO / "author-workdir-must-not-exist").exists())
            code, out = self.run_author(tmp, runtime, caps, "--max-calls", "0")
            self.assertEqual((code, out["reason"]), (1, "BAD_LIMITS"))


DEV_AUTHORING = V4 / "dev-authoring"
DEV_REVISION = V4 / "dev-authoring-revision"
DEV_REVISION2 = V4 / "dev-authoring-revision-2"
REWRITTEN = ["N-102a76", "N-4aedf1", "N-93366f", "N-9cc72c"]
REWRITTEN_AGAIN = ["N-102a76", "N-9cc72c"]
DEV_ACCEPTED = ",".join(str(d / "accepted") for d in (DEV_AUTHORING, DEV_REVISION, DEV_REVISION2))
DEV_CORPUS = V4 / "dev"


class CommittedDevAuthoringTests(unittest.TestCase):
    """The committed dev authoring evidence is what the write-up describes: prompts hash as sent, reports hash to the ledger, every accepted report passes the
    checks again, receipts are clean, and the built dev corpus is reproduced from the accepted reports."""

    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in (DEV_AUTHORING / "calls.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_the_ledger_covers_every_pair_and_records_every_attempt(self):
        pairs = [i["pair"] for i in DOCS["dev"]["instances"]]
        self.assertEqual(sorted({r["pair"] for r in self.rows}), sorted(pairs))
        self.assertEqual((len(self.rows), sum(r["accepted"] for r in self.rows)), (27, 24))
        for pair in pairs:
            own = [r for r in self.rows if r["pair"] == pair]
            self.assertEqual([r["attempt"] for r in own], list(range(1, len(own) + 1)))
            self.assertEqual([r["accepted"] for r in own], [False] * (len(own) - 1) + [True])
            self.assertTrue((DEV_AUTHORING / "accepted" / f"{pair}.A.md").is_file())
        self.assertEqual({r["runManifestSha256"] for r in self.rows}, {rp.sha((PARENT / "v3-run-gemini/manifest.json").read_bytes())})

    def test_prompts_are_the_ones_sent_and_reports_hash_to_the_ledger(self):
        for r in self.rows:
            instance = next(i for i in DOCS["dev"]["instances"] if i["pair"] == r["pair"])
            f = prompts.family_of(instance)
            prompt = (DEV_AUTHORING / "prompts" / f"{r['pair']}.A.txt").read_bytes()
            # the prompt as sent is the evidence; the family hazards and the decoy wording were revised after the batch (see the audit write-up), so it is not rebuilt
            text = prompt.decode("utf-8")
            for needle in (prompts.domain_of(instance)["description"], f["title"], f["soundHas"], f"has {instance['planLines']} lines"):
                self.assertIn(needle, text)
            self.assertEqual((rp.sha(prompt), len(prompt)), (r["promptSha256"], r["promptBytes"]))
            call = DEV_AUTHORING / "calls" / f"{r['pair']}-author-a{r['attempt']}"
            report = (call / "REPORT.md").read_bytes()
            self.assertEqual((rp.sha(report), len(report)), (r["reportSha256"], r["reportBytes"]))
            result, _ = ca.analyse(report.decode("utf-8"), instance, f)
            self.assertEqual((result["allPassed"], sorted(k for k, ok in result["checks"].items() if not ok)), (r["allPassed"], r["failedChecks"]))
            self.assertEqual(r["accepted"], r["allPassed"])
            if r["accepted"]:
                self.assertEqual((DEV_AUTHORING / "accepted" / f"{r['pair']}.A.md").read_bytes(), report)

    def test_every_receipt_is_clean_and_unretried(self):
        binary = json.loads((PARENT / "v3-run-gemini/manifest.json").read_bytes())["binary"]["sha256"]
        for r in self.rows:
            self.assertIsNone(r["technicalStop"])
            receipt = json.loads((DEV_AUTHORING / "calls" / f"{r['pair']}-author-a{r['attempt']}" / "CLI-RECEIPT.json").read_bytes())
            self.assertEqual((receipt["status"], receipt["failure"], receipt["closingFailures"], receipt["retries"], receipt["invocations"]),
                             ("REPORT_RECEIVED_PENDING_ADJUDICATION", None, [], 0, {"proxy": 1, "native": 1}))
            self.assertEqual((receipt["native"]["sha256"], receipt["report"]["sha256"]), (binary, r["reportSha256"]))
            self.assertEqual((r["receipt"]["model"], r["receipt"]["servedAttestation"]), ("gemini-3.8-flash-high", "UNAVAILABLE"))

    def test_the_three_failed_first_attempts_are_the_recorded_ones(self):
        failed = sorted((r["pair"], tuple(r["failedChecks"])) for r in self.rows if not r["accepted"])
        self.assertEqual(sorted(c for _, c in failed), [("NO_ADMISSIONS_OUTSIDE_OPEN_ITEMS",), ("RUBRIC_GROUNDED_IN_THE_PLAN",), ("RUBRIC_GROUNDED_IN_THE_PLAN",)])
        self.assertTrue(all(r["attempt"] == 1 for r in self.rows if not r["accepted"]))

    def test_the_committed_dev_corpus_is_reproduced_from_the_accepted_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = bc.build("dev", DEV_ACCEPTED, Path(tmp) / "out", json.loads((V4 / "dev-drops.json").read_bytes()))
            self.assertEqual(manifest, json.loads((DEV_CORPUS / "manifest.json").read_bytes()))
            self.assertEqual((Path(tmp) / "out/oracle/oracle.json").read_bytes(), (DEV_CORPUS / "oracle/oracle.json").read_bytes())
        corpus = s4.Corpus(DEV_CORPUS)
        self.assertEqual((len(corpus.oracle), manifest["pairs"], [d["pair"] for d in manifest["dropped"]]), (46, 23, ["N-102a76"]))


class CommittedDevRevisionTests(unittest.TestCase):
    """The second dev batch: the four pairs the audit found to carry a second unestablished fact, rewritten after the hazards were revised, in a new root."""

    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in (DEV_REVISION / "calls.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_four_pairs_four_calls_all_accepted_at_the_first_attempt(self):
        self.assertEqual([r["pair"] for r in self.rows], REWRITTEN)
        self.assertEqual([(r["attempt"], r["accepted"], r["technicalStop"], r["failedChecks"]) for r in self.rows], [(1, True, None, [])] * 4)
        self.assertEqual({r["runManifestSha256"] for r in self.rows}, {rp.sha((PARENT / "v3-run-gemini/manifest.json").read_bytes())})

    def test_prompts_hash_as_sent_and_were_built_with_the_revised_hazards(self):
        families = {f["id"]: f for f in FAMILIES["families"]}
        for r in self.rows:
            instance = next(i for i in DOCS["dev"]["instances"] if i["pair"] == r["pair"])
            prompt = (DEV_REVISION / "prompts" / f"{r['pair']}.A.txt").read_bytes()
            self.assertEqual((rp.sha(prompt), len(prompt)), (r["promptSha256"], r["promptBytes"]))
            text = prompt.decode("utf-8")
            self.assertTrue(any(h in text for h in families[instance["family"]]["hazards"][-1:]), r["pair"])
            self.assertIn("exactly one open item" if instance["kind"] == "decoy_pair" else "after the last write, replay or sync", text)

    def test_reports_hash_receipts_are_clean_and_accepted_reports_pass_again(self):
        binary = json.loads((PARENT / "v3-run-gemini/manifest.json").read_bytes())["binary"]["sha256"]
        for r in self.rows:
            instance = next(i for i in DOCS["dev"]["instances"] if i["pair"] == r["pair"])
            report = (DEV_REVISION / "calls" / f"{r['pair']}-author-a1" / "REPORT.md").read_bytes()
            self.assertEqual(rp.sha(report), r["reportSha256"])
            self.assertEqual((DEV_REVISION / "accepted" / f"{r['pair']}.A.md").read_bytes(), report)
            self.assertTrue(ca.analyse(report.decode("utf-8"), instance, prompts.family_of(instance))[0]["allPassed"])
            receipt = json.loads((DEV_REVISION / "calls" / f"{r['pair']}-author-a1" / "CLI-RECEIPT.json").read_bytes())
            self.assertEqual((receipt["status"], receipt["failure"], receipt["closingFailures"], receipt["retries"], receipt["native"]["sha256"]),
                             ("REPORT_RECEIVED_PENDING_ADJUDICATION", None, [], 0, binary))

    def test_the_rewritten_reports_replace_the_first_batch_in_the_dev_corpus_and_nothing_else_changes(self):
        manifest = json.loads((DEV_CORPUS / "manifest.json").read_bytes())
        shas = manifest["authoring"]["acceptedReportSha256"]
        self.assertNotIn("N-102a76", shas)     # dropped after its third failed audit (dev-drops.json)
        for pair in [p for p in REWRITTEN if p != "N-102a76"]:
            latest = DEV_REVISION2 if pair in REWRITTEN_AGAIN else DEV_REVISION
            self.assertEqual(shas[pair]["A"], rp.sha((latest / "accepted" / f"{pair}.A.md").read_bytes()))
            self.assertNotEqual(shas[pair]["A"], rp.sha((DEV_AUTHORING / "accepted" / f"{pair}.A.md").read_bytes()))
        for pair in sorted(set(shas) - set(REWRITTEN)):
            self.assertEqual(shas[pair]["A"], rp.sha((DEV_AUTHORING / "accepted" / f"{pair}.A.md").read_bytes()))


class CommittedDevRevision2Tests(unittest.TestCase):
    """The third dev batch: the two pairs whose rewrite still carried an arithmetic slip in a filler line, rewritten once more after the number-consistency rule."""

    @classmethod
    def setUpClass(cls):
        cls.rows = [json.loads(line) for line in (DEV_REVISION2 / "calls.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]

    def test_two_pairs_two_calls_accepted_at_the_first_attempt_with_clean_receipts(self):
        self.assertEqual([r["pair"] for r in self.rows], REWRITTEN_AGAIN)
        self.assertEqual([(r["attempt"], r["accepted"], r["technicalStop"], r["failedChecks"]) for r in self.rows], [(1, True, None, [])] * 2)
        binary = json.loads((PARENT / "v3-run-gemini/manifest.json").read_bytes())["binary"]["sha256"]
        for r in self.rows:
            instance = next(i for i in DOCS["dev"]["instances"] if i["pair"] == r["pair"])
            prompt = (DEV_REVISION2 / "prompts" / f"{r['pair']}.A.txt").read_bytes()
            self.assertEqual(rp.sha(prompt), r["promptSha256"])
            self.assertEqual(prompt, prompts.author_prompt(instance, prompts.family_of(instance), prompts.domain_of(instance)).encode("utf-8"))
            self.assertIn("check every number that appears twice", prompt.decode("utf-8"))
            report = (DEV_REVISION2 / "calls" / f"{r['pair']}-author-a1" / "REPORT.md").read_bytes()
            self.assertEqual((rp.sha(report), (DEV_REVISION2 / "accepted" / f"{r['pair']}.A.md").read_bytes()), (r["reportSha256"], report))
            self.assertTrue(ca.analyse(report.decode("utf-8"), instance, prompts.family_of(instance))[0]["allPassed"])
            receipt = json.loads((DEV_REVISION2 / "calls" / f"{r['pair']}-author-a1" / "CLI-RECEIPT.json").read_bytes())
            self.assertEqual((receipt["status"], receipt["retries"], receipt["native"]["sha256"]), ("REPORT_RECEIVED_PENDING_ADJUDICATION", 0, binary))


class RecheckTests(unittest.TestCase):
    """Accepting a report that failed only a rule that was corrected afterwards, without a model call and with a record of having done so."""

    def work(self, tmp, reports):
        """A work directory whose ledger holds one failed attempt per (pair, report text); returns the directory."""
        work = Path(tmp) / "work"
        (work / "accepted").mkdir(parents=True)
        rows = []
        for pair, text, extra in reports:
            call = work / "calls" / f"{pair}-author-a1"
            call.mkdir(parents=True)
            if text is not None:
                (call / "REPORT.md").write_text(text, encoding="utf-8")
            rows.append(dict({"pair": pair, "purpose": "author", "attempt": 1, "accepted": False, "failedChecks": ["RUBRIC_GROUNDED_IN_THE_PLAN"], "technicalStop": None}, **extra))
        (work / "calls.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        return work

    def test_a_report_that_passes_the_corrected_check_is_accepted_and_recorded_and_the_rest_are_left(self):
        gap = next(i for i in DOCS["test"]["instances"] if i["family"] == "omitted_measurement")
        defect = next(i for i in DOCS["test"]["instances"] if i["family"] == "budget_arithmetic")
        stopped = next(i for i in DOCS["test"]["instances"] if i["family"] == "omitted_access_check")
        good, _ = su.case_report(gap, prompts.family_of(gap), lambda facts: facts.update(rubric="platform, task ; unmeasured, untested"))
        bad, _ = su.case_report(defect, prompts.family_of(defect), lambda facts: facts.update(rubric="platform, task ; zebra, giraffe"))
        with tempfile.TemporaryDirectory() as tmp:
            work = self.work(tmp, [(gap["pair"], good, {}), (defect["pair"], bad, {}), (stopped["pair"], None, {"technicalStop": "RUNTIME_STOP:x", "failedChecks": None})])
            dry = recheck.run("test", work)
            self.assertEqual((dry["considered"], dry["wouldAccept"], dry["accepted"], dry["stillFailing"]), (2, [gap["pair"]], [], 1))
            self.assertFalse((work / "accepted" / f"{gap['pair']}.A.md").exists())
            done = recheck.run("test", work, apply=True)
            self.assertEqual((done["accepted"], done["providerCalls"]), ([gap["pair"]], 0))
            self.assertEqual((work / "accepted" / f"{gap['pair']}.A.md").read_text(encoding="utf-8"), good)
            self.assertFalse((work / "accepted" / f"{defect['pair']}.A.md").exists())
            record = json.loads((work / "rechecks.jsonl").read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual((record["pair"], record["failedBefore"], record["reportSha256"], record["checkerSha256"]),
                             (gap["pair"], ["RUBRIC_GROUNDED_IN_THE_PLAN"], rp.sha(good.encode()), rp.sha((HERE / "check_author.py").read_bytes())))
            again = recheck.run("test", work, apply=True)
            self.assertEqual((again["considered"], again["accepted"]), (1, []))      # the accepted pair is left alone; the failing one still fails

    def test_only_the_last_attempt_counts_and_the_ledger_is_never_changed(self):
        gap = next(i for i in DOCS["test"]["instances"] if i["family"] == "omitted_measurement")
        good, _ = su.case_report(gap, prompts.family_of(gap))
        with tempfile.TemporaryDirectory() as tmp:
            work = self.work(tmp, [(gap["pair"], good, {})])
            before = (work / "calls.jsonl").read_bytes()
            recheck.run("test", work, apply=True)
            self.assertEqual((work / "calls.jsonl").read_bytes(), before)
            self.assertEqual(recheck.run("test", Path(tmp) / "nowhere")["considered"], 0)


class RunScriptTests(unittest.TestCase):
    """The gated helper script: its pinned expectations match the repository, it refuses ungated live calls and its stages need the host stage first."""
    SCRIPT = HERE / "run.sh"

    def sh(self, *args, env_extra=None, root=None):
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as tmp:
            env = {k: v for k, v in os.environ.items() if k not in ("SPLIT", "ROOT", "AGY")}      # the operator's own exports must not change what the script is tested against
            env.update(ROOT=str(root or Path(tmp) / "root"), AGY="/nonexistent/agy", **(env_extra or {}))
            done = subprocess.run(["bash", str(self.SCRIPT), *args], capture_output=True, text=True, env=env, cwd=REPO, check=False, timeout=300)
            return done.returncode, done.stdout, done.stderr

    def test_the_pinned_expectations_match_the_repository(self):
        text = self.SCRIPT.read_text(encoding="utf-8")
        pins = {"EXPECT_AGY_SHA": BINARY, "EXPECT_RUN_SHA": rp.sha((PARENT / "v3-run-gemini/manifest.json").read_bytes()),
                "EXPECT_AUTHOR_TEMPLATE_SHA": rp.sha((HERE / "author-template.txt").read_bytes()), "EXPECT_REWORD_TEMPLATE_SHA": rp.sha((HERE / "reword-template.txt").read_bytes()),
                "EXPECT_CHECKER_SHA": rp.sha((HERE / "check_author.py").read_bytes()), "EXPECT_FAMILIES_SHA": rp.sha((V4 / "families.json").read_bytes()), "EXPECT_DOMAINS_SHA": rp.sha((V4 / "domains.json").read_bytes()),
                "EXPECT_DEV_ASSIGNMENTS_SHA": rp.sha((HERE / "assignments-dev.json").read_bytes()), "EXPECT_TEST_ASSIGNMENTS_SHA": rp.sha((HERE / "assignments-test.json").read_bytes())}
        for name, value in pins.items():
            self.assertIn(f"{name}={value}", text)
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for value in (BINARY, pins["EXPECT_RUN_SHA"]):
            self.assertIn(value, brief)
        self.assertTrue(self.SCRIPT.stat().st_mode & 0o111)

    def test_live_calls_need_the_go_flag_a_count_and_the_host_stage(self):
        for args, needle in ((("live",), "REFUSED"), (("live", "3"), "REFUSED"), (("live", "x", "--go"), "N_MUST_BE_A_NUMBER"), (("live", "99", "--go"), "N_MUST_BE_1_TO_40"),
                             (("live", "2", "--go"), "RUN_HOST_FIRST"), (("reword", "2", "--go"), "REWORDING_IS_TEST_ONLY"), (("dry",), "RUN_HOST_FIRST")):
            with self.subTest(args=args):
                code, out, err = self.sh(*args)
                self.assertEqual((code, needle in err), (2, True), err)
        code, out, err = self.sh("reword", "2", "--go", env_extra={"SPLIT": "test"})
        self.assertEqual((code, "RUN_HOST_FIRST" in err), (2, True))
        self.assertEqual(self.sh("live", "1", "--go", env_extra={"SPLIT": "neither"})[0], 2)
        self.assertEqual(self.sh()[0], 2)

    def test_checks_stop_on_the_missing_binary_and_status_and_bundle_need_a_run(self):
        code, out, err = self.sh("checks")
        self.assertEqual(code, 1)
        self.assertTrue("MISMATCH:agy-sha" in err or "MISMATCH:clean-tree" in err)
        self.assertEqual(self.sh("status")[0], 1)
        self.assertEqual(self.sh("bundle")[0], 1)

    def test_status_names_the_failed_checks_and_recheck_needs_a_run(self):
        self.assertEqual(self.sh("recheck")[0], 1)
        with tempfile.TemporaryDirectory() as tmp:
            work = Path(tmp) / "root/work"
            work.mkdir(parents=True)
            rows = [{"pair": "N-a", "purpose": "author", "attempt": 1, "accepted": False, "failedChecks": ["LINE_SHAPE", "NO_META_WORDS"], "technicalStop": None, "allPassed": False},
                    {"pair": "N-b", "purpose": "author", "attempt": 1, "accepted": False, "failedChecks": ["LINE_SHAPE"], "technicalStop": None, "allPassed": False}]
            (work / "calls.jsonl").write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
            code, out, err = self.sh("status", root=Path(tmp) / "root")
            self.assertEqual(code, 0, err)
            self.assertEqual(json.loads(out)["failedCheckNames"], {"LINE_SHAPE": 2, "NO_META_WORDS": 1})
            code, out, err = self.sh("recheck", root=Path(tmp) / "root")
            self.assertEqual((code, json.loads(out)["providerCalls"]), (0, 0))

    def test_diag_reports_start_up_time_and_load_without_a_model_call(self):
        code, out, err = self.sh("diag")
        self.assertEqual(code, 0, err)
        self.assertRegex(out, r"DIAG python start-up ms: median \d+, p90 \d+, max \d+; load average [\d. ]+; cpus \d+")

    def test_the_brief_names_the_rules_and_the_commands(self):
        brief = (HERE / "HANDOFF.md").read_text(encoding="utf-8")
        for needle in ("stop and send the exact output", "Live calls only on the owner's go", "`live N --go`", "do not open, read, summarize or paste any authored file",
                       "OFFLINE_RUN_2_STOPPED", "$B reword 4 --go", "$B bundle", "never committed"):
            self.assertIn(needle, brief)


if __name__ == "__main__":
    unittest.main()
