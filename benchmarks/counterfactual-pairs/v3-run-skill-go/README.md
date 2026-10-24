# The skill-go run: the skill-style prompt plus one sentence, on corpus v3

One new arm, `skill-go`, on the [held-out corpus v3](../v3/README.md) through the Claude CLI route: the skill-style request of pilots 1 and 2 with **one line added** after the corpus prompt, the sentence from the `defined-go` arm adapted to the skill-style vocabulary (`NO_BLOCKERS_FOUND` for `GO`). It asks whether the sentence that made the plain-request arm judge 64 of 64 sound plans `GO` also stops the skill-style arm hedging 30 of 64 of them, without costing the defect twins or the evidence-gap twins ([why, and what is already known](PREREGISTRATION.md)). **Nothing has been run yet.** The arm was designed after the three v3 arms were read, so v3 is no longer held out for this question; the preregistration says so.

| File | Role |
| --- | --- |
| `PREREGISTRATION.md` | The frozen design: provenance, question, the arm, conditions, the optional concurrent control, metrics, labels, hypotheses, reading, stop rules and claims |
| `manifest.json`, `build_manifest.py` | The run manifest: pins the preregistration, the corpus v3 manifest hash, the arm's manifest and the skill-style system prompt (it also binds the unchanged `skill` arm for the optional control). `--check` fails if anything changed |
| `../ablation/skill-go/` | The arm: `skill-go-sentence.txt` (the one line), its manifest and `build_manifest.py` |
| `../run_pilot_claude.py`, `../verify_run.py` | The driver and verifier, extended with `--arm skill-go` (refused without a run manifest; the request is checked byte for byte against the skill-style request plus the one line); the other arms behave as before |
| `analyze.py` | The v3 analysis plus the preregistered labels for `skill-go` against `skill` and against `defined-go`, and the paired overclaiming comparison |
| `test_run.py` | Offline tests with a stub CLI: the one-line difference for all 64 cases, the sentence's relation to the `defined-go` sentence, manifest binding and refusals, a full 64-case run and its verification, the labels on simulated arms |
| `HANDOFF.md`, `run.sh` | The short handoff (where to find things, the rules, five commands) and the helper it drives: `checks`, `dry`, `live N --go` (refused without the flag), `bundle`. Two required runs, two optional control runs, about $5 to $10 |

```bash
python3 -B -I benchmarks/counterfactual-pairs/ablation/skill-go/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3-run-skill-go/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3-run-skill-go/test_run.py        # about 15 seconds
```

No model call is made by anything here except `run_pilot_claude.py --execute`, which the runbook gates behind the owner's go.
