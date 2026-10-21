# Handoff brief: run the pilot from Antigravity, with Claude as the reviewer

This brief is for an **Antigravity agent** acting as orchestrator. It runs the counterfactual-pairs pilot by driving the **Claude CLI** as the reviewer. Read all of it before running anything. The owner, not you, decides whether live model calls happen or any money is spent.

## 1. What this is, and what its results can claim

This is a **different route** from the repository's qualified Gemini routes ([HANDOFF.md](HANDOFF.md) covers those). Here:

- The **reviewer** is a Claude model, started one turn per case by `run_pilot_claude.py` through `claude -p`.
- **You are only the orchestrator.** You are a Gemini-based agent, but you are not under test. You do not review, judge or score anything.
- The route is labelled `claude-cli` in every ledger row. It says **nothing** about Gemini 3.8 Flash / High, the skill's qualified Flash or Argon runtimes, or technical containment. The reviewer is isolated by CLI configuration (no tools, no settings, no project files, an empty working directory), not by the qualified Bubblewrap sandbox.
- It is **not** an Antigravity Preflight native-route result. It tests whether a reviewer's judgments follow the changed fact in a plan rather than keywords or a tendency to reject everything. That question is route-independent.
- The Claude CLI reports which model served each turn, which the Gemini routes cannot. Every row records it, and a mismatch is a recorded stop.
- A pilot of 12 pairs supports no general accuracy rate. Everything is reported, including stops.

Design and corpus: [README.md](README.md), [testing-next.md](../../docs/testing-next.md).

## 2. Inputs the owner must give you

Ask for any that are missing. Do not guess, search the machine, or choose values yourself.

| Input | Notes |
| --- | --- |
| Absolute path to the `claude` executable | Must already be installed and authenticated for the user running this session |
| Exact model id | For example the id the owner names. No default, no alias search, no fallback |
| Effort | One of `low`, `medium`, `high`, `xhigh`, `max`. The owner chooses |
| Working root | A directory **outside** the repository, for example `/tmp/pilot-claude`. It is reused only to resume the same trial |
| Written owner confirmation | That live calls to the Claude CLI are authorized, that they will use the owner's Claude account or credits, and the per-case spend cap (default `--max-budget-usd 1.0`; a case's prompt is a few kilobytes) |

## 3. Rules that override convenience

These matter more than usual because coding agents tend to fix errors automatically.

1. **Never self-heal.** If any command fails or prints something this brief does not expect, do **not** debug it, edit files, change flags, install anything, log in, set API keys or retry. Stop, paste the exact output and wait.
2. **Zero retries.** Never rerun a case, rerun a trial, or delete or recreate a workdir. A recorded stop is a result.
3. **Do not modify** any file in the repository. In particular `run_pilot.py`, `run_pilot_claude.py`, `score.py`, `build_corpus.py`, `packets/`, `prompt.txt`, `manifest.json` and `oracle/`.
4. **Do not read `oracle/`, do not score, and do not judge reports.** Do not say whether a report looks right. Do not edit or summarize a report's findings.
5. **Do not authenticate.** Never run `claude login` or `claude setup-token`, never create or export API keys, and never read credential files. If the CLI is not authenticated, stop.
6. **One model route only.** Do not call any model other than through the driver. Do not use any other CLI, API or your own judgment as a substitute reviewer.
7. **Live calls need a fresh go.** Run `--execute` only after the owner writes "go trial N" in this session, for that trial only. Earlier approvals do not carry over.
8. **Antigravity behavior:**
   - Run terminal commands one at a time, with command approval on. Do **not** use "always proceed" or auto-run for the `--execute` step.
   - Do not start parallel or sub-agents, and never run two drivers at once.
   - Do not use the browser, or create or modify artifacts or files in the repository. Save evidence only under the working root.
   - Do not commit, push or open a pull request.
9. **No secrets in output.** Do not paste credentials, tokens or environment variables. Report hashes and bounded fields.

## 4. Stage A: verify the repository (no model)

```bash
git rev-parse HEAD
git status --short                      # must be empty
sha256sum benchmarks/counterfactual-pairs/manifest.json
python3 -B -I tools/check_release.py
python3 -B -I benchmarks/counterfactual-pairs/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/test_score.py
python3 -B -I benchmarks/counterfactual-pairs/test_run_pilot_claude.py
```

Expected: a clean tree, and `PASS` / `OK` from every check. `test_run_pilot_claude.py` takes about 6 seconds. Record the commit hash and manifest hash.

## 5. Stage B: Claude CLI identity (no model call)

```bash
/abs/path/to/claude --version
sha256sum /abs/path/to/claude
```

Record both. Do not run `claude` in any other way, and do not run a test prompt to check authentication. The driver's first live case is the first model call.

## 6. Stage C: dry run (no model call)

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py \
  --claude-bin /abs/path/to/claude --model <MODEL_ID> --effort <EFFORT> \
  --workdir <root>/work
```

Expected last line: `"status": "DRY_RUN_PREPARED_ONLY"`, `"prepared": 24`, `"route": "claude-cli"`, plus the CLI version. The dry run only runs `claude --version`, writes the 24 request files under `<root>/work/trial1/dry-requests/`, and makes no model call. It does not block a later `--execute` in the same workdir.

Show the owner the full output and one `dry-requests/<case>/request.txt`. **Stop and wait for "go trial 1".** If it prints `DRY_RUN_STOPPED` or `STOPPED`, report the `reason` verbatim and stop.

## 7. Stage D: live trial N (only after "go trial N")

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py \
  --claude-bin /abs/path/to/claude --model <MODEL_ID> --effort <EFFORT> \
  --workdir <root>/work --trial N --execute
```

For each of the 24 cases, in the frozen random order, the driver runs exactly one `claude -p` turn from an empty directory, with: all tools disabled (`--tools ""`), `--safe-mode`, no session persistence, slash commands disabled, MCP restricted to an empty config, a fixed read-only reviewer system prompt, JSON output, the pinned model and effort, a per-case spend cap, and the request on stdin. It appends one line per case to `<root>/work/responses-trialN.jsonl`. No fallback model is configured.

Run it in the background and poll the ledger's line count. Expect roughly 10 to 90 seconds per case.

**First-case check.** When the first line appears, report only these facts, without judging content:
- the ledger line's `servedModels`, `costUsd`, `wallSeconds` and whether it has a `technicalStop`
- whether `<root>/work/trialN/attempts/<case>/REVIEW.md` ends with a `MACHINE SUMMARY` block

If the served model is not the requested one, or the format is wrong, stop and ask. Otherwise let it finish.

**If the process dies:** do not start over. Tell the owner and, with their approval, rerun the **identical** command. Recorded cases are skipped, and an attempt directory with no record is logged as `INTERRUPTED_UNKNOWN_STATE` rather than re-run.

**If it prints `HALTED_CONSECUTIVE_STOPS`** (three stops in a row): do not rerun. Report each `technicalStop` and the contents of that case's `claude-stderr.txt` (first 20 lines).

### Stop reference

| Output | Meaning | Action |
| --- | --- | --- |
| `CLAUDE_BIN_INVALID` | Path is relative, missing or not executable | Ask the owner for the absolute path |
| `CLAUDE_VERSION_FAILED` | `claude --version` failed | Stop and report |
| `WORKDIR_INSIDE_REPOSITORY` | `--workdir` is inside the checkout | Choose a path outside |
| `CORPUS_PIN_MISMATCH:<file>` | A frozen file changed | Stop and report; do not regenerate |
| `WRAPPER_TIMEOUT` | No result within 600 s | Recorded stop; report |
| `NO_JSON_OUTPUT:exitK` | CLI did not print JSON (for example not authenticated) | Recorded stop; report stderr; do not log in |
| `CLAUDE_ERROR:<subtype>` | The CLI reported an error or a spend cap was hit | Recorded stop; report |
| `MODEL_MISMATCH` | Served model does not match the request | Recorded stop; report `servedModels` |
| `UNPARSEABLE_REPORT:<reason>` | No valid machine summary | Recorded technical stop; keep the report |
| `INTERRUPTED_UNKNOWN_STATE` | Attempt directory had no record | Recorded stop; report |
| `HALTED_CONSECUTIVE_STOPS` | Three stops in a row | Do not rerun; report |

A technical stop is **not** a wrong judgment. It stays in the ledger, and nothing replaces it.

## 8. Further trials

The design uses two separately authorized observations per case. After trial 1 is reported, wait for "go trial 2" and repeat Stage D with `--trial 2`, using the **same** workdir and arguments. The driver keeps trials separate by file and directory name. Do not change the model, effort, binary or flags between trials.

## 9. Hand back (no scoring)

- **Identity:** commit hash, manifest SHA-256, `claude --version` output and binary SHA-256, requested model, effort, per-case spend cap, host OS, and date and time of each trial.
- **Per trial:** counts of recorded, executed and stopped cases; each stop code with its case id; the total of `costUsd` across the ledger and the set of `servedModels` values.
- **Evidence** left untouched under `<root>/work`: `responses-trialN.jsonl`, and per case `request.txt`, `claude-output.json`, `claude-stderr.txt` and `REVIEW.md`.
- **Anything surprising,** quoted verbatim.

Then tell the owner the evidence is ready to bring back to a session on this branch, where `score.py` runs on the ledger, every mechanism and extra claim is adjudicated by hand, and results are reported with Wilson intervals and the `claude-cli` route label. Do not run `score.py` yourself.
