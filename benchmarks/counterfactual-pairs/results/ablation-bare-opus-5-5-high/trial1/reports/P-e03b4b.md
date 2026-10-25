# Review: build step metadata summary vs. 1500-byte stdout cap

## Blocking issue: the observed test case already breaks the cap

The plan's own test data exceeds the limit:

- Three values of about 700 bytes each come to about **2100 bytes**, before keys or JSON syntax.
- The fixed overhead is small but not zero. Six keys of up to 12 bytes, plus quotes, colons, commas, braces and value quotes, add up to about 110 bytes. That leaves roughly **1390 bytes** for all values combined.
- Values are "kept whole," so nothing in the plan brings that summary under 1500.

## The pre-write assertion doesn't prevent the failure

Checking encoded byte length before writing is correct, and better than checking character count. But the plan doesn't say what happens when the assertion fires. In practice the step fails either way: it aborts on the assertion, or it writes and the harness rejects it. Both outcomes abort the release with no retry. The assertion turns an overflow into a clearer error message, but it doesn't make the step succeed.

## Secondary concerns

1. **Escaping can expand values.** ASCII escaping turns each non-ASCII character into `\uXXXX`, which is 6 bytes or 12 for a surrogate pair. The plan doesn't say whether "roughly 700 bytes" was measured before or after escaping. The size budget has to be computed on the escaped form.
2. **Diagnostics are lost on failure.** The debug log is deleted on exit, including when the size assertion fails. The one run you'd most want to inspect leaves no trace. Consider keeping the log when the step fails, or printing its path to stderr.
3. **No size limit on individual values.** Nothing limits a single value, so the 2100-byte case is a realistic input, not an edge case.

## Required changes

Choose one of these and state it explicitly:

- **Spill large values out of stdout (preferred).** Write the full summary to an artifact or file. Put a compact pointer on stdout, such as path, sha256 and byte length, with any small fields inline. This keeps values whole, which seems to be a requirement.
- **Truncate deterministically.** Cap each value to its share of a computed budget (about 1390 bytes for values, measured after escaping). Add a `truncated` flag or marker, and accept that values are no longer whole.
- **Get the cap raised** in the harness contract, if large values are expected.

Then add a test that uses the 3 × 700-byte case, plus non-ASCII-heavy values, and confirms the step succeeds.

The design can't satisfy its own constraints on data it has already seen, and a failure aborts the release with no retry. It needs a design change, not just tuning.

VERDICT: NO_GO