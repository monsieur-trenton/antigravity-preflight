# Reviewer requests for corpus v4

What the reviewer under test is shown, as files and a builder, with nothing run on a model. This is the v4 counterpart of `v3`'s `prompt.txt` and `run_pilot.py` request builders; the corpus itself is [../test-audit-revision/](../test-audit-revision/README.md) (sealed) and the draft [PREREGISTRATION.md](PREREGISTRATION.md) says how the arms will be compared.

**Not the audit prompt.** The blind audit asked Claude whether a plan is sound, in the author's vocabulary. The reviewer arms use the skill's review contract, so an arm cannot do well by recognising the audit's questions.

## Files

| File | Role |
| --- | --- |
| `prompt.txt` | The skill-style contract. Source S01 is the plan, optional S02 a reference excerpt the plan is subject to. Keeps the two v3 sentences that tell the reviewer not to report an unsupported blocker and not to treat missing evidence as a proven defect. |
| `format-suffix.txt` | One question (Q01) and the machine summary block. A FINDING line cites `S01:12` or `S02:5`, so a quotation is checked against the source it names. |
| `bare-request.txt`, `bare-reference-lead.txt` | The bare arm: a plain "Please review this plan", the material, and a final line that is exactly one of `VERDICT: GO`, `GO_WITH_CHANGES`, `NO_GO`. |
| `review_requests.py` | `build(arm, sources)` for the arms `skill`, `skill-go` and `bare`; `skill_request`, `bare_request`, `reading_view`, `parse_bare`. Accepts only `["S01"]` or `["S01", "S02"]`; anything else is refused. |
| `manifest.json`, `build_manifest.py` | SHA-256 pins of these files and of the borrowed ones (the skill-go sentence, the bare system prompt, the v4 parser and scorer, the families, the v3 driver and scorer, the Claude CLI system prompt). `--write` regenerates, `--check` fails on any difference. Not a run manifest. |
| `test_review.py` | Offline tests: no label or family word in any request, deterministic numbered requests for every dev case and arm, `skill-go` equals `skill` plus exactly one sentence, the worst-case request stays under the 131,072-byte prompt cap, bad source sets refused, round trip through `parse_v4` and `score_v4`, bare verdict parsing. |

## Arms

| Arm | Request | Routes |
| --- | --- | --- |
| `skill` | the skill-style contract and numbered sources | Gemini 3.8 Flash High native; Claude Opus 5.5 CLI |
| `skill-go` | `skill` plus the one optional-suggestions sentence tested in v3 | Claude Opus 5.5 CLI |
| `bare` | a plain request, verdict on the last line | Gemini 3.8 Flash High native (and, optionally, Claude) |

**Caveat that stays attached to the Gemini `bare` arm.** The native runtime sends the request byte for byte as the user message (the verifier checks this), but under its fixed agent persona (`preflight-inline`: inline snapshots only, no tools, a cited Markdown report). The bare request therefore sits inside the runtime's own framing, which a plain chat request would not have. The arm measures "the plain request, in this runtime", not "no skill at all". If an offline check shows the wrapper changes the request more than the preregistration allows, the arm is dropped and the drop is reported.

## Where the rest is

The block driver, the Gemini multi-source packet, the schedule, the run manifest builder, the verifier, the analysis and the mechanism-reading tool are in [../run/](../run/HANDOFF.md). The run manifest, which binds the corpus, these files, the drivers and the preregistration, is written at the freeze.
