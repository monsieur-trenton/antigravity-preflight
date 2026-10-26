# Handoff: the blind audit of a v4 split

**Goal:** run the blind audit of one built v4 corpus (dev or test) through the Claude CLI, one tool-free turn per call, and hand the answers back. Everything is in the repository on branch `claude/modest-gates-8eyuke` (or `main` once merged); you only run `run.sh`, which checks, stops at the first failure and never retries. Nothing is scored here and you never see which member of a pair is which.

The owner gives you two things with the go: the corpus directory (the repository's `benchmarks/counterfactual-pairs/v4/dev`, or an unpacked private archive for the test split) as `CORPUS`, and the SHA-256 of its `manifest.json` as `CORPUS_SHA`.

## Where to find things

| Need | Look at |
| --- | --- |
| What is asked and why | [../SPEC.md](../SPEC.md) (the audit questions), [audit.py](audit.py) |
| The system prompt and the three request templates | [system-prompt.txt](system-prompt.txt), [member-request.txt](member-request.txt), [pair-request.txt](pair-request.txt), [claim-request.txt](claim-request.txt) |
| Every command below | [run.sh](run.sh) |
| How the answers are read (not your job) | [audit_report.py](audit_report.py) |

Expected values (`run.sh checks` compares them for you): `claude` 2.1.306 with SHA-256 `520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe` (the binary of the v3 Claude runs), the four template files by hash (in `run.sh`), and the corpus manifest hash the owner names. If the `claude` binary has changed, stop and say so: the owner decides.

## Rules

1. If anything fails or prints something unexpected: **stop and send the exact output**. Do not debug, edit, install, log in or retry.
2. Do not edit or commit anything in the repository. **Do not open `oracle/` in the corpus directory, any `packets/` file or any `attempts/*/request.txt`, and do not read or judge an answer.** The audit is blind: it only works if nobody who sees its results is also looking at the answer key as it runs.
3. A live call costs money (about 90 calls and a few dollars for the dev split; about 300 for the test split). **Run `live N --go` only after the owner's go, and only as many calls as the owner names.** Never rerun a call; the driver records every call, stops included, and skips it next time. If the process dies, say so and ask first.
4. The calls are independent and the order is fixed by a seed. Run `live N --go` repeatedly until the summary shows `executed` equal to 0 and `alreadyRecorded` equal to `callsScheduled`.

## Steps (from anywhere inside your clone)

```bash
git fetch origin && git checkout claude/modest-gates-8eyuke && git pull     # the branch the owner names
export ROOT=/tmp/v4audit                                                    # new, outside the repository
export CORPUS=...  CORPUS_SHA=...                                            # as the owner gave them
export CLAUDE=/home/john/.local/bin/claude                                   # skip if that is already where it is
B=benchmarks/counterfactual-pairs/v4/audit/run.sh

$B checks     # no model call; ends CHECKS_PASSED
$B dry        # no model call; writes the requests, prints the number of calls scheduled
```
Show the owner the `dry` output and wait for their go. Then, in batches the owner names:
```bash
$B live 20 --go     # at most 20 calls; prints the driver's summary and appends it to $ROOT/identity.txt
```
The summary has `stopped` (calls whose answer could not be parsed, or that hit a platform stop or a model mismatch) and, after three in a row, `halted`. Paste each summary to the owner without comment.

## Hand back

```bash
$B bundle     # writes ~/v4-audit.tar.gz
```
Upload that file and stop. It holds `identity.txt`, `audit-answers.jsonl` (one row per call, with the parsed answer or the stop) and, per call, the request, the answer and the CLI output.

## Afterwards (not your job)

`audit_report.py report` reads the answers against the oracle: a pair is passed, passed with something for a person to read, sent to review (rewrite or drop) or incomplete. `audit_report.py spot` writes the unlabelled sample for the owner's own check of at least a fifth of the pairs. Drops are recorded with their reasons before the split is frozen.
