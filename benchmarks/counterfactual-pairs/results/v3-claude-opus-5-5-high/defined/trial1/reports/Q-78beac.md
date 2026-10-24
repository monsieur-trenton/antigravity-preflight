# Review: Nightly Export Move to `exports-prod/nightly/`

## What holds up

- **Write access is verified.** svc-export wrote to the exact bucket and prefix with its own credentials. The bucket policy has no pending changes before tonight, so that result should still apply at 01:00.
- **Lifecycle timing is fine.** The pipeline reads the export about 8 hours after it is written (01:00 to 09:00), and objects are deleted after 7 days. There is plenty of margin.
- **Object size is within the stated limit.** About 30 GB is far below the 5 TB per-object maximum.

Nothing in the plan shows it will fail tonight. Some of the evidence, though, covers less than it appears to.

## Gaps to close

1. **The write test doesn't cover the real upload.** A 1 KB object proves the account can write, but not that a 30 GB object will upload. Many object stores cap a single upload request well below the per-object limit. S3, for example, caps a single PUT at 5 GB, so larger objects need multipart upload. Multipart can also need extra permissions, such as aborting uploads or listing parts.
   - **Fix:** Confirm the export tool uses multipart or chunked upload for large objects, and that svc-export has any extra permissions this needs.
   - **Better:** Do a test write with a multi-GB object before 01:00.

2. **The release pipeline's read side isn't addressed.** The plan covers writing, but not reading. It doesn't confirm:
   - that the 09:00 pipeline is set to read from `exports-prod/nightly/` instead of the shared drive;
   - that the pipeline's identity has read and list access to that prefix;
   - how the pipeline finds tonight's object (exact key, naming scheme, or "latest").
   - **Fix:** Verify these points, ideally with a test read using the pipeline's own credentials.

3. **There is no safety net for one run, no retry, and a hard release dependency.** If anything new fails tonight (upload size, credentials, network), the release is lost for the day and nobody may notice until 09:00.
   - **Fix:** Add one or more of the following:
     - an alert on export failure or a missing object;
     - a manual rerun procedure with an owner on call;
     - keeping the shared-drive output for the first night or two as a fallback;
     - allowing one retry for the first run.

4. **Completion signal (minor).** Make sure the pipeline can tell a finished 30 GB object from a partial one. Multipart uploads usually show up only after completion, but a marker object or a check on the expected size or checksum removes the doubt.

## Summary

The plan is sound as stated, and nothing in it is shown to fail. However, the write test didn't exercise a large upload, the read side is unverified, and one failure costs a day's release. Close these gaps before 01:00.

VERDICT: GO_WITH_CHANGES