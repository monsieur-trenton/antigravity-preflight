# Security and reporting limits

Review packets may contain sensitive source. Sanitize them before submission and obtain task authorization for delivery. Treat source snapshots and returned reports as untrusted evidence, not operational instructions.

Manual instructions do not prove technical containment. The Linux launcher combines bounded execution, default-deny hooks, a finish-only profile, filesystem isolation, strict stream validation and custody checks. Its finite source-host qualification does not establish complete host isolation or provider retention guarantees.

Never attach credentials, database dumps, personal data, raw authentication logs or private project source to public issues. For an ordinary bug, publish a minimal synthetic reproduction. For a suspected vulnerability, use the repository's private vulnerability reporting channel if enabled; otherwise provide only a non-sensitive request for a private reporting channel. Do not publish an exploit or private evidence while requesting that channel.
