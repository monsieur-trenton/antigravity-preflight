# Review: build-step metadata summary vs. the 1500-byte stdout cap

**The plan fails on data it has already seen.** The test case you describe can't fit under the cap.

## Size check

- **Values:** 3 × ~700 bytes ≈ 2100 bytes. That alone is already over 1500.
- **Keys and JSON structure:** 6 keys × up to 12 bytes, plus quotes, colons, commas and braces, adds roughly 100 more bytes.
- **Total:** about 2200 bytes or more, against a hard cap of 1500.

Because values are "kept whole," nothing in the plan reduces this size. ASCII escaping only makes it worse: any non-ASCII character becomes `\uXXXX` (6 bytes), so encoded values can grow.

## Why the assertion doesn't help

The pre-write assertion stops the step from emitting more than 1500 bytes. But a failed assertion is still a failed step. Since a failed step "aborts the release without a retry," the result is the same either way: the release aborts. The assertion turns a cap violation into a clearer error, but it doesn't make the step succeed. Nothing in the plan bounds the output size or provides a fallback.

## What's fine

- Moving the debug log to a temp file, outside stdout, is correct and doesn't count toward the cap.
- Asserting on encoded byte length, rather than character count, is the right measurement.
- Compact JSON and short fixed keys are sensible.

## Required changes (any one approach works)

1. **Move large values out of stdout.** Write the full summary to an artifact file, and print only a small pointer (path plus hash) or a bounded subset on stdout.
2. **Cap each value's size.** Truncate or summarize each value with an explicit marker such as `"truncated": true` and the original length. Budget so that the worst-case total stays under 1500 with margin, for example about 200 bytes per value plus structure.
3. **Store large values by reference.** Keep a hash or ID on stdout and put the full content in the artifact.

Also, add a test that uses the observed 3 × 700-byte case, plus a worst-case escaping case, so the assertion is exercised in CI and not discovered at release time.

VERDICT: NO_GO