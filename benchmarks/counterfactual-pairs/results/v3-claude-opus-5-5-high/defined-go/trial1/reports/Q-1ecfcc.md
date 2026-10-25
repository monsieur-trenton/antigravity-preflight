## Review

**Rate math.** The worst-case aggregate is 8 workers × 5 req/s = **40 req/s**, below the 50 req/s ceiling. That leaves 10 req/s (20%) of headroom.

**Do the stated conditions hold?**
- **Fixed worker count:** Exactly 8 workers for the whole run, so the aggregate cannot grow mid-run.
- **Retries:** HTTP 500 retries use the same limiter allowance as first attempts, so a retry storm cannot push any worker above 5 req/s.
- **Window semantics:** Each worker caps itself over *any* one-second window, which matches the vendor's rule. In any one-second window, each worker sends at most 5, so all eight together send at most 40. No coordination between workers is needed for this to hold.
- **Shared key:** No other service uses the key during the backfill, so nothing else adds load.

The 50 req/s requirement holds under the plan's own stated conditions. I found no rule the plan breaks and nothing it requires changing.

**Optional hardening (not required):**
- **Network jitter.** The limiter counts send times, but the vendor counts arrival times. Jitter could bunch requests slightly at the vendor's end. The 10 req/s headroom absorbs this in practice. A slightly more conservative limiter (e.g., 4.5 req/s) or a short gap between bursts would widen the margin.
- **Throttling responses.** Treat HTTP 429 or other throttling signals as a reason to back off, not to retry right away.
- **Monitoring and a kill switch.** Watch the vendor's reported request rate and keep a way to stop the job quickly.
- **Run time.** At 40 req/s, 3.2M rows take about 80,000 s, or roughly 22 hours plus retries. Plan the schedule around that.

VERDICT: GO