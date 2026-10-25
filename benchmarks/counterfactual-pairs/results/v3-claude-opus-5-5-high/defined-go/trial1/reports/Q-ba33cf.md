# Review: Date-Parsing Library Upgrade (2.8 → 3.0) in the Billing Service

**The plan holds up.** Each risk to its rule (the 14 existing callers must behave exactly as today) is addressed with evidence.

## Checks against the rule

1. **Caller behaviour.** All 14 callers were replayed against 3.0 using last month's full recorded inputs. Those inputs cover every date format the callers pass, and the outputs matched 2.8 byte for byte. This directly tests the stated rule, not a proxy for it.
2. **Runtime compatibility.** Version 3.0 needs runtime 11 or later. Every billing host runs 12, so the upgrade won't fail to load.
3. **Archived reporting tool.** It keeps its own pinned 2.8 copy in a separate directory. It isn't one of the 14 callers and isn't redeployed, so the upgrade doesn't touch it and it doesn't affect the rule.
4. **Timing.** The 14:00 deploy leaves 12 hours before the 02:00 invoice run. That is enough time to notice a broken deploy and roll back before any invoices are produced.

I found no step that would fail and no point where the plan breaks its own rule.

## Optional hardening (not required)

- **Pre-run canary.** Before 02:00, run a dry invoice batch on 3.0 and diff it against a 2.8 dry run. This catches date values that don't appear in last month's data, such as month-end, leap-day or DST boundaries specific to tonight.
- **Rollback trigger.** Agree in advance who can revert to 2.8, and by what time, if anything looks wrong before the run.
- **Dependency lock.** Confirm the lockfile pins exactly 3.0, so a later patch release doesn't slip in.

These would make the plan more robust, but it works as written.

VERDICT: GO