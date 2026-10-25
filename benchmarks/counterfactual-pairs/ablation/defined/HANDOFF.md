# Handoff brief: run the defined-verdicts arm (Claude CLI route)

For an orchestrating agent (Claude Code, an Antigravity agent, or a person) on the machine that ran the bare arm. Read all of this first. The owner, not you, decides whether live model calls happen and any money is spent.

This runs **only the `defined` arm**. The comparison arms are committed evidence (pilot 2 and the bare-arm run), so do not run those again. This brief reuses the structure of the [bare-arm brief](../HANDOFF.md); read that for the full stage-by-stage detail. The differences are below, and where they conflict, this file wins.

## 0. Decisions the owner must give you

Do not guess, search the machine, or pick values yourself. Ask for any that are missing.

| Decision | Required value | Why |
| --- | --- | --- |
| Absolute path to `claude` | `/home/john/.local/bin/claude`, the binary the bare arm used | The arms must differ only in the prompt |
| Binary SHA-256 | `520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe` | Same binary as the bare arm. If it differs, **stop and tell the owner before anything runs**; never install or downgrade |
| CLI version | `2.1.306 (Claude Code)` | Same as pilot 2 and the bare arm |
| Exact model id / effort | `claude-opus-5-5` / `high` | Same as both earlier arms |
| Per-case spend cap | `--max-budget-usd 5.0` | The value the bare arm used, so those two arms match. It never bound there (largest case $0.0756) |
| Trials | 2 | One tool-free turn per case per trial |
| Working root | a new directory **outside** the repository, e.g. `/tmp/defined` | Never reuse an earlier workdir |
| Written authorization | none | Live calls to the Claude CLI are authorized, use the owner's account or credits, and by how much |

**Expected cost and time.** The bare arm cost $1.38 and $1.40 for 40 cases and took about 17 s per case. Expect about the same, roughly $1.40 per trial and 10 to 15 minutes. An estimate, not a bound.

## 1. What this is, and what its results can claim

The [preregistration](PREREGISTRATION.md), pinned by [manifest.json](manifest.json), is the authority; read it first. In short: the bare arm gave a verdict line with no meaning and its verdicts did not separate defective plans from sound ones (21 of 37 pairs ordered), although its reports had found every defect. This arm is **identical to the bare arm except for one block of five lines defining the three verdicts**, and asks whether that closes the gap.

- Route `claude-cli`, a Claude model, not Gemini. Isolation is CLI configuration, not the qualified containment.
- Either outcome is valid and is published as found, including "worse than bare".
- You are the **orchestrator**: prepare, launch, verify and report. You never judge a case, never score, and never improve the prompt.

## 2. Rules that override convenience

1. **Never self-heal.** If a command fails or prints anything unexpected, do not debug, edit, change flags, install, log in, set keys or retry. Stop, paste the exact output, and wait.
2. **Do not touch the prompt.** Never edit `defined-request.txt`, `bare-system.txt`, `rubric.json`, either `PREREGISTRATION.md`, either `manifest.json` or any other repository file. If the arm behaves badly (for example the model ignores the definitions or ends with text after the verdict line), that is a result.
3. **Zero retries.** Never rerun a case or trial, delete or recreate a workdir, or rerun after a stop. A recorded stop is a result.
4. **Do not read `v2/oracle/`, score anything, or judge reports.** Do not say whether a report looks right, and do not edit or summarize one.
5. **Do not authenticate.** Never run `claude login` or `claude setup-token`, create or export API keys, or read credential files.
6. **One model route only.** Never use another model, CLI or service, including yourself, as a substitute reviewer.
7. **Live calls need a fresh go.** Run `--execute` only after the owner writes "go trial N" in this session, for that trial only.
8. **No secrets in output.** Do not commit, push or open a pull request. Keep evidence under the working root.
9. Antigravity or other auto-running agents: run terminal commands one at a time with approval on, never auto-run `--execute`, no parallel agents, no browser, never two drivers at once.

## 3. Stage A: verify the repository (no model call)

```bash
git rev-parse HEAD
git status --short                                   # must be empty
sha256sum benchmarks/counterfactual-pairs/v2/manifest.json benchmarks/counterfactual-pairs/ablation/manifest.json benchmarks/counterfactual-pairs/ablation/defined/manifest.json
python3 -B -I tools/check_release.py
python3 -B -I benchmarks/counterfactual-pairs/v2/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/ablation/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/ablation/defined/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/ablation/test_ablation.py
python3 -B -I benchmarks/counterfactual-pairs/test_verify_run.py
```

Expected: clean tree, and `PASS` or `OK` everywhere. The v2 manifest must be `79facc8afe49f243009a813e63f9f77adfa284567982af2282daf9948eb6316b` and the bare-arm manifest `35d7ea8dd779078b95b3c854da645f3039f91bec2cec068c8f9355fab4c4dcbb`. Record all three manifest hashes and the commit.

## 4. Stage B: Claude CLI identity (no model call)

```bash
/home/john/.local/bin/claude --version
sha256sum /home/john/.local/bin/claude
```

Both must match section 0. Do not run `claude` any other way and do not send a test prompt: the first live case is the first model call.

## 5. Stage C: dry run (no model call)

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm defined \
  --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /home/john/.local/bin/claude --model claude-opus-5-5 --effort high \
  --max-budget-usd 5.0 --workdir <root>/work
```

Expected last line: `"status": "DRY_RUN_PREPARED_ONLY"`, `"prepared": 40`, `"arm": "defined"`. Show the owner the full output and one `<root>/work/trial1/dry-requests/<case>/request.txt`. Confirm, without judging anything, that it begins `Please review this plan.`, shows the plan as plain lines (no `[S01:n]` numbering), contains the five-line `Verdicts mean this:` block, and ends with the three `VERDICT:` options. **Stop and wait for "go trial 1".**

## 6. Stage D: live trial N (only after "go trial N")

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm defined \
  --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /home/john/.local/bin/claude --model claude-opus-5-5 --effort high \
  --max-budget-usd 5.0 --workdir <root>/work --trial N --execute
```

For each of the 40 cases, in the frozen random order, one `claude -p` turn from an empty directory with all tools disabled, safe mode, no session persistence, the system prompt "You are a helpful assistant.", JSON output, the pinned model and effort, and the request on stdin. One line per case is appended to `<root>/work/responses-trialN.jsonl`. Run it in the background and poll the line count.

**First-case check.** Report only: `servedModels`, `costUsd`, `wallSeconds`, `safetyStops`, whether it has a `technicalStop`, and whether `<root>/work/trialN/attempts/<case>/REVIEW.md` ends with a `VERDICT:` line.

**Expect some stops.** In the bare arm, 4 of the 8 `output_bytes` observations were interrupted by the platform. That family may be interrupted here too. The driver records it as `SAFETY_INTERRUPTED:<n>`, a stop and never a verdict, and the preregistration reports the primary result with and without `output_bytes`. A `MODEL_MISMATCH` stop (any served model other than the requested one) is likewise recorded. If the driver prints `HALTED_CONSECUTIVE_STOPS` (three in a row), do not rerun and do not edit anything: report each stop code, each stopped case's `safety_stops`, `num_turns` and `modelUsage` from its `claude-output.json`, and the end of its `REVIEW.md`, and let the owner decide. The owner may authorize continuing the identical command with `--max-consecutive-stops 99`; they may not authorize changing the prompt.

**If the process dies:** do not start over; tell the owner and, with approval, rerun the identical command. Recorded cases are skipped, and an attempt directory with no record is logged `INTERRUPTED_UNKNOWN_STATE`.

| Output | Meaning | Action |
| --- | --- | --- |
| `ABLATION_CORPUS_MISMATCH` | `--corpus` is not the corpus the arm is pinned to | Fix the argument; no model was called |
| `ABLATION_PIN_MISMATCH:<file>` | A frozen file of this arm, or a file it borrows from the bare arm, changed | Stop and report; do not regenerate |
| `CORPUS_PIN_MISMATCH:<file>` | A frozen corpus file changed | Stop and report |
| `SAFETY_INTERRUPTED:<n>` | The platform interrupted a reply; the saved report may be an apology | Recorded stop; report; do not rerun |
| `MODEL_MISMATCH` | Any served model differs from the request, including a second model beside it | Recorded stop; report `servedModels` |
| `UNPARSEABLE_REPORT:NO_VERDICT_LINE` | The last line is not a verdict line | Recorded technical stop; keep the report |
| `CLAUDE_BIN_INVALID`, `CLAUDE_VERSION_FAILED`, `WORKDIR_INSIDE_REPOSITORY`, `WRAPPER_TIMEOUT`, `NO_JSON_OUTPUT:exitK`, `CLAUDE_ERROR:<reason>`, `INTERRUPTED_UNKNOWN_STATE`, `HALTED_CONSECUTIVE_STOPS` | As in the [v2 brief](../../v2/HANDOFF.md) | Recorded stop or stop-and-report; do not rerun |

## 7. Stage E: verify the run (no model call, after every trial)

```bash
python3 -B -I benchmarks/counterfactual-pairs/verify_run.py --arm defined \
  --corpus benchmarks/counterfactual-pairs/v2 --workdir <root>/work \
  --model claude-opus-5-5 --effort high --trials 1          # then --trials 1,2 after trial 2
```

It checks the corpus and arm pins (including the borrowed bare files), one ledger row per case, every saved request against what the frozen prompt and corpus produce, report hashes, the stamp and the system prompt, that every served model matches the request, and that no safety-interrupted observation was recorded as a verdict. Expected: `"failures": []` and exit status 0; stops are listed, not failures. Paste its full output. If `failures` is not empty, stop and report; do not repair evidence.

## 8. Later trials

After trial 1 is verified and reported, wait for "go trial 2", then repeat Stages D and E with `--trial 2` and the **same** workdir, model, effort, cap, binary and CLI. Change nothing between trials.

## 9. Hand back (no scoring)

- **Identity:** commit, the v2, bare-arm and defined-arm manifest SHA-256, `claude --version` and binary SHA-256, model, effort, spend cap, host OS, date and time of each trial.
- **Per trial:** recorded, executed and stopped counts; every stop code with its case id; total `costUsd`; the full `verify_run.py` output.
- **Evidence** untouched under `<root>/work`: `responses-trialN.jsonl`, and per case `request.txt`, `claude-output.json`, `claude-stderr.txt`, `REVIEW.md`. Bundle the working root as one archive.
- **Anything surprising,** quoted verbatim.

Then tell the owner the evidence is ready, and stop.

## 10. What happens afterwards

In a session on this branch, with the oracle available: `verify_run.py --arm defined` is rerun; the ledger is scored; [analyze.py](../analyze.py) runs twice, `defined` against `bare` and `defined` against the skill-style arm, each with and without the pre-specified exclusions, with the as-run and documented-rule views; every `defined`-arm defect twin without `NO_GO` and every sound plan with `NO_GO` is read in full and classified; and the outcome is labelled with the preregistered descriptive labels (closes the gap, partly closes it, does not close it, or worse). The baseline for the new "verdict follows finding" metric is 36 of 36 for the skill-style arm and 19 of 34 for the bare arm. Results are committed with the unmodified reports.
