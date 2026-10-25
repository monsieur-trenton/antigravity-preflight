#!/usr/bin/env bash
# Gated helper for the authoring probe (see HANDOFF.md). Subcommands: checks | host | dry | live --go | bundle.
# One live model call in total. Stops at the first failure; never retries.
#   ROOT  working root, new and outside the repository (default /tmp/v4probe)
#   AGY   absolute path to the agy binary (default /home/john/.local/bin/agy)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

C=benchmarks/counterfactual-pairs
P=$C/v4/probe
ROOT=${ROOT:-/tmp/v4probe}
AGY=${AGY:-/home/john/.local/bin/agy}
EXPECT_AGY_SHA=16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508
EXPECT_RUN_SHA=d853fee334b39a42d8b1b20b87a9dc27d68f108a9a4b4afa8e28c48e901ff5d2
EXPECT_PROMPT_SHA=7c5875f6ea00dbf0641c0c64fa20510f1ba543793c4acf239de0c64324990529

need_equal() { [ "$2" = "$3" ] || { echo "MISMATCH:$1 expected $3 got $2" >&2; exit 1; }; }
probe() {  # probe WORKDIR [--execute]
  python3 -B -I $P/probe.py --runtime-dir runtime/flash-high --capabilities "$ROOT/caps" \
    --qualification "$ROOT/qual/DUAL-OFFLINE-QUALIFICATION.json" --workdir "$1" ${2:-}
}

case "${1:-}" in
  checks)  # no model call
    need_equal clean-tree "$(git status --short)" ""
    need_equal run-manifest "$(sha256sum $C/v3-run-gemini/manifest.json | cut -d' ' -f1)" "$EXPECT_RUN_SHA"
    need_equal prompt "$(sha256sum $P/author-prompt.txt | cut -d' ' -f1)" "$EXPECT_PROMPT_SHA"
    need_equal agy-sha "$(sha256sum "$AGY" | cut -d' ' -f1)" "$EXPECT_AGY_SHA"
    python3 -B -I tools/check_release.py
    python3 -B -I $C/v3-run-gemini/build_manifest.py --check
    python3 -B -I $P/test_probe.py
    python3 -B -I $C/test_run_pilot.py
    echo "CHECKS_PASSED commit $(git rev-parse HEAD)"
    ;;
  host)  # the offline qualification and the capabilities probe: no review turn; run once
    mkdir -p "$ROOT"
    python3 -B -I tools/qualify_offline.py "$ROOT/qual"
    python3 -B -I runtime/flash-high/scripts/cli_capabilities.py "$AGY" "$ROOT/caps"
    python3 -B -I -c "
import json,sys
q=json.load(open('$ROOT/qual/DUAL-OFFLINE-QUALIFICATION.json')); c=json.load(open('$ROOT/caps/RESULT.json'))
assert q['status']=='PASS', q['status']
assert c['status']=='PASS_METADATA_CAPABILITIES_ONLY' and c['binaryStable'] is True, c['status']
print('HOST_OK qualification', q['status'], 'capabilities', c['status'], 'version', c.get('observedVersion'))"
    {
      echo "commit: $(git rev-parse HEAD)"
      echo "run manifest (v3 gemini): $(sha256sum $C/v3-run-gemini/manifest.json | cut -d' ' -f1)"
      echo "prompt: $(sha256sum $P/author-prompt.txt | cut -d' ' -f1)"
      echo "agy: $AGY  $(sha256sum "$AGY" | cut -d' ' -f1)"
      echo "agy version: $(cat "$ROOT/caps/VERSION.stdout")"
      echo "host: $(uname -a)"
    } > "$ROOT/identity.txt"
    ;;
  dry)  # no model call
    [ -f "$ROOT/caps/RESULT.json" ] || { echo "RUN_HOST_FIRST" >&2; exit 2; }
    probe "$ROOT/dry"
    echo "--- the prompt that would be sent (first lines):"; head -5 "$ROOT/dry/packet/prompt.txt"
    ;;
  live)  # live --go : the one model call, only with the owner's go
    [ "${2:-}" = "--go" ] || { echo "REFUSED: live --go needs the owner's go" >&2; exit 2; }
    [ -f "$ROOT/caps/RESULT.json" ] || { echo "RUN_HOST_FIRST" >&2; exit 2; }
    { echo; echo "== live call"; echo "start: $(date -Is)"; } >> "$ROOT/identity.txt"
    probe "$ROOT/live" --execute | tee -a "$ROOT/identity.txt" || true
    echo "end: $(date -Is)" >> "$ROOT/identity.txt"
    ;;
  bundle)
    [ -f "$ROOT/live/PROBE-SUMMARY.json" ] || { echo "NOTHING_TO_BUNDLE" >&2; exit 1; }
    out="$HOME/v4-probe.tar.gz"
    stage=$(mktemp -d)
    mkdir -p "$stage/probe"
    cp "$ROOT/identity.txt" "$ROOT/live/PROBE-SUMMARY.json" "$stage/probe/"
    [ -f "$ROOT/live/PROBE-OUTPUT.md" ] && cp "$ROOT/live/PROBE-OUTPUT.md" "$stage/probe/"
    cp "$ROOT/live/attempt/CLI-RECEIPT.json" "$stage/probe/" 2>/dev/null || true
    cp "$ROOT/live/attempt/CLI-INIT.json" "$stage/probe/" 2>/dev/null || true
    cp "$ROOT/caps/RESULT.json" "$stage/probe/CAPABILITIES-RESULT.json"
    cp "$ROOT/qual/DUAL-OFFLINE-QUALIFICATION.json" "$stage/probe/"
    tar czf "$out" -C "$stage" probe
    rm -rf "$stage"
    ls -lh "$out"
    ;;
  *) echo "usage: run.sh checks | host | dry | live --go | bundle" >&2; exit 2;;
esac
