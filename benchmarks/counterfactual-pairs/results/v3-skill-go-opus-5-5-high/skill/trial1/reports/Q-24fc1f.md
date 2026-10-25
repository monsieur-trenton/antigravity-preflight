**Rationale**

The snapshot contains **no blocker that its own text supports**. It does contain one material unverified risk.

- **Line 4 (main risk):** svc-export has never written to exports-prod/nightly/ with its own credentials, and its permissions on that bucket are unchecked. Lines 2, 3 and 5 make the impact severe:
  - The 01:00 run is not retried (line 2).
  - A missing export blocks the 09:00 release, which then does not ship that day (line 3).
  - No policy change is pending to fix permissions before tonight (line 5).
  - The snapshot does not say the permissions are wrong, only that they are unverified. This is missing evidence, not a proven defect, so it is a RISK, not a BLOCKER.
  - Recommended change: before tonight, run a test write and delete under nightly/ using svc-export's own credentials, or review the bucket policy in the infrastructure repository.
- **Line 2 (note):** The no-retry policy means nothing recovers a single failure, such as a permission denial, before 09:00. This adds to the line 4 risk.
- **Line 6:** This is internally consistent. Reading within 8 hours falls well inside the 7-day lifecycle window, so it is not a finding.
- **Line 7:** This is internally consistent. 30 GB is far below the stated 5 TB per-object limit, so it is not a finding.

All seven lines were reviewed.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: CHANGES_RECOMMENDED
FINDING: RISK | UNVERIFIED | 4 | No write to exports-prod/nightly/ has been attempted with svc-export's own credentials, and its permissions on that bucket have not been checked.
FINDING: NOTE | VERIFIED | 2 | The export runs once at 01:00 under the service account svc-export, and a failed run is not retried.