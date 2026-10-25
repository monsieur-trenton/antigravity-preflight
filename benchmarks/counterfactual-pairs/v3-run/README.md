# The v3 run: tooling and preregistration

Three arms (`skill`, `defined`, `defined-go`) on the held-out [corpus v3](../v3/README.md), six runs in one sitting. **It has been run once, six runs: see the [results](../results/v3-claude-opus-5-5-high/README.md).**

| File | Role |
| --- | --- |
| `PREREGISTRATION.md` | The frozen design: arms, the six-run order, conditions, comparisons, labels, human reading, stop rules. It defers the corpus design and the primary metrics to the [corpus preregistration](../v3/PREREGISTRATION.md) |
| `manifest.json`, `build_manifest.py` | The run manifest: pins the preregistration, the corpus v3 manifest hash, the two arm manifests' hashes and the skill-style system prompt's hash. The arms' own manifests still name corpus v2 and are never edited; this binds them to v3 for this run. `--check` fails if anything changed |
| `analyze.py` | The preregistered analysis: three primary rates, strict and ordered pairs, secondary rates (including gap named but dismissed, from the v3 rubric), a per-family table, every pairwise paired comparison with an exact sign test, and the labels. Reads only the ledgers and reports it is given |
| `test_run.py` | Offline tests: manifest currency, tamper refusals, the stubbed driver under the run manifest for all three arms, the verifier's binding checks, and the analysis and labels on simulated arms |
| `HANDOFF.md` | The gated runbook for the orchestrating agent; it needs the owner's go before every live run and requires the run identity to be returned |

```bash
python3 -B -I benchmarks/counterfactual-pairs/v3-run/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3-run/test_run.py
python3 -B -I benchmarks/counterfactual-pairs/v3-run/analyze.py --corpus benchmarks/counterfactual-pairs/v3 \
  --rubric benchmarks/counterfactual-pairs/v3/rubric.json --arm skill=<dir> --arm defined=<dir> --arm defined-go=<dir> --out <file>
```
