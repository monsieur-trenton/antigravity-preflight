# Cross-source format reference (a shortened illustration, not a case)

This shows the shape of a `cross_source_defect` pair and its oracle, shortened so it fits on a page: real plans have 25 to 50 lines and real references 8 to 25. It is never sent to a reviewer and never reused as a case. The family is `config_limit`; the domain is `message_queue_consumer_scaling`.

## Reference excerpt (S02, the same in both members except where the twin differs)

```
S02:1  Queue orders-events accepts at most 40 concurrent consumers per consumer group.
S02:2  Each consumer may hold at most 200 unacknowledged messages.
S02:3  A consumer group that exceeds its consumer limit is paused by the broker until an operator resumes it.
S02:4  The batch size per fetch is limited to 500 messages.
S02:5  Partition count for orders-events is fixed at 48 and cannot be changed without recreating the queue.
```

## Plan (S01), sound member, lines 4 to 8 only

```
S01:4  The consumer group payments-reconciler will run 36 consumers during the backlog drain.
S01:5  Each consumer fetches 400 messages per request and holds at most 150 unacknowledged messages.
S01:6  If the group is paused by the broker, the drain stops and the nightly reconciliation misses its 06:00 deadline.
S01:7  The drain is expected to take about two hours at this size.
S01:8  The group is resumed by the on-call engineer only after the cause of a pause has been found.
```

## Twin: one edit in one source

Line 4 of the plan becomes: `The consumer group payments-reconciler will run 48 consumers during the backlog drain.` Nothing else changes, and no line mentions the limit.

## Oracle for the twin (hidden)

```json
{
  "case": "R-0a1b2c", "pair": "N-0001", "family": "config_limit", "kind": "cross_source_defect", "domain": "message_queue_consumer_scaling",
  "wording": "A", "role": "changed", "expectedClass": "DEFECT", "expectedVerdict": "NO_GO", "difficulty": "direct",
  "sources": [{"id": "S01", "role": "plan", "lines": 34}, {"id": "S02", "role": "reference", "lines": 5}],
  "requirement": {"source": "S01", "line": 6},
  "citeAnyOf": [{"source": "S01", "line": 4}, {"source": "S02", "line": 1}],
  "changed": {"type": "edited", "source": "S01", "lines": [4], "positionBucket": "early"},
  "decoyLines": [],
  "mechanism": "Line 4 of the plan sets 48 consumers; line 1 of the reference allows at most 40 per group, and line 3 says the broker pauses a group that exceeds it.",
  "whyNoFallback": null,
  "baitNotes": ["the two-hour estimate is not measured", "resumption depends on one engineer"],
  "rubricKeywords": [["consumer", "48"], ["40", "limit", "at most"]]
}
```

Note what the near-miss limits do: the sound plan's 400-message fetch is under line 4 of the reference (500) and its 150 unacknowledged messages under line 2 (200), and the partition count (48) is a number that the twin's edit coincides with on purpose, so a reviewer that matches numbers without reading the limit can be misled.
