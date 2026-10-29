# Running the v4 reviewer run in blocks

Hand-off for whoever runs it (the owner, or an orchestrating agent on the owner's machine). Nothing here runs a model unless `--execute` is given. The agent-facing version is the skill [`.claude/skills/v4-benchmark-blocks/SKILL.md`](../../../../.claude/skills/v4-benchmark-blocks/SKILL.md); the design and the hypotheses are in [../review/PREREGISTRATION.md](../review/PREREGISTRATION.md).

## What the pieces are

| File | Role |
| --- | --- |
| `schedule.py`, `schedule-test.json`, `schedule-dev.json` | The blocks (6 pairs each, both wordings of a pair together, kinds mixed), the step order per route (arms alternate block by block), and the optional repeat steps. Rebuilt from public inputs and checked against the corpus manifest's pins; reads no case text. |
| `build_run_manifest.py` | The frozen run manifest: corpus hash, schedule hash, the reviewer files, the drivers, the preregistration, the Gemini runtime package and `agy` binary, the Claude model and system prompt. Written at the freeze. |
| `run_v4.py` (`status`, `next`, `bundle`) | The block driver for the `claude` and `gemini` routes. One turn per case, zero retries, resumable, stops at a case boundary. |
| `blocks.sh` | A wrapper that reads `~/.v4-bench.env` and calls the above. |
| `verify_v4.py` | Checks a workdir against the frozen files without reading the oracle. |
| `analyze_v4.py` | The preregistered analysis (needs the oracle, so it runs where the sealed corpus is). |
| `mechanism.py` | The blind mechanism reading: build items, read them with a model, turn answers into judgments. |
| `test_run_v4.py` | Offline tests with a stub Claude binary and a stub native runtime. |

## One-time setup (owner)

1. The sealed corpus directory (the build with text, from the authoring and revision bundles; `manifest.json` hash `2d13d475…b4b25`). Keep it outside the repository.
2. A working directory outside the repository for the run's state (`V4_WORKDIR`); it holds ledgers, attempts and the block log, and it is what makes the run resumable.
3. For Claude: the absolute path of the `claude` binary used in v3 (Claude Code 2.1.306). For Gemini: the `flash-high` runtime directory, the frozen capabilities directory and the offline qualification envelope for this host, as for the v3 Gemini run.
4. `~/.v4-bench.env`:

   ```bash
   V4_SPLIT=test                       # dev to rehearse on the public dev corpus
   V4_WORKDIR=$HOME/v4-run             # outside the repository
   V4_CORPUS=$HOME/v4-corpus-test      # the sealed corpus (with text)
   V4_RUN_MANIFEST=$HOME/antigravity-preflight/benchmarks/counterfactual-pairs/v4/run/manifest.json
   V4_CLAUDE_BIN=/abs/path/claude
   V4_RUNTIME_DIR=$HOME/antigravity-preflight/runtime/flash-high
   V4_CAPABILITIES=$HOME/caps
   V4_QUALIFICATION=$HOME/qual/DUAL-OFFLINE-QUALIFICATION.json
   ```

   `manifest.json` here is the frozen run manifest; it does not exist until the preregistration is frozen. To rehearse on the dev corpus, write one with `build_run_manifest.py --split dev --write ~/dev-run.json` and point `V4_RUN_MANIFEST` at it; a rehearsal's results are never evidence for the test split.
5. Measure first: run one small block (`blocks.sh next claude --execute --max-cases 3`, then the same for Gemini) while watching the machine, and read `blocks.sh status <route>` (seconds per case, peak child memory, load). If a block bogs the host down, shrink what you run per session (`--max-cases`, `--max-minutes`) or ask for a smaller block size before the freeze.

## Pacing and the machine

- **A block is the unit**: about 40 minutes of Gemini time, about 10 of Claude. A step is one block for one arm and trial; the schedule alternates arms block by block, so stopping anywhere leaves the arms equally far along.
- **Guards, all between cases**: `--max-minutes` (a case is not started if it could end past the budget, using the longest case seen), `--max-cases`, `--max-load` (default 1.5), the `STOP` file, `--max-total-usd` (Claude), three stops in a row. The driver also lowers its CPU and I/O priority.
- **Total time is unchanged** (about 24 Gemini block-runs of about 40 minutes and 48 Claude block-runs of about 10), but no session needs more than you give it. There is no deadline between blocks: days or weeks are fine.
- **Never run two blocks at once**, and never Claude and Gemini together.

## A session

```bash
B=benchmarks/counterfactual-pairs/v4/run/blocks.sh
$B status claude
$B next claude --execute --steps 2 --max-minutes 30
$B verify claude              # "failures" must be []
```

A block that was cut short (time, load, STOP) is continued by the same command; nothing is rerun. A case directory with no ledger row (a crash mid-call) is recorded as `INTERRUPTED_UNKNOWN_STATE` and never rerun.

## What an orchestrating agent must not do

Open case text, the oracle, an `attempts/` directory, a report or a packet; retry or repair a stop; edit the repository, the ledgers or the manifest; commit, push or open a pull request; run a live call the owner has not named; run the optional repeat steps without approval; state a result.

## Handing evidence back

- `blocks.sh bundle OUT.tar.gz --redacted` is for a session that must not see sealed text: ledgers with each quotation replaced by its hash, the block log, and the native receipts.
- `blocks.sh bundle OUT.tar.gz` (without `--redacted`) holds requests, reports and receipts. It stays with the owner or goes only to a reader the owner trusts with the text.
- Scoring needs the oracle. `blocks.sh analyze analysis.json` runs it where the corpus is; the output holds counts, pair ids and case ids, no plan text. Any adjudication file is written before the analysis is run.

## Mechanism reading

`mechanism.py build` writes the reading items (decisive fact and one report, no arm, route, trial or case) and a key; `mechanism.py read` asks a tool-free Claude turn per item (the reader is not blind to being Claude, and is not independent of the Claude arms); `mechanism.py ingest` turns the answers into the judgments file that `analyze_v4.py --judgments` takes. Run it after the blocks it covers are verified.

## Before the first live block of the test split

The preregistration is frozen and the run manifest is written from it (`build_run_manifest.py --split test --write …/manifest.json`), the full offline test suite passes at that commit, and a rehearsal on the dev corpus has run at least one block per route and verified clean. The owner says go.
