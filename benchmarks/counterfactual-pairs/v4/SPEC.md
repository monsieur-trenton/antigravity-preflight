# Corpus v4: case specification

Status: **a specification, not a preregistration.** It fixes what a v4 case is, what its oracle must say and what a family specification must contain, so that authors, auditors, the scorer and the checkers work from one definition. It follows the [v4 plan](../../../docs/v4-plan.md) and the [authoring probe](probe/results/RESULT.md), whose four defects are designed out below. [families.json](families.json) holds the 14 families and [domains.json](domains.json) the pool of domains; [check_families.py](check_families.py) validates both and the oracle schema.

## Units

- **Family**: a mechanism (for example "a number in the plan exceeds a limit in a referenced settings excerpt"). 14 of them, 3 dev and 11 test.
- **Instance**: one pair built from a family in one domain, with the buckets below assigned by a seed committed before authoring. Test: 80 instances; dev: 24.
- **Pair**: a **sound** member and a **changed** member (the twin) that differ by one edit.
- **Wording**: A is the authored pair. B is an equivalent rewording of the whole pair, made for 12 test instances (3 per kind) to measure consistency; dev has none. Test cases: 160 for A and 24 for B, 184 in all; dev 48.

## Kinds and the verdict each member must get

| Kind | Twin's one edit | Sound member | Twin | Test pairs |
| --- | --- | --- | --- | --- |
| `omitted_unknown` | delete the 1 to 3 lines that state the decisive fact; nothing replaces them | `GO` | `GO_WITH_CHANGES` | 20 |
| `cross_source_defect` | change exactly one line in exactly one of two sources so that the plan contradicts the reference | `GO` | `NO_GO` | 24 |
| `defect` | change one line in place (single source, plan of 30 to 60 lines) | `GO` | `NO_GO` | 20 |
| `decoy_pair` | edit or delete one line so that a stated open item stops being non-binding | `GO` | `GO_WITH_CHANGES` | 16 |

`GO`, `GO_WITH_CHANGES` and `NO_GO` are `NO_BLOCKERS_FOUND`, `CHANGES_RECOMMENDED` and `BLOCKERS_FOUND`. A sound member that draws `GO_WITH_CHANGES` is a hedge; a sound member that draws `NO_GO` is a false blocker; a twin that draws `GO` is waved through, and an evidence-gap twin that draws `NO_GO` is overclaimed, as in v3.

## What a case file holds

**Reviewer-visible** (the packet): the plan as `S01`, one sentence per line, 60 to 220 characters, 25 to 80 lines; for `cross_source_defect`, a second source `S02` (the reference excerpt, 8 to 25 lines, one entry per line). Lines are not numbered in the file; the reviewer's view numbers each source from 1 and labels them (`[S01:3]`, `[S02:5]`). Findings cite **source-qualified lines** (`S02:5`); the scorer and parsers of v4 must read that form natively, not as a tolerated deviation.

**Hidden** (the oracle, one record per case, never in a packet; numbers refer to that case's own numbering, and the twin's numbers shift after a deletion):

```json
{
  "case": "R-3f9a12", "pair": "N-0412", "family": "config_limit", "kind": "cross_source_defect", "domain": "message_queue_consumer_scaling",
  "wording": "A", "role": "changed", "expectedClass": "DEFECT", "expectedVerdict": "NO_GO", "difficulty": "direct",
  "sources": [{"id": "S01", "role": "plan", "lines": 34}, {"id": "S02", "role": "reference", "lines": 14}],
  "requirement": {"source": "S01", "line": 6},
  "citeAnyOf": [{"source": "S01", "line": 19}, {"source": "S02", "line": 7}],
  "changed": {"type": "edited", "source": "S01", "lines": [19], "positionBucket": "middle"},
  "decoyLines": [{"source": "S01", "line": 27}],
  "mechanism": "Line 19 sets 48 consumers, above the 40 allowed by line 7 of the settings excerpt.",
  "whyNoFallback": null,
  "baitNotes": ["no ramp-up plan", "single alert channel"],
  "rubricKeywords": [["consumer", "48"], ["limit", "40", "maximum"]]
}
```

For a sound member the same record carries `"role": "sound"`, `expectedClass: "SOUND"`, `expectedVerdict: "GO"`, `mechanism: null`, and `changed` describes the edit that makes its twin (so a pair is bound by its records). `citeAnyOf` for a sound member is empty. For `omitted_unknown` and for a deletion in `decoy_pair` the oracle also states `whyNoFallback`, because the decisive fact has no line in the twin: the accepted citation is the requirement line or the line that performs the governed step (the family's `citeRule`).

## Rules that apply to every family

1. **One edit, nothing else.** The twin is the sound member with exactly the family's edit. A deletion removes the named lines and adds nothing; an in-place edit changes one line and moves none. Checked by a program against the oracle's `changed` field.
2. **A testable requirement, stated in the plan.** The requirement is one sentence from which a reader can decide whether the plan meets it (the probe's "either the old or the new path" could not be decided and is the model of what to avoid). Each family's `requirement` gives the template.
3. **Silent omission.** In an `omitted_unknown` twin nothing says that something is unknown, unmeasured, pending or to be decided. Open items appear only on the decoy lines of `decoy_pair` families, and there they are flagged as open on purpose.
4. **No absorbing fallback.** Nothing elsewhere in the twin bounds the missing quantity, implies the missing access or makes the contradiction harmless. The author's `whyNoFallback` is a claim that the audit checks, not evidence.
5. **No meta words** in plan lines: twin, sound, benchmark, oracle, decisive, counterfactual, test case, omitted.
6. **Positions are assigned, not chosen.** The builder assigns, from a committed seed, the bucket (early, middle or late third of the plan) of the requirement, of the changed lines and of the decoy or open-item lines. Across the instances of a family each bucket gets at least a third, rounded down, and no bucket more than a third plus one. The decoy or open item is at least five lines from the changed lines, and never adjacent to a gap left by a deletion.
7. **Domains are assigned.** Each instance's domain is drawn from [domains.json](domains.json): none more than four times in a split or twice in a family; `devOnly` domains never in test. Length of the plan is also assigned (30 to 60 lines for single-source families, 25 to 50 for the plan of a cross-source one).
8. **Baits are natural, not planted.** `baitNotes` records two or three nitpicks a reviewer could raise about the plan that are not decisive (no rehearsal, a single alert channel). They measure hedging; they are not lines of the plan and not decoys.
9. **Wording B.** B has the same number of lines, the same line-by-line content and the same positions of the edit. In every line the multiset of tokens that contain a digit, an identifier, a path or a name in capitals is identical in A and B; everything else may differ. A program checks it.
10. **Size.** One authoring call returns one pair: sound plan, twin, and for cross-source the reference, plus the oracle draft, under 28,000 bytes (the runtime's report cap is 32,768).

## What the audit asks (blind to class)

For each member shown alone, and then each pair shown with the members unlabelled: (1) which one needs a change, and why; (2) what single fact would change your verdict; (3) is the twin the sound member with one edit and nothing else; (4) is anything in either member unknown or contradictory apart from the intended edit; (5) does the requirement decide the verdict; (6) does the author's claim that nothing absorbs the gap hold. The owner's spot check covers at least a fifth of the pairs, class hidden. A pair whose class the auditors do not recover, or whose edit is not exactly one edit, is rewritten or dropped before the split is frozen, and the drop is recorded.

## Seeding and sealing

The test split's families are public; its instances (domain, positions, lengths and which pairs get wording B) are drawn from a seed whose hash is committed before any case is authored, and the authored test cases are committed only as hashes until the arms are preregistered. The dev split is open from the start and is the only place where prompts and tooling may be tuned.

## Not decided here

The audit prompts, the reviewer prompts for the Gemini bare arm and the multi-source reviewer request, the source-qualified citation parser and scorer, the rubric of "gap named" per instance, and the preregistration itself. Each is a later step in the plan.
