# Plan Review: Source Coverage Report

## Requirements check

**Every source appears exactly once.** The report is built by looping over the whole inventory and writing one section per source. With four sources supplied, that gives four sections, each source once. ✅

**Covered sources match the supplied inventory.** The report's sections come straight from the inventory, so they match it by construction and the checker accepts the report. ✅

**No INCOMPLETE label.** The loop never skips a source, so none is left out. The report can be recommended for readiness. ✅

**Per-section content.** Each section shows the source's SHA-256 and line count. Both can be computed for any source, changed or not, so every section can be filled in. ✅

## The point that looks risky but isn't

The note that "in a typical diff, only one or two of the four sources change" might suggest the report covers only changed sources. That would leave out two or three sources, get the report labelled INCOMPLETE and fail the checker. The plan does not do that. It loops over the **whole inventory**, not over the diff, so unchanged sources still get their sections. How many sources a diff changes has no effect on coverage.

## Optional hardening (not required)

These would only make a working plan more robust:

- **Assert the section count equals the inventory size** (4) before emitting the report. This catches an accidental filter added later.
- **Guard against duplicate inventory entries**, for example by deduplicating on source ID. This keeps "exactly once" true even if the input list is malformed.
- **Optionally mark each section as changed or unchanged** for reader convenience, without affecting coverage.

## Conclusion

The plan meets every rule it states. The suggestions above are optional robustness improvements, not changes the plan needs.

VERDICT: GO