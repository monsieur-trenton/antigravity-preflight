---
name: v4-benchmark-blocks
description: Run, resume, check or stop the antigravity-preflight v4 benchmark in small blocks, one block at a time, over days or weeks. Use when the owner says "run the next benchmark block", "continue the v4 run", "how far is the benchmark", or "stop the benchmark". Makes live model calls only when the owner has authorized this session to; never opens case text.
---

# v4 benchmark blocks

The v4 reviewer run is cut into small blocks (6 pairs, about 12 to 14 cases) so it can be done in short sessions on a machine the owner is also using. Everything it needs is in `benchmarks/counterfactual-pairs/v4/run/`; the full procedure and the reasons are in `HANDOFF.md` there. The preregistration is `benchmarks/counterfactual-pairs/v4/review/PREREGISTRATION.md`.

You are the **orchestrator**. You run commands and report numbers. You do not interpret, edit, commit or push anything.

## Rules (they are part of the benchmark's validity)

1. **Live calls need the owner's go in this conversation**, naming how much: for example "run two Claude blocks" or "run Gemini for 90 minutes". Without it, run `status` and dry runs only. Never widen a go: one go covers the amount named, then stop and report.
2. **never open** the corpus text, the oracle, an `attempts/` directory, a report, a request file or a packet. They are sealed case text. Read only the JSON these commands print.
3. **No retries, no repairs, no reruns.** A stop is recorded by the driver and stays. If a block halts, say why and wait.
4. **One process at a time.** Do not start a second block, and do not run the Claude and Gemini routes at once.
5. **Do not edit** any file under the repository, the workdir's ledgers, or the run manifest. Do not commit, push, or open a pull request.
6. If the machine is busy (the driver stops with `HOST_LOAD`), do not work around it. Report it and offer to try later.

## Commands

The wrapper reads the owner's settings from `~/.v4-bench.env` (see HANDOFF.md) and calls `run_v4.py` and `verify_v4.py`. From the repository root:

```bash
B=benchmarks/counterfactual-pairs/v4/run/blocks.sh
$B status claude            # progress, next step, measured seconds per case, spend, peak memory
$B status gemini
$B next claude              # DRY RUN: builds requests, no model call
$B next claude --execute --steps 1 --max-minutes 30         # one block, never starting a case that could pass 30 minutes
$B next gemini --execute --steps 1 --max-minutes 60
$B verify claude            # after a block: checks the ledger against the frozen files; "failures" must be []
$B stop                     # the running block stops after its current case;  $B resume removes the STOP file
$B bundle /path/handback.tar.gz --redacted   # ledgers with quotations hashed, block log, receipts: safe to hand back
```

## A session

1. `status` for the route. Tell the owner what is next and the estimate (`nextStepEstimateMinutes`).
2. Confirm the owner's go covers it. If it does not, ask once, with the numbers.
3. `next <route> --execute --steps N --max-minutes M` with the amounts the owner named. Add `--max-load` only if the owner names a different load limit (default 1.5).
4. Read the printed JSON: `blockRuns` (cases recorded, stops, cost, wall seconds, peak memory) and `stoppedBecause` (`STEPS_DONE`, `TIME_BUDGET`, `MAX_CASES`, `HOST_LOAD`, `STOP_FILE`, `SPEND_CAP`, `CONSECUTIVE_STOPS`, `NO_MORE_STEPS`).
5. `verify <route>`. Report `failures` verbatim. If it is not empty, stop and say so; do not continue to the next block.
6. Report in a few lines: blocks done of total, stops, cost, anything unusual. Never state a result or a rate: the analysis is the owner's, after the run.

Between sessions nothing needs to be kept in your memory: the workdir holds the state, and `status` rebuilds it. Do not run the optional repeat steps (`--include-optional`) unless the owner has approved them by name.
