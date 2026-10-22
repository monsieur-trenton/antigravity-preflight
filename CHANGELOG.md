# Changelog

## Unreleased

- Add an offline fault-injection harness for the citation checker: 13 mechanical faults stopped with the expected reason, 2 semantic faults recorded as passing through, 4 manual checks listed as not exercised.
- Add dependency-free SVG figures (light and dark) generated from committed results, with a `--check` mode in CI.
- Add a frozen 24-case blind counterfactual-pair corpus (six families, two wordings), a hidden oracle and a scorer with Wilson intervals, tested with simulated reviewers. No model has been run on it.
- Add a one-turn, zero-retry pilot driver for qualified Flash or Argon hosts (dry run by default, resume-safe, halts on repeated stops) and a ledger-reading scorer; tested with a stub runtime and the real packet functions.
- Add a separate `claude-cli` route for the counterfactual-pair pilot (tool-free, isolated `claude -p` turns, served-model check, per-case spend cap) with an Antigravity orchestrator brief. It is not a qualified Gemini runtime; results are labelled by route and model.
- Record pilot 1 (Claude Opus 5.5 via the Claude CLI, 2 trials of 24 cases, 0 stops, $1.14) with the unmodified reports, the pre-registered score and a post-hoc adjudication that found one corpus family flawed. Add a verdict-matrix figure generated from the committed ledgers. API errors are now labelled by `terminal_reason`.
- Add counterfactual-pair corpus v2 (40 cases, 10 families, seven needing inference, distractors in every sound plan, a rebuilt output-byte family), a preregistration pinned by its manifest, and the record of four blind audit rounds on its sound plans. The scorer gains a corpus option, `citeAnyOf` citation lines and the preregistered ordinal metric as new keys; pilot 1's committed score still reproduces exactly. No model has been run on v2.
- Add `verify_run.py`, which checks a Claude CLI working directory against a frozen corpus (pins, one row per case, request bytes, report hashes, served model, stamp) without reading the oracle, and a self-contained brief for the v2 pilot. Verified against pilot 1's real run.
- Record pilot 2 (corpus v2, Claude Opus 5.5 via the Claude CLI, 2 trials of 40 cases, 0 stops, $2.14): preregistered primary metric 20/20 in both trials, strict 13/20 and 11/20 because 40% of sound plans were hedged, 0 false blockers, 0 unsupported VERIFIED findings; one pair adjudicated invalid under the preregistered rule. The scorer gains `--adjudication`, which adds an adjusted block beside the all-pairs result. The pair-matrix figure is generalized (pilot 1's is byte-identical) and generated for pilot 2 from the committed files.
- Add a preregistered bare-prompt ablation arm for corpus v2: frozen bare prompt files and keyword rubric pinned to the v2 manifest, `--arm bare` in the Claude driver and verifier (the default arm and all existing ledgers are unchanged), verdict-only metrics and bare-arm grading in the scorer, an `analyze.py` that compares two arms with paired units and an exact sign test, tests and a gated handoff brief. No bare-arm observation exists yet.
- Record the bare-prompt ablation (corpus v2, Claude Opus 5.5 via the Claude CLI, 2 trials, $2.78): verdict-only ordinal discrimination 21/37 against the skill-style arm's 40/40 (16 units against 0), neither arm blocked a sound plan, and the human reading found the defect named in all 15 missed bare twins. The run exposed platform safety interruptions (4 observations, all `output_bytes`, bare arm only) and one mixed-model observation; the driver now stops on any non-requested served model and on a safety interruption, the verifier enforces both, and the scorer and `analyze.py` take an adjudication that reclassifies named observations as stops in a second view beside the as-run one.
- Add a preregistered third ablation arm, bare plus defined verdicts (`--arm defined`), differing from the bare arm by exactly one five-line definition block (checked by a test): own manifest that borrows the bare system prompt and rubric by hash so the bare arm's manifest and evidence are untouched, a preregistration with outcome labels fixed in advance, the "verdict follows finding" metric in `analyze.py` (baseline 36/36 skill-style, 19/34 bare), tests and a gated brief.
- Record the third ablation arm (corpus v2, Claude Opus 5.5 via the Claude CLI, 2 trials, $2.33): 35/39 pairs ordered against the bare arm's 21/37 (12 units against 0, p = 0.0005) and the skill-style arm's 40/40 (4 units against 0, all in the documented runtime-budget family, p = 0.125); the preregistered label is "partly closes the gap". All 35 defect twins with a verdict received `NO_GO` (bare 19/34), no sound plan was blocked, and sound plans were still hedged (clean 8/40 against 24/40). One safety interruption (`output_bytes`) recorded as a stop; the orchestrator's binary hash, cap and host were not in the returned archive. A three-arm figure is generated from the committed ledgers and analyses.
- Add a preregistered fourth ablation arm (`--arm defined-go`): the defined arm plus exactly one sentence saying that optional suggestions that only make a working plan more robust are not changes the plan needs (a test checks the one-sentence difference). The sentence was written after the defined result, on the same corpus, and the preregistration says an improvement is therefore not out-of-sample. Own manifest borrowing the bare system prompt and rubric; earlier manifests untouched; outcome labels fixed in advance including "costs detection"; `analyze.py` gains strict pair discrimination, defect-twin and `fourth_arm_label` outputs as additive keys; tests and a gated brief that requires the run identity to be returned.
- Record the fourth ablation arm (corpus v2, Claude Opus 5.5 via the Claude CLI, 2 trials, $1.84, 0 stops, run identity returned complete): all 40 sound plans judged clean (defined 8/40, skill-style 24/40; 32 units to 0, p < 0.0001) and all 36 defect twins blocked, but 3 of the 4 uncertainty-twin observations (runtime-budget family) judged `GO`, so the preregistered label is "costs detection"; strict pair discrimination 37/40 against 24/40 skill-style. The sentence was written after the defined result on this corpus, so it is not out-of-sample. The platform interruptions did not recur. A four-arm figure is generated from the committed ledgers; the shared figure panels were refactored (the three-arm figure's data is unchanged, its panel caption corrected).
- Add counterfactual-pair corpus v3, a held-out successor to v2: 64 cases in 16 families (8 defect, 8 evidence-gap with no absorbing fallback), written by four independent model authors from a written specification, audited blind before freezing (two gap audits; two classification audits on which both readers matched the intended class on all 64 plans), with a preregistration that fixes three primary rates, the strict summary and four hypotheses before any observation, a keyword rubric, tests and a manifest. No reviewer arm has run on it; the ablation arms need v3 bindings, an `analyze.py` that takes a rubric and a run preregistration first.
- Add the benchmark plan covering ablation, counterfactual pairs and downstream-effect trials. No new live model observations were collected.

## 0.3.0 — 2026-10-19

- Publish the exact owner-activated r15 Argon / High runtime and its updated qualification envelope.
- Add deterministic source assembly, workspace/mode integrity checks, init-catalogue telemetry, registered cleanup/timing evidence and native citation recursion handling.
- Add portable 732-case suites run twice plus 40 saved-envelope controls, current activation provenance and r15 review reconciliation.
- Clarify available PLAN/DIFF support; preserve the original Flash runtime and manual default.

## 0.2.0 — 2026-10-18

- Add the exact qualified and owner-activated Argon / High native runtime, explicit profile binding and credit selection.
- Keep manual Flash default and original Flash runtime unchanged.
- Add portable Argon offline checks, provenance, source-host summaries and review reconciliation.


## Earlier additions included in 0.2.0

- Publish a sanitized historical four-case plan-audit case study, preserving original responses/scores and documenting the unqualified execution route and flawed oracle/control.
- Add strict retrospective label extraction and offline regression tests; keyword hints supply no semantic credit.
- Propose blind counterfactual testing and full-workflow integrity testing. No new live model observations were collected.

## 0.1.0 — 2026-10-17

Initial public release targeting Gemini 3.8 Flash / High.

- Manual PLAN/DIFF packet, review, coverage, citation and adjudication workflow.
- Local numbered-source and exact-quotation tools with 50 fixture scenarios.
- Byte-preserved six-file Flash native runtime and two-run 332-case offline harness.
- Portable project profile and a complete synthetic manual example.
- Source-host P1–P5 qualification and activation status documented with accepted limitations.

Publication changes documentation, packaging and offline release tooling. It does not change the qualified runtime bytes, install/activate a runtime on another host, add Argon support, or resume native observer work.

The offline harness's synthetic proxy uses a readiness file instead of opening an unused Unix socket. No native socket/authentication behavior is credited by these controls.
