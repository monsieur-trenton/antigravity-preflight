# Handoff: authoring corpus v4

**Goal:** have the Gemini 3.8 Flash High native route write the pairs of one split of corpus v4, one live call per pair, and hand the unmodified reports back. Everything is in the repository on branch `claude/modest-gates-8eyuke` (or `main` once merged); you only run `run.sh`, which checks, stops at the first failure and never retries a call on its own. Nothing is scored here.

Run the **dev** split first (24 pairs, open, `SPLIT=dev`). Run the **test** split (80 pairs and 12 rewordings, `SPLIT=test`) only after the owner says the dev pairs have been read and the checks and prompts are settled.

## Where to find things

| Need | Look at |
| --- | --- |
| What a case is and the rules every family follows | [../SPEC.md](../SPEC.md) |
| The families and domains | [../families.json](../families.json), [../domains.json](../domains.json) |
| Which pair gets which domain, length and positions (from a committed seed) | [assignments-dev.json](assignments-dev.json), [assignments-test.json](assignments-test.json), [seeds.json](seeds.json), [assign.py](assign.py) |
| The prompts that will be sent | [author-template.txt](author-template.txt), [reword-template.txt](reword-template.txt), built per pair by [prompts.py](prompts.py) |
| The mechanical checks each report must pass | [check_author.py](check_author.py) |
| Every command below | [run.sh](run.sh) |
| The driver, and how the route was shown to work as a generator | [author.py](author.py), [../probe/results/RESULT.md](../probe/results/RESULT.md) |

Expected values (`run.sh checks` compares them for you): `agy` at `/home/john/.local/bin/agy` with SHA-256 `16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508` (version containing `1.4.1`); the v3 Gemini run manifest `d853fee334b39a42d8b1b20b87a9dc27d68f108a9a4b4afa8e28c48e901ff5d2`; the two templates and the two assignment files by hash, which are in `run.sh`.

## Rules

1. If anything fails or prints something unexpected, **stop and send the exact output**. Do not debug, edit, install, update, log in or retry on your own.
2. Do not edit or commit anything in the repository, and do not change a prompt or an assignment. Do not fix, trim or "improve" an authored report: a report is either accepted unmodified by the checks or it is kept as a failed attempt.
3. **Live calls only on the owner's go, and only as many as the owner names** (`live N --go`). Each call takes about 2 to 3 minutes and spends the owner's account credits. A pair is tried at most twice in total (the driver counts earlier attempts); a pair that has used both attempts is the owner's decision, not yours.
4. **Test split: do not open, read, summarize or paste any authored file** (`accepted/`, `calls/*/REPORT.md`, `prompts/`). Upload the archive and stop. Dev split: you may look, but you are not asked to judge.
5. The route needs the owner's logged-in desktop session (D-Bus and Secret Service), kept awake. Do not use any other model or CLI as a substitute, and send nothing from this machine except the final archive.

## Known flake: the offline qualification (`host`)

`host` runs the repository's 664-case offline qualification of the runtime, twice. One timing control, `prompt_no_read`, gives the host 0.5 seconds; on a slow or busy machine it can elapse and the run stops with `OFFLINE_RUN_2_STOPPED` (seen once, during the authoring probe, and gone on a rerun in a fresh root; no model was called). It has now happened twice, both times soon after `checks` (which runs the test suites): the second time `OFFLINE_RUN_1_STOPPED` with a load average of 9 on 4 cpus. **Wait a few minutes after `checks`, run `$B diag`, and start `host` only when the one-minute load average is below about 1.5 and nothing else is running.** Do not retry on your own: send the output. The owner may authorize one rerun in a **new** `ROOT`; `$B diag` (no model call) shows how slow the machine is at that moment.

## Steps (from anywhere inside your clone)

```bash
git fetch origin && git checkout claude/modest-gates-8eyuke && git pull     # the branch the owner names
export SPLIT=dev                              # or test, when the owner says so
export ROOT=/tmp/v4author-$SPLIT              # new, outside the repository
B=benchmarks/counterfactual-pairs/v4/author/run.sh

$B checks     # no model call; ends CHECKS_PASSED
$B host       # offline qualification + capabilities probe, once per ROOT; no model call; ends HOST_OK
$B dry        # no model call; builds every prompt and shows the start of one
```
Show the owner the `dry` output and wait for their go. Then, in batches the owner names:
```bash
$B live 3 --go          # at most 3 authoring calls, one per pair that is not yet accepted, in assignment order
$B status               # no model call: calls, stops, failed checks, accepted, not accepted, attempts used up
```
Repeat `live N --go` while the owner says so. A pair whose report fails a check is tried again by the next `live`, until it has used two attempts. Prints one JSON line per invocation: paste it to the owner without comment.

Test split only, after all 80 pairs are accepted (or the owner says to go on without the ones that are not):
```bash
$B reword 4 --go        # at most 4 wording-B rewordings of accepted pairs (12 in all)
```

## Re-authoring named pairs (dev only, when the owner says)

After the dev audit, four pairs are rewritten with the revised family hazards: `N-102a76,N-4aedf1,N-93366f,N-9cc72c`. Use a **new** `ROOT` so that the earlier accepted reports are not touched and the attempt counts start again (two attempts per pair, as before):
```bash
export SPLIT=dev ROOT=/tmp/v4author-dev2
$B checks && $B host && $B dry        # the same three stages; dry builds only the prompts
$B live 4 --go N-102a76,N-4aedf1,N-93366f,N-9cc72c
$B status                             # all four accepted? repeat live for any that failed a check
$B bundle                             # ~/v4-author-dev-v4author-dev2.tar.gz
```

## Hand back

```bash
$B bundle     # writes ~/v4-author-$SPLIT-<basename of ROOT>.tar.gz
```
Upload that file and stop. It holds `identity.txt` (commit, hashes, versions, host, the start and end of each batch and every driver summary), `calls.jsonl` (one row per call with the mechanical results), `accepted/`, `prompts/`, every call's report and CLI receipt, the capabilities result and the qualification result. For `SPLIT=test` it is private to the owner and the repository session: it is never committed.

## Afterwards (not your job)

The accepted reports are built into a corpus directory, the blind audit runs on it ([../audit/HANDOFF.md](../audit/HANDOFF.md)), the owner spot-checks at least a fifth of the pairs, and pairs that fail are rewritten or dropped with the reason recorded before the split is frozen.
