**Rationale**

Q01 asks whether the snapshot's own text supports a blocker. It does not. It does support a significant risk that should be fixed before tonight's run.

- **Line 4 (main risk):** The export moves to a new destination tonight (line 1). However, svc-export has never written to exports-prod/nightly/, and its permissions on that bucket have not been checked. The snapshot does not say the permissions are missing or wrong. It only says nobody has checked. Missing evidence is not a proven defect, so this is a RISK, not a BLOCKER. Its evidence label is UNVERIFIED because the snapshot does not show whether the write will succeed or fail.
- **Lines 2 and 3 (impact):** The export runs once and is not retried if it fails. If it has not completed, the 09:00 release is blocked for the day. So a permission failure would mean losing that day's release, with no automatic recovery.
- **Line 5 (context):** No bucket policy change is pending or scheduled before tonight's run. If a permission gap exists, nothing already planned would close it. This does not show that a gap exists.
- **Lines 6 and 7:** No conflicts. Objects are kept for 7 days and the pipeline reads each export within 8 hours. The 30 GB export is well under the stated 5 TB per-object limit. These lines are consistent with each other and with the rest of the plan.

**Recommended change:** Before 01:00, run a test write to exports-prod/nightly/ using svc-export's own credentials, or review its effective permissions on that bucket. Alternatively, arrange a manual rerun or fallback before the 09:00 release.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: CHANGES_RECOMMENDED
FINDING: RISK | UNVERIFIED | 4 | No write to exports-prod/nightly/ has been attempted with svc-export's own credentials, and its permissions on that bucket have not been checked.
FINDING: NOTE | VERIFIED | 2 | The export runs once at 01:00 under the service account svc-export, and a failed run is not retried.
FINDING: NOTE | VERIFIED | 3 | The 09:00 release pipeline uses tonight's export as its input, and if the export has not completed, that morning's release is blocked and does not ship that day.