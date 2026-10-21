# Third arm: bare plus defined verdicts

Does defining the three verdicts, and nothing else, close the gap that the [bare-arm run](../../results/ablation-bare-opus-5-5-high/README.md) found? There the verdict-only metric put the skill-style arm at 40 of 40 pairs and the bare arm at 21 of 37, yet the bare reviewer had named the planted defect in all 15 twins it missed, then ended `GO_WITH_CHANGES`. **This arm has not been run yet.**

| | Bare arm | This arm |
| --- | --- | --- |
| System prompt | "You are a helpful assistant." | identical, borrowed by hash |
| Request | "Please review this plan.", the plan as plain text, a request to end with a `VERDICT:` line | identical, plus: `GO` needs no changes; `GO_WITH_CHANGES` works as written but should be improved; `NO_GO` will fail or break a rule it states |

The block is the only difference. The comparison arms are committed evidence, so only this arm needs running.

| File | Role |
| --- | --- |
| `defined-request.txt` | The frozen request; the only reviewer-visible text of this arm besides the borrowed system prompt |
| `PREREGISTRATION.md`, `manifest.json`, `build_manifest.py` | The frozen design, its pins, and the borrowed files' hashes; `--check` fails if anything changes |
| `HANDOFF.md` | The gated runbook, written against the machine and binary that ran the bare arm |

New preregistered metric: **verdict follows finding**, the share of defect twins whose report matches the family rubric that received `NO_GO`. Baseline from the committed evidence: 36 of 36 for the skill-style arm, 19 of 34 for the bare arm. Preregistered outcome labels: closes the gap, partly closes it, does not close it, or worse. The wording of the definitions is close to what the skill's contract means by a blocker, which is the hypothesis, and the preregistration says so.

```bash
python3 -B -I benchmarks/counterfactual-pairs/ablation/defined/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm defined --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /abs/path/to/claude --model claude-opus-5-5 --effort high --max-budget-usd 5.0 --workdir <root>/work     # dry run
```

Add `--execute --trial N` only with the owner's go. Read the [handoff brief](HANDOFF.md) first.
