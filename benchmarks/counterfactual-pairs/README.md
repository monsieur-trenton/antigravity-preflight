# Blind counterfactual pairs: frozen pilot corpus

Prepared for benchmark B in the [benchmark plan](../../docs/benchmark-plan.md) and the design in [testing-next.md](../../docs/testing-next.md). **No model has been run on this corpus.** This directory holds the frozen inputs and the scorer, so the live pilot can be authorized and run without changing either afterwards.

## What is here

| Path | Reviewer may see it? | Purpose |
| --- | --- | --- |
| `packets/P-xxxxxx.txt` | Yes, one per submission | 24 plan snapshots with random identifiers and neutral content |
| `prompt.txt` | Yes | The single frozen review prompt |
| `oracle/oracle.json` | **Never** | Family, role, expected class and decisive line per case |
| `manifest.json` | Orchestrator only | SHA-256 pin of every file, plus a randomized submission order |
| `build_corpus.py` | n/a | Regenerates everything deterministically (seed in the file) |
| `score.py`, `test_score.py` | n/a | Scorer and its simulated-reviewer tests |

Six families, each a sound plan and a defective counterpart that differs in **one line**, in two equivalent wordings (A and B): output byte limits, required coverage, ownership and authorization, absent versus null, caller/callee compatibility, and runtime-budget evidence. Four cases per family, 24 in total.

The runtime-budget twin is deliberately not a defect. It lacks measured throughput, so the correct judgment is uncertainty (no VERIFIED blocker, and not a clean verdict). A reviewer that claims an inevitable timeout is scored `OVERCLAIMED`.

## Why the design resists gaming

- A reviewer that rejects everything flags all 12 sound plans and earns zero pair discrimination.
- A reviewer that approves everything misses every changed plan and also earns zero.
- Pair discrimination needs the sound plan *and* its changed twin judged correctly, in the same wording.
- Titles, family names and roles never appear in a packet; a test fails if they do.
- Credit for finding a defect requires a VERIFIED BLOCKER citing the decisive line with a quotation that actually appears on it.

## Running the pilot on a qualified host

To have an orchestrating agent such as Claude Code run it, give it the staged, gated [handoff brief](HANDOFF.md).

Prerequisites, all supplied by you for a host and runtime you are authorized to use: the exact agy binary, a frozen capabilities directory produced by `cli_capabilities.py`, and the offline qualification envelope for the chosen runtime. This repository does not distribute the binary or credentials, and host qualification does not transfer. Follow [runtime.md](../../skills/antigravity-preflight/references/runtime.md) or [argon-high.md](../../docs/argon-high.md) for setup. The route is never implied: choose the runtime directory explicitly. Argon additionally needs `--runtime-profile argon-high`, effort `high` and `useG1Credits=true`.

1. Confirm `build_corpus.py --check` and `test_run_pilot.py` pass, and record `manifest.json`'s hash and the repository commit.
2. **Dry run.** Prepares all 24 packets and calls no model. Use a fresh `--workdir` outside the repository, because prepare refuses to reuse an existing seed.

   ```bash
   python3 -B -I benchmarks/counterfactual-pairs/run_pilot.py \
     --runtime-dir runtime/flash-high --capabilities /frozen/capabilities \
     --qualification /path/DUAL-OFFLINE-QUALIFICATION.json --workdir /fresh/dry-run
   ```

3. **Live trial.** Add `--execute` with a new workdir, and `--trial 1`. Each case runs exactly one native turn: prepare, copy the seed once, verify the copy byte-for-byte, then `run --authorize-live`. There are no retries, repairs or fallbacks. A recorded case, including a stop, is never run again; an attempt directory with no record is logged as `INTERRUPTED_UNKNOWN_STATE`. The driver halts after three consecutive stops. Run `--trial 2` separately, in its own authorized invocation.
4. Score: `python3 -B -I benchmarks/counterfactual-pairs/score.py /workdir/responses-trial1.jsonl results-trial1.json`. Pass both trial ledgers as one JSON list to get repeatability.
5. Keep the original `GEMINI-REVIEW.md` in each `attempts/<case>/` unchanged, with its hash in the ledger. Record the retained cleanup and settlement fields from each `CLI-RECEIPT.json`. Adjudicate by hand every verdict, decisive quotation, mechanism and extra claim; preserve all failures.

The driver appends a fixed question and a machine-readable summary block to the frozen prompt (see `FORMAT_SUFFIX` in `run_pilot.py`). A report that does not follow it is recorded as `UNPARSEABLE_REPORT`, a technical stop kept apart from wrong semantic judgments, and still needs a human reading. For the original Flash route the numbered snapshot is placed inside the prompt, as its runbook requires; Argon assembles it from the declared source.

**Validation status.** The driver is tested against a stub runtime, and all 24 packets are accepted by the real Flash and Argon packet code (`row_bytes`, `assemble_packet`). It has not been run against a real agy binary. Expect to check the first dry run and the first live case by hand.

## Alternative route: Claude CLI as the reviewer

`run_pilot_claude.py` runs the same corpus with a Claude model as the reviewer, through `claude -p`, one turn per case. It is a **different route**, labelled `claude-cli` in every ledger row. It is not covered by the skill's qualified runtimes and says nothing about Gemini 3.8 Flash / High. Isolation is CLI configuration (tools disabled, `--safe-mode`, no session persistence, empty working directory, fixed read-only system prompt), not Bubblewrap containment, so make no containment claim. Unlike the Gemini routes, the CLI reports the serving model; a mismatch with the requested model is recorded as a stop and never scored. The same rules apply: dry run by default, zero retries, recorded cases never rerun.

To have an Antigravity agent orchestrate it, give it the [Antigravity handoff brief](HANDOFF-ANTIGRAVITY-CLAUDE.md). Costs are the owner's, capped per case with `--max-budget-usd`. Score the ledger with the same `score.py`, which reports the route, requested model and served models in its output.

## What the result will and will not show

Counts are reported with Wilson 95% intervals. Twelve pairs cannot support a general accuracy rate, and two trials of one case are not independent observations. The proposed pilot gate is zero unsupported VERIFIED findings, complete source and question coverage, and every mandatory oracle check satisfied before any readiness claim. Technical stops are counted apart from wrong semantic judgments.
