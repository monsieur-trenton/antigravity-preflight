# Handoff brief: the preregistered v3 run (three arms, six runs, Claude CLI route)

For an orchestrating agent (Claude Code, an Antigravity agent, or a person) on the machine that ran the earlier arms. Read all of this first. The owner, not you, decides whether live model calls happen and any money is spent.

This runs the **six runs** of the [preregistration](PREREGISTRATION.md) on the held-out [corpus v3](../v3/README.md): three arms (`skill`, `defined`, `defined-go`) times two trials, in one sitting, in the fixed order below. The earlier evidence on corpus v2 is committed, so none of it is rerun. The structure follows the [defined-go brief](../ablation/defined-go/HANDOFF.md) and the [bare-arm brief](../ablation/HANDOFF.md); the differences are below, and where they conflict, this file wins.

## 0. Decisions the owner must give you

Do not guess, search the machine, or pick values yourself. Ask for any that are missing.

| Decision | Required value | Why |
| --- | --- | --- |
| Absolute path to `claude` | `/home/john/.local/bin/claude` | The binary every earlier arm used; the arms must differ only in the prompt |
| Binary SHA-256 | `520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe` | If it differs, **stop and tell the owner before anything runs**; never install or downgrade |
| CLI version | `2.1.306 (Claude Code)` | The same for every arm |
| Exact model id / effort | `claude-opus-5-5` / `high` | The same for every arm |
| Per-case spend cap | `--max-budget-usd 5.0` | The value the earlier arms used; it has never bound (largest case $0.0756) |
| Trials | 2 | Fixed by the preregistration |
| Working root | a new directory **outside** the repository, e.g. `/tmp/v3run` | One subdirectory per arm: `<root>/work-skill`, `<root>/work-defined`, `<root>/work-defined-go`. Never reuse an earlier workdir |
| Authorization mode | **"go run N"** for each run (default), or one message that names all six runs and a total spend limit | Say which. With the single-message mode you still stop at every anomaly |
| Written authorization | none | Live calls to the Claude CLI are authorized, use the owner's account or credits, and by how much |

**Expected cost and time.** About $1.5 to $1.9 and 12 to 18 minutes per run; about $10 in total (range $9 to $13). An estimate scaled from the v2 runs, not a bound.

## 1. What this is, and what its results can claim

The preregistration is the authority; read it and the [corpus preregistration](../v3/PREREGISTRATION.md) first. In short: corpus v3 has 64 cases, 8 of whose twins leave one decisive fact unestablished with nothing in the plan absorbing the miss. The run asks whether the one-sentence arm still makes sound plans clean, still blocks defect twins, and still costs evidence-gap twins their `GO_WITH_CHANGES`, with the skill-style arm for comparison.

- Route `claude-cli`, a Claude model, not Gemini. Isolation is CLI configuration, not the qualified containment.
- Either outcome is valid and is published as found.
- You are the **orchestrator**: prepare, launch, verify and report. You never judge a case, never score, and never improve a prompt.

## 2. Rules that override convenience

1. **Never self-heal.** If a command fails or prints anything unexpected, do not debug, edit, change flags, install, log in, set keys or retry. Stop, paste the exact output, and wait.
2. **Do not touch anything in the repository.** Not a prompt, a manifest, a preregistration, `rubric.json`, a packet or any script. If an arm behaves badly (the model ignores a definition, ends with text after the verdict line), that is a result.
3. **Zero retries.** Never rerun a case or a run, delete or recreate a workdir, or rerun after a stop. A recorded stop is a result.
4. **Do not read `v3/oracle/`, `v3/families.json` or `v3/audit/`, score anything, or judge reports.** Do not say whether a report looks right, and do not edit or summarize one.
5. **Do not authenticate.** Never run `claude login` or `claude setup-token`, create or export API keys, or read credential files.
6. **One model route only.** Never use another model, CLI or service, including yourself, as a substitute reviewer.
7. **Live calls need a go.** Run `--execute` only after the owner's go for that run (or the single message that named it).
8. **The order is fixed.** Do not reorder, skip or merge runs, and never run two drivers at once.
9. **No secrets in output.** Do not commit, push or open a pull request. Keep evidence under the working root.
10. Antigravity or other auto-running agents: run terminal commands one at a time with approval on, never auto-run `--execute`, no parallel agents, no browser.

## 3. The six runs, in this order

| Run | Trial | Arm | Workdir |
| --- | --- | --- | --- |
| 1 | 1 | `skill` | `<root>/work-skill` |
| 2 | 1 | `defined-go` | `<root>/work-defined-go` |
| 3 | 1 | `defined` | `<root>/work-defined` |
| 4 | 2 | `defined` | `<root>/work-defined` |
| 5 | 2 | `skill` | `<root>/work-skill` |
| 6 | 2 | `defined-go` | `<root>/work-defined-go` |

Record the start and end time of every run.

## 4. Stage A: verify the repository (no model call)

```bash
git rev-parse HEAD
git status --short                                   # must be empty
sha256sum benchmarks/counterfactual-pairs/v3/manifest.json benchmarks/counterfactual-pairs/v3-run/manifest.json \
  benchmarks/counterfactual-pairs/ablation/manifest.json benchmarks/counterfactual-pairs/ablation/defined/manifest.json \
  benchmarks/counterfactual-pairs/ablation/defined-go/manifest.json
python3 -B -I tools/check_release.py
python3 -B -I benchmarks/counterfactual-pairs/v3/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3-run/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/ablation/defined/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/ablation/defined-go/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3/test_corpus.py
python3 -B -I benchmarks/counterfactual-pairs/v3-run/test_run.py
python3 -B -I benchmarks/counterfactual-pairs/test_verify_run.py
python3 -B -I benchmarks/counterfactual-pairs/test_run_pilot_claude.py
```

Expected: a clean tree, `PASS` or `OK` everywhere, and these hashes: v3 corpus `1ad685287cf4623dae5e8b3109554b2f0859152a28875e8ddfc4d4c5e7554202`; the v3 run manifest `3751f9acabeb2d60acfd6dd132db8079cc66c7b4ffc14a0ed7a4628d8e4d2f6a` (it is stamped on every ledger row); bare arm `35d7ea8dd779078b95b3c854da645f3039f91bec2cec068c8f9355fab4c4dcbb`; defined `60f9268660ec0fb2fd545d2c835d5997eaa2f1362a798af7e92a43415d817484`; defined-go `b628683f9140c2c20c4f583c672244b15a99fd4a3c007efc348bb7ee68b0f356`. Record all of them and the commit.

## 5. Stage B: Claude CLI identity (no model call)

```bash
/home/john/.local/bin/claude --version
sha256sum /home/john/.local/bin/claude
```

Both must match section 0. Do not run `claude` any other way and do not send a test prompt: the first live case is the first model call.

## 6. Stage C: dry runs, one per arm (no model call)

For each of `skill`, `defined-go`, `defined`:

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm <ARM> \
  --corpus benchmarks/counterfactual-pairs/v3 --run-manifest benchmarks/counterfactual-pairs/v3-run/manifest.json \
  --claude-bin /home/john/.local/bin/claude --model claude-opus-5-5 --effort high \
  --max-budget-usd 5.0 --workdir <root>/work-<ARM>
```

Expected last line of each: `"status": "DRY_RUN_PREPARED_ONLY"`, `"prepared": 64`, the arm's name and `"runManifestSha256"`. Show the owner the three outputs and one `<root>/work-<ARM>/trial1/dry-requests/<case>/request.txt` per arm. Confirm, without judging anything: the `skill` request begins `You are reviewing one plan snapshot.`, numbers the snapshot lines and ends with a `MACHINE SUMMARY` block; the other two begin `Please review this plan.`, show the plan as plain lines, contain the `Verdicts mean this:` block, and end with the three `VERDICT:` options; the `defined-go` request additionally has the sentence beginning `Optional suggestions`, and the `defined` request does not. **Stop and wait for "go run 1".**

## 7. Stage D: a live run (only after the go for that run)

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot_claude.py --arm <ARM> \
  --corpus benchmarks/counterfactual-pairs/v3 --run-manifest benchmarks/counterfactual-pairs/v3-run/manifest.json \
  --claude-bin /home/john/.local/bin/claude --model claude-opus-5-5 --effort high \
  --max-budget-usd 5.0 --workdir <root>/work-<ARM> --trial <N> --execute
```

for the arm and trial of that run in section 3. One `claude -p` turn per case, from an empty directory with all tools disabled, in the frozen random order; one line per case is appended to `<root>/work-<ARM>/responses-trial<N>.jsonl`. Run it in the background and poll the line count.

**First-case check (run 1 only, then for each new arm's first run).** Report only: `servedModels`, `costUsd`, `wallSeconds`, `safetyStops`, whether it has a `technicalStop`, and (for the verdict-only arms) whether its report ends with a `VERDICT:` line.

**Expect some stops.** The platform interrupted bare-style prompts on one family in earlier arms (4 of 80 bare, 1 of 80 defined, 0 of 80 defined-go); v3 has no such family, so there may be none. The driver records `SAFETY_INTERRUPTED:<n>` and `MODEL_MISMATCH` as stops, never verdicts. If it prints `HALTED_CONSECUTIVE_STOPS` (three in a row), do not rerun and do not edit anything: report each stop code, each stopped case's `safety_stops`, `num_turns` and `modelUsage` from its `claude-output.json`, and the end of its report, and let the owner decide. The owner may authorize continuing the identical command with `--max-consecutive-stops 99`; they may not authorize changing anything else.

**If the process dies:** do not start over; tell the owner and, with approval, rerun the identical command. Recorded cases are skipped, and an attempt directory with no record is logged `INTERRUPTED_UNKNOWN_STATE`.

| Output | Meaning | Action |
| --- | --- | --- |
| `RUN_CORPUS_MISMATCH` | `--corpus` is not the corpus the run manifest names | Fix the argument; no model was called |
| `RUN_ARM_NOT_BOUND` | the arm is not one of the run's three | Fix the argument |
| `RUN_ARM_MANIFEST_MISMATCH:<arm>`, `RUN_PIN_MISMATCH:<file>`, `RUN_SYSTEM_PROMPT_MISMATCH`, `ABLATION_PIN_MISMATCH:<file>`, `CORPUS_PIN_MISMATCH:<file>` | A frozen file changed | Stop and report; do not regenerate |
| `SAFETY_INTERRUPTED:<n>` | The platform interrupted a reply | Recorded stop; report; do not rerun |
| `MODEL_MISMATCH` | Any served model differs from the request | Recorded stop; report `servedModels` |
| `UNPARSEABLE_REPORT:<reason>` | The report did not end in the required form | Recorded technical stop; keep the report |
| `CLAUDE_BIN_INVALID`, `CLAUDE_VERSION_FAILED`, `WORKDIR_INSIDE_REPOSITORY`, `WRAPPER_TIMEOUT`, `NO_JSON_OUTPUT:exitK`, `CLAUDE_ERROR:<reason>`, `INTERRUPTED_UNKNOWN_STATE`, `HALTED_CONSECUTIVE_STOPS` | As in the [v2 brief](../v2/HANDOFF.md) | Recorded stop or stop-and-report; do not rerun |

## 8. Stage E: verify the run (no model call, after every run)

```bash
python3 -B -I benchmarks/counterfactual-pairs/verify_run.py --arm <ARM> \
  --corpus benchmarks/counterfactual-pairs/v3 --run-manifest benchmarks/counterfactual-pairs/v3-run/manifest.json \
  --workdir <root>/work-<ARM> --model claude-opus-5-5 --effort high --trials <N>      # use --trials 1,2 after the arm's second run
```

It checks the corpus and arm pins, one ledger row per case, every saved request against what the frozen prompt and corpus produce, report hashes, the stamp (including the run manifest hash), that every served model matches the request, and that no safety-interrupted observation was recorded as a verdict. Expected: `"failures": []` and exit status 0; stops are listed, not failures. Paste its full output. If `failures` is not empty, stop and report; do not repair evidence. Then report, for that run: recorded, executed and stopped counts, every stop code with its case id, total `costUsd`, start and end times. Then wait for the next go.

## 9. Hand back (no scoring)

Write `<root>/identity.txt` and include it in the archive. **Required** (the earlier archives omitted it):
- the commit, and the SHA-256 of the v3, v3-run, bare, defined and defined-go manifests;
- `claude --version` and the binary's SHA-256, model, effort, the exact spend cap passed, host OS, and the start and end time of each of the six runs;
- per run: recorded, executed and stopped counts, every stop code with its case id, total `costUsd`, and the full `verify_run.py` output.

Evidence stays untouched under `<root>`: per arm `responses-trial<N>.jsonl`, and per case `request.txt`, `claude-output.json`, `claude-stderr.txt` and the saved report. Bundle `<root>` as one archive. Report anything surprising verbatim, then tell the owner the evidence is ready, and stop.

## 10. What happens afterwards

In a session on this branch, with the oracle available: `verify_run.py` is rerun for every arm; an adjudication file naming any stops is written **before any metric is computed**; the skill-style ledger is scored with `score.py --corpus ...v3`; [analyze.py](analyze.py) runs for all three arms (all pairs, with its documented-rule view if the adjudication reclassifies anything, and the pre-specified exclusion views); the reading in the preregistration is done; the preregistered labels are applied; and results are committed with the unmodified reports.
