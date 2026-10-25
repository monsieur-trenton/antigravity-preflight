# Authorship and pre-run audit of the v3 corpus

Disclosed in the [preregistration](../PREREGISTRATION.md). Everything here happened before any reviewer arm saw a v3 plan.

## Authorship

The 16 families were written by **four independent model authors** (fresh Claude Opus agents, no tools, no files, no repository access), each given only the construction specification in [author-brief.txt](author-brief.txt) and a list of family ids and themes. They saw no arm, no result, no prompt used by any arm, and not the sentence that the fourth arm adds. Two authors wrote four defect families each (`d1`, `d2`), two wrote four evidence-gap families each (`u1`, `u2`). Their replies are in [../families.json](../families.json) exactly as returned, with one added field (`author`). **No text was edited after the audits, and none was edited before them**: the builder's structural checks (one changed line, line counts, numbers equal across wordings, forbidden words, line length) passed on the authors' first output.

What this does and does not buy. The authors are Claude models, so blind spots may correlate with Claude reviewers. The specification and the family themes were written by me (the benchmark's author) after seeing the v2 results and knowing the sentence the fourth arm adds; the evidence-gap themes were chosen as generic gaps (throughput, compatibility, idempotency, third-party limits, duplicate data, rollback time, payload size, permissions), not as variations on v2's runtime-budget plan. The specification asks for evidence-gap plans in which nothing makes a miss harmless, which is a design choice with a consequence: see the preregistration's limits.

## Method

Plans were unlabeled, shuffled with ids that carry no information, and given to fresh Opus agents that were told to read one file and use no other tool. The oracle was never given to an agent. Judgments were keyed to it afterwards.

- **Gap audit** (two agents, 32 plans each, the v2 style): for each plan, count real gaps, say whether the plan's own lines show a blocker (a failure, with the mechanism), whether a stated requirement depends on an unmeasured, unchecked or unconfirmed fact, and whether the plan is fully sound as it stands. Condensed per-plan answers: [judgments.json](judgments.json).
- **Classification audit** (two agents, each classifying all 64 plans in a different order), new for v3 because v2's one evidence-gap twin turned out to be contestable (see the preregistration). Each plan is classified with these definitions, which do not say which plans are expected to be which:
  - `FAILS`: the plan's own lines show that, as written, it will fail or break a rule it states; the lines and mechanism can be named from the text alone.
  - `UNESTABLISHED`: no line shows the plan failing, but at least one requirement or rule it states depends on a fact the plan leaves unmeasured, unchecked or unconfirmed, and nothing in the plan would make a miss harmless.
  - `ESTABLISHED`: every requirement or rule the plan states is established by its own lines; minor implementation details it does not spell out do not count.
  Per-plan classes keyed to the oracle: [classification.json](classification.json).
- The full model text was not retained verbatim. The four family files and the four audit replies were transcribed by me into [../families.json](../families.json), [judgments.json](judgments.json) and [classification.json](classification.json) and then compared programmatically with the agents' original replies in the session transcript: every family text, every gap-audit field and every class matched.

## Results

| | Count |
| --- | --- |
| Plans classified identically by both readers | **64 of 64** |
| Plans on which both readers match the class the construction rules assign | **64 of 64** (32 sound plans `ESTABLISHED`, 16 defect twins `FAILS`, 16 evidence-gap twins `UNESTABLISHED`) |
| Sound plans in which a gap audit flagged a blocker | 0 of 32 |
| Sound plans in which a gap audit flagged an unestablished fact | 0 of 32 |
| Sound plans a gap audit called fully sound | 32 of 32 |
| Defect twins in which a gap audit flagged a blocker | 16 of 16 |
| Evidence-gap twins in which a gap audit flagged a blocker | 0 of 16 (none was treated as a proven defect) |
| Evidence-gap twins in which a gap audit flagged the unestablished fact | 16 of 16 |

## Findings and limits

- No plan was changed, because nothing was flagged. That is suspicious as well as reassuring. v2's audits found pedantic gaps in every sound plan for a stricter reader, and these 32 sound plans drew none, which can mean the authors' explicit bounds worked, or that these auditors were lenient, or that the prompt (which allowed "would you pass it as it stands") produced a different bar. The audit cannot tell which.
- The classification audit is the check that v2 lacked: the evidence-gap twins are labelled `UNCERTAIN` by two independent blind readers with no fallback to argue from. It shows the labels are not contestable by those readers; it does not show they are not contestable by every reader, and the readers are Claude models.
- Both audits ran once, in one round. Neither was repeated after any edit because there was none.
- All auditors and authors were Claude models; a flaw that Claude models share would be invisible here.
