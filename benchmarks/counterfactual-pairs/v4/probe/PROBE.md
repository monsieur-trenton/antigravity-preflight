# The authoring probe: can the Gemini review runtime write a benchmark case?

Corpus v4 will have Gemini write the cases and Claude audit them blind ([plan](../../../../docs/v4-plan.md)). The native runtime was qualified as a tool-free **reviewer** with a fixed question and a machine-summary parser. It was never asked to write anything. This probe asks it once, with one assignment, before any family is specified. **It makes one live model call. It scores nothing, reviews nothing and produces no case that will be used.**

## What is asked

[author-prompt.txt](author-prompt.txt) is the whole prompt (pinned by hash in the brief). It assigns one *omitted unknown* pair: a plan for moving a payments API to a new CDN, a requirement stated in the plan (no more than five minutes of mixed routing, restorable within five), a decisive fact stated only in the sound plan (the DNS record's TTL lowered to 60 s forty-eight hours ahead, and checked against public resolvers), a decoy line in both (a real but non-binding open item), and a twin that is the sound plan with the decisive lines deleted and nothing put in their place. The output format is fixed so a program can read it.

The packet carries a one-line placeholder source because the runtime requires one; the prompt carries the assignment. The run is bound to the same runtime package and `agy` binary as the [v3 Gemini run](../../v3-run-gemini/README.md) and takes the same capabilities and offline-qualification steps.

## Questions the probe answers

| # | Question | How it is decided |
| --- | --- | --- |
| 1 | **Transport.** Does a non-review prompt run to a report at all? | The receipt: `REPORT_RECEIVED_PENDING_ADJUDICATION`, one native call, zero retries. A runtime stop (for instance a step type outside the qualified set) is a finding, not a failure to retry |
| 2 | **Persona.** Does the reviewer persona (`preflight-inline`: "return a cited Markdown report") override the assignment? | Whether the output is a case block or a review. Mechanical: `BLOCKS_IN_ORDER`, `NOTHING_OUTSIDE_THE_CASE` |
| 3 | **Size.** Does a pair fit under the report cap (32,768 bytes)? | The saved report's byte count against the cap; a truncated report fails the markers |
| 4 | **Instruction following.** Can it keep to a strict format and a strict relation between the two plans? | The mechanical checks of [check_probe_output.py](check_probe_output.py): the twin is exactly the sound plan minus the oracle's fact lines, line shape and length, no meta words, no admissions outside the decoy, the oracle block complete and consistent |
| 5 | **Quality.** Are the plans realistic and the twin a fair test? | Read by a person after the mechanical checks, with the criteria below. Not decided by a program |

## Reading criteria (applied by whoever reads the output, after the checks)

1. **Silent omission.** Does the twin read as a complete plan that simply never mentions the fact, with no hint, no gap-shaped sentence and no line that now dangles?
2. **No absorbing fallback.** Does anything else in the twin bound how long clients keep the old address (a rollback line that implies it, a monitoring line that would catch it)? The author's `why_no_fallback` is a claim to check, not evidence.
3. **Decisiveness.** Would a careful reviewer who noticed the omission be right to say the requirement is not shown to hold? Or is the requirement achievable regardless?
4. **Noise that is noise.** Do the other 30-odd lines read like a real plan without introducing a second unestablished fact that bears on the requirement?
5. **Tempting alternative.** Is the author's `tempting_alternative` really a distraction and really not decisive?
6. **Leakage.** Any phrasing that gives away which plan is the twin or that something was removed.

## What the result decides

- **Works as a generator** (checks mostly pass, the reading finds a usable pair): the existing runtime can serve for authoring through a thin wrapper, with the report as the output; next is the family specifications.
- **Works but weakly** (format fine, quality poor in a specific way): the specification must be tighter or the author model changed (Argon is the qualified stronger candidate); the failure mode found is written into the specification.
- **Does not work** (a runtime stop, the persona wins, the cap bites): authoring goes through another route or by hand, and the v4 plan's author decision is reopened.

Whatever happens is recorded as found. The probe's output is never edited and is not reused as a case.
