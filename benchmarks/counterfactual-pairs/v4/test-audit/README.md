# Blind audit of the test corpus (interim record)

268 calls to Claude Opus 5.5 through the Claude CLI on the 184-case sealed test corpus (manifest `a9ec80f2…f8b3a`, the one rebuilt from the authoring bundle), run by the owner's orchestrator at commit `4b8b6ef` on 2026-10-28: $14.80, no safety stops, every call served `claude-opus-5-5`. Same auditor and caveats as [the dev audit](../dev-audit/README.md). **The case text is sealed: the ledgers here are redacted (each free-text answer field replaced by its SHA-256), and no attempt directory is committed.**

- [audit-answers-redacted.jsonl](audit-answers-redacted.jsonl) is the ledger as run; six member answers were recorded as technical stops (`UNPARSEABLE_ANSWER:BAD_REFS`: commentary in parentheses after a reference). [audit-answers-lenient-redacted.jsonl](audit-answers-lenient-redacted.jsonl) holds those six re-read under the one stated relaxation of `reparse_lenient.py` (held answer hash-checked, parenthetical commentary dropped, nothing else), which replaces the same calls in the report.
- [audit-report.json](audit-report.json) reads the two ledgers against the oracle: **80 pairs, 14 pass, 40 pass with lines to read, 26 go to review; class recovered for 145 of 160 members; first-pass agreement 54 of 80 pairs.**

The reading of the 26 review pairs and the decision on them follow in a later commit.
