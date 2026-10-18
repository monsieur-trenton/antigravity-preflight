# CLI update checks

Use only for an owner-authorized CLI attempt. Manual Gemini review remains the default. The Flash route was activated on the source qualification host; another host or changed runtime requires applicable qualification and owner authorization. Native observer development remains parked.

Do not compare the current version to a hardcoded historical release. Updates remain available; each new attempt uses a fresh runtime candidate. Do not install, update, downgrade, change accounts, substitute models, or retry a model call as an implicit response to a compatibility stop.

1. Syntax-check the complete final bytes of `runtime/flash-high/scripts/cli_capabilities.py` and retain its hash before execution. Run it once with the native executable and a new evidence path:

   `python3 -B -I runtime/flash-high/scripts/cli_capabilities.py /absolute/path/to/agy /absolute/new/capability-evidence`

2. The helper freezes a read-only binary copy and queries that copy for version, help and available models. Each command's exact bounded stdout/stderr, exit status, timing and cleanup outcome is saved before content is interpreted. Help may appear on stdout, stderr or both: decode both strictly and separate them with a newline when checking flag tokens. Timeout, overflow, failed commands, malformed text, missing required flags, an unavailable/ambiguous exact model or source/frozen binary drift stops the candidate. Commands after a failed command remain unrun. Model enumeration may contact the provider; it is not a generative review.
3. `PASS_METADATA_CAPABILITIES_ONLY` requires the current interface flags and the exact `gemini-3.8-flash-high` / `Gemini 3.8 Flash (High)` catalogue row. Any nonempty bounded single-line version is observational, including a future release. An unchanged version does not bypass capability checks. Version text and binary SHA-256 are separate observations; neither explains how the CLI obtained the other.
4. Bind the frozen copy's exact hash to the review launcher and include metadata, helper, profile, hook, packet and qualification identities in the plan. Rerun the applicable source-free stream/parser controls against the final launcher. Check native init against the pinned model, agent, working directory and permission mode before sending a prompt. A help flag proves advertised syntax, not runtime semantics or technical containment. Unsupported stream changes stop admission; do not loosen validation automatically.
5. Use one explicitly authorized bounded call, with no host retry or model fallback. Preserve report/citation failures and cleanup/custody evidence. These checks grant no activation, native, product or release credit.

The helper's source-free process tests are in `runtime/flash-high/scripts/test_cli_capabilities.py`. Run twice into separate new roots after changes. Each 48-case run covers ASCII/LF and Unicode/CRLF outputs, old/current/future/prerelease versions, missing/prefix flags, exact model identity, failed commands, invalid text, timeout/overflow and binary drift. Channel controls cover help on stdout, stderr and both, missing/prefix flags on stderr, invalid UTF-8 on either help channel and a token split across channels that must remain missing. Fixture scripts are syntax-checked and hash-recorded before execution; no real CLI or provider is called. Both runs share the test implementation, so they are repeatability evidence, not independent implementation proof.

## Argon route

The optional Argon package uses its own seven-file pins and explicit profile. Its metadata helper accepts `argon-high` as the third positional argument; follow the [Argon runbook](https://github.com/monsieur-trenton/antigravity-preflight/blob/v0.2.0/docs/argon-high.md). Metadata capture is unsandboxed, inherits the real environment/home and may contact the provider. Review sandboxing does not apply to that capture step.
