# Fourth arm: defined verdicts plus one sentence on optional suggestions

The [defined arm](../defined/README.md) closed most of the verdict gap but not the sound-plan part of it: it blocked all 35 defect twins that produced a verdict, yet judged only 8 of 40 sound plans clean, against 24 of 40 for the skill-style arm ([results](../../results/ablation-defined-opus-5-5-high/README.md)). Its sound-plan reviews said "these are improvements, not blockers" and then ended `GO_WITH_CHANGES`. This arm adds **one sentence** and asks whether that makes sound plans clean without losing the defect twins. **It has not been run yet.**

| | Defined arm | This arm |
| --- | --- | --- |
| System prompt | "You are a helpful assistant." | identical, borrowed by hash |
| Request | "Please review this plan.", the plan as plain text, the five-line definition block, a request to end with a `VERDICT:` line | identical, plus: *Optional suggestions that only make a working plan more robust are not changes it needs; if that is all you have, the verdict is GO.* |

**The sentence was written after seeing the defined arm's result, on the same corpus.** An improvement here is therefore a check of the mechanism, not out-of-sample evidence; the [preregistration](PREREGISTRATION.md) says so and fixes the outcome labels (including "costs detection") before any observation exists. A test checks that the request differs from the defined arm's by exactly that sentence.

| File | Role |
| --- | --- |
| `defined-go-request.txt` | The frozen request; the only reviewer-visible text of this arm besides the borrowed system prompt |
| `PREREGISTRATION.md`, `manifest.json`, `build_manifest.py` | The frozen design, its pins, and the borrowed files' hashes; `--check` fails if anything changes |
| `HANDOFF.md` | The gated runbook for the machine and binary that ran the earlier arms |

```bash
python3 -B -I benchmarks/counterfactual-pairs/ablation/defined-go/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm defined-go --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /abs/path/to/claude --model claude-opus-5-5 --effort high --max-budget-usd 5.0 --workdir <root>/work     # dry run
```

Add `--execute --trial N` only with the owner's go. Read the [handoff brief](HANDOFF.md) first.
