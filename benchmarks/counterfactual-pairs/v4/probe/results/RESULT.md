# Result of the authoring probe

One live call, as [PROBE.md](../PROBE.md) fixes it, run on 2026-10-25 (18:37 to 18:39 PDT) by the owner's orchestrator and returned as an archive (SHA-256 `f6ae439d51ce5817f0bd78126b9ca34b494dec8142ac2b7cdc45ab67fed3af93`, unpacked here unmodified). Read by me, the author of the probe and of the prompt, after the mechanical checks; the owner has not yet read the pair. **One sample: a feasibility result, not a measure of how often the runtime authors a usable case.**

## What happened

| | |
| --- | --- |
| Route | `runtime/flash-high`, model `gemini-3.8-flash-high` as requested (`servedAttestation: UNAVAILABLE`), `agy` 1.4.1 SHA-256 `16e228cb…f7508`, bound to the v3 Gemini run manifest `d853fee3…01ff5d2` |
| Commit | `a892f8f3c091ccd4155cc47db28d55b37006a0ab` |
| Prompt | `author-prompt.txt`, 3,325 bytes, SHA-256 `7c5875f6…90529`; 3,407 bytes on the wire, delivery `COMPLETE` |
| Receipt | `REPORT_RECEIVED_PENDING_ADJUDICATION`, no failure or closing failure, zero retries, one proxy and one native invocation, both reaped, private home and socket directory removed |
| Time and size | 152.7 s; the report is 10,311 bytes (the cap is 32,768) |
| Host stage | The first attempt stopped in the offline qualification (run 2, case 190, `FULL_JSON_FRAME_ACCOUNTED`, a 0.5 s control timing out, no model call), as the orchestrator reported in chat; its output was not returned. The rerun in a fresh root passed: 664 cases in two runs, status `PASS`. The two `diag` lines I asked for were not returned, so whether the machine was slower the first time is not recorded |
| Mechanical checks | All 14 pass: the markers, nothing outside the case, the oracle fields and numbers, 36 sound lines (32 to 44), line shape (117 to 216 characters, median 134), the twin is exactly the sound plan minus lines 13 and 14, no meta words, no admissions outside the decoy line, the decoy line does admit something |

## Questions of PROBE.md

1. **Transport: yes.** A non-review prompt ran to a clean receipt on the qualified route, in the time of an ordinary review turn.
2. **Persona: the assignment won.** The report is a case block with nothing before or after it; no review, no preamble.
3. **Size: fine for one pair.** 10.3 KB for a 36-line pair. The 32 KB cap means one pair per call up to roughly 90 lines in total; two wordings of one 45-line plan in one call would be about 20 KB.
4. **Instruction following: complete.** Every rule a program can decide held, including the exact twin relation and the oracle's line numbers (13, 14 for the fact, 15 for the decoy, 5 for the requirement), which are correct.
5. **Quality: usable, with four defects to design out.** Reading below.

## Reading against the criteria

- **Silent omission: yes.** The twin goes from the web application firewall line straight to the decoy and reads as a complete plan. Nothing dangles, no hedge or gap-shaped sentence, no hint that two lines are gone.
- **No absorbing fallback: plausibly yes, not certainly.** Nothing in the twin gives the current TTL or bounds how long caches keep the old address. Two lines come close and a careful reviewer might lean on them: the Dublin bridge "will verify when total request volume on Cloudflare declines below one percent" (a measurement, not a bound) and the 72-hour authorization of Cloudflare origin addresses (which makes stale clients harmless, not absent). The rollback also changes the same DNS record, so it depends on the same missing fact; that strengthens decisiveness.
- **Decisiveness: yes.** With the fact, a 60-second TTL checked against public resolvers makes the five-minute requirement credible; without it the plan cannot show it. The omission is the sort of thing an engineer would query.
- **Noise: good.** Realistic names, times, dashboards and ownership, internally consistent (the cutover at 02:30 inside the 02:00 to 04:30 window, the checkpoint at 03:30, the close at 04:00, observation for 48 hours). I found no second unestablished fact bearing on the requirement. The twin is still a plan a reviewer can pick at (no ramp, no rehearsal, a single record), which is what v4 needs from a sound plan.
- **Tempting alternative: weak.** The author named the decoy itself (the pending billing approval) rather than a technical alternative gap, so the field is no use as written.
- **Leakage: one cue.** The decoy sits directly after the removed lines, and the fact lines are mid-plan (13 and 14 of 36). Across 80 pairs that would be a pattern; positions must be randomized by the specification, not left to the author.

## Defects in the prompt, found by reading (mine, not the model's)

1. **The requirement sentence is ambiguous.** I wrote "no more than five minutes in which clients can reach either the old or the new path"; read literally, clients can always reach both during a cutover. The author copied it into the plan verbatim, so the sound plan's own requirement is unclear. Family specifications must give the requirement as a testable sentence ("within five minutes of the change every client resolves the new address").
2. **`tempting_alternative` was misread** because the prompt invited a gap "a reviewer might name instead", and the decoy is the obvious one. It should ask for a technical gap present in both plans that is not decisive, separately from the decoy.
3. **Positions are the author's choice**, and the author chose adjacent ones (above).
4. **Only one wording.** The prompt asks for one pair; wording B (an equivalent rewording of the whole plan) was not tested. It needs either a second call or both wordings in one call.

## Costs of authoring at the planned size, from this one call

About 153 s per pair. Eighty test pairs in two wordings is 160 plans; if one call yields one wording, about 6.8 hours of Gemini time before any failed or redone call, plus the dev split, plus the audit. That is of the order of one test-run trial and should be in the budget. Authoring retries are allowed (a rejected authored case is not a benchmark observation); every discarded call is recorded.

## What it decides

Under PROBE.md: **works as a generator.** The existing review runtime can serve for authoring through a thin wrapper with the saved report as the output. This does not settle the v4 author decision, because:
- the author here is the same model and route as the Flash reviewer under test, so a Flash-authored case may suit a Flash reviewer better than a Claude one. Claude arms on the same cases and the Claude audit are the guard, and a stronger or different-family author (Argon) would be the cleaner choice but is untested on this route;
- this is one pair, chosen by me, in a domain a language model writes well.

The next step is the family specifications, written with the four design changes above, followed by a small authored dev set that is read in full before the test split is written.

## Files

[orchestrator-identity.txt](orchestrator-identity.txt), [PROBE-SUMMARY.json](PROBE-SUMMARY.json), [PROBE-OUTPUT.md](PROBE-OUTPUT.md) (the author's report, unmodified), [CLI-RECEIPT.json](CLI-RECEIPT.json), [CLI-INIT.json](CLI-INIT.json), [CAPABILITIES-RESULT.json](CAPABILITIES-RESULT.json), [DUAL-OFFLINE-QUALIFICATION.json](DUAL-OFFLINE-QUALIFICATION.json). The output is not edited and is not reused as a case.
