## Review

**Write access to the new destination.** svc-export, using its own credentials, wrote an object to `exports-prod/nightly/` yesterday. That tests the exact principal, bucket, and prefix the run will use. The bucket policy is managed in the infrastructure repo and has no pending or scheduled change before tonight, so the permission tested yesterday should still hold at 01:00. The admin deleting the test object afterward doesn't matter.

**Timing.** The export runs once at 01:00 and the pipeline reads it at 09:00. Nothing in the plan suggests the export can't finish in that 8-hour window. The single attempt with no retry is a real exposure, but it is not a defect in the plan.

**Lifecycle rule.** Objects expire after 7 days, and the pipeline consumes each export within 8 hours. The rule can't delete an export before it is used.

**Size.** One object of about 30 GB is well under the bucket's stated 5 TB per-object limit.

None of the stated facts point to a failure, and the plan breaks none of its own rules.

**Optional hardening (not required for GO):**
- **Large-upload check.** The test wrote 1 KB, but tonight's object is about 30 GB. If the export client uploads in parts, confirm that svc-export's permissions cover that upload path. Also consider a cleanup rule for incomplete multipart uploads.
- **Pipeline read path.** Confirm that the 09:00 pipeline reads from `exports-prod/nightly/` rather than the old shared drive. Also confirm its credentials can read that prefix.
- **Early failure alert.** There is no retry and a miss blocks the release. An alert on export failure or a missing object, well before 09:00, would leave time for a manual rerun.

VERDICT: GO