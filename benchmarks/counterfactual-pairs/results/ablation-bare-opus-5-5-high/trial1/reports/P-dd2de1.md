# Review: Per-Source Report Plan

**Overall:** The plan is sound. The checker needs the report's sources to match the inventory exactly. Building the report by looping over the full inventory meets that requirement by construction, rather than depending on which sources changed.

## What works

- **Iterating the full inventory, not the diff, is the key decision.** A typical diff touches only one or two of the four sources. A diff-driven report would usually omit sources, get labelled INCOMPLETE, and fail the checker. The plan avoids that trap.
- **The exactly-once requirement follows naturally.** One loop pass over the inventory produces one section per source, assuming the inventory has no duplicates.
- **SHA-256 plus line count gives each section verifiable content.** It also confirms that unchanged sources were actually read, not just listed.

## Hardening suggestions (none blocking)

1. **Validate the inventory before looping.** Assert that it has exactly four entries and no duplicate identifiers or paths. A duplicated entry would produce two sections, and a missing one would produce three. Either way the checker rejects the report, so catching it early gives a clearer error.
2. **Never skip a source silently on a read error.** If a file can't be read or hashed, fail loudly or emit a section with an explicit error marker. A `continue` in the loop would turn a read error into an INCOMPLETE report.
3. **Define the hash and line-count rules.**
   - Hash the raw bytes, with no newline normalization.
   - Count lines consistently, including how a final line without a trailing newline is handled.
   - Hash the post-diff version of each file.
4. **Consider a changed/unchanged flag per section.** Most sources won't change in a given diff. Showing this status makes the report easier to read without affecting coverage.
5. **Add a self-check before output.** Compare the set of reported sources to the inventory set, and fail if they differ. This mirrors the checker's rule locally.

VERDICT: GO