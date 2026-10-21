# Plan Review: Source Coverage Report

## Summary

The plan's main design choice is correct. **It loops over the full supplied inventory, not over the diff.** A typical diff touches only one or two of the four sources. A diff-driven report would routinely omit sources, get labelled INCOMPLETE, and fail the checker. Iterating over the inventory guarantees every source gets a section, whatever changed.

## What Works

- **Coverage comes from the inventory.** The set of sources in the report matches the supplied inventory by construction, which is what the checker compares against.
- **One loop pass gives one section per source**, which satisfies "exactly once" if the inventory itself is clean.
- **SHA-256 plus line count** gives each section a concrete, checkable fingerprint, including for unchanged sources.

## Gaps to Address

1. **Unreadable or missing sources aren't handled.** If one source can't be read, the plan doesn't say what happens. If the loop skips it or aborts, the report becomes INCOMPLETE. Instead, always emit the section and record an explicit error status, such as `ERROR: file not found`, in place of the hash and line count.

2. **"Exactly once" depends on a clean inventory.** If the inventory has duplicate entries, or the same file under different spellings (`./a.py` vs `a.py`), the loop will write duplicate sections. Normalize identifiers, then dedupe or fail loudly before generating the report.

3. **The output isn't checked before it's emitted.** Add a final assertion that the set of section identifiers equals the inventory set and has no repeats. This catches problems before the checker does.

4. **The metrics need precise definitions.**
   - Hash the raw bytes, not decoded or newline-normalized text, so hashes are reproducible.
   - Define line count, especially whether a final line without a trailing newline counts. Then the numbers match tools like `wc -l` or are documented as differing.

5. **Optional: show change status.** Since most sources are unchanged in a typical diff, a `changed`/`unchanged` marker per section would help reviewers focus. Unchanged sources must still get full sections, not be collapsed or omitted.

6. **Use a deterministic order.** Use inventory order or sorted order so reports are stable across runs and easy to diff.

## Conclusion

The core approach is sound and meets the coverage requirement. The changes above are hardening: error handling for unreadable sources, inventory deduplication, and a self-check. Together they ensure the "exactly once" guarantee holds in edge cases.

VERDICT: GO_WITH_CHANGES