# Test audit, second round, and the final test corpus

66 calls to Claude Opus 5.5 through the Claude CLI on the 19 pairs rewritten after the first test audit, against the 182-case corpus of the rewrite round (manifest `0198eeb2…a989a808`), run by the owner's orchestrator at commit `c5e2fa8` on 2026-10-29: $3.75, no safety stops, one member answer recorded as a stop (its commentary is not parenthetical, so the lenient re-read refused it). Same auditor and caveats as the [first round](../test-audit/README.md); the case text is sealed and the ledger here is redacted.

## Result for the 19 rewritten pairs

| Decision | Pairs |
| --- | --- |
| Pass or pass with lines to read | 11 (N-0338d1, N-0a7387, N-32b8ec, N-5e4a36, N-6b4be1, N-7f61bb, N-95483c, N-af104e, N-c86ed8, N-e154ea, N-f41ebe) |
| Sent back again | 8 (N-497117, N-4c39c5, N-797729, N-9123f1, N-9be677, N-a86988, N-acf6ba, N-ef81c9) |

For N-497117 the sound-member answer is the recorded stop, but the twin was already recovered as an unestablished fact where the oracle says defect, so it is sent back on that alone. Reasons are codes only: a sound plan not recovered as sound (4 pairs), a twin recovered as the wrong class (2), not exactly one edit (2, one of them together with a sound plan not recovered), the wrong plan chosen (1).

## The policy and the final corpus

The policy was fixed before the round: rewrite once, drop what is still sent back. **The 8 are dropped** (reasons in [../test-drops.json](../test-drops.json), from codes only), with N-68f179 from the rewrite round, **9 dropped in all. The final test corpus is 71 pairs and 166 cases, manifest `2d13d475…b4b25`** ([sealed-manifest-final.json](sealed-manifest-final.json); the 12 wording-B pairs are all kept). Read against it, every remaining pair passes or passes with lines to read: 15 pass and 56 pass with lines to read, class recovered for 142 of 142 members, **agreement 71 of 71 pairs after rewriting and dropping. The first pass was 60 of 80, and the rewrite round recovered 11 of 19**; the 71 is not a first-pass rate. [audit-report-final.json](audit-report-final.json) is the report on the final corpus; [audit-report-before-drops.json](audit-report-before-drops.json) is the same answers read against the 79-pair corpus.

By family, pairs and share kept: contract_clause 8 of 8, open_item_becomes_decisive 8 of 8, config_limit 7 of 8, budget_arithmetic 7 of 7, ordering_dependency 7 of 7, omitted_measurement 6 of 7, omitted_propagation_window 6 of 7, scope_authority 6 of 6, omitted_access_check 6 of 6, open_item_absorbed 6 of 8, **policy_rule 4 of 8**. By kind: 20 single-source defects, 19 cross-source defects, 18 omitted unknowns, 14 decoy pairs. Twins: 47 defects and 24 gaps.

## Limits that matter for any claim built on this corpus

- **The corpus has been filtered by a Claude auditor.** A pair survives only if Claude Opus 5.5, shown the members blind, recovers the intended class (and, for deleted gaps, accepts the author's claim). The cases that remain are therefore ones a Claude model finds unobjectionable, and the Claude review arms are the arms most likely to be flattered by that. A Gemini reading of the dropped pairs, or of the retained ones, would test it; none exists.
- **The author and the audited reviewer arms share a family in one direction each**: Gemini 3.8 Flash High wrote the cases and is also a reviewer arm; Claude audited them and is also a reviewer arm.
- **No human has read any pair blind.** The owner's spot check was not done.
- **Dropping is uneven**: `policy_rule` keeps 4 of 8, so family-level statements about it rest on four pairs.
- **Selection by one auditor's objections includes some that may be overreach** (the abstract triage of the first round rated a few categories as likely overreach); the dropped pairs are reported, not hidden.
