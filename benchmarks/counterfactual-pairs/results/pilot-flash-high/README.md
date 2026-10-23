# Pilot: Counterfactual Pairs — Gemini 3.8 Flash High Native CLI Pilot

Two trials of the frozen 24-case counterfactual pairs corpus ([../../README.md](../../README.md)), run through [`run_pilot.py`](../../run_pilot.py) with the qualified native CLI route `flash-high`.

This run provides the Gemini 3.8 Flash / High like-for-like comparison against the Claude CLI pilot ([../pilot1-claude-opus-5-5-high/](../pilot1-claude-opus-5-5-high/)), executed inside bubblewrap sandboxes with isolated private homes and filtered Secret Service token proxying.

## Run Identity

| Field | Value |
| :--- | :--- |
| **Route / Model / Effort** | `flash-high` / `gemini-3.8-flash-high` / `high` |
| **CLI Binary Path** | `/home/john/.local/bin/agy` |
| **Binary Version** | `1.4.1` |
| **Binary SHA-256** | `16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508` |
| **Corpus** | `benchmarks/counterfactual-pairs` (corpus v1, 24 cases) |
| **Manifest SHA-256** | `9885c1cf66d546882b49db70e5b360f5c49f7dbd6464a1856c223aca7ac32e46` |
| **Host OS** | Linux Mint 22.3 (Ubuntu 24.04 noble base) |
| **Host Kernel** | `Linux john-laptop 7.0.0-38-generic #38~24.04.4-Ubuntu SMP PREEMPT_DYNAMIC Mon Sep 14 16:37:11 UTC 2 x86_64 x86_64 x86_64 GNU/Linux` |
| **Trials** | 2 independent trials of 24 cases each, 1 native tool-free turn per case, zero retries |
| **Timestamps** | Trial 1: 2026-10-22 15:56 to 17:02 PDT; Trial 2: 2026-10-22 17:16 to 18:23 PDT |
| **Process Reaping** | 100% confirmed across all 48 attempts (`privateHomeAbsent: true`, `socketDirectoryAbsent: true`) |
| **Evidence in Repo** | [trial1/](trial1/) (ledger, reports, receipts), [trial2/](trial2/) (ledger, reports, receipts), [orchestrator-reported-identity.json](orchestrator-reported-identity.json), [HANDOFF-REPORT.md](HANDOFF-REPORT.md) |
| **Complete Raw Archive** | Staged at `/tmp/counterfactual-pairs-pilot-flash-high.tar.gz` (SHA-256: `b8e22782c2db840318dbbf26b8342f6a6b4b01a8d883f25124484b60b44cc203`) |

## Trial Breakdown

| Assessment / Outcome | Trial 1 (Count / 24) | Trial 2 (Count / 24) | Notes |
| :--- | :--- | :--- | :--- |
| `NO_BLOCKERS_FOUND` | 12 | 13 | 12 cases matched across trials |
| `CHANGES_RECOMMENDED` | 6 | 5 | 5 cases matched across trials |
| `BLOCKERS_FOUND` | 3 | 5 | 3 cases matched; 2 were format stops in T1 |
| Technical Stops (`MALFORMED_FINDING`) | 3 | 1 | Line prefix `S01:` caused stop; T2 parsed bare digits |
| **Total Recorded** | **24** | **24** | **21 of 24 (87.5%) exact outcome agreement** |

### Per-Case Comparison

| Case | Trial 1 Verdict | T1 Wall (s) | Trial 2 Verdict | T2 Wall (s) | Agreement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `P-113ed2` | `NO_BLOCKERS_FOUND` | 50.8 | `NO_BLOCKERS_FOUND` | 38.2 | Match |
| `P-97610e` | `MALFORMED_FINDING` (stop) | 267.4 | `MALFORMED_FINDING` (stop) | 242.9 | Match |
| `P-b0b834` | `CHANGES_RECOMMENDED` | 236.4 | `CHANGES_RECOMMENDED` | 212.8 | Match |
| `P-c0cca7` | `NO_BLOCKERS_FOUND` | 40.5 | `NO_BLOCKERS_FOUND` | 81.2 | Match |
| `P-304538` | `CHANGES_RECOMMENDED` | 352.9 | `CHANGES_RECOMMENDED` | 352.1 | Match |
| `P-6b8046` | `MALFORMED_FINDING` (stop) | 302.0 | `BLOCKERS_FOUND` | 48.8 | Diff |
| `P-c6f970` | `CHANGES_RECOMMENDED` | 313.3 | `CHANGES_RECOMMENDED` | 405.0 | Match |
| `P-39e236` | `NO_BLOCKERS_FOUND` | 51.3 | `NO_BLOCKERS_FOUND` | 59.5 | Match |
| `P-c3cd60` | `CHANGES_RECOMMENDED` | 232.6 | `CHANGES_RECOMMENDED` | 277.0 | Match |
| `P-94be28` | `BLOCKERS_FOUND` | 95.1 | `BLOCKERS_FOUND` | 398.4 | Match |
| `P-e14c78` | `NO_BLOCKERS_FOUND` | 44.9 | `NO_BLOCKERS_FOUND` | 75.3 | Match |
| `P-3daca8` | `BLOCKERS_FOUND` | 332.0 | `BLOCKERS_FOUND` | 56.1 | Match |
| `P-313185` | `NO_BLOCKERS_FOUND` | 36.9 | `NO_BLOCKERS_FOUND` | 53.0 | Match |
| `P-7a8a51` | `MALFORMED_FINDING` (stop) | 321.2 | `BLOCKERS_FOUND` | 124.0 | Diff |
| `P-398544` | `CHANGES_RECOMMENDED` | 345.9 | `NO_BLOCKERS_FOUND` | 464.3 | Diff |
| `P-aa3181` | `NO_BLOCKERS_FOUND` | 64.7 | `NO_BLOCKERS_FOUND` | 82.4 | Match |
| `P-59d7fb` | `BLOCKERS_FOUND` | 63.1 | `BLOCKERS_FOUND` | 180.4 | Match |
| `P-381273` | `NO_BLOCKERS_FOUND` | 50.0 | `NO_BLOCKERS_FOUND` | 53.4 | Match |
| `P-ac2234` | `NO_BLOCKERS_FOUND` | 93.4 | `NO_BLOCKERS_FOUND` | 76.2 | Match |
| `P-fcc070` | `CHANGES_RECOMMENDED` | 229.3 | `CHANGES_RECOMMENDED` | 201.0 | Match |
| `P-6544fb` | `NO_BLOCKERS_FOUND` | 22.1 | `NO_BLOCKERS_FOUND` | 63.3 | Match |
| `P-ea57a1` | `NO_BLOCKERS_FOUND` | 128.9 | `NO_BLOCKERS_FOUND` | 39.5 | Match |
| `P-882b26` | `NO_BLOCKERS_FOUND` | 226.3 | `NO_BLOCKERS_FOUND` | 328.3 | Match |
| `P-5a8028` | `NO_BLOCKERS_FOUND` | 104.6 | `NO_BLOCKERS_FOUND` | 153.7 | Match |

## Next Steps for Independent Evaluation Session

Per Section 9 of [`HANDOFF.md`](../../HANDOFF.md):
1. **Scoring:** Run `python3 -B -I benchmarks/counterfactual-pairs/score.py trial1/responses.jsonl` and `trial2/responses.jsonl` against the frozen oracle.
2. **Adjudication:** Inspect each case's markdown report under `reports/` and receipt under `receipts/` to adjudicate mechanism correctness, citation accuracy, and any extra findings.
3. **Statistical Reporting:** Compute paired discrimination and Wilson 95% confidence intervals across the pair families.
