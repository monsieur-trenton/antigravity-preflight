# Handoff: the skill-go run (skill-style prompt plus one sentence, corpus v3, Claude CLI route)

For the owner or an orchestrating agent on the machine that ran the earlier arms. The [preregistration](PREREGISTRATION.md) is the authority; this is the copy-paste runbook. Live calls spend the owner's account or credits (about $2.4 and 17 to 22 minutes per run), so the owner decides whether each run happens.

## Rules that override convenience

1. **Never self-heal.** If a command fails or prints anything unexpected, do not debug, edit, change flags, install, log in or retry. Stop and send the exact output.
2. **Do not touch the repository.** Not a prompt, manifest, rubric, packet or script. Do not commit or push.
3. **Zero retries.** Never rerun a case or a run, delete or recreate a workdir, or rerun after a stop. A recorded stop is a result.
4. **Do not read `v3/oracle/`, `v3/families.json` or `v3/audit/`, score anything, or judge a report.**
5. **Do not authenticate.** No `claude login`, no API keys, no credential files.
6. **One model route only.** No other model or CLI as a substitute reviewer.
7. **The order is fixed and one driver runs at a time.** Evidence stays under the working root.

## The runs, in this order

| Run | Trial | Arm | Workdir | Required |
| --- | --- | --- | --- | --- |
| 1 | 1 | `skill-go` | `$ROOT/work-skill-go` | yes |
| 2 | 1 | `skill` (control) | `$ROOT/work-skill` | optional |
| 3 | 2 | `skill` (control) | `$ROOT/work-skill` | optional |
| 4 | 2 | `skill-go` | `$ROOT/work-skill-go` | yes |

The control is the unchanged skill-style arm run again, so that the comparison is concurrent rather than against the ledgers of 2026-10-23. Say before you start whether it runs (about $10 with it, $5 without).

## 0. Setup (once)

```bash
cd ~/Coding/antigravity-preflight            # your clone
git fetch origin claude/modest-gates-8eyuke && git checkout claude/modest-gates-8eyuke && git pull
git status --short                           # must print nothing
export ROOT=/tmp/v3sgrun                     # new, outside the repository
export CLAUDE=/home/john/.local/bin/claude
export C=benchmarks/counterfactual-pairs
mkdir -p $ROOT
```

## 1. Checks (no model call)

```bash
$CLAUDE --version                            # 2.1.306 (Claude Code)
sha256sum $CLAUDE                            # 520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe
git rev-parse HEAD
sha256sum $C/v3/manifest.json $C/v3-run-skill-go/manifest.json $C/ablation/skill-go/manifest.json
python3 -B -I tools/check_release.py
python3 -B -I $C/v3/build_corpus.py --check
python3 -B -I $C/ablation/skill-go/build_manifest.py --check
python3 -B -I $C/v3-run-skill-go/build_manifest.py --check
python3 -B -I $C/v3-run-skill-go/test_run.py
python3 -B -I $C/test_verify_run.py
python3 -B -I $C/test_run_pilot_claude.py
```

Expected hashes: v3 corpus `1ad685287cf4623dae5e8b3109554b2f0859152a28875e8ddfc4d4c5e7554202`; run manifest `585b20e17961f7924088aa0190b988c89c6062c29c30a143e6b2b8268d132376` (stamped on every ledger row); arm manifest `c464860942d815dffebba2b454e0816b7a7755ca7c7f10ca924ac14a9b8ebacc`. Every check prints `PASS` or `OK`. Record the commit and the hashes.

## 2. Define the commands, then dry-run both arms (no model call)

```bash
run() {  # usage: run ARM TRIAL [--execute]
  python3 -B -I $C/run_pilot_claude.py --arm "$1" \
    --corpus $C/v3 --run-manifest $C/v3-run-skill-go/manifest.json \
    --claude-bin $CLAUDE --model claude-opus-5-5 --effort high \
    --max-budget-usd 5.0 --workdir $ROOT/work-"$1" --trial "$2" $3
}
check() {  # usage: check ARM TRIALS   (e.g. check skill-go 1  or  check skill-go 1,2)
  python3 -B -I $C/verify_run.py --arm "$1" \
    --corpus $C/v3 --run-manifest $C/v3-run-skill-go/manifest.json \
    --workdir $ROOT/work-"$1" --model claude-opus-5-5 --effort high --trials "$2"
}
run skill-go 1; run skill 1                  # each ends "DRY_RUN_PREPARED_ONLY", "prepared": 64
diff $ROOT/work-skill-go/trial1/dry-requests/Q-015661/request.txt $ROOT/work-skill/trial1/dry-requests/Q-015661/request.txt
```

The `diff` must show exactly one line, the sentence beginning `Optional suggestions`, present only in the `skill-go` request (line 7). Show the owner the output and **wait for "go run 1"**.

## 3. The live runs (only after the owner's go for each run)

```bash
run skill-go 1 --execute && check skill-go 1          # run 1
run skill 1 --execute && check skill 1                # run 2 (optional control)
run skill 2 --execute && check skill 1,2              # run 3 (optional control)
run skill-go 2 --execute && check skill-go 1,2        # run 4
```

After each: `check` must show `"failures": []` (stops are listed, not failures). Note start and end times. After run 1 report only `servedModels`, `costUsd`, `wallSeconds`, `safetyStops` and whether any row has a `technicalStop`.

- **Process dies:** do not start over; with the owner's approval rerun the identical command (recorded cases are skipped).
- **`HALTED_CONSECUTIVE_STOPS`:** do not rerun; send each stop code and the stopped cases' `claude-output.json`; the owner may authorize the identical command with `--max-consecutive-stops 99`, nothing else.
- **`RUN_MANIFEST_REQUIRED`, `RUN_ARM_NOT_BOUND`, `RUN_PIN_MISMATCH`, `ABLATION_PIN_MISMATCH`, `ABLATION_SYSTEM_PROMPT_MISMATCH`:** a frozen file or argument is wrong; stop and report, do not regenerate.

## 4. Hand back (no scoring)

Write `$ROOT/identity.txt` with: the commit; the three hashes above; the `claude` version and hash; `uname -a`; the spend cap `5.0`; whether the control ran; per run, the start and end times, the recorded, executed and stopped counts, every stop code with its case id, the total `costUsd` and the full `check` output.

```bash
tar czf ~/v3-skill-go.tar.gz -C $ROOT .
ls -lh ~/v3-skill-go.tar.gz                  # a few MB expected
```

Upload it and stop. Do not score or read the oracle.

## 5. What happens afterwards

In a session on this branch: `verify_run.py` is rerun; an adjudication naming any stops is written **before any metric**; each skill-style ledger is scored with `score.py --corpus ...v3`; [analyze.py](analyze.py) runs against the control (or the earlier `skill` ledgers) and `defined-go`; the preregistered reading is done; the labels are applied; results are committed with the unmodified reports.
