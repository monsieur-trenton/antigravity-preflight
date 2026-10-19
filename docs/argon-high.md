# Gemini 4 Argon / High — available

Full native Argon / High support for PLAN and DIFF review is available in v0.3.0. The seven runtime files in `runtime/argon-high` are byte-identical to the r15 tree owner-activated on October 19, 2026. Manual Gemini 3.8 Flash / High remains the default; the original six-file Flash runtime is unchanged.

| Setting | Argon native route |
| --- | --- |
| Revision / profile | `r15` / `argon-high` |
| Model / effort | `gemini-4-argon-high` / `high` |
| Credits | `useG1Credits=true` |
| Registry | `runtime/argon-high/RUNTIME-PROFILES.json` |

Authenticate [all seven pins](../qualification/argon-runtime-pins.json). Use a full repository checkout: installing only the manual skill does not install sibling native packages. The registry retains a Flash profile for controls; it does not replace the separately published original Flash route.

## What r15 completes

- Deterministic prompt assembly from the instruction request and every declared source, including hashes, strict LF rows and a reversible byte representation.
- Checks before launch and at closing for complete workspace inventories, content hashes, sizes and full POSIX modes; extra entries, symlinks and special bits are refused.
- Explicit profile, model, effort and credit selection; no runtime override or fallback.
- Sanitized init tool-catalogue evidence, registered direct-child identities, and bounded numeric-group settlement observations with wall and host-monotonic timestamps.
- Isolated Python hook invocation and content-free recursion failures in the native citation helper.

The [source-host summary](../qualification/argon-source-host-summary.json) records r15 offline qualification, acceptance, independent Claude review, fresh native denial credit (2/2), known-bad/known-good advisory review and owner ratification/activation. Packet A retained BLOCKERS_FOUND with 95 exact quotes and 99 coordinates. Packet B retained NO_BLOCKERS_FOUND with zero false blockers, five accepted nonblocking notes, 79 exact quotes and 128 coordinates. These are finite fixtures, not a general accuracy estimate. Qualification does not transfer to another host.

## Offline checks

```bash
python3 -B -I tools/check_release.py
python3 -B -I tools/qualify_argon_offline.py /tmp/argon-r15-offline-fresh
```

Each fresh run has 48 capability and 142 launcher controls per profile, 24 parser, 42 overflow, 76 completion, 96 profile, 107 integrity and seven timing controls: 732 total. Two fresh sequential runs total 1,464, followed by 40 controls against the actual saved envelope. Only synthetic local Python children and explicitly mocked probes are used; no agy, auth proxy or provider/model is called. Test-only portability edits replace an unused synthetic proxy socket with a readiness file and adjust fixture imports. Qualified runtime bytes are unchanged.

The historical source-host suite had 1,828 cases per run plus 64 actual-document controls. Its extra private denial-driver controls are excluded from the portable suite. The [exact historical envelope](../qualification/argon-source-host-offline-qualification.json) and newly generated portable envelope have different scope. Neither is host authorization.

## Authorized host workflow

Read the [native runbook](../skills/antigravity-preflight/references/runtime.md) for Linux dependencies, limits, authority and citation adjudication. Obtain the vendor binary separately. After applicable host qualification and authorization, capture metadata using the exact binary:

```bash
python3 -B -I runtime/argon-high/scripts/cli_capabilities.py /absolute/path/to/agy /fresh/capabilities argon-high
```

Metadata capture is unsandboxed and inherits the real environment/home; model enumeration may contact the provider. It is not a containment check.

Prepare a fresh task packet with `PACKET.json` schema version 1, PLAN or DIFF mode, pinned sources, questions and an instruction request. Supply the request once; do not duplicate complete source files inside it. Prepare locally:

```bash
python3 -B -I runtime/argon-high/scripts/cli_review.py prepare /packet/PACKET.json /frozen/capabilities /fresh/seed --runtime-profile argon-high
```

The raw request is preserved as `packet/PROMPT-REQUEST.bin`. The assembler writes the complete evidence payload to the descriptor-defined prompt path and binds it in the schema-v2 plan. The 131,072-byte prompt cap applies to that complete assembled payload; source representation and metadata consume capacity. JSON framing/escaping may make the NDJSON wire representation larger. Preserve the seed inventory, plan and PREPARE-RESULT; verify CLI-GATE is absent. Old seeds/plans must be prepared afresh for r15.

Copy the seed once into a fresh attempt, authenticate the complete inventory, then invoke only for a commissioned live review:

```bash
python3 -B -I runtime/argon-high/scripts/cli_review.py run /fresh/attempt --qualification /your/DUAL-OFFLINE-QUALIFICATION.json --authorize-live
```

One native session/proxy/turn, zero retries; 600 active seconds, 45 initialization seconds, 2,097,152 bytes per stream and 32,768 report bytes. The flag records intent, not external owner authority. Review registered settlement and cleanup fields, preserving primary failures and separate closing faults. Preserve/hash the original report, verify all task coverage and submitted coordinates, and adjudicate every premise before independent review. The qualification fixtures' eight sections do not replace the actual task's declared review contract.

## Accepted limits

Tool-catalogue telemetry does not enforce exact tool-set equality. Numeric group observations do not exclude PID/PGID reuse, escaped descendants, arbitrary host processes or backend requests. A failed settlement raises before returning probe history. Wall-clock timestamps are observations; host-monotonic ordering is assessed within the same host/boot, not a new runtime enforcement predicate. Real saved settlement examples show single absence probes with non-null observed identities; nullable timing coverage is separately mocked, and signal-handler installation is not independently acknowledged.

Shared host/helper lineage, shared network and service-level Secret Service access remain. Serving model/effort, provider retention and backend request counts are unattested. Optional normal finish-hook audits are not credited where absent. Immutable historical request text retains Flash labels while bound profile/init select Argon. Source assertions unrun during static qualification remain runtime obligations. Prompt bytes accepted by the host pipe are not a delivered-wire digest or proof of provider consumption; persistent custody checks do not exclude every transient change.

The source installation intentionally retains historical staging labels such as UNRUN; the later sealed activation establishes ACTIVE_R15_ARGON without rewriting those records. This public runbook describes the current activated route. No live call or native qualification rerun is part of publication. Native observer remains PARKED. Production review requirements remain project-owned; the originating workflow requires separate independent Claude review.
