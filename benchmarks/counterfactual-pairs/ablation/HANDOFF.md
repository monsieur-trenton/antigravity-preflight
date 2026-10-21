# Handoff brief: run the bare-prompt arm (Claude CLI route)

For an orchestrating agent (Claude Code, an Antigravity agent, or a person) on a machine where the `claude` CLI is installed and logged in. Read all of this first. The owner, not you, decides whether live model calls happen and any money is spent.

This runs **only the bare arm**. The comparison arm is pilot 2's committed evidence, so do not run the skill-style prompt again unless the owner separately asks for a concurrent skill arm (see section 10).

## 0. Decisions the owner must give you

Do not guess, search the machine, or pick values yourself. Ask for any that are missing.

| Decision | Required value | Why |
| --- | --- | --- |
| Absolute path to `claude` | the same installation as pilot 2 if possible | The arms must differ only in the prompt bundle |
| Exact model id | `claude-opus-5-5` | Same as pilot 2 |
| Effort | `high` | Same as pilot 2 |
| CLI version | `2.1.306 (Claude Code)` | Same as pilot 2. If `claude --version` shows another version, **stop and tell the owner before anything runs**; the owner decides whether the difference is acceptable. Never install or downgrade |
| Per-case spend cap | the value pilot 2 used (the ledger did not record it; the pilot 2 brief suggested `--max-budget-usd 0.50`) | Ask the owner which cap was used, and use the same |
| Trials | 2 | One tool-free turn per case per trial |
| Working root | a new directory **outside** the repository, e.g. `/tmp/ablation` | Never reuse a pilot 2 workdir |
| Written authorization | none | Live calls to the Claude CLI are authorized, use the owner's account or credits, and by how much |

**Expected cost and time.** Pilot 2 cost $1.24 and $0.90 for 40 cases and took about 12 seconds per case. A bare review is freer-form, so expect roughly the same, perhaps $1 to $2 per trial and 10 to 30 minutes per trial. An estimate, not a bound.

## 1. What this is, and what its results can claim

The question, the two arms, the metrics, the exclusions and the limits are in [PREREGISTRATION.md](PREREGISTRATION.md), pinned by [manifest.json](manifest.json). Read it first. In one paragraph: the same 40 plans of corpus v2 go to the same model, but instead of the skill-style prompt (review-contract wording, numbered reading view, labelled machine summary) the reviewer receives "Please review this plan.", the plan as plain text, and a request to end with `VERDICT: GO`, `GO_WITH_CHANGES` or `NO_GO`. It tests the *bundle* of prompt and packet, not the citation check or the adjudication step, and it cannot attribute an effect to one component.

- Route `claude-cli`, a Claude model, not Gemini. Isolation is CLI configuration (tools disabled, safe mode, no session persistence, empty working directory), not the qualified containment.
- The bare arm may do as well as, or better than, the skill arm. Either is a valid result and is published as found.
- You are the **orchestrator**: prepare, launch, verify and report. You never judge a case, never score, and never improve the prompt.

## 2. Rules that override convenience

1. **Never self-heal.** If a command fails or prints anything unexpected, do not debug, edit, change flags, install, log in, set keys or retry. Stop, paste the exact output, and wait.
2. **Do not touch the prompt.** The bare prompt files are frozen. If the bare arm behaves badly (for example the model keeps adding text after the verdict line), that is a result, not a bug to fix. Never edit `bare-request.txt`, `bare-system.txt`, `rubric.json`, `PREREGISTRATION.md`, `manifest.json` or any other repository file.
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
sha256sum benchmarks/counterfactual-pairs/v2/manifest.json benchmarks/counterfactual-pairs/ablation/manifest.json
python3 -B -I tools/check_release.py
python3 -B -I benchmarks/counterfactual-pairs/v2/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/ablation/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/ablation/test_ablation.py
python3 -B -I benchmarks/counterfactual-pairs/test_verify_run.py
```

Expected: clean tree, and `PASS` or `OK` everywhere (`test_ablation.py` about 10 seconds, `test_verify_run.py` about 20). The v2 manifest hash must be `79facc8afe49f243009a813e63f9f77adfa284567982af2282daf9948eb6316b`; the ablation manifest is bound to it, and the driver refuses any other corpus. Record both manifest hashes and the commit.

## 4. Stage B: Claude CLI identity (no model call)

```bash
/abs/path/to/claude --version
sha256sum /abs/path/to/claude
```

Record both. If the version is not `2.1.306 (Claude Code)`, stop and ask (section 0). Do not run `claude` any other way and do not send a test prompt: the first live case is the first model call.

## 5. Stage C: dry run (no model call)

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm bare \
  --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /abs/path/to/claude --model claude-opus-5-5 --effort high \
  --max-budget-usd <CAP> --workdir <root>/work
```

Expected last line: `"status": "DRY_RUN_PREPARED_ONLY"`, `"prepared": 40`, `"arm": "bare"`. It writes the 40 request files under `<root>/work/trial1/dry-requests/` and makes no model call.

Show the owner the full output and one `request.txt`. Confirm, without judging anything, that it begins `Please review this plan.`, shows the plan as plain lines (no `[S01:n]` numbering), and ends with the three `VERDICT:` options. **Stop and wait for "go trial 1".**

## 6. Stage D: live trial N (only after "go trial N")

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm bare \
  --corpus benchmarks/counterfactual-pairs/v2 \
  --claude-bin /abs/path/to/claude --model claude-opus-5-5 --effort high \
  --max-budget-usd <CAP> --workdir <root>/work --trial N --execute
```

For each of the 40 cases, in the frozen random order, one `claude -p` turn from an empty directory with all tools disabled, safe mode, no session persistence, the system prompt "You are a helpful assistant.", JSON output, the pinned model and effort, the spend cap, and the plain request on stdin. One line per case is appended to `<root>/work/responses-trialN.jsonl`.

Run it in the background and poll the ledger's line count.

**First-case check.** When the first line appears, report only: `servedModels`, `costUsd`, `wallSeconds`, whether it has a `technicalStop`, and whether `<root>/work/trialN/attempts/<case>/REVIEW.md` ends with a line `VERDICT: GO`, `VERDICT: GO_WITH_CHANGES` or `VERDICT: NO_GO`.

**A missing or malformed verdict line is expected to be possible in this arm.** It is recorded as `UNPARSEABLE_REPORT:NO_VERDICT_LINE`, a technical stop that the analysis counts as an instruction-following result. If the driver prints `HALTED_CONSECUTIVE_STOPS` (three in a row), do not rerun and do not edit anything. Report the stop codes and the end of each stopped `REVIEW.md` verbatim, and let the owner decide. The owner may authorize continuing the identical command with `--max-consecutive-stops 99` so the arm is completed as it behaves; they may not authorize changing the prompt.

**If the process dies:** do not start over; tell the owner and, with approval, rerun the identical command. Recorded cases are skipped, and an attempt directory with no record is logged `INTERRUPTED_UNKNOWN_STATE`.

| Output | Meaning | Action |
| --- | --- | --- |
| `ABLATION_CORPUS_MISMATCH` | `--corpus` is not the corpus the bare arm is pinned to | Fix the argument; no model was called |
| `ABLATION_PIN_MISMATCH:<file>` | A frozen bare-arm file changed | Stop and report; do not regenerate |
| `CORPUS_PIN_MISMATCH:<file>` | A frozen corpus file changed | Stop and report |
| `CLAUDE_BIN_INVALID`, `CLAUDE_VERSION_FAILED` | Bad path or the CLI cannot run | Stop and report |
| `WORKDIR_INSIDE_REPOSITORY` | `--workdir` is inside the checkout | Choose a path outside |
| `WRAPPER_TIMEOUT`, `NO_JSON_OUTPUT:exitK`, `CLAUDE_ERROR:<reason>`, `MODEL_MISMATCH` | As in the [v2 brief](../v2/HANDOFF.md) | Recorded stop; report |
| `UNPARSEABLE_REPORT:NO_VERDICT_LINE` | The last line is not a verdict line | Recorded technical stop; keep the report |
| `INTERRUPTED_UNKNOWN_STATE`, `HALTED_CONSECUTIVE_STOPS` | As above | Do not rerun; report |

## 7. Stage E: verify the run (no model call, after every trial)

```bash
python3 -B -I benchmarks/counterfactual-pairs/verify_run.py --arm bare \
  --corpus benchmarks/counterfactual-pairs/v2 --workdir <root>/work \
  --model claude-opus-5-5 --effort high --trials 1          # then --trials 1,2 after trial 2
```

It checks the corpus and arm pins, one ledger row per case, every saved request against what the frozen bare prompt and corpus produce, report hashes, the stamp (including the bare system prompt) and the served model. Expected: `"failures": []` and exit status 0; technical stops are listed, not failures. Paste its full output. If `failures` is not empty, stop and report; do not repair evidence.

## 8. Later trials

After trial 1 is verified and reported, wait for "go trial 2", then repeat Stages D and E with `--trial 2` and the **same** workdir, model, effort, cap and CLI. Change nothing between trials.

## 9. Hand back (no scoring)

- **Identity:** commit, v2 and ablation manifest SHA-256, `claude --version` and binary SHA-256, model, effort, spend cap, host OS, date and time of each trial.
- **Per trial:** recorded, executed and stopped counts; every stop code with its case id; total `costUsd`; the full `verify_run.py` output.
- **Evidence** untouched under `<root>/work`: `responses-trialN.jsonl`, and per case `request.txt`, `claude-output.json`, `claude-stderr.txt`, `REVIEW.md`. Bundle the working root as one archive.
- **Anything surprising,** quoted verbatim.

Then tell the owner the evidence is ready, and stop.

## 10. What happens afterwards

In a session on this branch the arms are compared as preregistered: `verify_run.py --arm bare` is rerun; `score.py --corpus ...v2` scores the bare ledger; [analyze.py](analyze.py) compares it with pilot 2's committed skill arm (paired units, exact sign test, the secondary metrics, the keyword rubric on defect twins, and a comparability check on model, effort and CLI version); and every bare report that is a missed defect twin or a blocked sound plan is read in full and classified, with the classifications written down before any adjusted figure. Results are committed with the unmodified reports.

If the owner wants a **concurrent** skill arm (to remove the non-concurrency caveat), run the [v2 brief](../v2/HANDOFF.md) afterwards with the same model, effort, CLI, cap and a new workdir, and say so when handing back; the analysis then compares the two fresh arms, and pilot 2 is compared with them separately as supplementary evidence.
