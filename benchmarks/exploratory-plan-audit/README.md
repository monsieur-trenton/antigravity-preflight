# Exploratory plan audit evaluation

One saved four-case experiment asked a CLI configured for Gemini 3.8 Flash / High to audit reconstructed execution plans. Every saved response matched its original expected GO/NO-GO label. Retrospective source inspection found weaknesses in both the scoring and case labels, so this experiment provides examples of reviewer behavior rather than a general accuracy estimate.

## Execution scope

The retained runner source invokes agy with `--model gemini-3.8-flash-high --effort high --mode plan --dangerously-skip-permissions -p`. This execution path bypasses the published qualified launcher. Its prompt requests a static, tool-free audit; the wrapper inherits its working directory and environment. The saved records contain no tool-event audit or isolation proof. Complete isolation from other projects or models was not established. No access violation is inferred from that missing evidence.

The model field is a wrapper configuration label. The saved files do not independently attest the serving model, effort, binary identity, implicit instruction sources, or backend request count. The experiment did not run the plans' code or measure compression performance. The source/publication identities and limited redactions are recorded in [provenance.json](provenance.json).

## Saved observations and retrospective adjudication

| Reconstructed case | Original expected label | Saved response | Reported complete CLI wall time | Retrospective judgment |
| --- | --- | --- | --- | --- |
| Output assertion threshold | NO-GO | NO-GO | 19.92 s | Core concern supported: the proposed 1,250-byte input estimate exceeds the 1,100-byte assertion while fitting the external 1,500-byte cap. This is conditional reasoning about the supplied estimate, not execution of the historical failure. |
| Compression work window | NO-GO | NO-GO | 52.35 s | Budget risk recognized. The prompt supplied no measured throughput establishing inevitable overrun. The response's throughput and speedup figures are unsupported by the supplied packet. |
| Incomplete required coverage | NO-GO | NO-GO | 19.17 s | Core contract contradiction supported. The response's additional prediction about downstream validator behavior was not established by supplied validator source. |
| Purported clean control | GO | GO | 194.69 s | Invalid unconditional clean control: the fallback pointer embeds an unbounded path and retains an unhandled assertion. The response conditions its approval on ordinary path lengths; those bounds were absent from the case contract. |

The first three calls averaged **30.48 seconds**; all four averaged **71.53 seconds**. These are saved end-to-end CLI wall times, not timestamps of first defect detection. The control took **194.69 seconds**. Each case has one saved observation; the calls are not repeated independent trials.

The original scorer marked all four PASS using label substring matching and one-keyword tripwire credit. That scorecard is retained as [historical evidence](historical/README.md), not endorsed as a validated result. The scorer misclassified `NO_BLOCKERS_FOUND` as NO-GO and an unrelated sentence containing “ongoing” as GO. It did not require successful process outcomes before awarding a match. Those defects do not prove that the four saved labels were extracted incorrectly; they limit the scoring method.

We do not report “100% recall” or “0% false alarm rate.” Three adverse labels and one flawed control do not establish those general rates. There is no head-to-head model comparison, qualified-runtime benchmark result, cost-saving estimate, or independent product certification here.

## Corrected retrospective scoring

[evaluate.py](evaluate.py) recognizes explicit binary verdict declarations, refuses conflicting labels and failed process outcomes, and keeps keyword hints separate from semantic credit. It is scoped to the historical binary prompt. It does not convert the skill's NO_BLOCKERS_FOUND assessment into readiness or execution authorization. Human adjudication must still assess mechanisms, assumptions and source support.

From the repository root:

```bash
python3 -B -I benchmarks/exploratory-plan-audit/test_evaluate.py
python3 -B -I benchmarks/exploratory-plan-audit/evaluate.py
```

Both commands are offline; they launch no model or native CLI. The published [retrospective extraction](retrospective-labels.json) records the four original label matches without claiming four semantically validated passes. Original local experimental files were not modified and no new live observations were created.

## Follow-up testing

See [two proposed skill tests](../../docs/testing-next.md): blind counterfactual pairs and full-workflow evidence integrity. A repaired control and a throughput-evidenced timing case require new separately authorized model trials; they cannot inherit the original run's outputs.
