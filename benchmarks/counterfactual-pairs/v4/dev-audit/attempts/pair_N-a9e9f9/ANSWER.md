Plan Y needs a change; Plan X can be carried out as written.

S01:42 in both plans says the secondary cluster may only be promoted if there are zero orphaned records across the 140 million settlement rows. Promoting with orphans would corrupt the downstream ledger reconciliation tables. The promotion at S01:50 in X and S01:48 in Y is irreversible.

- **Plan X** meets the condition. S01:45 runs the integrity query over all 140 million `settlement_entries` rows against `settlement_batches`. S01:46 reports zero orphans before promotion. One small point: a three-minute scan starting after 02:55 would end after the 02:57 audit-log confirmation in S01:47. That step can run in parallel, so it does not block the plan.
- **Plan Y** is identical to X except that X's S01:45–46 are removed. The later lines are renumbered but otherwise unchanged. Y keeps the condition at S01:42 but never checks it before the irreversible promotion at S01:48.

AUDIT-BEGIN
NEEDS_CHANGE: Y
WHY: Plan Y states that promotion requires zero orphaned settlement records but never runs the integrity check before the irreversible promotion at S01:48.
ONE_EDIT: YES
DIFFERENCE: Plan Y is Plan X with lines S01:45–46 deleted (the full integrity query over settlement_entries and its zero-orphan result), and nothing else changed.
AUDIT-END