# Citation checker fault injection

Starts from the valid baseline in [examples/plan](../../examples/plan), applies **one fault per variant**, and runs the real [manual_citations.py](../../skills/antigravity-preflight/scripts/manual_citations.py) command line. No model, native CLI or provider is called.

![Fault injection matrix](../../docs/figures/fault-gate-matrix.svg)

| Class | Count | Expectation | Observed |
| --- | --- | --- | --- |
| Mechanical (hash drift, path escape, symlink, duplicate key, bad ledger, wrong coordinate, hallucinated quote) | 13 | Stopped with the exact reason code | 13 stopped, 13 reasons matched |
| Semantic (verbatim but misleading quotation) | 2 | Script accepts; Codex checks the premise | 2 accepted |
| Not exercised (coverage, unanswered question, report custody, model obeying injected text) | 4 | No script in the manual route | Listed, not scored |

The semantic rows are the point of the exercise. The quotation check is a substring match on the cited line, so a quote that drops "Do not" still matches while reversing the source's meaning, and a one-word quote proves almost nothing. This is consistent with the skill's rule that a matching quotation proves text placement, not that a claim is true. Neither row is a test failure; each is a documented limit that the Codex premise check in [SKILL.md](../../skills/antigravity-preflight/SKILL.md) step 4 must cover. If the checker is later hardened (for example with a minimum quote length), update the expectation and regenerate.

## Run

```bash
python3 -B -I benchmarks/fault-injection/run_faults.py            # rewrite results.json
python3 -B -I benchmarks/fault-injection/run_faults.py --check    # fail if results.json is stale
python3 -B -I benchmarks/plots/make_figures.py                    # redraw docs/figures
```

`results.json` records the SHA-256 of the checker it exercised, so any change to the script makes `--check` fail until the results are regenerated and reviewed.

## Scope

These results show the deterministic gate behaves as specified on 19 fixtures. They do not measure model review quality, and the 13/13 figure is not a general detection rate.
