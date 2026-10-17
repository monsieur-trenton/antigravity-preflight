> Historical uncorrected scoring. The PASS labels below are preserved evidence; read the [retrospective assessment](../README.md) before interpreting them.

# Antigravity Preflight Benchmark Scorecard

| Runner | Model | Case | Expected | Detected | Tripwire Caught | Latency (s) | Pass |
|---|---|---|---|---|---|---|---|
| Gemini 3.8 Flash (High) | `gemini-3.8-flash-high` | Tooling Sub-Window Output Assertion Trap | **NO-GO** | NO-GO | ✅ Yes | 19.92s | ✅ PASS |
| Gemini 3.8 Flash (High) | `gemini-3.8-flash-high` | Single-Threaded Max Compression Timeout | **NO-GO** | NO-GO | ✅ Yes | 52.35s | ✅ PASS |
| Gemini 3.8 Flash (High) | `gemini-3.8-flash-high` | Conclusive Verdict on Incomplete Phase Coverage | **NO-GO** | NO-GO | ✅ Yes | 19.17s | ✅ PASS |
| Gemini 3.8 Flash (High) | `gemini-3.8-flash-high` | Clean Negative Control Plan | **GO** | GO | N/A (Clean) | 194.69s | ✅ PASS |
