# Review: Nightly Export Move to exports-prod/nightly/

## What the plan establishes

- **Write access is proven, not assumed.** svc-export wrote to the exact destination, `exports-prod/nightly/`, using its own credentials. Because no policy change is pending, that result should still hold tonight.
- **Retention fits the timeline.** The pipeline reads each export within 8 hours, and the lifecycle rule deletes objects after 7 days. That leaves a wide margin.
- **Size is not a concern.** At about 30 GB, the export is far under the 5 TB per-object limit.
- **Timing works.** A 01:00 start leaves 8 hours before the 09:00 release, which is plenty for a 30 GB write.

I see nothing in the plan that fails or contradicts its own claims.

## Optional hardening (not required)

The plan has no retry, and a failed run blocks the release. These checks would lower the chance of a bad morning:

1. **Large-upload path.** The test wrote 1 KB, but a 30 GB object will go up as a multipart upload. If the bucket uses SSE-KMS, multipart also needs `kms:Decrypt` in addition to `kms:GenerateDataKey`. A small write can pass while a large one fails, so a quick check of the bucket's encryption setup would close this gap.
2. **Consumer side.** Confirm that the 09:00 pipeline reads from `exports-prod/nightly/` and not the old shared drive, and that it has read access to the bucket.
3. **Failure visibility.** An alert on export failure, or on the object being missing by around 03:00, would leave time to rerun by hand before 09:00.

None of these is a defect in the plan as written. Each one only makes a working plan more robust.

VERDICT: GO