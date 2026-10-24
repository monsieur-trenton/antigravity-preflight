# Review: Date-Parsing Library Upgrade (2.8 → 3.0) for the Billing Service

The plan's main constraint is that none of the 14 existing callers may change behaviour, because wrong due dates would go out to customers at 06:00 and can't be recalled. The plan addresses each risk directly.

## How each risk is handled

1. **Behavioural equivalence for the 14 callers.** All 14 were run on 3.0 against last month's complete recorded inputs. Those inputs cover every date format the callers supply. The output was byte-for-byte identical to 2.8. That is direct evidence the constraint holds, not an inference from changelogs.

2. **Runtime prerequisite.** Version 3.0 needs runtime 11 or newer. Every billing host already runs 12, so no host-level change is needed and nothing will fail at load time.

3. **Other consumers of 2.8.** The only other user is the archived reporting tool. It has its own pinned 2.8 copy in a separate directory, isn't one of the 14 callers, and isn't redeployed. The upgrade doesn't touch it, so it can't break or pick up 3.0 by accident.

4. **Timing.** The change ships in the routine 14:00 deploy, 12 hours before the 02:00 invoice run. Any deploy-time problem would show up and could be rolled back long before invoices are produced.

## Assessment

The stated rule (no behaviour change in any of the 14 callers) is backed by an exhaustive, format-complete replay with identical output. The two side risks, the runtime requirement and the pinned 2.8 consumer, are both already resolved. The deploy schedule leaves plenty of room to recover before anything irreversible happens. I don't see a gap that would make the plan fail or break its own rule, and nothing needs to change.

VERDICT: GO