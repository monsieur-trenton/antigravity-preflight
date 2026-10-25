# Review: Build Step Metadata Summary vs. 1500-Byte Stdout Cap

## The core problem: the summary can't fit under the cap

The plan's own numbers break the cap.

- **Values alone:** 3 × ~700 bytes ≈ 2100 bytes. That is already about 600 bytes over the 1500-byte limit, before counting keys or JSON syntax.
- **Overhead:** 6 keys of up to 12 bytes each, plus quotes, colons, commas and braces, adds roughly 100 to 120 more bytes.
- **Kept whole:** Values are never truncated or split, so nothing brings the output back under the limit.

This isn't a rare edge case. It is a summary the team actually saw in testing.

## The assertion doesn't save the release

The pre-write check (encoded byte length ≤ 1500) is correct. ASCII escaping means byte count equals character count, so it measures the right thing. But it only changes how the step fails, not whether it fails:

- If the assertion trips, the step fails and the release aborts with no retry.
- If it were removed, the harness would reject the oversized stdout, with the same result.

So the plan has a check but no fallback. Any summary like the tested one aborts the release.

## Things that are fine

- Keeping the debug log off stdout is correct, and it doesn't count toward the cap.
- Checking the encoded byte length, rather than character count, before writing is the right method.
- Compact JSON with fixed keys keeps overhead small and predictable.

## Required changes

1. **Size large values to fit, or move them out of stdout.** Options:
   - Write the full summary to a persistent artifact file. Print only a compact JSON pointer to stdout, such as the path, a hash and short key fields.
   - Use a per-value byte budget with explicit truncation markers, e.g. `"…(truncated, sha256=…)"`. This conflicts with "kept whole," so that rule would have to change.
2. **Don't use the debug log as overflow storage.** It is deleted on exit, so anything put there is lost.
3. **Define what happens when the check fails.** Degrade to the pointer form instead of failing the step. Keep the hard assertion only as a final safety net.
4. **Add a test with the observed worst case** (three values of ~700 bytes, all keys at 12 bytes) to confirm stdout stays at or under 1500 bytes.

VERDICT: NO_GO