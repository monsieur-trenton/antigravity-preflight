# Review: Nightly Export Migration to exports-prod/nightly/

## The main risk: svc-export's write access has never been tested

This is the one item that needs action before 01:00.

- Nobody has written to `exports-prod/nightly/` using svc-export's credentials.
- Nobody has checked its permissions on that bucket.
- The export runs once and is not retried.
- If the export fails, the 09:00 release is blocked and nothing ships that day.

If svc-export lacks write permission, the first sign will be a failed export overnight. No retry will follow, and the release will be lost.

Nothing in the plan shows the permission is missing, so I can't say the plan will fail. But its first real test happens in the one window where a failure costs a day's release.

## Required changes (all doable before tonight)

1. **Do a test write with svc-export's own credentials.** Write a small object to `exports-prod/nightly/`, then read it back. Use the account itself (impersonation or its key), not an admin account, since admin access tells you nothing about svc-export.
2. **Read the bucket policy in the infrastructure repo.** Confirm svc-export has the needed permissions on the `nightly/` prefix. For a single 30 GB object this may include multipart upload actions, not just a basic put. Also check for deny statements, encryption-key permissions, or prefix conditions that could block the write. No policy change is pending, so if access is missing, the fix has to be made today.
3. **Plan a fallback for tonight only.** Either keep the old shared-drive export as a backup, or have someone on call who can rerun the export by hand before 09:00 if it fails. The no-retry design makes this worth having for the first run.
4. **Optional:** add an alert for export failure or a missing object, so a failure is found before 09:00 rather than at it.

## Items that are fine as stated

- **Lifecycle rule:** Objects are deleted after 7 days, and the pipeline reads each export within 8 hours. That leaves a wide margin.
- **Object size:** About 30 GB against a 5 TB per-object limit is no concern. The client just needs to use multipart upload, as most SDKs do automatically at this size, which ties back to the permission check in item 2.
- **No pending bucket policy change:** This means no surprise change will break access tonight. It also means no fix is on the way if access is wrong.

## Summary

The design is sound, but the one step everything depends on, svc-export writing to the new bucket, is unproven. A test write today plus a fallback for the first run removes most of the risk. If the test write fails, this becomes a NO_GO until the bucket policy is fixed.

VERDICT: GO_WITH_CHANGES