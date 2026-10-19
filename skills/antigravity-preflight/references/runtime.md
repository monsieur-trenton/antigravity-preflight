# Native runtime routes

Manual Gemini 3.8 Flash / High remains the default. Use the native CLI route only for a specifically authorized task after applicable local qualification. Production code still requires the project's independent review. Native observer development remains PARKED.

## Original Flash package and configuration

The repository's `runtime/flash-high` directory contains the exact six qualified normal-runtime files plus their offline harness. The six runtime bytes are unchanged from the source-host qualification. [Runtime pins](https://github.com/monsieur-trenton/antigravity-preflight/blob/v0.3.0/qualification/runtime-pins.json) enumerate every file; authenticate all six, not just the runner. [Qualification notes](https://github.com/monsieur-trenton/antigravity-preflight/blob/v0.3.0/docs/qualification.md) state the source-host evidence and accepted limits.

- Runner, from repository root: `runtime/flash-high/scripts/cli_review.py`.
- Model: `gemini-3.8-flash-high`; effort: `high`. No silent substitution.
- Source-host native binary: agy 1.3.6, SHA-256 `e14253aa79d4e910cbf8bcb40b68e80f9e85476725e130ed085122c98face92b`, 217,768,144 bytes. Obtain it separately through the vendor; it is not included here.
- Profile: EXACT_R3_NORMAL_FINISH_ONLY. Internal finish is enabled; operational tools, delegation, plugins, skills and MCP are disabled.
- Linux dependencies: `/usr/bin/python3`, `/usr/bin/bwrap`, `/usr/bin/xdg-dbus-proxy`, and a functioning authenticated Secret Service session.

The fixed `/home/john` strings inside the byte-preserved runner designate its private sandbox guest home and filtered identity. They are not a required host checkout path. Changing them changes qualified code and requires affected requalification. macOS/Windows native execution has not been qualified.

## Before live use

Read [CLI update checks](cli-updates.md). Capture the exact binary and bounded version/help/model metadata only under authorization; model enumeration may contact the provider. Do not recapture metadata, update/install a runtime, change accounts or run a probe as an implicit response to a stop. A version string alone is insufficient.

Run `tools/qualify_offline.py`, which performs two fresh runs internally, into one fresh output root. Its `DUAL-OFFLINE-QUALIFICATION.json` binds this exact six-file package for the runner's offline admission predicate. That predicate does not establish native qualification, technical independence or owner authorization. Another host still needs applicable native boundary and known-bad/known-good qualification, risk disposition and an owner decision. The published source-host record does not activate your machine.

## Commissioned Flash task workflow

1. Prepare a sanitized PLAN or DIFF packet under the packet and review contracts. Use task snapshots; do not expose owner-only qualification oracles.
2. `PACKET.json` has `schemaVersion: 1`, `mode`, unique `Qnn` questions, a pinned prompt row (`path`, `sha256`, `bytes`), and unique `Snn` source rows with those fields plus `id`. Paths are regular relative files without symlinks or traversal. Up to 99 sources/questions; prompt and combined source caps are each 131,072 bytes. The prompt must contain the actual reviewable evidence, coordinates, questions and coverage requirements; file binding alone does not establish semantic completeness.
3. Authenticate the exact runner/package, binary, metadata and qualification. Syntax-check complete final Python bytes before execution. Prepare once into a fresh absent task-owned seed outside packet, capabilities and runtime roots:

   `python3 -B -I runtime/flash-high/scripts/cli_review.py prepare <packet>/PACKET.json <frozen-capabilities> <absent-seed>`

   Preparation is local and does not invoke agy. Record the complete seed inventory, `CLI-PLAN.json` and `PREPARE-RESULT.json`; ensure `CLI-GATE.json` is absent. Counts depend on your packet.
4. For an explicitly commissioned live task on a qualified host, copy the seed once into a fresh absent attempt, verify all files and modes, and preserve the seed unconsumed. Invoke once:

   `python3 -B -I runtime/flash-high/scripts/cli_review.py run <fresh-attempt> --qualification <your-offline-envelope> --authorize-live`

   The flag records intent; it is not owner authorization. Limits: one native session, one auth proxy, one turn, zero host retries; 600 active seconds, 45 initialization seconds, 2,097,152 bytes per stream, 131,072 prompt bytes, 32,768 report bytes. No automatic retry, second turn, prompt repair or fallback.
5. Retain direct-child reaping, registered owned-group absence, private-home/socket removal and unchanged input/package custody. The runner receipt alone does not prove every group-absence check; source-host P3/P4 used additional bounded orchestration. New task orchestration must be separately checked. Never run old fixed-path launch scripts against a new task. No escaped-descendant or whole-host containment claim follows.
6. Preserve and hash `GEMINI-REVIEW.md` unchanged. Check all required sections, every source/question and every explicit finding/question quote at its submitted LF coordinate. Extract a complete citation ledger and use `check-citations <attempt> <ledger>`. A matching ledger does not establish extraction completeness or substantive truth. Adjudicate every premise; preserve rejected/unresolved findings. A mismatch stops admission; do not repair coordinates in the original report.

Retain bounded, content-free transport/cleanup receipts. Do not publish raw streams, credentials or authentication scratch. The normal runner is the route in this release; historical schema adapters and P2 challenge drivers are not included.

## Limits and changes

Default-deny hooks, filesystem isolation, stream validation and closing custody are separate layers. Shared network and read-only system exposure remain. Source-host serving model/effort, backend request counts, provider retention and complete host isolation are not independently attested. One host session is not one measured backend request. No universal review accuracy is claimed.

Binary, model, effort, profile, runtime, contract or validator changes invalidate affected proof. Require a fresh candidate, applicable offline/native qualification and owner decision. Preserve stopped attempts. Native observer work remains outside this release; no automatic independent-review launch or changed-runtime installation follows.

## Available r15 Argon / High route

The seven-file owner-activated Argon package is available separately in a full repository checkout. Select `argon-high` explicitly, with model `gemini-4-argon-high`, effort `high` and `useG1Credits=true`. Its prepare command requires `--runtime-profile argon-high`; its metadata helper takes positional `argon-high`. Use the [Argon runbook and pins](https://github.com/monsieur-trenton/antigravity-preflight/blob/v0.3.0/docs/argon-high.md). The Flash instructions above continue to describe the original six-file Flash route. Copying only this manual skill does not install either native package.

Metadata helpers run outside the review sandbox and inherit the real environment/home. Secret Service permissions are service-level, and the review retains shared network access. Offline envelopes validate supplied shape and pins, not external authority. Per-directory one-shot enforcement does not prevent copying a seed for another attempt; honor the commissioned zero-retry procedure.

The current Argon route is the r15 tree activated on October 19, 2026. Its schema-v2 plan assembles the raw request with all declared source bytes, checks workspace inventories/modes before launch and at closing, and records sanitized init-catalogue evidence and bounded registered-group observations. Follow the Argon runbook for fresh packet/seed preparation: the Flash instruction above requiring the prompt to carry all evidence manually does not apply to r15 assembly. Caller inventory checks remain useful defense in depth. The assembled 131,072-byte cap includes representation overhead and is distinct from the escaped NDJSON wire size. Numeric-group receipts do not establish universal containment, process identity across reuse, delivered-wire hashes or provider consumption.
