# Review: nightly customer export moving to exports-prod/nightly/

**Nothing stated in the plan makes it fail.** It contains no contradiction, and it breaks none of its own rules.

## Points that hold up

- **Lifecycle rule:** Objects are deleted after 7 days, and the pipeline reads each export within 8 hours. The rule cannot remove an export before the release uses it.
- **Object size:** About 30 GB is far below the 5 TB per-object limit.
- **Bucket policy:** No policy change is pending or scheduled before tonight, so nothing will change permissions unexpectedly before 01:00.
- **Timing:** The export runs at 01:00 and the release at 09:00. That leaves an 8-hour window, which fits the stated read pattern.

## Main risk: svc-export's write access is unverified

No one has tried writing to `exports-prod/nightly/` with svc-export's own credentials, and its permissions on the bucket haven't been checked. Two facts in the plan make this risky:

- A failed run is not retried.
- If the export hasn't completed, the 09:00 release is blocked for the whole day.

So a missing permission would cost a day's release, and you would probably only find out in the morning. The plan doesn't say permissions are missing, so this isn't a certain failure. It is an untested assumption, and the cost of being wrong is high.

## Recommended before tonight (optional, but cheap and worth doing)

1. **Test the credentials now.** Under svc-export's own credentials, write a small test object to `exports-prod/nightly/`, then read it back and delete it. Because a 30 GB single object is likely a multipart upload, also check that svc-export has the permissions multipart uploads need (initiate, upload part, complete, abort).
2. **Check the reader's access.** Confirm the 09:00 pipeline's identity can read from `exports-prod/nightly/`.
3. **Add an alert.** Set up an alert on export failure or a missing object, for example by about 02:00. Then someone can rerun the export manually before 09:00 instead of losing the release.
4. **Plan a fallback.** Decide whether the old shared drive stays available as a fallback for the first night.

These steps make the plan more robust. They don't fix a defect in it as written.

VERDICT: GO