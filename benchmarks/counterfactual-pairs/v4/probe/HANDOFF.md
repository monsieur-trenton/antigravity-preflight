# Handoff: the authoring probe

**Goal:** one live call to the Gemini 3.8 Flash High native route, with an authoring prompt instead of a review prompt, to see whether the runtime can write a benchmark case. Everything is in the repository on branch `claude/modest-gates-8eyuke` (or `main` once merged); you only run `run.sh`, which checks, stops at the first failure and never retries. Nothing is scored.

## Where to find things

| Need | Look at |
| --- | --- |
| What is being tested and how it is read | [PROBE.md](PROBE.md) |
| The one prompt that will be sent | [author-prompt.txt](author-prompt.txt) |
| Every command below | [run.sh](run.sh) |
| The driver and the mechanical checks | [probe.py](probe.py), [check_probe_output.py](check_probe_output.py) |
| Why the probe exists | [../../../../docs/v4-plan.md](../../../../docs/v4-plan.md) |

Expected values (`run.sh checks` compares them for you): `agy` at `/home/john/.local/bin/agy` with SHA-256 `16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508` and version containing `1.4.1` (the binary of the v3 Gemini run); the v3 Gemini run manifest `d853fee334b39a42d8b1b20b87a9dc27d68f108a9a4b4afa8e28c48e901ff5d2`; the prompt `7c5875f6ea00dbf0641c0c64fa20510f1ba543793c4acf239de0c64324990529`.

## Rules

1. If anything fails or prints something unexpected, **stop and send the exact output**. Do not debug, edit, install, update, log in or retry.
2. Do not edit or commit anything in the repository, and do not change the prompt. Do not read the output for quality or fix it: the owner and the reviewer in the repo session read it.
3. **One live call in total.** Run `live --go` only after the owner's go. If it stops or the output is poor, that is the result: never run it twice, and never reuse a working directory.
4. The route needs the owner's logged-in desktop session (D-Bus and Secret Service), kept awake; the call itself takes a few minutes. The call spends the owner's account credits.
5. Do not use any other model or CLI as a substitute, and do not send anything from this machine except the final archive.

## Steps (from anywhere inside your clone)

```bash
git fetch origin && git checkout claude/modest-gates-8eyuke && git pull     # the branch the owner names
export ROOT=/tmp/v4probe                                                    # new, outside the repository
B=benchmarks/counterfactual-pairs/v4/probe/run.sh

$B checks     # no model call; ends CHECKS_PASSED
$B host       # offline qualification + capabilities probe, once; no review turn; ends HOST_OK
$B dry        # no model call; prepares the packet and shows the first lines of the prompt
```
Show the owner the `dry` output and wait for their go. Then, once:
```bash
$B live --go  # the one live call
$B bundle     # writes ~/v4-probe.tar.gz (a few KB)
```

`live` prints one JSON line: `status` (`COMPLETE` or `STOPPED`), `wallSeconds`, the receipt fields and the mechanical checks. Paste that line to the owner without comment. Upload `~/v4-probe.tar.gz` and stop: it holds `identity.txt`, `PROBE-SUMMARY.json`, `PROBE-OUTPUT.md` (if a report came back), the receipt, the init record, the capabilities result and the qualification result.

## Afterwards (not your job)

The output is read against the criteria in PROBE.md, the result is written into the v4 plan, and the decision on the authoring route is made.
