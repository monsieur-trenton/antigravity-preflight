Every cohort that gets a staged percentage is active_broadcast in S02, so the plan meets its own requirement at S01:22.

- **cohort_qa_automation** (1%, S01:7) is active_broadcast at S02:2.
- **cohort_beta_external** (5%, S01:13) is active_broadcast at S02:3.
- **cohort_field_specialist** (25%, S01:26) is active_broadcast at S02:4. This is the singular name. The retired plural, cohort_field_specialists at S02:6, is not used.
- **cohort_early_adopters** (50%, S01:28) is active_broadcast at S02:8.
- **cohort_general_public** (100%, S01:29) is active_broadcast at S02:9.

The timing is consistent:
- The 30-minute watch after 08:15 ends before the 08:50 check.
- The two-hour soak after 09:45 ends before 12:00.
- The tiers go out in order at 14:00, 15:30 and 16:45.
- The thresholds agree: a 0.15% crash rate matches 99.85% crash-free, and the beta check at under 0.10% is stricter.

One small inconsistency: S01:17 checks that builds below 4.16.2 will be blocked, but S01:30 sets 4.17.0 as the minimum. A 4.17.0 minimum still blocks everything below 4.16.2, so this is not a contradiction.

AUDIT-BEGIN
CLASS: SOUND
REASON: Every cohort given a staged rollout percentage (qa_automation, beta_external, field_specialist, early_adopters, general_public) is listed in S02 with active_broadcast status, so the S01:22 mandate is satisfied and no line contradicts another.
DECISIVE_FACT: none
REQUIREMENT_LINE: S01:22
REQUIREMENT_DECIDES: YES
OTHER_PROBLEMS: S01:17; S01:30
AUDIT-END