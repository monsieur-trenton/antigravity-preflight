# Counterfactual-Pairs Pilot Hand Back Report

**Execution Role:** Qualified native host pilot orchestrator  
**Status:** Both Trial 1 and Trial 2 complete. All 24 cases per trial recorded in independent ledgers. Process reaping and sandbox isolation verified clean across all 48 attempts. No repository modifications made. `score.py` has not been invoked (reserved for a separate session).

---

## 1. System & Binary Identity

- **Git Commit:** `d935c72339b5ec3119ebaa1ff528bf09bbcc02b9`
- **Manifest SHA-256:** `9885c1cf66d546882b49db70e5b360f5c49f7dbd6464a1856c223aca7ac32e46` (`benchmarks/counterfactual-pairs/manifest.json`)
- **Runtime Directory:** `runtime/flash-high`
- **Runtime Profile:** `flash-high` (default profile; model `gemini-3.8-flash-high`, effort `high`)
- **Executable Path:** `/home/john/.local/bin/agy`
- **Binary SHA-256:** `16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508`
- **Binary Version:** `1.4.1`
- **Host OS:** Linux Mint 22.3 (Ubuntu 24.04 noble base)
- **Host Kernel:** `Linux john-laptop 7.0.0-38-generic #38~24.04.4-Ubuntu SMP PREEMPT_DYNAMIC Mon Sep 14 16:37:11 UTC 2 x86_64 x86_64 x86_64 GNU/Linux`

---

## 2. Execution Timestamps

- **Offline Qualification:** `2026-10-22T15:53:28-07:00`
- **Capabilities Check:** `2026-10-22T15:53:39-07:00`
- **Dry Run:** `2026-10-22T15:54:03-07:00`
- **Trial 1 Start:** `2026-10-22T15:56:27-07:00` (first attempt receipt)
- **Trial 1 Completion:** `2026-10-22T17:02:48-07:00` (ledger timestamp)
- **Trial 2 Start:** `2026-10-22T17:16:07-07:00` (first attempt receipt)
- **Trial 2 Completion:** `2026-10-22T18:23:39-07:00` (ledger timestamp)

---

## 3. Evidence Locations on Disk

All artifacts remain preserved under the working root `/tmp/pilot`:

- **Qualification File:** `qual/DUAL-OFFLINE-QUALIFICATION.json` (`status: PASS`, 664 cases across 2 passes)
- **Capabilities Directory:** `caps/` (contains `RESULT.json`, `VERSION.stdout`, `MODELS.stdout`, `HELP.stderr`, and freeze manifests)
- **Dry Run CLI Gate:** `dry/CLI-GATE.json` is absent (as required; dry run generated 24 packet seeds without invoking any model turns or gates)
- **Trial 1 Ledger:** `live1/responses-trial1.jsonl`
- **Trial 1 Attempts:** `live1/trial1/attempts/` (24 case subdirectories)
- **Trial 2 Ledger:** `live2/responses-trial2.jsonl`
- **Trial 2 Attempts:** `live2/trial2/attempts/` (24 case subdirectories)

---

## 4. Trial Outcomes Summary

### Trial 1
- **Total Cases Recorded:** 24 / 24
- **Executed Normally:** 21
- **Recorded Technical Stops:** 3
  - `UNPARSEABLE_REPORT:MALFORMED_FINDING`: 3 cases
    - `P-97610e`
    - `P-6b8046`
    - `P-7a8a51`
- **Assessment Breakdown (24 cases):**
  - `NO_BLOCKERS_FOUND`: 12
  - `CHANGES_RECOMMENDED`: 6
  - `BLOCKERS_FOUND`: 3
  - Technical Stops (`MALFORMED_FINDING`): 3

### Trial 2
- **Total Cases Recorded:** 24 / 24
- **Executed Normally:** 23
- **Recorded Technical Stops:** 1
  - `UNPARSEABLE_REPORT:MALFORMED_FINDING`: 1 case
    - `P-97610e`
- **Assessment Breakdown (24 cases):**
  - `NO_BLOCKERS_FOUND`: 13
  - `CHANGES_RECOMMENDED`: 5
  - `BLOCKERS_FOUND`: 5
  - Technical Stops (`MALFORMED_FINDING`): 1

---

## 5. CLI-RECEIPT & Resource Reaping Summary

Every individual case attempt was executed within an unshared bubblewrap sandbox with D-Bus proxy secret-service token forwarding.

### Trial 1
- **Receipt Status Counts:** `REPORT_RECEIVED_PENDING_ADJUDICATION`: 24 / 24
- **Process Reaping:** Confirmed 100% across all 24 attempts:
  - `native.reaped: true` (24/24)
  - `proxy.reaped: true` (24/24)
  - `privateHomeAbsent: true` (24/24)
  - `socketDirectoryAbsent: true` (24/24)
- **Total Wall Clock Time:** 4,005.78s (~1h 06m 45s)
- **Per-Case Wall Seconds:**
  - Min: 22.09s (`P-6544fb`)
  - Median: 116.78s
  - Max: 352.93s (`P-304538`)

### Trial 2
- **Receipt Status Counts:** `REPORT_RECEIVED_PENDING_ADJUDICATION`: 24 / 24
- **Process Reaping:** Confirmed 100% across all 24 attempts:
  - `native.reaped: true` (24/24)
  - `proxy.reaped: true` (24/24)
  - `privateHomeAbsent: true` (24/24)
  - `socketDirectoryAbsent: true` (24/24)
- **Total Wall Clock Time:** 4,066.93s (~1h 07m 47s)
- **Per-Case Wall Seconds:**
  - Min: 38.18s (`P-113ed2`)
  - Median: 103.24s
  - Max: 464.26s (`P-398544`)

---

## 6. Case-by-Case Comparison

| Case | Trial 1 Assessment / Stop | T1 Sec | Trial 2 Assessment / Stop | T2 Sec | Outcome Agreement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `P-113ed2` | `NO_BLOCKERS_FOUND` | 50.8s | `NO_BLOCKERS_FOUND` | 38.2s | **Match** |
| `P-97610e` | `UNPARSEABLE_REPORT:MALFORMED_FINDING` | 267.4s | `UNPARSEABLE_REPORT:MALFORMED_FINDING` | 242.9s | **Match** |
| `P-b0b834` | `CHANGES_RECOMMENDED` | 236.4s | `CHANGES_RECOMMENDED` | 212.8s | **Match** |
| `P-c0cca7` | `NO_BLOCKERS_FOUND` | 40.5s | `NO_BLOCKERS_FOUND` | 81.2s | **Match** |
| `P-304538` | `CHANGES_RECOMMENDED` | 352.9s | `CHANGES_RECOMMENDED` | 352.1s | **Match** |
| `P-6b8046` | `UNPARSEABLE_REPORT:MALFORMED_FINDING` | 302.0s | `BLOCKERS_FOUND` | 48.8s | Difference |
| `P-c6f970` | `CHANGES_RECOMMENDED` | 313.3s | `CHANGES_RECOMMENDED` | 405.0s | **Match** |
| `P-39e236` | `NO_BLOCKERS_FOUND` | 51.3s | `NO_BLOCKERS_FOUND` | 59.5s | **Match** |
| `P-c3cd60` | `CHANGES_RECOMMENDED` | 232.6s | `CHANGES_RECOMMENDED` | 277.0s | **Match** |
| `P-94be28` | `BLOCKERS_FOUND` | 95.1s | `BLOCKERS_FOUND` | 398.4s | **Match** |
| `P-e14c78` | `NO_BLOCKERS_FOUND` | 44.9s | `NO_BLOCKERS_FOUND` | 75.3s | **Match** |
| `P-3daca8` | `BLOCKERS_FOUND` | 332.0s | `BLOCKERS_FOUND` | 56.1s | **Match** |
| `P-313185` | `NO_BLOCKERS_FOUND` | 36.9s | `NO_BLOCKERS_FOUND` | 53.0s | **Match** |
| `P-7a8a51` | `UNPARSEABLE_REPORT:MALFORMED_FINDING` | 321.2s | `BLOCKERS_FOUND` | 124.0s | Difference |
| `P-398544` | `CHANGES_RECOMMENDED` | 345.9s | `NO_BLOCKERS_FOUND` | 464.3s | Difference |
| `P-aa3181` | `NO_BLOCKERS_FOUND` | 64.7s | `NO_BLOCKERS_FOUND` | 82.4s | **Match** |
| `P-59d7fb` | `BLOCKERS_FOUND` | 63.1s | `BLOCKERS_FOUND` | 180.4s | **Match** |
| `P-381273` | `NO_BLOCKERS_FOUND` | 50.0s | `NO_BLOCKERS_FOUND` | 53.4s | **Match** |
| `P-ac2234` | `NO_BLOCKERS_FOUND` | 93.4s | `NO_BLOCKERS_FOUND` | 76.2s | **Match** |
| `P-fcc070` | `CHANGES_RECOMMENDED` | 229.3s | `CHANGES_RECOMMENDED` | 201.0s | **Match** |
| `P-6544fb` | `NO_BLOCKERS_FOUND` | 22.1s | `NO_BLOCKERS_FOUND` | 63.3s | **Match** |
| `P-ea57a1` | `NO_BLOCKERS_FOUND` | 128.9s | `NO_BLOCKERS_FOUND` | 39.5s | **Match** |
| `P-882b26` | `NO_BLOCKERS_FOUND` | 226.3s | `NO_BLOCKERS_FOUND` | 328.3s | **Match** |
| `P-5a8028` | `NO_BLOCKERS_FOUND` | 104.6s | `NO_BLOCKERS_FOUND` | 153.7s | **Match** |

- **Exact Agreement Across Trials:** 21 / 24 cases (87.5%)
- **Differences:** 3 / 24 cases (2 parsed in Trial 2 after format stop in Trial 1; 1 assessment difference)

---

## 7. Observations Quoted from Pilot Output

1. **Format of stopped finding lines (`MALFORMED_FINDING`):**
   In Trial 1 on `P-97610e`, `P-6b8046`, and `P-7a8a51`, and in Trial 2 on `P-97610e`, the finding line included the snapshot identifier prefix `S01:` in the line number field:
   - `P-97610e` (both trials):
     > `"FINDING: BLOCKER | VERIFIED | S01:3 | The job enumerates directories more than 7 days old and removes every one of them."`
   - `P-6b8046` (Trial 1):
     > `"FINDING: BLOCKER | VERIFIED | S01:3 | schedule() keeps its old usage: window = parse_window(start, end), followed by window + 3600."`
   - `P-7a8a51` (Trial 1):
     > `"FINDING: BLOCKER | VERIFIED | S01:3 | The job lists directories older than 7 days and deletes all of them."`
   
   The pilot runner's parsing check in `benchmarks/counterfactual-pairs/run_pilot.py#L85`:
   ```python
   need(number.isdigit(), "MALFORMED_FINDING")
   ```
   evaluated to `False` due to `"S01:3"`.

2. **Parsing resolution in Trial 2 for `P-6b8046` and `P-7a8a51`:**
   In Trial 2, the model output bare digit line numbers for these two cases:
   - `P-7a8a51` (Trial 2):
     > `"FINDING: BLOCKER | VERIFIED | 3 | The job lists directories older than 7 days and deletes all of them."`
   - `P-6b8046` (Trial 2):
     > `"FINDING: BLOCKER | VERIFIED | 3 | schedule() keeps its old usage: window = parse_window(start, end), followed by window + 3600."`
   Both parsed cleanly without technical stops.
