# Review: build step metadata summary vs. 1500-byte stdout cap

## Blocking issue: the summary already exceeds the cap in testing

The plan states three facts that together guarantee failure:

1. **The cap is hard.** Stdout is limited to 1500 bytes per command. Going over fails the step and aborts the release, with no retry.
2. **Values are kept whole.** Nothing truncates, elides, or splits them.
3. **Testing produced a summary over the limit.** Three values of about 700 bytes each come to about 2100 bytes of values alone. Six quoted keys of up to 12 bytes each, plus quotes, colons, commas, and braces, add roughly 100–130 bytes more.

That summary would be about 2200 bytes, roughly 700 bytes over the cap.

The pre-write assertion does not solve this. It only detects the overflow. When it fires, the step still fails and the release still aborts with no retry. The assertion turns a harness-enforced failure into a self-reported one, but the result is the same. The plan as written fails on input it has already been tested with.

## Required changes (any one approach, applied consistently)

- **Bound the values.** Set a per-value byte budget so the worst case fits: 6 keys and all JSON overhead plus 6 maximum-size values must be at most 1500. Truncate with a marker, and record the original length or hash so the truncation is visible. This drops the "kept whole" property, so the plan should say so explicitly.
- **Move large values off stdout.** Write the full summary to a durable artifact, not the temp debug log, which is deleted on exit. Then emit only a compact pointer or digest on stdout, which stays well under the cap.
- **Make the assertion degrade, not abort.** If the encoded size is over 1500, fall back to a reduced summary (truncated values, or keys plus lengths and hashes) instead of failing.

## Smaller points

- **Measure what the harness measures.** The assertion should check the exact bytes written to stdout, including any trailing newline and in the same encoding. ASCII escaping can expand values; `\uXXXX` turns 1 character into 6 bytes. So measure after escaping, not before.
- **Debug log.** Not counting it toward the cap is fine, as long as nothing in the step (logging libraries, subprocesses) writes to stdout by default. Consider routing stray output to stderr.

## Summary

The approach is reasonable, but its constraints contradict each other. "Values kept whole" combined with observed values of about 700 bytes each cannot fit under a hard 1500-byte cap, and the assertion only changes how the failure is reported.

VERDICT: NO_GO