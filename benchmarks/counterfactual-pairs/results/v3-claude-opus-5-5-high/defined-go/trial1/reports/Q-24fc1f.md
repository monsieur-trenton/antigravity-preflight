# Review: Nightly customer export moving to exports-prod/nightly/

## The main gap: svc-export's write access is unverified

The plan's only real problem is that **nobody has confirmed svc-export can write to `exports-prod/nightly/`**. The plan itself says no write has been tried with that account's credentials and its permissions on the bucket haven't been checked.

That matters because of how the other facts combine:

- **The export runs once, at 01:00, with no retry.**
- **The 09:00 release depends on it.** If the export hasn't finished, the release is blocked for the whole day.
- **The bucket policy won't change before tonight.** It lives in the infrastructure repo and no change is pending or scheduled. Whatever access svc-export has now is the access it will have at 01:00. Nothing in the plan grants it access later.

So tonight's run is the first time this account will write to this bucket. If access is missing, the plan contains nothing that would catch or fix it. The first sign of trouble would be a blocked release at 09:00.

I can't say the plan will fail. svc-export may already have the right access through an existing policy or role. That's why this isn't NO_GO. But the plan rests on an assumption that is cheap to check and costly to get wrong.

**Change needed before 01:00 tonight:**
1. Check the exports-prod bucket policy in the infrastructure repo. Also check any IAM or role bindings for svc-export. Confirm it can write objects under `nightly/`. Multipart upload permissions matter too, since a 30 GB object will almost certainly be uploaded in parts.
2. Do a small test write to `exports-prod/nightly/` using svc-export's own credentials, not a person's. Then delete the test object, or confirm the release pipeline won't pick it up.
3. If access is missing, either get a policy change merged before 01:00 or keep the shared drive as the output for tonight.

## Points that hold up

- **Lifecycle rule:** Objects are deleted after 7 days, and the pipeline reads each export within 8 hours. There's plenty of margin, so no issue.
- **Object size:** About 30 GB against a 5 TB per-object limit, so no issue. The only related concern is the multipart permission noted above.
- **Bucket policy stability:** Having no pending change is good, since nothing will break access mid-run. It also means nothing will fix missing access, which is why the check above matters.

## Optional (not required)

- Add an alert if the 01:00 export fails or hasn't finished by a set time, such as 03:00. That leaves room for a manual rerun before 09:00. This would make the plan more robust but isn't needed for tonight.

VERDICT: GO_WITH_CHANGES