# Dev rehearsal, Claude route (tooling check, not evidence)

Run from the cloud session that wrote the tooling, on the public dev corpus (manifest `1e89ac9d…82975`) with a rehearsal run manifest (`711e6f82…a87a26`, split `dev`, not the frozen test manifest), through `blocks.sh` as the skill describes: dry run, one live case, then steps 1 and 2 of the Claude schedule (block B01, arms `skill-go` and `skill`, trial 1; 12 cases each), with a deliberate stop on the time budget and a resume.

| Check | Result |
| --- | --- |
| Dry run | 12 requests built, no ledger written, repeatable |
| One live case (`--max-cases 1`) | recorded; served model `claude-opus-5-5`, $0.068, 18 s |
| Step 1 (skill-go, B01) | 12 of 12 recorded, 0 stops, $0.86, complete |
| Step 2 (skill, B01), first call | stopped by `TIME_BUDGET` after 8 of 12 cases (the reserve is the longer of 120 s and 1.5 times the longest case, so it stops early rather than late) |
| Step 2, resume | the remaining 4 recorded, step complete; nothing rerun |
| `verify` | `failures: []`, 24 rows, 0 stops, 2 steps complete |
| Redacted bundle | ledgers with quotations hashed, block log; no reports or requests |
| Cost | $1.83 for 24 cases |
| Measured | 22.1 s per case; peak child memory 231 MB; child CPU about 2 s per case; load average 0.03 to 0.08 |

**Limits.** This container is not the owner's machine, so the memory, CPU and load figures say nothing about its effect there; the Claude Code binary is 2.1.312, not the v3 run's 2.1.306, so this proves the flags and parsing, not the pinned binary; no request was altered after seeing a report; the verdicts were not read and mean nothing. The Gemini route could not be rehearsed here (no `agy`, capabilities or qualification envelope): it is covered only by the stub-runtime tests and needs the owner's machine.
