**Rationale**

The snapshot's own text does not support a blocker. The batch limit could be breached, but nothing shows that it will be.

- **Possible breach, not shown.** Line 1 sets a hard limit of 5,000,000 bytes per request. Line 4 allows under 1,000 bytes of overhead, which leaves about 4,999,000 bytes for records. Line 2 fixes batches at 500 records, with no byte cap. A batch is refused only if its 500 records average more than about 9,998 bytes each.
- **Unbounded field.** Line 3 says the free-text notes field has no length cap, so such a batch is possible.
- **Sizes never measured.** Line 5 says record sizes are unknown, so whether any batch actually breaches the limit cannot be checked. Treating that unknown as a proven failure would overstate the evidence.
- **Refusal cannot be recovered.** Line 6 says a refused batch is never resent. Line 7 says one missing invoice fails reconciliation and leaves the month open. If a refusal happens, the job has no recovery path, and the text confirms this.
- **The gap is fixable before sending.** Line 2 says the snapshot stays fixed after month close. Measuring it beforehand, or adding a byte-based check before each request, would give results that still hold at send time.
- **Timeout is fine.** Line 8 sets a 120-second timeout, which covers the partner's stated 60-second worst case. There is no finding there.

Changes are recommended: split batches by size as well as count, or measure the snapshot before sending. Nothing here rises to a text-supported blocker.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: CHANGES_RECOMMENDED
FINDING: RISK | UNVERIFIED | 2 | Its input is the closed month-end snapshot, which stays fixed after the month is closed, and the job splits it into batches of 500 records.
FINDING: RISK | VERIFIED | 6 | Each batch is sent in exactly one request and a refused batch is never sent again, since the partner regards a second submission for the same period as a duplicate filing.
FINDING: NOTE | VERIFIED | 5 | Nobody has measured how large the serialized records in the closed snapshot are, so the size of the biggest record is not known.