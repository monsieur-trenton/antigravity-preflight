# Results: Preregistered Corpus v3 Evaluation on Gemini 3.8 Flash High Native Route

This archive contains the complete experimental results and metadata from the two-trial preregistered evaluation of the Gemini 3.8 Flash High native route on the held-out **corpus v3** (64 counterfactual test cases).

---

## Directory Structure

```
.
├── identity.txt                         # Full system identity, hashes, timestamps, and verifier reports
├── README.md                            # This document
├── qual/
│   └── DUAL-OFFLINE-QUALIFICATION.json  # 2-pass offline qualification envelope (664 cases, PASS)
├── caps/
│   ├── RESULT.json                      # Host capabilities probe (model, binary hashes, version)
│   └── VERSION.stdout                   # Binary version output (1.4.1)
├── trial1/
│   ├── responses-trial1.jsonl           # Primary JSONL ledger (64 rows)
│   ├── reports/                         # Case review markdown files (63 reports, <case>.md)
│   └── receipts/                        # Host containment & process receipts (64 receipts, <case>.json)
└── trial2/
    ├── responses-trial2.jsonl           # Primary JSONL ledger (64 rows)
    ├── reports/                         # Case review markdown files (64 reports, <case>.md)
    └── receipts/                        # Host containment & process receipts (64 receipts, <case>.json)
```

---

## How to Read the Results

### 1. The Ledgers (`trialN/responses-trialN.jsonl`)
Each line in `responses-trialN.jsonl` represents one evaluated case in the pinned evaluation order.

Example row format:
```json
{
  "case": "Q-3e839b",
  "trial": 1,
  "route": "native-flash-high",
  "parser": "snapshot-label-tolerant",
  "binarySha256": "16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508",
  "runManifestSha256": "d853fee334b39a42d8b1b20b87a9dc27d68f108a9a4b4afa8e28c48e901ff5d2",
  "completeness": "COMPLETE",
  "assessment": "NO_BLOCKERS_FOUND",
  "findings": [],
  "reportSha256": "f88b0ca7b1dc303ea589c2675eda5c695826c07d650df0c774e0161456ed59d6",
  "wallSeconds": 112.31
}
```

* For successful reviews, `assessment` is one of `NO_BLOCKERS_FOUND`, `CHANGES_RECOMMENDED`, or `BLOCKERS_FOUND`.
* If a technical stop occurred, `technicalStop` indicates the stop reason (e.g., `RUNTIME_STOP:{"code": "UNQUALIFIED_STEP", ...}` on `Q-497363` in Trial 1).

### 2. The Review Reports (`trialN/reports/<case>.md`)
Contains the exact text emitted by the Gemini reviewer for each case, culminating in the machine-readable summary block:
```
MACHINE SUMMARY
COMPLETENESS: <COMPLETE | INCOMPLETE>
ASSESSMENT: <NO_BLOCKERS_FOUND | CHANGES_RECOMMENDED | BLOCKERS_FOUND>
FINDING: <SEVERITY> | <EVIDENCE> | <LINE> | <QUOTATION>
```

### 3. Containment & Execution Receipts (`trialN/receipts/<case>.json`)
Each receipt records the bwrap sandbox containment, host pipe prompt delivery, process reaping, and timing metrics:
* `status`: `REPORT_RECEIVED_PENDING_ADJUDICATION` or `STOPPED`
* `processes`: confirmation that both native and proxy child processes were spawned and reaped.
* `privateHomeAbsent` & `socketDirectoryAbsent`: confirmation of complete ephemeral filesystem cleanup.
* `elapsedSeconds`: total wall-clock seconds for the native execution turn.

---

## Verifier Note on `PROMPT_DELIVERY`
`verify_gemini_run.py` tests `delivery["wireBytes"] == len(expected_prompt)`. Because the runtime (`runtime/flash-high/scripts/cli_review.py`) wraps the prompt in a 71-byte stream-JSON envelope (`{"event": "user", "message": {"content": ...}}\n`), `wireBytes` and `bytesWritten` both equal `len(expected_prompt) + 71`. The delivery status is `COMPLETE` across all cases.
