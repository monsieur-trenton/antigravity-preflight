# Review: Build Step Metadata Summary vs. 1500-Byte Stdout Cap

The plan will fail on data it has already seen in testing.

## The core problem: the summary can't fit

- **The values alone exceed the cap.** One test summary held three values of about 700 bytes each. That is about 2100 bytes, roughly 600 bytes over the 1500-byte cap, before any keys or punctuation.
- **The JSON structure adds more.** Six keys of up to 12 bytes, plus quotes, colons, commas and braces, add up to about 130 more bytes.
- **Values are kept whole.** Nothing truncates, summarizes or moves the large values, so the output stays over the cap.
- **ASCII escaping makes it worse, not better.** Encoded bytes equal characters at best. Escapes like `\uXXXX` or `\"` only grow the values.

## The assertion catches the overflow but doesn't fix it

Checking the encoded byte length before writing is correct. It measures bytes, not characters, and it prevents a silent over-cap write. But when it trips, the step still fails. Either way, the harness contract says a failed step aborts the release with no retry. So a summary like the one seen in testing breaks the release whether the assertion fires or the harness rejects the oversized stdout. The guard turns the failure into a clear error, but the release is still blocked.

## Things that are fine

- Keeping the debug log in a temp file, off stdout, is correct. It doesn't count toward the cap, and removing it on exit is reasonable. You might keep it on failure to help diagnose aborts, but that is optional.
- Fixed keys and compact JSON are good choices. The key overhead is small and predictable.

## What needs to change

Pick a strategy that guarantees the output fits in 1500 bytes:
1. **Set a per-value byte budget.** Truncate values with a clear marker, such as `"…(truncated, N bytes)"`. The budget should cover the full worst case: six values plus about 130 bytes of structure, all within 1500.
2. **Move large values out of stdout.** Write the full values to an artifact file and put only a path or hash in the summary.
3. **Drop or shorten fields that can be long.** Do this if they aren't needed in the stdout summary.

Keep the pre-write byte assertion as a final safety net. Also add a test case using the observed three-by-700-byte summary, so it can't regress.

VERDICT: NO_GO