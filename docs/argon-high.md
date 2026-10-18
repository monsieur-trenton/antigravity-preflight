# Gemini 4 Argon / High

v0.2.0 publishes the exact seven owner-activated runtime files in `runtime/argon-high`. Manual Gemini 3.8 Flash / High remains the default; the existing six-file Flash runtime is unchanged. Select Argon explicitly; no fallback or automatic migration is configured.

| Setting | Argon native route |
|---|---|
| Profile | `argon-high` |
| Model | `gemini-4-argon-high` |
| Effort | `high` |
| Credits | `useG1Credits=true` |
| Registry | `runtime/argon-high/RUNTIME-PROFILES.json` |

Authenticate [all seven pins](../qualification/argon-runtime-pins.json) and read the [native runbook](../skills/antigravity-preflight/references/runtime.md). Run native commands from a full repository checkout; copying only the manual skill does not install sibling runtimes. The registry includes a Flash profile for compatibility controls; that does not replace qualification of the separately published Flash package.

The source host completed qualification, independent acceptance with risks, and Gate E owner activation on 2026-10-17. Packet A checked 77/77 quotations; clean Packet B checked 93/93, with zero false blockers. P2 earned 2/2 denial credit. These finite fixtures do not measure general accuracy. [The sanitized summary](../qualification/argon-source-host-summary.json) records custody and limitations. Publication does not activate another host.

## Offline checks

```bash
python3 -B -I tools/check_release.py
python3 -B -I tools/qualify_argon_offline.py /tmp/argon-offline-fresh
```

Each fresh run has 48 capability and 142 launcher controls per profile, 24 parser, 42 overflow, 76 completion and 96 profile controls: 618 total. Two runs total 1,236; a further 40 controls exercise the actual saved envelope. Synthetic proxy fixtures use readiness files, avoiding an unused Unix socket. No qualified runtime bytes were edited. The historical byte-identical source-host envelope records 1,714 cases per run, including private denial-driver controls excluded from this portable subset. Neither envelope is native authorization.

## Authorized host workflow

After host-specific qualification and authorization, capture bounded metadata using the exact separately obtained binary:

```bash
python3 -B -I runtime/argon-high/scripts/cli_capabilities.py /absolute/path/to/agy /fresh/capabilities argon-high
```

Metadata capture is unsandboxed and inherits the environment and real home; model enumeration may contact the provider. It requires task authorization. It is not a containment check.

Prepare a reviewed packet once into a fresh seed:

```bash
python3 -B -I runtime/argon-high/scripts/cli_review.py prepare /packet/PACKET.json /frozen/capabilities /fresh/seed --runtime-profile argon-high
```

Preserve the seed. Copy it once into a fresh attempt, authenticate the copy, then invoke only for an explicitly commissioned live review:

```bash
python3 -B -I runtime/argon-high/scripts/cli_review.py run /fresh/attempt --qualification /your/DUAL-OFFLINE-QUALIFICATION.json --authorize-live
```

The flag records intent; it cannot establish owner authority. Profile, model, effort, credits and registry are bound in the plan and checked against init/qualification. Apply the original runbook's packet caps, one-turn limits, citation adjudication and closing checks. No live run is part of this publication.

## Accepted limits

Acceptance used the same host/helper/prior context; reviewer identity and serving model/effort/backend counts were not independently attested. D2/D3 optional hook audits were absent. Cleanup evidence concerns registered groups, not arbitrary escaped descendants. Historical prompts retain Flash labels, while plan/init bind Argon. Unrun downstream JavaScript tests remain obligations, not completed checks.

The retained runtime still has the review findings described in [the reconciliation](reviews/2026-10-17-reconciliation.md). Altering runtime bytes to address them requires a new candidate and affected qualification. Run the release checker before native preparation: it rejects extra assets, but the retained runner itself still copies the asset tree. Hashes establish consistency, not trusted authorship or semantic correctness.
