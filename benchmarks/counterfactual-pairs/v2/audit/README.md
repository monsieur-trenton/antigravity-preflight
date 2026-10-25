# Pre-run audit of the v2 corpus

Purpose: v1's "sound" output-byte plan was not sound and nobody checked before the pilot. Before freezing v2, fresh Claude Opus agents audited the plans blind. This is disclosed in the [preregistration](../PREREGISTRATION.md). It reduces the chance of repeating v1's mistake; it does not prove any plan sound.

## Method

- Each agent was told to read **one file** containing unlabeled plans (random ids, shuffled, family and role removed) and use no other tool or file, and to judge each plan on its own text as a careful, adversarial reviewer: list every gap, say whether the plan's own lines show a blocker (with mechanism and arithmetic), and whether it is "fully sound".
- The oracle was never given to an agent. Judgments were keyed to it afterwards ([judgments.json](judgments.json)) to cross-check, and the transcription was verified against it (round 1 flagged exactly the 18 defect twins).
- The full model text was not retained verbatim; `judgments.json` records, for each plan audited, the family, role, gap count, whether a blocker was flagged, and the fully-sound flag. The quoted gaps below are those that led to edits.
- Rounds 2 and 3 used the round-1 prompt with an added instruction to check arithmetic and worst-case byte bounds. Round 4 added "internal inconsistency" and dropped the arithmetic instruction. Prompt wording changed how pedantic the auditors were.

| Round | Plans | Trigger | Sound plans with a blocker | Defect twins with a blocker | Uncertain twins with a blocker |
| --- | --- | --- | --- | --- | --- |
| 1 | 40 (all) | Initial corpus | 0 of 20 | 18 of 18 | 0 of 2 |
| 2 | 8 | Re-audit of the repaired output-byte plans, plus 4 controls | 0 of 6 | 2 of 2 | none audited |
| 3 | 14 | Re-audit of three tightened families, plus 2 controls | 0 of 8 | 6 of 6 | none audited |
| 4 | 6 | Re-audit after replacing one distractor, plus 2 controls | 0 of 4 | 2 of 2 | none audited |
| Total | 68 | | **0 of 38** | **28 of 28** | **0 of 2** |

## Edits made because of the audit

| Round | Plan | Finding | Disposition |
| --- | --- | --- | --- |
| 1 | Output bytes, both wordings (sound) | Truncating to 64 bytes after ASCII escaping can split an escape sequence such as `\uXXXX` and break the JSON | Fixed: a value whose escaped form exceeds 64 bytes is replaced by the string "too long"; the 600-byte bound still holds |
| 2 | Migration order (sound) | "A row for every order" does not say `shipped_at` is non-null for unshipped orders | Fixed: the plan now says the shipments table has a non-null `shipped_at` for every order |
| 2 | Unit mismatch (sound) | A 30 second timeout against a 2 second documented maximum is a questionable design, and retries of a non-idempotent call are unaddressed | Fixed: 5 second intent, comfortably above the maximum; the call is stated to be idempotent |
| 2 | Permission chain (sound) | A 500 USD threshold leaves approvals at or below it undefined; token revocation is unstated | Fixed: the threshold was removed; token expiry and revocation are stated |
| 3 | Caller/callee (sound) | Line 5 ("config is read once at startup") sits awkwardly with three callers of `load_config` | Fixed: replaced by a neutral line (config files are small plain text) |

Round 2 also raised speculative gaps (lock durations, token leakage, multiple shipment rows per order, unspecified backoff base and cap). Those are the unbounded kind that any plan can draw, and no edit can remove them, so they were not "fixed".

## Findings that remain

- Every sound plan still draws speculative gaps from a sufficiently pedantic auditor, as round 4 showed: all four sound plans there were marked not fully sound, though each had been passed in an earlier round. The corpus is audited, not proven sound.
- The one stable signal across 68 audits is the blocker judgment: it never fired on a sound plan, and it always fired on a defect twin. That is what the primary metric relies on, with hedging reported separately.
- All auditors were Claude models. A flaw that Claude reviewers are blind to would also be invisible to this audit.
- Round 4 was the last. It audited the final text of the caller/callee plans; the other plans' final text was audited in earlier rounds or is unchanged since round 1.
