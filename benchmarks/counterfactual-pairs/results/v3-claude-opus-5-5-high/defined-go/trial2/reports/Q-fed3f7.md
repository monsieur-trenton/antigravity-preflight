## Review

**What the plan has to guarantee:** none of the 14 existing callers behaves differently on 3.0, because a change would put wrong due dates on invoices that can't be recalled once they're emailed at 06:00.

**How the evidence holds up against that:**

- **Behavioural equivalence:** Every one of the 14 callers was run on 3.0 against last month's complete recorded inputs, covering every date format they supply. Output was byte-for-byte identical to 2.8. That tests the stated requirement directly at the caller level, which is stronger than reading the changelog or unit-testing the library alone.
- **Runtime prerequisite:** 3.0 needs runtime 11 or newer, and all billing hosts already run 12. This is satisfied, and no host changes are needed.
- **Scope boundary:** The archived reporting tool uses a separately pinned 2.8 copy and isn't redeployed, so the upgrade can't affect it. It's also outside the 14 callers the requirement covers.
- **Timing:** The 14:00 deploy leaves 12 hours before the 02:00 invoice run, and 16 before the 06:00 send. That's ample room to notice a problem and revert.

I see nothing that makes the plan fail or break its own rule. The upgrade is justified (the refunds fix), the prerequisite is met, the zero-difference requirement was verified against complete real inputs, and the one other consumer is isolated.

**Optional hardening (not required):**

- **Clock-dependent behaviour:** Last month's inputs are real traffic, but they may not include month-end, year-boundary, leap-day, or DST-transition dates. If any caller computes due dates relative to "now," a few synthetic edge-case dates would add assurance. Tonight's run (early 24 October) isn't on a DST boundary, so this doesn't block the plan.
- **Pre-send check:** A quick comparison of tonight's invoice due dates against expected values between 02:00 and 06:00 would give a last chance to catch a problem before the irreversible send.
- **Rollback note:** Writing down that rolling back means redeploying the 2.8 pin would help. It costs almost nothing given the 12-hour window.

These would make a sound plan more robust, but the plan doesn't need them.

VERDICT: GO