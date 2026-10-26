"""Offline tests for the corpus v4 family specifications, the domain pool and the oracle schema. No model calls."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import sys
import unittest

sys.dont_write_bytecode = True

HERE = Path(__file__).resolve().parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


cf = load("t_check_families", HERE / "check_families.py")
FAMILIES = json.loads((HERE / "families.json").read_bytes())
DOMAINS = json.loads((HERE / "domains.json").read_bytes())
SPEC = (HERE / "SPEC.md").read_text(encoding="utf-8")
EXAMPLE = (HERE / "examples/cross-source-format.md").read_text(encoding="utf-8")


def json_blocks(text):
    return [json.loads(block) for block in re.findall(r"```json\n(.*?)\n```", text, re.S)]


def mutated(edit):
    doc = copy.deepcopy(FAMILIES)
    edit(doc)
    return cf.check_families(doc, DOMAINS)


class FamilyTests(unittest.TestCase):
    def test_the_committed_specification_validates(self):
        result = cf.run()
        self.assertEqual((result["status"], result["problems"], result["families"], result["domains"]), ("PASS", [], 14, 26))

    def test_the_targets_are_the_ones_the_plan_states(self):
        by_split = {"test": {}, "dev": {}}
        for f in FAMILIES["families"]:
            by_split[f["split"]][f["kind"]] = by_split[f["split"]].get(f["kind"], 0) + f["instances"]
        self.assertEqual(by_split["test"], {"omitted_unknown": 20, "cross_source_defect": 24, "defect": 20, "decoy_pair": 16})
        self.assertEqual(by_split["dev"], {"omitted_unknown": 8, "cross_source_defect": 8, "decoy_pair": 8})
        self.assertEqual((sum(by_split["test"].values()), sum(by_split["dev"].values())), (80, 24))
        self.assertEqual(sorted(f["id"] for f in FAMILIES["families"] if f["split"] == "dev"), ["omitted_precondition_check", "open_item_scope", "schema_state"])
        self.assertEqual(FAMILIES["targets"]["test"]["wordingBPairs"], 12)

    def test_every_kind_has_the_class_verdicts_and_sources_it_should(self):
        for f in FAMILIES["families"]:
            kind = cf.KINDS[f["kind"]]
            self.assertEqual((f["twinClass"], f["expectedVerdict"]["twin"], f["expectedVerdict"]["sound"]), (kind["twinClass"], kind["twinVerdict"], "GO"), f["id"])
            self.assertEqual([s["role"] for s in f["sources"]], ["plan", "reference"] if kind["needsReference"] else ["plan"], f["id"])

    def test_the_probe_defects_are_designed_out(self):
        text = json.dumps(FAMILIES)
        self.assertIn("payments_api_cdn_cutover", text)                          # named as dev-only, never an instance seed
        omitted = next(f for f in FAMILIES["families"] if f["id"] == "omitted_propagation_window")
        self.assertIn("within five minutes of the change every client resolves the new address", omitted["requirement"])
        self.assertTrue(any("testable sentence" in h for h in omitted["hazards"]))
        self.assertTrue(any("either the old or the new path" in h and "ambiguous" in h for h in omitted["hazards"]))
        self.assertIn("**Positions are assigned, not chosen.**", SPEC)
        self.assertIn("`baitNotes`", SPEC)                                       # the bait field is separate from the decoy

    def test_the_validator_catches_each_kind_of_mistake(self):
        self.assertIn("FAMILY_IDS_OR_COUNT", mutated(lambda d: d["families"].pop()))
        self.assertTrue(any(p.startswith("FAMILY_FIELDS:config_limit") for p in mutated(lambda d: d["families"][4].update(requirement=""))))
        self.assertTrue(any(p.startswith("KIND_MAPPING") for p in mutated(lambda d: d["families"][4].update(twinClass="UNCERTAIN"))))
        self.assertTrue(any(p.startswith("SOURCES") for p in mutated(lambda d: d["families"][4].update(sources=d["families"][4]["sources"][:1]))))
        self.assertTrue(any(p.startswith("LINE_RANGE") for p in mutated(lambda d: d["families"][0]["sources"][0].update(lines=[10, 200]))))
        self.assertIn("TARGET_COUNTS:test", mutated(lambda d: d["families"][0].update(instances=8)))
        self.assertIn("DEV_FAMILIES", mutated(lambda d: d["families"][5].update(split="dev")))
        self.assertIn("WORDING_B_TARGET", mutated(lambda d: d["targets"]["test"].update(wordingBPairs=5)))
        self.assertIn("VERDICT_MAP", mutated(lambda d: d.update(verdictMap={})))

    def test_the_domain_pool_has_room_and_keeps_the_probe_domain_out_of_test(self):
        self.assertEqual(cf.check_domains(DOMAINS), [])
        dev_only = [d["id"] for d in DOMAINS["domains"] if d["devOnly"]]
        self.assertEqual(dev_only, ["payments_api_cdn_cutover"])
        broken = copy.deepcopy(DOMAINS)
        broken["domains"] = broken["domains"][:10]
        self.assertIn("TEST_DOMAIN_CAPACITY", cf.check_domains(broken))
        duplicate = copy.deepcopy(DOMAINS)
        duplicate["domains"][1]["id"] = duplicate["domains"][2]["id"]
        self.assertIn("DOMAIN_IDS", cf.check_domains(duplicate))


class OracleSchemaTests(unittest.TestCase):
    def records(self):
        return json_blocks(SPEC)[0], json_blocks(EXAMPLE)[0]

    def test_the_oracle_examples_in_the_documents_are_well_formed(self):
        for record in self.records():
            self.assertEqual(cf.check_oracle(record), [], record["case"])

    def mutated(self, edit, which=0):
        record = copy.deepcopy(self.records()[which])
        edit(record)
        return cf.check_oracle(record)

    def test_each_rule_of_the_schema_is_enforced(self):
        self.assertEqual(self.mutated(lambda r: r.pop("mechanism")), ["ORACLE_FIELDS"])
        self.assertIn("ORACLE_CLASS_OR_VERDICT", self.mutated(lambda r: r.update(expectedVerdict="GO")))
        self.assertIn("ORACLE_SOURCES", self.mutated(lambda r: r.update(sources=r["sources"][:1])))
        self.assertIn("ORACLE_REQUIREMENT", self.mutated(lambda r: r.update(requirement={"source": "S01", "line": 99})))
        self.assertIn("ORACLE_CITE", self.mutated(lambda r: r.update(citeAnyOf=[])))
        self.assertIn("ORACLE_CITE", self.mutated(lambda r: r.update(citeAnyOf=[{"source": "S03", "line": 1}])))
        self.assertIn("ORACLE_CHANGED", self.mutated(lambda r: r["changed"].update(positionBucket="end")))
        self.assertIn("ORACLE_CHANGED_TYPE", self.mutated(lambda r: r["changed"].update(type="deleted")))
        self.assertIn("ORACLE_MECHANISM", self.mutated(lambda r: r.update(mechanism=None)))
        self.assertIn("ORACLE_WHY_NO_FALLBACK_UNEXPECTED", self.mutated(lambda r: r.update(whyNoFallback="x")))
        self.assertIn("ORACLE_RUBRIC", self.mutated(lambda r: r.update(rubricKeywords=[["a"]] * 4)))

    def test_a_sound_member_has_no_citation_no_mechanism_and_the_same_edit_recorded(self):
        def to_sound(r):
            r.update(role="sound", expectedClass="SOUND", expectedVerdict="GO", citeAnyOf=[], mechanism=None)
        self.assertEqual(self.mutated(to_sound), [])
        self.assertIn("ORACLE_CITE", self.mutated(lambda r: (to_sound(r), r.update(citeAnyOf=[{"source": "S01", "line": 4}]))))

    def test_an_omission_twin_needs_a_deleted_edit_and_the_reason_nothing_absorbs_it(self):
        def omission(r):
            r.update(kind="omitted_unknown", family="omitted_measurement", difficulty="omission", expectedClass="UNCERTAIN", expectedVerdict="GO_WITH_CHANGES",
                     sources=[{"id": "S01", "role": "plan", "lines": 34}], citeAnyOf=[{"source": "S01", "line": 6}],
                     changed={"type": "deleted", "source": "S01", "lines": [12, 13], "positionBucket": "middle"}, whyNoFallback="Nothing else bounds the run time.")
        self.assertEqual(self.mutated(omission), [])
        self.assertIn("ORACLE_WHY_NO_FALLBACK", self.mutated(lambda r: (omission(r), r.update(whyNoFallback=None))))
        self.assertIn("ORACLE_CHANGED_TYPE", self.mutated(lambda r: (omission(r), r["changed"].update(type="edited"))))

    def test_a_decoy_pair_needs_its_decoy_lines(self):
        def decoy(r):
            r.update(kind="decoy_pair", family="open_item_becomes_decisive", difficulty="decoy", expectedClass="UNCERTAIN", expectedVerdict="GO_WITH_CHANGES",
                     sources=[{"id": "S01", "role": "plan", "lines": 34}], citeAnyOf=[{"source": "S01", "line": 6}], whyNoFallback="No line absorbs the open item.",
                     decoyLines=[{"source": "S01", "line": 27}])
        self.assertEqual(self.mutated(decoy), [])
        self.assertIn("ORACLE_DECOYS_REQUIRED", self.mutated(lambda r: (decoy(r), r.update(decoyLines=[]))))


class DocumentTests(unittest.TestCase):
    def test_the_spec_states_the_rules_the_checkers_and_the_plan_depend_on(self):
        for needle in ("**One edit, nothing else.**", "**Silent omission.**", "**No absorbing fallback.**", "**Wording B.**", "source-qualified lines", "28,000 bytes",
                       "`GO_WITH_CHANGES`", "160 for A and 24 for B, 184 in all; dev 48", "committed in the clear before any case is authored"):
            self.assertIn(needle, SPEC)

    def test_the_example_is_labelled_as_a_format_reference_and_never_a_case(self):
        self.assertIn("not a case", EXAMPLE.splitlines()[0])
        self.assertIn("never sent to a reviewer and never reused as a case", EXAMPLE)


if __name__ == "__main__":
    unittest.main()
