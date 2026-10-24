# Review: Nightly Customer Export Move to exports-prod/nightly/

This plan holds up. Each risk that could block the 09:00 release has a stated control.

| Risk | Status |
|---|---|
| **Write access** | Covered. Yesterday's 1 KB write used svc-export's own credentials against the exact bucket and prefix, and it succeeded. That tests the real identity, not an approximation. |
| **Access changing before tonight** | Covered. The bucket policy lives in the infrastructure repo, and no change is pending or scheduled before the run. Yesterday's result should still hold at 01:00. |
| **Test object getting in the way** | Covered. An administrator removed it, so it can't be mistaken for tonight's output or conflict with it. |
| **Retention** | Covered. Objects are deleted after 7 days, and the pipeline reads within 8 hours. That leaves a large margin. |
| **Object size** | Covered. About 30 GB is far under the stated 5 TB per-object limit. |
| **No retry, 09:00 dependency** | Accepted. A failed run blocks that day's release. The plan states this consequence openly, and nothing above points to a likely failure. |

None of the plan's facts conflict with each other or with its own rules. Nothing as written will fail.

## Optional hardening (not required for GO)

- **Upload method for a single 30 GB object.** Many object stores cap a single upload request well below the per-object limit. S3, for example, allows 5 GB per single PUT. The 1 KB test wouldn't reveal this. If the export tool doesn't already use multipart or resumable uploads, confirm that it does. With no retry, this is the cheapest thing to double-check.
- **Reader side.** The plan says the pipeline uses tonight's export. You could also confirm that its input path points to exports-prod/nightly/ rather than the old shared drive, and that its identity can read the bucket.
- **Early signal.** An alert on 01:00 export failure would at least give someone notice before 09:00, even though nothing retries automatically.

VERDICT: GO