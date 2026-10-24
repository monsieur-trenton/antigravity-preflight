# Plan Review: Nightly Customer Export to exports-prod

## The main risk: the write path is unverified, and tonight has no safety net

The biggest problem is the combination of four facts the plan states:

1. **svc-export has never written to `exports-prod/nightly/`** with its own credentials, and nobody has checked its permissions on that bucket.
2. **Nothing will fix the permissions before tonight.** No bucket-policy change is pending or scheduled. If access is missing now, it will still be missing at 01:00.
3. **A failed run is not retried.**
4. **A failed export blocks the 09:00 release** for the whole day.

So tonight's run is the first real test of this write path, and if it fails, nothing recovers it. The facts don't show the write *will* fail. svc-export may already have access through an existing grant. But nothing shows it *will* succeed either, and a failure costs a full day's release.

**Required before 01:00:**
- **Test the write as svc-export.** Using svc-export's own credentials, not an admin or personal account, write, read back and delete a small test object under `exports-prod/nightly/`. Also confirm any other actions the export job uses, such as listing, overwriting or multipart operations.
- **Check the bucket policy in the infrastructure repo.** Confirm it grants svc-export what it needs. If it doesn't, either merge the change before tonight or postpone the cutover.
- **Keep a fallback ready.** Keep the old shared-drive path working for tonight, or have someone on call who can re-run the export manually before 09:00. One manual run fits easily in the 8-hour window if it's planned in advance.

## Secondary points

- **30 GB single object.** The 5 TB per-object limit is not the constraint that matters. Many object stores, including S3, cap a *single PUT* at 5 GB, so a 30 GB object usually needs multipart upload. Confirm the export client uses multipart, and that svc-export has the permissions multipart needs, such as initiating, uploading parts and completing the upload. Ideally, make the test write above large enough to use multipart.
- **Lifecycle rule (7 days).** This is fine. The pipeline reads within about 8 hours (01:00 to 09:00), well inside the window. The only effect is that exports older than 7 days can't be re-run or audited. Check whether anyone needs that history.
- **Who reads the bucket.** The plan covers svc-export's write access but not the release pipeline's read access to `exports-prod/nightly/`. Verify that too, since a read failure would block the release in the same way.
- **Detecting failure.** With no retry, someone should be alerted soon after 01:00 if the export fails, not when the release breaks at 09:00.

## Summary

The destination, timing, lifecycle rule and object size all work. The weak point is that tonight's run is the first write with untested credentials, with no retry and a release that depends on it. That is a real chance of a lost release day, but not a certain failure, so the plan can proceed only after the write path is tested and a fallback is in place.

VERDICT: GO_WITH_CHANGES