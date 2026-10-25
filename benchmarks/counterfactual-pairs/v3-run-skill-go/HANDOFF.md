# Handoff: the skill-go run

**Goal:** run one preregistered arm (the skill-style prompt plus one sentence) on the held-out corpus, two trials, and hand the evidence back. Everything is in the repository on branch `claude/modest-gates-8eyuke`; you only run `run.sh`, which does the checks, stops on the first failure and never retries.

## Where to find things

| Need | Look at |
| --- | --- |
| Why, what is predicted, how it will be read | [PREREGISTRATION.md](PREREGISTRATION.md) |
| The one sentence being tested | [../ablation/skill-go/skill-go-sentence.txt](../ablation/skill-go/skill-go-sentence.txt) |
| The runner (every command below) | [run.sh](run.sh) |
| The corpus, runs and results so far | [../v3/README.md](../v3/README.md), [../results/v3-claude-opus-5-5-high/README.md](../results/v3-claude-opus-5-5-high/README.md) |
| What is frozen and pinned | [manifest.json](manifest.json), [../ablation/skill-go/manifest.json](../ablation/skill-go/manifest.json) |

Expected hashes (`run.sh checks` compares them for you): corpus v3 `1ad685287cf4623dae5e8b3109554b2f0859152a28875e8ddfc4d4c5e7554202`; run manifest `585b20e17961f7924088aa0190b988c89c6062c29c30a143e6b2b8268d132376`; arm manifest `c464860942d815dffebba2b454e0816b7a7755ca7c7f10ca924ac14a9b8ebacc`; `claude` 2.1.306 with SHA-256 `520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe`.

## Rules

1. If anything fails or prints something unexpected: **stop and send the exact output**. Do not debug, edit, install, log in or retry.
2. Do not edit or commit anything in the repository. Do not read `v3/oracle/`, score anything or judge a report.
3. A live run costs money (about $2.4 and 20 minutes each). **Run `live N --go` only after the owner's go for that run.** Never rerun a run; if the process dies, ask first.
4. Order is fixed and one run at a time. The owner says before starting whether the optional control (runs 2 and 3) is included: about $5 without it, $10 with it.

## Steps (from anywhere inside your clone)

```bash
git checkout claude/modest-gates-8eyuke && git pull
export ROOT=/tmp/v3sgrun                     # new, outside the repository
export CLAUDE=/home/john/.local/bin/claude   # skip if that is already where it is
B=benchmarks/counterfactual-pairs/v3-run-skill-go/run.sh

$B checks          # no model call; ends CHECKS_PASSED
$B dry             # no model call; ends with a diff of exactly one line, the sentence "Optional suggestions ..."
```
Show the owner the `dry` output and wait for their go. Then, one at a time, each only on the owner's go:
```bash
$B live 1 --go     # skill-go, trial 1
$B live 2 --go     # skill, trial 1  (optional control)
$B live 3 --go     # skill, trial 2  (optional control)
$B live 4 --go     # skill-go, trial 2
```
Each prints the driver's summary and then the verifier's, and appends both to `$ROOT/identity.txt`. The verifier must show `"failures": []` (stops are listed, not failures). If it does not, stop and send the output.

## Hand back

```bash
$B bundle          # writes ~/v3-skill-go.tar.gz (a few MB)
```
Upload that file and stop. It contains the ledgers, the unmodified reports, the CLI outputs and `identity.txt` (commit, hashes, versions, host, start and end times, counts, costs, verifier output). Say whether the control ran.

## Afterwards (not your job)

The results are verified, an adjudication is written before any metric, the ledgers are scored and analysed with [analyze.py](analyze.py), and the labels in the preregistration are applied.
