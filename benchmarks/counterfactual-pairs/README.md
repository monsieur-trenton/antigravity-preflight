# Blind counterfactual pairs: frozen pilot corpus

Prepared for benchmark B in the [benchmark plan](../../docs/benchmark-plan.md) and the design in [testing-next.md](../../docs/testing-next.md). **No model has been run on this corpus.** This directory holds the frozen inputs and the scorer, so the live pilot can be authorized and run without changing either afterwards.

## What is here

| Path | Reviewer may see it? | Purpose |
| --- | --- | --- |
| `packets/P-xxxxxx.txt` | Yes, one per submission | 24 plan snapshots with random identifiers and neutral content |
| `prompt.txt` | Yes | The single frozen review prompt |
| `oracle/oracle.json` | **Never** | Family, role, expected class and decisive line per case |
| `manifest.json` | Orchestrator only | SHA-256 pin of every file, plus a randomized submission order |
| `build_corpus.py` | n/a | Regenerates everything deterministically (seed in the file) |
| `score.py`, `test_score.py` | n/a | Scorer and its simulated-reviewer tests |

Six families, each a sound plan and a defective counterpart that differs in **one line**, in two equivalent wordings (A and B): output byte limits, required coverage, ownership and authorization, absent versus null, caller/callee compatibility, and runtime-budget evidence. Four cases per family, 24 in total.

The runtime-budget twin is deliberately not a defect. It lacks measured throughput, so the correct judgment is uncertainty (no VERIFIED blocker, and not a clean verdict). A reviewer that claims an inevitable timeout is scored `OVERCLAIMED`.

## Why the design resists gaming

- A reviewer that rejects everything flags all 12 sound plans and earns zero pair discrimination.
- A reviewer that approves everything misses every changed plan and also earns zero.
- Pair discrimination needs the sound plan *and* its changed twin judged correctly, in the same wording.
- Titles, family names and roles never appear in a packet; a test fails if they do.
- Credit for finding a defect requires a VERIFIED BLOCKER citing the decisive line with a quotation that actually appears on it.

## Running the pilot (requires owner authorization)

1. Confirm `python3 -B -I benchmarks/counterfactual-pairs/build_corpus.py --check` passes, and record `manifest.json`'s hash.
2. Send **only** `prompt.txt` and one `packets/*.txt` per submission, in `submissionOrder`. One turn each, no automatic retries or repairs. Use two separately authorized observations per case (`"trial": 1` and `2`). Pin and record model, effort and runtime; record unavailable attestation.
3. Save each returned report unmodified. Write the parsed observations to a responses file in the shape documented at the top of `score.py`. Preserve the original reports.
4. `python3 -B -I benchmarks/counterfactual-pairs/score.py responses.json results.json`
5. Adjudicate by hand every verdict, decisive quotation and mechanism, plus any extra claim the mechanical score cannot judge. Preserve all failures.

The scorer refuses to run if any frozen file has changed, and refuses unknown cases, duplicate observations and malformed fields.

## What the result will and will not show

Counts are reported with Wilson 95% intervals. Twelve pairs cannot support a general accuracy rate, and two trials of one case are not independent observations. The proposed pilot gate is zero unsupported VERIFIED findings, complete source and question coverage, and every mandatory oracle check satisfied before any readiness claim. Technical stops are counted apart from wrong semantic judgments.
