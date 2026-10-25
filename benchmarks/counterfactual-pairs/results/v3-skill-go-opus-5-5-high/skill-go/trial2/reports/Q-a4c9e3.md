**Rationale**

The plan does not keep each request under the byte limit, and its own lines show that a rejection cannot be recovered.

- **Fixed record count, no byte limit.** The partner rejects any request body over 5,000,000 bytes (line 1). The job splits batches by record count only, at 500 records each (line 2). Nothing in the plan measures or caps the serialized size of a batch.
- **Record size is not bounded.** Each record has a notes field with no length limit (line 3), and record sizes have never been measured (line 5). Bodies are sent uncompressed with under 1,000 bytes of overhead (line 4). A batch therefore fits only if its 500 records average under about 9,998 bytes, and the plan gives no basis for assuming that.
- **A rejection is permanent.** A rejected batch is never resent because of the duplicate-filing rule (line 6). Its invoices then stay missing, reconciliation fails, and the month stays open until the next cycle (line 7).

The snapshot does not show that any batch actually exceeds the limit, so I am not claiming one does. The defect is that the plan relies on an unchecked size assumption where a wrong guess cannot be undone. The text supports this directly, which makes it a blocker rather than a robustness suggestion. The snapshot is closed and does not change (line 2), so the plan could measure record sizes or split batches by bytes before sending. The timeout change on line 8 is consistent with the documented 60-second response time and raises no issue.

MACHINE SUMMARY
COMPLETENESS: COMPLETE
ASSESSMENT: BLOCKERS_FOUND
FINDING: BLOCKER | VERIFIED | 2 | The job reads the closed month-end snapshot, which no longer changes once the month is closed, and sends it in batches of 500 records.