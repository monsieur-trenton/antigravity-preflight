# The v3 run on the Gemini route: tooling and preregistration

One arm (the skill-style prompt, as the [Gemini pilot](../results/pilot-flash-high/README.md) ran it), two trials, on the held-out [corpus v3](../v3/README.md) through the native `flash-high` runtime. **Nothing has been run yet.** The Claude-route run (three arms) has its own [package](../v3-run/README.md).

| File | Role |
| --- | --- |
| `PREREGISTRATION.md` | The frozen design: the question, the one arm, what differs from the Gemini v1 pilot (the corpus, the wrapper driver, one parser relaxation), the conditions, metrics, comparisons, hypotheses, reading and stop rules |
| `manifest.json`, `build_manifest.py` | The run manifest: pins the preregistration, the corpus v3 manifest hash, the `runtime/flash-high` package (one hash over every file), the `agy` binary's SHA-256 (the one every receipt of the pilot recorded) and the parser. `--check` fails if anything changed |
| `../run_gemini_v3.py` | The driver: a wrapper around `run_pilot.py` (which is not edited) that refuses unless the corpus, runtime package, capabilities probe and binary match the manifest, reads a snapshot label `S01:<n>` in a FINDING's line field as line n, and stamps every ledger row |
| `../verify_gemini_run.py` | The verifier for a trial's working directory: prompts byte-identical to the frozen corpus, report and receipt hashes, re-parse reproduces the ledger, clean receipts (no retries, processes reaped, sandbox removed, prompt delivered, binary hash), order and stamps |
| `test_run.py` | Offline tests with a stub runtime: the manifest, the parser relaxation and its limits, the driver's refusals, a full 64-case run, the verifier's failure modes |
| `HANDOFF.md` | The gated runbook; it needs the owner's go before each trial and requires the run identity to be returned |

```bash
python3 -B -I benchmarks/counterfactual-pairs/v3-run-gemini/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3-run-gemini/test_run.py        # about 2 minutes
```

The analysis is [v3-run/analyze.py](../v3-run/analyze.py), which takes one arm (rates and no comparisons) or several (paired comparisons), so the Gemini run can be compared with the Claude skill-style arm if both exist.
