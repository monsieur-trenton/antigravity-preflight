# Handoff brief: run the counterfactual-pairs pilot on a qualified host

This brief is for an orchestrating agent (for example Claude Code) running on the host that owns the authenticated `agy` binary. Read all of it before running anything. The owner, not you, decides whether live model calls happen.

> **Corpus v2.** The self-contained brief for the preregistered v2 corpus is [v2/HANDOFF.md](v2/HANDOFF.md); prefer it. In short, to run the [v2 corpus](v2/README.md) with this brief instead, add `--corpus benchmarks/counterfactual-pairs/v2` to every `run_pilot*.py` and `score.py` command below, use a fresh working directory, run `python3 -B -I benchmarks/counterfactual-pairs/v2/build_corpus.py --check` and `python3 -B -I benchmarks/counterfactual-pairs/v2/test_corpus.py` in Stage A, and read every "24" as "40" (cases, prepared, executed and ledger lines). Nothing else changes. Read the [preregistration](v2/PREREGISTRATION.md) first.

## 1. Purpose and your role

The pilot gives one reviewer model, through the repository's native runtime, 24 plan snapshots. Twelve are sound plans, and twelve are one-line-changed defective counterparts (five defective, one uncertain-evidence case, in two wordings each). The goal is to find out whether the reviewer's judgments follow the changed fact rather than keywords or a tendency to reject everything. The design is in [README.md](README.md) and [testing-next.md](../../docs/testing-next.md).

You are the **orchestrator**. You prepare, launch, preserve evidence and report. You are **not** the reviewer and you do not judge any case. The reviewer is the native `agy` session that `run_pilot.py` starts, one turn per case.

The pilot supports a small, qualified statement about this corpus and this runtime. It does not support a general accuracy rate. Report everything, including stops and failures.

## 2. Inputs you must have before starting

Ask the owner for any that are missing. Do not guess or search the machine for them.

| Input | Notes |
| --- | --- |
| Route | `flash-high` (default route) or `argon-high`. The owner chooses; never switch. Argon also requires `--runtime-profile argon-high`, model `gemini-4-argon-high`, effort `high`, `useG1Credits=true`. |
| Absolute path to the exact `agy` binary | Obtained separately from the vendor. This repository does not distribute it. |
| Working root | A directory **outside** the repository, for example `/tmp/pilot`. It must not exist yet for the first run. |
| Written owner confirmation | That this host and runtime are qualified for native use, and that live calls are authorized. A repository checkout does not transfer the source host's qualification. |

Host requirements, per the runbook ([runtime.md](../../skills/antigravity-preflight/references/runtime.md), [argon-high.md](../../docs/argon-high.md)): Linux, Python 3.10+, `/usr/bin/bwrap`, `/usr/bin/xdg-dbus-proxy`, and an authenticated Secret Service session. Run in the owner's logged-in desktop session so the D-Bus session bus is available. If any is missing, stop and report; do not install anything.

## 3. Rules that override convenience

1. **Zero retries.** Never rerun a case or a trial. Never delete or recreate a workdir to "start clean". A recorded stop is a result. The driver also enforces this for recorded cases.
2. **Do not modify** `run_pilot.py`, `score.py`, `build_corpus.py`, `packets/`, `prompt.txt`, `manifest.json` or `oracle/`. If something looks wrong, stop and tell the owner.
3. **Do not read `oracle/` or score anything.** Scoring happens later, in a separate session, after all live runs are finished.
4. **Do not judge outputs.** Do not say whether a report "looks right", and do not edit, reformat or summarize a report's findings.
5. **No substitution.** Never use another model, CLI, API or cloud service. Never change accounts, update or install anything, or recapture capabilities in response to a failure.
6. **Live calls need a fresh go.** Run `--execute` only after the owner writes "go trial N" in this session, for that trial only. A previous go does not carry over to the next trial.
7. **Do not run two drivers at once**, and never share a workdir between trials.
8. **No secrets or scratch in your output.** Do not paste credentials, authentication scratch or raw provider streams. Report hashes and bounded receipt fields.
9. If any output differs from what this brief says to expect, **stop, paste the exact output, and wait**.
10. Do not push to the repository, open a pull request or commit results. Save evidence under the working root.

## 4. Stage A: verify the repository (no model)

```bash
git rev-parse HEAD
git status --short                      # must be empty
sha256sum benchmarks/counterfactual-pairs/manifest.json
python3 -B -I tools/check_release.py
python3 -B -I benchmarks/counterfactual-pairs/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/test_score.py
python3 -B -I benchmarks/counterfactual-pairs/test_run_pilot.py
```

Expected: a clean working tree, and `PASS` / `OK` from all four checks. `test_run_pilot.py` takes about 10 seconds. Record the commit hash and manifest hash; they identify the frozen corpus for this pilot.

## 5. Stage B: qualification envelope and capabilities

Use new, absent directories under the working root (`<root>`).

**B1. Offline qualification envelope** (no model, no agy):

```bash
python3 -B -I tools/qualify_offline.py <root>/qual            # flash-high
python3 -B -I tools/qualify_argon_offline.py <root>/qual      # argon-high
```

This writes `<root>/qual/DUAL-OFFLINE-QUALIFICATION.json`. It proves the supplied package bytes and offline controls, not host qualification or authorization.

**B2. Capabilities** (unsandboxed; inherits the real home and environment; model enumeration may contact the provider; it is not a review):

```bash
python3 -B -I runtime/flash-high/scripts/cli_capabilities.py /abs/path/to/agy <root>/caps
python3 -B -I runtime/argon-high/scripts/cli_capabilities.py /abs/path/to/agy <root>/caps argon-high
```

Run only the line for the chosen route, once. Require `"status": "PASS_METADATA_CAPABILITIES_ONLY"` in `<root>/caps/RESULT.json`. Record `<root>/caps/VERSION.stdout` and the frozen binary's SHA-256 from `RESULT.json`. If the status is anything else, stop. Do not retry, reinstall or update. See [cli-updates.md](../../skills/antigravity-preflight/references/cli-updates.md).

Show the owner both results.

## 6. Stage C: dry run (no model, no agy turn)

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot.py \
  --runtime-dir runtime/<flash-high|argon-high> [--runtime-profile argon-high] \
  --capabilities <root>/caps \
  --qualification <root>/qual/DUAL-OFFLINE-QUALIFICATION.json \
  --workdir <root>/dry
```

Expected: `"status": "DRY_RUN_PREPARED_ONLY"` and `"prepared": 24`. This runs the real `prepare` step 24 times and calls no model.

If it prints `DRY_RUN_STOPPED`, the `reason` and `case` fields name the failure. Report them verbatim and stop; do not edit the driver. The driver was tested against a stub and against the real packet functions, but never against a real `agy`, so this is the most likely place for a first-time mismatch.

Then show the owner:
- the full dry-run output
- one `<root>/dry/trial1/packets/<case>/prompt.txt`
- `ls -R` of one `<root>/dry/trial1/seeds/<case>`, confirming `CLI-GATE.json` is **absent**

**Stop here and wait for "go trial 1".** The dry-run workdir is not reused for live runs.

## 7. Stage D: live trial N (only after "go trial N")

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_pilot.py \
  --runtime-dir runtime/<flash-high|argon-high> [--runtime-profile argon-high] \
  --capabilities <root>/caps \
  --qualification <root>/qual/DUAL-OFFLINE-QUALIFICATION.json \
  --workdir <root>/liveN --trial N --execute
```

What it does for each of the 24 cases, in the frozen random order: write the packet, run `prepare`, copy the seed once and verify the copy byte for byte, then run `run --authorize-live` for exactly one native turn. It appends one line to `<root>/liveN/responses-trialN.jsonl` per case.

Run it in the background and poll the ledger line count. Expect roughly 20 seconds to a few minutes per case, so budget up to about an hour. Each case has a 600-second runtime limit and a 900-second wrapper timeout.

**First-case check.** When the first line appears, confirm only this: `<root>/liveN/trialN/attempts/<case>/GEMINI-REVIEW.md` ends with a `MACHINE SUMMARY` block (`COMPLETENESS:`, `ASSESSMENT:`, zero or more `FINDING:` lines). Report that, the case's `wallSeconds`, and whether the ledger line has a `technicalStop`. Do not judge the content. If the format is wrong, every case will be an `UNPARSEABLE_REPORT` stop, so ask the owner before letting the run continue.

**If the process or session dies:** do not start over. Tell the owner, then, with their approval, rerun the **identical** command. Recorded cases are skipped, and an attempt directory with no record is logged as `INTERRUPTED_UNKNOWN_STATE` and not re-run.

**If the driver prints `HALTED_CONSECUTIVE_STOPS`** (three stops in a row): do not rerun. Report the `technicalStop` values, and for each stopped case the `status`, `failure` and `closingFailures` in `attempts/<case>/CLI-RECEIPT.json`.

### Stop and error reference

| Output | Meaning | Action |
| --- | --- | --- |
| `PROFILE_MUST_MATCH_RUNTIME` | Argon without `--runtime-profile`, or Flash with one | Fix the arguments; no model was called |
| `WORKDIR_INSIDE_REPOSITORY` | `--workdir` is inside the checkout | Choose a path outside the repo |
| `RUNTIME_MISSING` | Wrong `--runtime-dir` | Fix the path |
| `CORPUS_PIN_MISMATCH:<file>` | A frozen file changed | Stop and report; do not regenerate mid-pilot |
| `PREPARE_FAILED` | The runtime's `prepare` refused the packet | Run that `prepare` command by hand once, without `--execute`, and report its error code |
| `SEED_COPY_MISMATCH` | Seed copy differs from seed | Stop and report |
| `WRAPPER_TIMEOUT` / `NO_RECEIPT` | The run hung or left no receipt | Recorded stop; report |
| `RUNTIME_STOP:{...}` | The runtime ended `STOPPED` | Recorded stop; report the receipt fields |
| `UNPARSEABLE_REPORT:<reason>` | Report lacks a valid machine summary | Recorded technical stop; keep the report; report |
| `INTERRUPTED_UNKNOWN_STATE` | Attempt directory existed without a record | Recorded stop; report |
| `HALTED_CONSECUTIVE_STOPS` | Three stops in a row | Do not rerun; report |

A technical stop is **not** a wrong judgment. It stays in the ledger, and nothing replaces it.

## 8. Further trials

The design uses two separately authorized observations per case. After trial 1 is finished and reported, wait for "go trial 2", then repeat Stage D with `--workdir <root>/live2 --trial 2`. Use the same route, capabilities and qualification envelope. Do not recapture capabilities between trials.

## 9. Hand back (no scoring)

Write the report below, then stop. Do not summarize model judgments and do not run `score.py`.

- **Identity:** commit hash, manifest SHA-256, route and profile, the exact `agy` path, its SHA-256 and version string from Stage B, host OS, and the date and time of each trial.
- **Per trial:** counts of recorded, executed and stopped cases, and each stop code with its case id.
- **Evidence locations** (left untouched under `<root>`): `liveN/responses-trialN.jsonl`; every `attempts/<case>/GEMINI-REVIEW.md`; every `attempts/<case>/CLI-RECEIPT.json`.
- **Receipt summary per trial**, from `CLI-RECEIPT.json`: `status`, `failure`, `closingFailures`, `elapsedSeconds`, `retries`, `promptDelivery.status`, `processes` (reaped), `privateHomeAbsent`, `socketDirectoryAbsent`. For Argon also `registeredSettlement`. Note that `servedAttestation` and `providerRequestCount` are `UNAVAILABLE`; that is expected and means the serving model and request count are unattested.
- **Anything surprising,** quoted verbatim.

Then tell the owner the evidence directory is ready to bring back to a session on this branch. There, `score.py` runs on the ledger, every mechanism and extra claim is adjudicated by hand, and results are reported with Wilson intervals.
