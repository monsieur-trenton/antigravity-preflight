# Handoff brief: run the preregistered v2 pilot (Claude CLI route)

For an orchestrating agent (Claude Code, an Antigravity agent, or a person) running on a machine where the `claude` CLI is installed and logged in. Read all of this before running anything. The owner, not you, decides whether live model calls happen and any money is spent.

## 0. Decisions the owner must give you

Do not guess, search the machine, or pick values yourself. Ask for any that are missing.

| Decision | Default for comparability with pilot 1 | Notes |
| --- | --- | --- |
| Absolute path to `claude` | none | Installed and authenticated for the user running this session |
| Exact model id | `claude-opus-5-5` | An alias or typo fails: pilot 1's first attempt used `opus-5.5` and every case stopped with an API error. The driver also stops any case whose served model does not match |
| Effort | `high` | One of `low`, `medium`, `high`, `xhigh`, `max` |
| Trials | 2 | One tool-free turn per case per trial; the preregistration requires two or more |
| Per-case spend cap | `--max-budget-usd 0.50` | Pilot 1 averaged about $0.03 per case. A case that exceeds the cap becomes a recorded stop, so do not set it low enough to cut off long inference cases. Same value for every trial |
| Working root | a new directory **outside** the repository, e.g. `/tmp/pilot2` | Never reuse a pilot 1 workdir |
| Written authorization | none | Live calls to the Claude CLI are authorized, will use the owner's Claude account or credits, and by how much |

**Expected cost and time.** Pilot 1 cost $0.67 and $0.47 for 24 cases and took about 11 seconds per case. Corpus v2 has 40 longer cases, so expect roughly $1 to $1.50 per trial and 10 to 30 minutes per trial. This is an estimate, not a bound; the spend cap bounds the worst case at 40 times the cap per trial.

## 1. What this is, and what its results can claim

Corpus v2 tests whether one reviewer model's verdicts follow a single changed fact in a plan, rather than keywords or a habit of approving or rejecting everything: 40 cases, 10 families, 20 pairs (a sound plan and a twin that differs in exactly one line), seven families needing inference across several lines. Its metrics, exclusion rule and limits are fixed in [PREREGISTRATION.md](PREREGISTRATION.md), pinned by the manifest. Read it first. The sound plans were audited blind before freezing ([audit/README.md](audit/README.md)); they are audited, not proven sound.

- Route `claude-cli`, a Claude model. It says nothing about Gemini or the qualified native runtimes, and nothing about the preflight skill's workflow value (a bare prompt versus the packet-and-adjudication process is a separate, later test).
- Isolation is CLI configuration (tools disabled, safe mode, no session persistence, empty working directory), not the qualified Bubblewrap containment. Make no containment claim.
- You are the **orchestrator**. You prepare, launch, verify and report. You never judge a case, and you never score.
- Nothing here estimates a general accuracy rate. Two trials of the same case are not independent samples.

## 2. Rules that override convenience

1. **Never self-heal.** If a command fails or prints anything this brief does not expect, do not debug, edit, change flags, install, log in, set keys or retry. Stop, paste the exact output, and wait.
2. **Zero retries.** Never rerun a case or trial, delete or recreate a workdir, or rerun after a stop. A recorded stop is a result.
3. **Do not modify any file in the repository.** In particular `PREREGISTRATION.md`, `manifest.json`, `packets/`, `prompt.txt`, `oracle/`, `build_corpus.py`, `score.py`, `run_pilot_claude.py`, `verify_run.py`. If something looks wrong, stop and report.
4. **Do not read `oracle/`, score anything, or judge reports.** Do not say whether a report looks right, and do not edit, reformat or summarize a report's findings.
5. **Do not authenticate.** Never run `claude login` or `claude setup-token`, create or export API keys, or read credential files. If the CLI is not authenticated, stop.
6. **One model route only.** Never use another model, CLI or service, including yourself, as a substitute reviewer.
7. **Live calls need a fresh go.** Run `--execute` only after the owner writes "go trial N" in this session, for that trial only.
8. **No secrets in output.** No credentials, tokens or environment variables.
9. Do not commit, push or open a pull request. Keep evidence under the working root.
10. Antigravity or other auto-running agents: run terminal commands one at a time with approval on, never use auto-run for `--execute`, do not start parallel agents, do not use a browser, and do not run two drivers at once.

## 3. Stage A: verify the repository (no model call)

```bash
git rev-parse HEAD
git status --short                                   # must be empty
sha256sum benchmarks/counterfactual-pairs/v2/manifest.json
python3 -B -I -c "import json;print(json.load(open('benchmarks/counterfactual-pairs/v2/manifest.json'))['pins']['PREREGISTRATION.md'])"
python3 -B -I tools/check_release.py
python3 -B -I benchmarks/counterfactual-pairs/v2/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/v2/test_corpus.py
python3 -B -I benchmarks/counterfactual-pairs/test_score.py
python3 -B -I benchmarks/counterfactual-pairs/test_run_pilot_claude.py
python3 -B -I benchmarks/counterfactual-pairs/test_verify_run.py
```

Expected: clean tree, and `PASS` or `OK` everywhere (`test_verify_run.py` and `test_corpus.py` take about 10 and 2 seconds). Record the commit, the manifest hash and the preregistration hash; together they identify what was frozen.

## 4. Stage B: Claude CLI identity (no model call)

```bash
/abs/path/to/claude --version
sha256sum /abs/path/to/claude
```

Record both. Pilot 1 used Claude Code 2.1.306; a different version is allowed but must be reported. Do not run `claude` any other way, and do not send a test prompt to check authentication: the first live case is the first model call.

## 5. Stage C: dry run (no model call)

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py \
  --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /abs/path/to/claude --model <MODEL_ID> --effort <EFFORT> \
  --max-budget-usd <CAP> --workdir <root>/work
```

Expected last line: `"status": "DRY_RUN_PREPARED_ONLY"`, `"prepared": 40`, `"route": "claude-cli"`, and the CLI version. The dry run only runs `claude --version` and writes the 40 request files under `<root>/work/trial1/dry-requests/`. It does not prevent a later `--execute` in the same workdir.

Show the owner the full output and one `dry-requests/<case>/request.txt`. **Stop and wait for "go trial 1".** On `DRY_RUN_STOPPED` or `STOPPED`, report the `reason` verbatim and stop.

## 6. Stage D: live trial N (only after "go trial N")

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py \
  --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /abs/path/to/claude --model <MODEL_ID> --effort <EFFORT> \
  --max-budget-usd <CAP> --workdir <root>/work --trial N --execute
```

For each of the 40 cases, in the frozen random order, the driver makes exactly one `claude -p` turn from an empty directory with all tools disabled, safe mode, no session persistence, slash commands disabled, MCP restricted to an empty config, a fixed read-only reviewer system prompt, JSON output, the pinned model and effort, the spend cap, and the request on stdin. It appends one line per case to `<root>/work/responses-trialN.jsonl`. No fallback model is configured.

Run it in the background and poll the ledger's line count.

**First-case check.** When the first line appears, report only: its `servedModels`, `costUsd`, `wallSeconds`, whether it has a `technicalStop`, and whether `<root>/work/trialN/attempts/<case>/REVIEW.md` ends with a `MACHINE SUMMARY` block. If the served model is not the requested one or the format is wrong, stop and ask. Otherwise let it finish.

**If the process dies:** do not start over. Tell the owner and, with approval, rerun the **identical** command. Recorded cases are skipped, and an attempt directory with no record is logged as `INTERRUPTED_UNKNOWN_STATE`, never re-run.

**On `HALTED_CONSECUTIVE_STOPS`** (three stops in a row): do not rerun. Report each `technicalStop` and the first 20 lines of that case's `claude-stderr.txt`.

| Output | Meaning | Action |
| --- | --- | --- |
| `CLAUDE_BIN_INVALID`, `CLAUDE_VERSION_FAILED` | Bad path or the CLI cannot run | Stop and report |
| `WORKDIR_INSIDE_REPOSITORY` | `--workdir` is inside the checkout | Choose a path outside |
| `CORPUS_PIN_MISMATCH:<file>` | A frozen file changed | Stop and report; do not regenerate |
| `WRAPPER_TIMEOUT` | No result within 600 s | Recorded stop; report |
| `NO_JSON_OUTPUT:exitK` | CLI did not print JSON (for example not authenticated) | Recorded stop; report stderr; do not log in |
| `CLAUDE_ERROR:<reason>` | The CLI reported an error, such as `api_error` or a spend cap | Recorded stop; report |
| `MODEL_MISMATCH` | Any served model differs from the request, including a second model beside the requested one | Recorded stop; report `servedModels` |
| `SAFETY_INTERRUPTED:<n>` | The platform interrupted a reply (`safety_stops` above 0); the saved report may be an apology or a continuation, never a clean review | Recorded stop; report; do not rerun |
| `UNPARSEABLE_REPORT:<reason>` | No valid machine summary | Recorded technical stop; keep the report |
| `INTERRUPTED_UNKNOWN_STATE` | Attempt directory with no record | Recorded stop; report |
| `HALTED_CONSECUTIVE_STOPS` | Three stops in a row | Do not rerun; report |

A technical stop is not a wrong judgment. It stays in the ledger and nothing replaces it.

## 7. Stage E: verify the run (no model call, after every trial)

```bash
python3 -B -I benchmarks/counterfactual-pairs/verify_run.py \
  --corpus benchmarks/counterfactual-pairs/v2 --workdir <root>/work \
  --model <MODEL_ID> --effort <EFFORT> --trials 1          # then --trials 1,2 after trial 2
```

It checks the corpus pins, one ledger row per case, every saved request byte-for-byte against the frozen corpus and driver, every report hash, that each report equals the CLI's result, the stamp, and the served model. It reads no oracle and scores nothing. Expected: `"failures": []` and exit status 0; technical stops are listed, not failures. Paste its full output. If `failures` is not empty, stop and report; do not repair evidence.

## 8. Later trials

After trial 1 is verified and reported, wait for "go trial 2", then repeat Stages D and E with `--trial 2` and the **same** workdir, model, effort, cap and CLI. Do not change any of them between trials. Do not recapture or reinstall anything.

## 9. Hand back (no scoring)

- **Identity:** commit hash, v2 manifest SHA-256, preregistration SHA-256, `claude --version` output and binary SHA-256, model, effort, spend cap, host OS, and the date and time of each trial.
- **Per trial:** recorded, executed and stopped counts; each stop code with its case id; total `costUsd`; the full `verify_run.py` output.
- **Evidence**, left untouched under `<root>/work`: `responses-trialN.jsonl`, and per case `request.txt`, `claude-output.json`, `claude-stderr.txt` and `REVIEW.md`. Bundle the whole working root as an archive for the owner to bring back.
- **Anything surprising,** quoted verbatim.

Then tell the owner the evidence is ready, and stop.

## 10. What happens after you hand back

In a session on this branch, with the oracle available, the results are scored against the preregistration:
1. `verify_run.py` is rerun on the returned archive.
2. `score.py --corpus benchmarks/counterfactual-pairs/v2` produces the primary (calibrated ordinal) and secondary metrics with Wilson intervals, per family, difficulty class and trial.
3. Every report that is not cleanly correct is read by hand. Any pair judged invalid is recorded in an adjudication file under the preregistration's rule **before** any adjusted figure is computed. The all-pairs result stays the headline.
4. Results, the unmodified reports, the adjudication and a verdict-matrix figure are committed under `results/`, with the corpus, route and model labelled. A flaw in the corpus found afterwards means a v3, not a re-score.

## 11. Appendix: running v2 on a qualified Gemini route instead

Use [../HANDOFF.md](../HANDOFF.md) for host setup, authorization and the stop table, with these changes: add `--corpus benchmarks/counterfactual-pairs/v2` to every `run_pilot.py` and `score.py` command, run the v2 checks above in Stage A, use a fresh workdir, and read every "24" as "40". The route label, qualification and containment claims are those of the Gemini runtime, not `claude-cli`. `verify_run.py` is specific to the Claude CLI route; for Gemini runs, verify the ledger against the preserved `CLI-RECEIPT.json` files by hand and say so. Comparing a Gemini result with a Claude result is valid only on the same corpus hash.
