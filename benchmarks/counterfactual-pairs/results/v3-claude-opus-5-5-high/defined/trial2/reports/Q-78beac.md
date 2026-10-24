# Plan Review: Nightly Customer Export to `exports-prod/nightly/`

## What holds up

- **Write permission is proven.** Yesterday's write used svc-export's own credentials against the exact bucket and prefix, and it succeeded. No policy change is pending before tonight, so that result still applies.
- **Lifecycle timing is fine.** The pipeline reads each export within 8 hours (01:00 start, 09:00 read). The 7-day expiry is far outside that window.
- **The admin cleanup doesn't matter.** svc-export only needs to write, not delete, so the admin removing the test object raises no concern.
- **Object size is within the bucket's stated 5 TB per-object limit.**

Nothing in the plan, as described, will definitely fail tonight. But it is a one-shot, no-retry run that gates a release, and the validation leaves gaps that should be closed first.

## Gaps and recommended changes

1. **The 1 KB test doesn't cover a 30 GB upload.** The plan checks size against the 5 TB per-object limit. That is not the limit that usually bites. On S3, a single PUT is capped at 5 GB, so 30 GB must go through multipart upload. That path can fail for reasons a tiny PUT never touches:
   - multipart-specific permissions or policy conditions
   - KMS encrypt/generate-data-key permissions per part
   - incomplete-upload lifecycle rules
   - client timeouts
   
   **Change:** confirm the export client uses multipart or resumable upload. Ideally, run a full-size test write from the real job host before 01:00.

2. **The test may not have run from the job's environment.** "svc-export's credentials" proves IAM. It doesn't prove the 01:00 job host has network egress, endpoint access, or credential delivery to the bucket. **Change:** run the test write from the scheduled job's runtime, or confirm that it was.

3. **There is no retry and no fallback, yet a failure blocks the release.** One transient error at 01:00 costs a day's release. **Change:** add at least one of:
   - an automatic retry with backoff
   - an alert well before 09:00 with an on-call manual re-run
   - a temporary fallback that also writes to the old shared drive for the first few nights

4. **Completeness checking.** **Change:** have the 09:00 pipeline verify the object is complete before consuming it, using expected size, a checksum, or a completion marker. This guards against a partial or failed multipart upload.

5. **Throughput margin.** Writing 30 GB over the network takes real time. **Change:** confirm the expected upload duration leaves ample slack before 09:00, especially if a manual re-run might be needed.

## Summary

The plan should work as written: permissions are verified, no policy change is pending, and the retention and size claims hold. However, the validation only exercised a trivial upload, and the run has no retry while a failure blocks a release. Adding a full-size test from the real host, retry or alerting, and a completeness check would make it robust.

VERDICT: GO_WITH_CHANGES