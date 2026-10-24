# Review: Nightly Customer Export Migration to exports-prod

## Assessment

**Nothing in the plan clearly fails, and it breaks none of its own rules.**

- **Permissions:** A write to `exports-prod/nightly/` using svc-export's own credentials succeeded yesterday.
- **Bucket policy:** No change to it is pending before tonight.
- **Lifecycle rule:** Objects are deleted after 7 days. The pipeline reads each export within 8 hours, so there is plenty of margin.
- **Size limit:** About 30 GB is far under the 5 TB per-object limit.

## Gaps worth closing

1. **The test didn't cover the real upload.** A 1 KB write shows the basic permission works. It says little about a single 30 GB object.
   - On S3-style stores, a single PUT tops out around 5 GB. A 30 GB object therefore needs a multipart or resumable upload.
   - That path can involve extra permissions (for example, AbortMultipartUpload), KMS encryption grants, timeouts, or client settings that a 1 KB PUT never touches.
   - Before 01:00, check that the export client is set up for multipart upload. If possible, run a test upload of realistic size as svc-export.

2. **One run with no retry, feeding a hard deadline.** Any temporary error (network, throttling, token expiry partway through upload) blocks the release with no automatic recovery.
   - Add at least one retry, or a resumable upload.
   - Alternatively, assign an on-call person with a written runbook for re-running the export manually.

3. **There is no monitoring or alert between 01:00 and 09:00.** A failure should page someone early enough to re-run the export. Waiting until 09:00 to find out is too late. A 30 GB export plus upload fits easily in 8 hours, so a 01:00 failure can still be recovered if someone hears about it promptly.

4. **There is no fallback.** Decide ahead of time whether the old shared drive stays available tonight as a backup output. Also decide whether the release pipeline can be pointed back at it.

5. **Timing is untested.** Upload speed to the bucket may differ from writes to the shared drive. Confirm the expected end-to-end time well before 09:00.

6. **The pipeline's input needs checking.** Confirm the 09:00 release pipeline has been updated to read from `exports-prod/nightly/`, with the correct object naming and read permissions. The plan describes only the write side.

## Conclusion

The plan should work as written. However, it has no redundancy on a path where one failure costs a full day of releases, and its only test did not exercise the real large-object upload. Validate the multipart path, add alerting, and add a retry or manual re-run procedure before tonight.

VERDICT: GO_WITH_CHANGES