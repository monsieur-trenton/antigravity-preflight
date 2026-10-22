# Bare-prompt ablation arm

Does the skill-style review bundle change a reviewer's verdicts, compared with simply asking the same model to review the plan? Pilot 2 left the skill-style arm at a ceiling (20/20), so it could not say whether the corpus was easy or the bundle was doing the work. This arm removes the bundle and keeps everything else. **The arm has been run once, with Claude Opus 5.5 through the Claude CLI: the skill-style arm was far ahead on the verdict-only metric, but in all 15 missed defect twins the bare reviewer had found and named the defect. See the [results](../results/ablation-bare-opus-5-5-high/README.md).** The design, hypotheses, metrics and limits are in the [preregistration](PREREGISTRATION.md), pinned by [manifest.json](manifest.json) to the exact corpus v2.

| | `skill` arm (pilot 2, reused) | `bare` arm (this experiment) |
| --- | --- | --- |
| System prompt | read-only advisory plan reviewer, no tools | "You are a helpful assistant." |
| User message | review-contract prompt, numbered reading view, question, labelled machine summary | "Please review this plan.", the plan as plain text, and a final `VERDICT:` line |
| Held fixed | corpus v2, model, effort, Claude CLI route, tool-free safe mode, empty working directory, one turn per case | the same |

It tests the **bundle**, not its parts, and not the skill's citation check or adjudication step. A bare arm that does as well or better is a possible, publishable outcome. The primary comparison is verdict-only ordinal pair discrimination on 40 matched units with an exact sign test; with the skill arm already at 40 of 40, the design can only detect a *worse* bare arm, and only a large one-directional difference.

## Files

| File | Role |
| --- | --- |
| `bare-system.txt`, `bare-request.txt` | The frozen bare prompt; the only reviewer-visible text of this arm |
| `rubric.json` | Keyword proxy for "names the planted mechanism", used on defect twins only (it has recall but no specificity) |
| `PREREGISTRATION.md`, `manifest.json`, `build_manifest.py` | The frozen design and its pins; `--check` fails if any pinned file or the corpus changes |
| `analyze.py` | The preregistered comparison of two arms; reads no oracle beyond case-to-family mapping |
| `test_ablation.py` | Tests of the frozen files, driver, scorer, verifier and analysis, with simulated arms |
| `HANDOFF.md` | The gated runbook for an orchestrating agent |

## Running it

The drivers take `--arm bare`; the verifier takes `--arm bare`; the scorer reads the bare ledger as it does any other, using verdict-only definitions for this arm.

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm bare --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /abs/path/to/claude --model claude-opus-5-5 --effort high --max-budget-usd <CAP> --workdir <root>/work     # dry run
python3 -B -I benchmarks/counterfactual-pairs/verify_run.py --arm bare --corpus benchmarks/counterfactual-pairs/v2 \
  --workdir <root>/work --model claude-opus-5-5 --effort high --trials 1,2
python3 -B -I benchmarks/counterfactual-pairs/ablation/analyze.py --corpus benchmarks/counterfactual-pairs/v2 \
  --arm skill=benchmarks/counterfactual-pairs/results/pilot2-v2-claude-opus-5-5-high --arm bare=<results dir> --exclude caller_callee
```

Add `--execute --trial N` for a live trial, only with the owner's go. Read the [handoff brief](HANDOFF.md) first.

## Third arm: bare plus defined verdicts

The bare arm's verdicts did not separate defective plans from sound ones, although its reports had found every defect. The [`defined` arm](defined/README.md) is identical to the bare arm except for a five-line block saying what `GO`, `GO_WITH_CHANGES` and `NO_GO` mean, and tests whether that closes the gap. It has its own [preregistration](defined/PREREGISTRATION.md) and manifest, which borrows the bare system prompt and the rubric by hash, so the bare arm's own manifest and evidence are untouched. **It has been run once** ([results](../results/ablation-defined-opus-5-5-high/README.md)): 35 of 39 pairs ordered against 21 of 37 for the bare arm, and the preregistered label is "partly closes the gap". To rerun it with `--arm defined`, use the [handoff brief](defined/HANDOFF.md).
