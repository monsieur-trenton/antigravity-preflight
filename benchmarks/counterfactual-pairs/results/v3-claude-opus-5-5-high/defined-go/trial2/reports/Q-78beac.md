# Review: Nightly Export to exports-prod/nightly/

## Assessment

None of the plan's stated facts point to a failure tonight.

- **Write access is verified.** Yesterday's test wrote to the exact bucket and prefix (`exports-prod/nightly/`) using svc-export's own credentials, so it tested the real identity and destination. An administrator then removed the test object, so it won't be mistaken for an export.
- **Permissions are stable.** The bucket policy lives in the infrastructure repository, and no change is pending or scheduled before tonight's 01:00 run. Yesterday's successful write should therefore still hold.
- **The lifecycle rule is harmless.** Objects are deleted after 7 days, and the pipeline reads each export within 8 hours (01:00 to 09:00). The export is long gone from the pipeline's point of view before deletion matters.
- **Object size is within limits.** At about 30 GB, the export is far below the bucket's stated 5 TB per-object limit.
- **The failure behaviour is stated, not hidden.** There is no retry, and a failed or late export blocks that day's release. That is a business risk, but it is a known consequence the plan spells out, not a flaw that makes it fail.

## Optional suggestions (not required)

These would make the plan more robust but are not changes it needs:

1. **Test at full size.** The test object was 1 KB, but the real export is 30 GB. Most clients upload objects that large in parts (multipart upload) rather than in one request. If your client does, a test with a multi-GB object would cover that path. Nothing in the plan suggests it will fail, so this is extra assurance only.
2. **Add early alerting.** Since a failed run isn't retried and blocks the release, an alert on failure (or on a missing object by around 03:00) would leave time for a manual rerun before 09:00.
3. **Keep the old shared drive as a fallback.** Leaving the previous target available for the first night or two would give you a quick rollback option.

VERDICT: GO