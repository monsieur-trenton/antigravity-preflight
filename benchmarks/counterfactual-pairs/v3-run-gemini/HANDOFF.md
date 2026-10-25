# Handoff brief: the preregistered v3 run on the Gemini 3.8 Flash High native route

For an orchestrating agent (Claude Code, an Antigravity agent, or a person) on the host that owns the authenticated `agy` binary and ran the Gemini pilot. Read all of this first. The owner, not you, decides whether live model calls happen.

This runs **one arm, two trials** of the [preregistration](PREREGISTRATION.md): the skill-style prompt, as the [Gemini pilot](../results/pilot-flash-high/README.md) ran it, on the held-out [corpus v3](../v3/README.md) (64 cases). It reuses the structure of the [pilot brief](../HANDOFF.md); the differences are below, and where they conflict, this file wins. The Claude-route run is a separate brief and is not part of this one.

## 0. Decisions and inputs the owner must give you

Do not guess, search the machine, or pick values yourself. Ask for any that are missing.

| Input | Required value | Why |
| --- | --- | --- |
| Route | `flash-high`, `--runtime-dir runtime/flash-high`, no runtime profile | The driver refuses anything else; never switch to Argon |
| Absolute path to `agy` | `/home/john/.local/bin/agy` | The binary the pilot used |
| `agy` SHA-256 and version | `16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508`, version containing `1.4.1` | The driver compares the capabilities probe's frozen-binary hash and version with the frozen run manifest. If either differs, **stop and tell the owner before any model turn**; never install, update or downgrade |
| Working root | a new directory **outside** the repository, e.g. `/tmp/v3gemini` | Never reuse the pilot's `/tmp/pilot` or any earlier workdir |
| Authorization | "go trial N" for each trial, in this session | Live calls are authorized by the owner, on the owner's account and credits |
| Session | the owner's logged-in desktop session, kept awake | The route needs the D-Bus session bus and the Secret Service; a trial takes about 3 hours |

**Expected time.** The pilot took about 4,000 s per trial for 24 cases (22 to 464 s per case). For 64 cases expect about **3 hours per trial** and 6 to 7 hours for both. An estimate, not a bound. Costs are the owner's; this repository does not record them.

Host requirements, as in the pilot brief: Linux, Python 3.10+, `/usr/bin/bwrap`, `/usr/bin/xdg-dbus-proxy`, an authenticated Secret Service session. If any is missing, stop and report; do not install anything.

## 1. What this is, and what its results can claim

Read the [preregistration](PREREGISTRATION.md) first; it is pinned by [manifest.json](manifest.json). In short: corpus v3 has 64 cases, eight of whose twins leave one decisive fact unestablished with nothing in the plan absorbing the miss. The run asks whether the Gemini reviewer keeps sound plans clean, blocks defect twins (including those that need inference) and flags evidence-gap twins as `GO_WITH_CHANGES`.

- Route `flash-high` on `agy`, a Gemini model **as requested and configured; the route cannot attest the served model** (the receipts say `servedAttestation: UNAVAILABLE`, and that is expected).
- The driver is [run_gemini_v3.py](../run_gemini_v3.py), a wrapper that leaves `run_pilot.py` unchanged. It binds the run to the frozen manifest and reads one thing differently from the pilot: a snapshot label `S01:<n>` in a FINDING's line field is read as line n. Nothing else about the prompt, the packets or the route changes.
- You are the **orchestrator**: prepare, launch, verify and report. You never judge a case, never score, and never improve anything.

## 2. Rules that override convenience

1. **Never self-heal.** If a command fails or prints anything unexpected, do not debug, edit, change flags, install, log in, recapture capabilities or retry. Stop, paste the exact output, and wait.
2. **Do not touch anything in the repository.** Not the driver, the verifier, a manifest, a preregistration, `rubric.json`, a packet or any script. If the reviewer behaves badly, that is a result.
3. **Zero retries.** Never rerun a case or a trial, delete or recreate a workdir, or rerun after a stop. A recorded stop is a result. The driver enforces this for recorded cases.
4. **Do not read `v3/oracle/`, `v3/families.json` or `v3/audit/`, score anything, or judge reports.** Do not say whether a report looks right, and do not edit, reformat or summarize one.
5. **No substitution.** Never use another model, CLI, API or service, including yourself, as a reviewer. Never change accounts.
6. **Live calls need a fresh go.** Run `--execute` only after the owner writes "go trial N" in this session, for that trial only. A previous go does not carry over.
7. **Never run two drivers at once**, and never share a workdir between trials: `live1` for trial 1, `live2` for trial 2.
8. **Do not commit, push or open a pull request.** (The pilot's orchestrator pushed its evidence despite the same rule; do not.) Keep all evidence under the working root and bundle it for the owner.
9. **No secrets or scratch in your output.** Do not paste credentials, authentication scratch or raw provider streams. Report hashes and bounded receipt fields.
10. If any output differs from what this brief says to expect, **stop, paste the exact output, and wait**.

## 3. Stage A: verify the repository (no model call)

```bash
git rev-parse HEAD
git status --short                                   # must be empty
sha256sum benchmarks/counterfactual-pairs/v3/manifest.json benchmarks/counterfactual-pairs/v3-run-gemini/manifest.json
python3 -B -I tools/check_release.py
python3 -B -I benchmarks/counterfactual-pairs/v3/build_corpus.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3-run-gemini/build_manifest.py --check
python3 -B -I benchmarks/counterfactual-pairs/v3/test_corpus.py
python3 -B -I benchmarks/counterfactual-pairs/v3-run-gemini/test_run.py        # about 2 minutes
python3 -B -I benchmarks/counterfactual-pairs/test_run_pilot.py
python3 -B -I benchmarks/counterfactual-pairs/test_score.py
```

Expected: a clean tree, `PASS` or `OK` everywhere, the v3 corpus manifest `1ad685287cf4623dae5e8b3109554b2f0859152a28875e8ddfc4d4c5e7554202` and the run manifest `d853fee334b39a42d8b1b20b87a9dc27d68f108a9a4b4afa8e28c48e901ff5d2`. Record both and the commit.

## 4. Stage B: qualification envelope and capabilities (no review turn)

Use new, absent directories under `<root>`.

```bash
python3 -B -I tools/qualify_offline.py <root>/qual
python3 -B -I runtime/flash-high/scripts/cli_capabilities.py /home/john/.local/bin/agy <root>/caps
```

The first writes `<root>/qual/DUAL-OFFLINE-QUALIFICATION.json`; require its status `PASS`. The second runs unsandboxed, may contact the provider to enumerate models, and is not a review; require `"status": "PASS_METADATA_CAPABILITIES_ONLY"` and `"binaryStable": true` in `<root>/caps/RESULT.json`, and record `VERSION.stdout`. Run each **once**, for both trials. If either is anything else, stop; do not retry, reinstall or update. Show the owner both results. (The driver compares `RESULT.json` with the frozen manifest before every run and refuses on a mismatch.)

## 5. Stage C: dry run (no model, no agy turn)

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_gemini_v3.py \
  --runtime-dir runtime/flash-high --capabilities <root>/caps \
  --qualification <root>/qual/DUAL-OFFLINE-QUALIFICATION.json \
  --corpus benchmarks/counterfactual-pairs/v3 \
  --run-manifest benchmarks/counterfactual-pairs/v3-run-gemini/manifest.json \
  --workdir <root>/dry
```

Expected: `"status": "DRY_RUN_PREPARED_ONLY"`, `"prepared": 64`, `"route": "native-flash-high"`, `"parser": "snapshot-label-tolerant"` and a `runManifestSha256` equal to the hash you recorded. Show the owner the full output, one `<root>/dry/trial1/packets/<case>/prompt.txt` (confirm, without judging, that it begins `You are reviewing one plan snapshot.`, shows the numbered `[S01:n]` lines and ends with the machine-summary block), and `ls -R` of one `<root>/dry/trial1/seeds/<case>` confirming `CLI-GATE.json` is **absent**. The dry-run workdir is never reused for live runs. **Stop and wait for "go trial 1".**

## 6. Stage D: live trial N (only after "go trial N")

```bash
python3 -B -I benchmarks/counterfactual-pairs/run_gemini_v3.py \
  --runtime-dir runtime/flash-high --capabilities <root>/caps \
  --qualification <root>/qual/DUAL-OFFLINE-QUALIFICATION.json \
  --corpus benchmarks/counterfactual-pairs/v3 \
  --run-manifest benchmarks/counterfactual-pairs/v3-run-gemini/manifest.json \
  --workdir <root>/liveN --trial N --execute
```

For each of the 64 cases in the frozen random order: write the packet, run `prepare`, copy the seed once and verify the copy byte for byte, then run one native turn. One line per case is appended to `<root>/liveN/responses-trialN.jsonl`. Run it in the background and poll the line count.

**First-case check.** When the first line appears, report only: its `wallSeconds`, whether it has a `technicalStop`, and whether `<root>/liveN/trialN/attempts/<case>/GEMINI-REVIEW.md` ends with a `MACHINE SUMMARY` block. Do not judge the content. If the format is wrong, every case will be a stop; ask the owner before letting it continue.

**If the process or session dies:** do not start over. Tell the owner, then, with their approval, rerun the **identical** command. Recorded cases are skipped, and an attempt directory with no record is logged `INTERRUPTED_UNKNOWN_STATE` and not rerun.

**If the driver prints `HALTED_CONSECUTIVE_STOPS`** (three in a row): do not rerun. Report each stop code, and for each stopped case the `status`, `failure` and `closingFailures` in `attempts/<case>/CLI-RECEIPT.json`. The owner may authorize continuing the identical command with `--max-consecutive-stops 99`; they may not authorize changing anything else.

| Output | Meaning | Action |
| --- | --- | --- |
| `RUN_CORPUS_MISMATCH`, `RUN_PIN_MISMATCH:<file>`, `RUN_RUNTIME_TREE_MISMATCH`, `CORPUS_PIN_MISMATCH:<file>` | A frozen file changed | Stop and report; do not regenerate |
| `RUN_BINARY_MISMATCH`, `RUN_BINARY_VERSION_MISMATCH`, `CAPABILITIES_NOT_PASS`, `CAPABILITIES_UNREADABLE`, `RUN_MODEL_MISMATCH` | The capabilities probe does not match the frozen run | Stop and report; no model was called |
| `RUN_RUNTIME_NOT_FLASH_HIGH`, `WORKDIR_INSIDE_REPOSITORY`, `RUNTIME_MISSING` | Wrong argument | Fix the argument; no model was called |
| `PREPARE_FAILED`, `SEED_COPY_MISMATCH` | The runtime refused the packet, or the seed copy differs | Stop and report |
| `WRAPPER_TIMEOUT`, `NO_RECEIPT`, `RUNTIME_STOP:{...}`, `INTERRUPTED_UNKNOWN_STATE` | Recorded stops | Report; do not rerun |
| `UNPARSEABLE_REPORT:<reason>` | The report is not in the required form, even with the one relaxation | Recorded technical stop; keep the report |
| `HALTED_CONSECUTIVE_STOPS` | Three stops in a row | Do not rerun; report |

A technical stop is **not** a wrong judgment. It stays in the ledger, and nothing replaces it.

## 7. Stage E: verify the trial (no model call, after every trial)

```bash
python3 -B -I benchmarks/counterfactual-pairs/verify_gemini_run.py \
  --corpus benchmarks/counterfactual-pairs/v3 \
  --run-manifest benchmarks/counterfactual-pairs/v3-run-gemini/manifest.json \
  --workdir <root>/liveN --trial N
```

It checks the corpus and run-manifest pins; one ledger row per case in the frozen order; the stamp; for every case that reached a report, that the prompt sent is byte-identical to what the frozen prompt and corpus produce, that the saved report matches the ledger and the receipt, that re-parsing it reproduces the ledger row, and that the receipt is clean (no failure, zero retries, one proxy and one native invocation, every process reaped, private home and socket directory gone, the prompt delivered in full, the native binary's SHA-256 the frozen one). Expected: `"failures": []` and exit status 0; stops and the count of snapshot labels read are listed, not failures. Paste its full output. If `failures` is not empty, stop and report; do not repair evidence. Then report, for that trial: recorded, executed and stopped counts, each stop code with its case id, start and end times.

**Then pack the evidence** (no model call; the working directory is read, never modified):

```bash
python3 -B -I benchmarks/counterfactual-pairs/bundle_gemini_evidence.py --workdir <root>/liveN --trial N --out <root>/evidence-trialN.tar.gz
mkdir <root>/check-trialN && tar -xzf <root>/evidence-trialN.tar.gz -C <root>/check-trialN
python3 -B -I benchmarks/counterfactual-pairs/verify_gemini_run.py --corpus benchmarks/counterfactual-pairs/v3 \
  --run-manifest benchmarks/counterfactual-pairs/v3-run-gemini/manifest.json --workdir <root>/check-trialN/liveN --trial N
```

A trial's working directory is tens of gigabytes (every seed and attempt carries a copy of the runtime and the binary), so **do not archive or upload it**. The bundle holds only what the verifier and the scorer read (the ledger, each case's report and receipt, the prompt sent and its snapshot), a few megabytes, with a `BUNDLE-MANIFEST.json` of hashes and of what was left out. Paste the bundler's one-line output and the second verifier's output; its `failures` must be `[]` and its counts must equal the first run's. Keep the full working directory untouched on the host. Then wait for the next go.

## 8. Hand back (no scoring)

Write `<root>/identity.txt`; the files to hand back are `identity.txt` and the two `evidence-trialN.tar.gz` bundles (**not** the whole working root). **Required** (an earlier archive omitted it):
- the commit; the SHA-256 of the v3 and run manifests; the route; the exact `agy` path, SHA-256 and `VERSION.stdout`; the capabilities `RESULT.json`; the qualification file's status and case counts; host OS and kernel; the start and end time of each trial;
- per trial: recorded, executed and stopped counts, each stop code with its case id, the number of snapshot labels read, and the full `verify_gemini_run.py` output;
- a receipt summary per trial from the `CLI-RECEIPT.json` files: counts by `status`, any `failure` or `closingFailures`, `elapsedSeconds` minimum, median and maximum, and whether every process was reaped and every private home and socket directory removed. `servedAttestation` and `providerRequestCount` are `UNAVAILABLE`; that is expected.

The full evidence stays untouched under `<root>` (`liveN/responses-trialN.jsonl`, and per case `trialN/packets/<case>/`, `trialN/attempts/<case>/`); the bundles are copies of the allowlisted files. Report anything surprising verbatim, then tell the owner the evidence is ready, and stop.

## 9. What happens afterwards

In a session on this branch, with the oracle available: `verify_gemini_run.py` is rerun for both trials; an adjudication file naming any stops is written **before any metric is computed**; the ledgers are scored with `score.py --corpus ...v3` (finding-level, with the unsupported-VERIFIED gate) and analysed with [analyze.py](../v3-run/analyze.py) (the three primary rates, strict and ordered pairs, gap named but dismissed, per family); the reading in the preregistration is done; the cross-route comparison with the Claude v3 run is made if that run exists; and results are committed with the unmodified reports.
