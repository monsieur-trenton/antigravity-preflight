# Review: Nightly Customer Export Move to exports-prod/nightly/

**The plan is plausible, but tonight's run has no margin for error.** There is one attempt with no retry, and a failure blocks the 09:00 release, so nothing ships that day. The evidence that the new path works is thinner than it looks.

## What holds up

- **Write permission:** svc-export, using its own credentials, has written to `exports-prod/nightly/`. The admin deleting the object afterwards doesn't affect that result.
- **Bucket policy:** It is managed in the infrastructure repo with no pending changes, so the permission shouldn't change before 01:00.
- **Lifecycle rule:** Objects expire after 7 days, and the pipeline consumes each export within 8 hours. The rule has no effect on the release.
- **Size limit:** About 30 GB is far below the stated 5 TB per-object limit.

## Gaps to address

1. **The 1 KB test doesn't exercise the real upload path.** A 30 GB object can't be sent as one request on most object stores (S3 caps a single PUT at 5 GB). It will go up as a multipart upload. That path can need permissions or configuration the small test never touched:
   - multipart create, complete, and abort actions;
   - with SSE-KMS, `kms:Decrypt` as well as `kms:GenerateDataKey`;
   - bucket-policy conditions on encryption headers.

   The 5 TB limit only shows the object fits. It doesn't show the upload will succeed. Before 01:00, run a full-size or at least multi-GB upload as svc-export, using the same client and settings as the export job.

2. **The plan doesn't confirm the release pipeline reads from the new location.** It covers where the export is written, not where the 09:00 pipeline reads. Confirm the pipeline's input path now points to `exports-prod/nightly/`. Also confirm the pipeline's identity can read from that prefix, and that any object-naming or "latest file" logic works there.

3. **There is no recovery path for a failed run.** With no retry, add:
   - an alert on export failure, or on the object being missing well before 09:00 (for example, by 03:00);
   - a documented manual re-run procedure and a named on-call owner;
   - a fallback, such as temporarily writing to the old shared drive as well, or a quick way to point the job back to it.

   The export window and runtime are also unstated. Confirm a 30 GB upload, plus a possible manual re-run, fits between 01:00 and 09:00.

4. **Minor:** Check that no other lifecycle or cleanup rule targets `nightly/`, and that the old shared-drive consumers have been retired or notified.

None of these gaps shows the plan will fail as written. Together they leave a single unrehearsed attempt guarding the day's release, so the plan should be strengthened before tonight.

VERDICT: GO_WITH_CHANGES