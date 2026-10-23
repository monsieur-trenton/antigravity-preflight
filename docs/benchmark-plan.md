# Benchmark plan

Four claims need separate evidence. Only the first is covered today.

1. **Deterministic gates reject bad evidence.** Covered offline: [demonstrated utility](demonstrated-utility.md), the [fault-injection harness](../benchmarks/fault-injection/README.md) and the qualification suites.
2. **Reviewer judgments follow material facts**, not titles or keywords. One saved four-case run exists with flawed scoring; see the [exploratory audit](../benchmarks/exploratory-plan-audit/README.md).
3. **The workflow beats asking Gemini directly.** Untested.
4. **Preflight moves blockers ahead of the independent reviewer.** Untested; this is the headline value.

| | Benchmark | Claim | Model calls | Figure |
| --- | --- | --- | --- | --- |
| A | Ablation: no preflight, raw Gemini prompt, full skill, on one seeded-defect corpus. First arm built: a [bare-prompt arm](../benchmarks/counterfactual-pairs/ablation/README.md) against the skill-style bundle on corpus v2 (Claude CLI route), preregistered and [run once](../benchmarks/counterfactual-pairs/results/ablation-bare-opus-5-5-high/README.md): verdict-only 21/37 against 40/40, but the bare reviewer found the defect in all 15 missed twins; it tests the prompt-and-packet bundle only. A [third arm](../benchmarks/counterfactual-pairs/ablation/defined/README.md) (bare plus five lines defining the verdicts) was preregistered and [run once](../benchmarks/counterfactual-pairs/results/ablation-defined-opus-5-5-high/README.md): 35/39 pairs ordered, partly closing the gap (sound plans still hedged), so most of the verdict gap is calibration rather than detection. A [fourth arm](../benchmarks/counterfactual-pairs/ablation/defined-go/README.md) (the same plus one sentence about optional suggestions, written after that result) was preregistered and [run once](../benchmarks/counterfactual-pairs/results/ablation-defined-go-opus-5-5-high/README.md): every sound plan clean and every defect twin blocked, but an unmeasured risk was waved through (label "costs detection"); the next step is a held-out corpus, now built as [corpus v3](../benchmarks/counterfactual-pairs/v3/README.md) (64 cases, 8 evidence-gap families, blind-audited) with a [preregistered three-arm run](../benchmarks/counterfactual-pairs/v3-run/PREREGISTRATION.md) and its tooling built, not yet run | 3 | Yes | Grouped bars by arm |
| B | Blind counterfactual pairs, six families ([design](testing-next.md)); [frozen corpus and scorer ready](../benchmarks/counterfactual-pairs/README.md), pilot 1 run on the `claude-cli` route only ([results](../benchmarks/counterfactual-pairs/results/pilot1-claude-opus-5-5-high/README.md)); the [Gemini 3.8 Flash High pilot](../benchmarks/counterfactual-pairs/results/pilot-flash-high/README.md) has run on the same corpus (8/12 under a documented rule, ordinal 20/20 on the valid families, like Claude); [corpus v2](../benchmarks/counterfactual-pairs/v2/README.md) preregistered and run once on the `claude-cli` route ([pilot 2](../benchmarks/counterfactual-pairs/results/pilot2-v2-claude-opus-5-5-high/README.md): primary metric 20/20, a ceiling for that reviewer) | 2 | Yes | Paired slope chart and confusion tile |
| C | Replay raw responses through the citation checker | 1, 3 | No | Finding funnel |
| D | Evidence-integrity fault injection | 1 | No | Fault × gate matrix (done for the citation checker) |
| E | Hostile source text, scored apart from the gates | 2 | Yes | Per-family result tiles |
| F | Same independent reviewer, with and without preflight | 4 | Yes | Before/after dumbbell |
| G | Mined corpus of plans or commits with later-confirmed defects | 2, 4 | Yes | Forest plot |
| H | Repeatability and cost, k ≥ 3 trials | all | Yes | Strip plot |

**Not yet possible offline.** The saved historical responses cite no `[S01:line]` coordinates, so benchmark C needs new responses produced with the numbered reading view.

## Rules for every benchmark

- Freeze and hash the corpus, prompts, project rules and answer key before any submission; keep the answer key out of reviewer-visible packets.
- Include verified-sound controls, or "reject everything" scores perfectly.
- Blind and randomize identifiers, titles and order; include equivalent rewordings.
- Pre-register pass gates and preserve every failure.
- Report counts with Wilson intervals per family. Do not publish a general rate from a small pilot.
- Report deterministic-gate results and model-judgment results separately.
- Pin model, effort and runtime. Model calls need the owner's authorization, one turn each, with no automatic retries.

## Figures

Plot raw counts and intervals, not bare percentages, below about 30 cases. Figures are dependency-free SVG with light and dark themes, drawn by [make_figures.py](../benchmarks/plots/make_figures.py) from committed result files. CI regenerates them with `--check`, so a figure cannot drift from its data. State is never carried by colour alone: stopped, accepted-with-caveat and not-exercised use different shapes.
