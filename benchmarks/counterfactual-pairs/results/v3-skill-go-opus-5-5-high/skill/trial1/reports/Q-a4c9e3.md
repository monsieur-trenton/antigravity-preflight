**Rationale**

The snapshot does not support a BLOCKER. It does support a significant unresolved risk.

- **The size limit is hard.** Line 1 sets a 5,000,000-byte cap per request, and an oversized request is rejected whole.
- **Batches are sized by count, not bytes.** Line 2 sends 500 records per batch with no byte limit. Line 4's envelope adds under 1,000 bytes, which leaves about 9,998 bytes per record on average.
- **Record size has no upper bound.** Line 3 says the notes field has no length limit. Line 5 says record sizes have not been measured.
- **This is a gap, not a proven defect.** Nothing in the snapshot shows that any batch actually exceeds the limit. Calling this a blocker would treat missing evidence as proof.
- **The gap can be closed.** Line 2 says the snapshot no longer changes once the month is closed. So its serialized sizes can be measured before sending, or the job can split batches by byte size.
- **The stakes are high.** Line 6 forbids resending a rejected batch, and line 7 says any missing invoice fails reconciliation and keeps the month open. One oversized batch would therefore be unrecoverable within the cycle. This should be resolved before running.
- **The timeout is consistent.** Line 8 sets 120 seconds, which is above the documented 60-second maximum.

All eight lines were reviewed.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: CHANGES_RECOMMENDED
FINDING: RISK | UNVERIFIED | 5 | The serialized sizes of the records in the closed snapshot have not been measured, so the size of the largest record is not known.
FINDING: RISK | UNVERIFIED | 2 | The job reads the closed month-end snapshot, which no longer changes once the month is closed, and sends it in batches of 500 records.
FINDING: NOTE | VERIFIED | 6 | The job makes exactly one request per batch and never resends a rejected batch, because the partner treats a second submission for the same period as a duplicate filing.