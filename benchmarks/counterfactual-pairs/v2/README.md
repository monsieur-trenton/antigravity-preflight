# Counterfactual pairs, corpus v2

A rebuilt, harder successor to the [v1 corpus](../README.md), prepared after [pilot 1](../results/pilot1-claude-opus-5-5-high/README.md) showed one v1 family was defective and the rest were mostly easy. **No model has been run on v2.** Its metrics, exclusion rule and limits are fixed in the [preregistration](PREREGISTRATION.md), which is pinned by the manifest.

| | v1 | v2 |
| --- | --- | --- |
| Cases | 24 (6 families) | 40 (10 families) |
| Defect types | mostly a visible contradiction between two lines | 7 of 10 families need inference: arithmetic, ordering, units, a rule applied to a fact elsewhere |
| Distractors | none | alarming-but-fine lines in every sound plan, repeated in the twin |
| Sound plans checked before freezing | no | four blind audit rounds ([record](audit/README.md)) |
| Primary metric | strict pair discrimination | calibrated ordinal pair discrimination, preregistered; strict reported beside it |
| Oracle | one decisive line | every legitimate citation line (`citeAnyOf`), plus a difficulty class |

Families: output byte limit (rebuilt), required coverage, ownership and authorization (inference), absent vs null, caller/callee (inference), runtime budget evidence (uncertainty, not a defect), deadline arithmetic, migration order, unit mismatch, permission chain.

Files: `packets/` and `prompt.txt` are the only reviewer-visible files (the prompt is byte-identical to v1's, so routes stay comparable); `oracle/` and `PREREGISTRATION.md` are never sent to a reviewer; `manifest.json` pins everything; `build_corpus.py --check` regenerates and compares; `test_corpus.py` tests the corpus and its metrics with simulated reviewers.

## Running it

The drivers and scorer take `--corpus`. Everything else in [HANDOFF.md](../HANDOFF.md) or [HANDOFF-ANTIGRAVITY-CLAUDE.md](../HANDOFF-ANTIGRAVITY-CLAUDE.md) applies, with 40 cases instead of 24:

```bash
python3 -B -I benchmarks/counterfactual-pairs/v2/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /abs/path/to/claude --model <MODEL_ID> --effort <EFFORT> --workdir <root>/work-v2          # dry run
python3 -B -I benchmarks/counterfactual-pairs/score.py --corpus benchmarks/counterfactual-pairs/v2 \
  <root>/work-v2/responses-trial1.jsonl results-v2-trial1.json
```

Add `--execute --trial N` for a live trial, only with the owner's go. Use a **new workdir** for v2: a ledger from v1 would be refused by the scorer, and mixing corpora in one workdir is not supported.

## Limits

- Audited, not proven sound: every sound plan still draws speculative gaps from a pedantic reader, and the auditors were Claude models.
- The primary metric cannot credit the two `evidence_gap` pairs when a reviewer hedges on the sound plan (documented in the preregistration).
- It still tests plan review of short text snapshots; it says nothing about the skill's workflow, a Gemini route, or real repositories.
