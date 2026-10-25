# Preregistration: corpus v3 on the Gemini 3.8 Flash High native route

Frozen with `manifest.json`: this file is pinned by hash, and the manifest names the exact corpus v3 manifest, the `flash-high` runtime package (one hash over every file) and the `agy` binary's SHA-256. Written before any v3 observation by any reviewer exists. The corpus design, the three primary rates, the strict summary and the general hypotheses are in the [corpus preregistration](../v3/PREREGISTRATION.md); the Claude-route arms have their [own run preregistration](../v3-run/PREREGISTRATION.md). This file fixes what the Gemini run adds.

## Question

On a held-out corpus with eight evidence-gap families and no absorbing fallbacks, does the reviewer the skill actually targets, Gemini 3.8 Flash High through the qualified native route, (a) judge sound plans `GO`, (b) block defect twins, including those that need inference across lines, and (c) flag evidence-gap twins as `GO_WITH_CHANGES` rather than waving them through or calling them blockers? The Claude-route runs cannot answer this: their findings (verdict calibration, the cost of the optional-suggestions sentence) say nothing about Gemini.

## The one arm

The skill-style prompt exactly as the [Gemini pilot](../results/pilot-flash-high/README.md) ran it: the frozen `prompt.txt` (byte-identical for v1, v2 and v3), the numbered snapshot placed inside the prompt, and the fixed question and machine-summary block of `run_pilot.py`. There are no ablation arms on this route; the defined-verdict and sentence arms exist only for the Claude CLI.

## What differs from the Gemini v1 pilot, and why

| | v1 pilot | this run |
| --- | --- | --- |
| Corpus | v1, 24 cases | v3, 64 cases |
| Driver | `run_pilot.py` | `run_gemini_v3.py`, a wrapper that leaves `run_pilot.py` unchanged and adds the binding below |
| Report parser | strict: the line field of a FINDING must be digits | the same, **except that a snapshot label `S01:<n>` in the line field is read as line `<n>`** |
| Binding | none | a run manifest: corpus, runtime package, binary identity, preregistration; every ledger row is stamped with it |

The relaxation was chosen **after seeing the v1 pilot's four format stops** (the reviewer wrote the label `S01:3` in the line field of four correct VERIFIED blockers). It changes only how a report is read, not what the model is sent, so the prompt, the packets and the route are the ones the v1 pilot used. The quotation must still appear verbatim on the cited line and every other format rule stands. A row that used the relaxation carries `snapshotLabelRead: true` and the count is reported. **No other relaxation is admitted after the fact**: a report that still fails the parser is a technical stop and stays one, and the only documented-rule view is the one a relaxation preregistered here would define (none beyond this one).

## Conditions

Route `flash-high` (`runtime/flash-high`, no runtime profile); model `gemini-3.8-flash-high` and effort `high` as requested and configured (the route cannot attest the served model, and the receipts say so); `agy` 1.4.1, SHA-256 `16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508`, the binary of the v1 pilot; Linux with Bubblewrap, a private home per case, the filtered credential proxy; one native turn per case with a 600 second runtime limit; **two trials**, each separately authorized, each in its own working directory (`live1`, `live2`), each in the frozen submission order; zero retries; a recorded case is never rerun and an attempt directory with no record is logged as `INTERRUPTED_UNKNOWN_STATE`. The capabilities probe and the offline qualification are run once for both trials.

**Time.** The v1 pilot took about 4,000 seconds per trial for 24 cases (about 167 seconds per case on average, 22 to 464 seconds). Expect about 64 x 167 s, around **3 hours per trial**, so about 6 to 7 hours for both. Credits and account are the owner's; this repository records neither.

## Metrics and analysis

Defined in the corpus preregistration and computed by [analyze.py](../v3-run/analyze.py) (one arm: the three primary rates, strict and ordered pair discrimination, the secondary rates including gap named but dismissed, verdict follows finding, per family, per trial) and by `score.py --corpus v3` (the preregistered finding-level score: strict pair discrimination, false blockers, changed twins judged correctly, **unsupported VERIFIED findings, a gate that must be zero**). The all-pairs result is the headline; the sensitivity views are the adjudicated exclusions and reclassifications of an adjudication file written before any metric. Wilson 95% intervals; two trials of one case are not independent. Stops are removed from denominators, never counted as verdicts.

## Comparisons

- **Descriptive baselines, not hypotheses tests:** the Gemini v1 pilot (a different, easier corpus) and the Claude route's skill-style arm on v2 (4 of 4 evidence-gap twins flagged, 40 of 40 pairs ordered).
- **Cross-route, if the Claude v3 run has been done:** `analyze.py` with two arms (this run and the Claude skill-style arm), paired on matched (case, trial) units with an exact sign test, reported as descriptive. The two ran on different days with different wrappers, so a difference is a difference between routes as run, not between models.

## Hypotheses, stated before any v3 data (analysed two-sided; the opposite outcome is reportable)

1. **Sound plans** are judged `GO` at a high rate (v1 pilot: 24 of 24; the skill-style prompt says missing evidence is not a defect).
2. **Defect twins** are blocked at a lower rate on the five `inference` families than on the three `direct` ones: the v1 pilot's one systematic miss was a defect that needed a premise about the diff (a RISK instead of a blocker).
3. **Evidence-gap twins** are judged `GO_WITH_CHANGES` at a high rate, because the contract names missing evidence as a risk, not a blocker (v1: 4 of 4 on the one such family). The failure modes to look for are `GO` (waved through) and `NO_GO` (overclaimed).
4. The reports for evidence-gap twins **name the unestablished fact** in most cases whatever the verdict (the keyword rubric, recall only, read on a sample).

No pass threshold is claimed and nothing estimates a general accuracy rate.

## Human reading, fixed in advance

Read in full: every evidence-gap twin not judged `GO_WITH_CHANGES`, every defect twin without `NO_GO`, every sound plan not judged `GO`, every technical stop's report, and a sample of up to ten correct evidence-gap twins. Classified by whether the report names the planted gap or defect and what it does with it. Coverage stated; the reader is the corpus author, who has seen the scores.

## Stops and adjudication

Technical stops are recorded and kept apart from wrong judgments. An adjudication file naming each stop and any reclassification is written before any metric; the as-run result is the headline. A run that halts on three consecutive stops is not rerun; the owner decides whether to continue with `--max-consecutive-stops 99`, which changes nothing else.

## What results can claim

For one model as requested, one route, one binary and this corpus hash, under the corpus preregistration's limits (Claude authors and auditors of the corpus; evidence gaps with no absorbing fallback; short plan notes). The served model is unattested. Nothing about the skill's citation check or adjudication step beyond the scored VERIFIED findings, nothing about Argon, and nothing about real repositories.

## Running

`run_gemini_v3.py` with `--corpus benchmarks/counterfactual-pairs/v3 --run-manifest benchmarks/counterfactual-pairs/v3-run-gemini/manifest.json`, then `verify_gemini_run.py` with the same two arguments per trial. The gated runbook is [HANDOFF.md](HANDOFF.md).
