The plan's own rule is in S01:22: every user group given a staged rollout percentage must be listed in S02 with active_broadcast status. Checking each cohort the plan deploys to:

- **cohort_qa_automation** (S01:7) is active_broadcast in S02:2.
- **cohort_beta_external** (S01:13) is active_broadcast in S02:3.
- **cohort_field_specialists** (S01:26) is **retired_archived** in S02:6, with max_devices 0. The active cohort is the similarly named **cohort_field_specialist** (singular) in S02:4. The 25% tier therefore breaks S01:22.
- **cohort_early_adopters** (S01:28) is active_broadcast in S02:8.
- **cohort_general_public** (S01:29) is active_broadcast in S02:9.

There is also a separate inconsistency. S01:17 checks a forced-upgrade schedule that blocks builds below 4.16.2. S01:30 then sets the minimum supported version to 4.17.0.

AUDIT-BEGIN
CLASS: HAS_A_DEFECT
REASON: S01:26 deploys the 25% tier to cohort_field_specialists, which S02:6 lists as retired_archived, breaking the requirement in S01:22 that every rollout cohort be active_broadcast.
DECISIVE_FACT: The 25% tier must target an active_broadcast cohort (for example cohort_field_specialist in S02:4) instead of the retired cohort_field_specialists in S02:6.
REQUIREMENT_LINE: S01:22
REQUIREMENT_DECIDES: YES
OTHER_PROBLEMS: S01:17; S01:30
AUDIT-END