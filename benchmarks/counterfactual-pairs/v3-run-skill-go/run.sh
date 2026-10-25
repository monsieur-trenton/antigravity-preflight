#!/usr/bin/env bash
# Gated helper for the skill-go run (see HANDOFF.md). Subcommands: checks | dry | live N --go | bundle. Stops at the first failure; never retries.
#   ROOT    working root, new and outside the repository (default /tmp/v3sgrun)
#   CLAUDE  absolute path to the claude binary (default /home/john/.local/bin/claude)
# Runs: 1 skill-go trial 1; 2 skill trial 1 (control, optional); 3 skill trial 2 (control, optional); 4 skill-go trial 2.
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

C=benchmarks/counterfactual-pairs
D=$C/v3-run-skill-go
ROOT=${ROOT:-/tmp/v3sgrun}
CLAUDE=${CLAUDE:-/home/john/.local/bin/claude}
EXPECT_CLAUDE_VERSION="2.1.306 (Claude Code)"
EXPECT_CLAUDE_SHA=520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe
EXPECT_CORPUS_SHA=1ad685287cf4623dae5e8b3109554b2f0859152a28875e8ddfc4d4c5e7554202
EXPECT_RUN_SHA=585b20e17961f7924088aa0190b988c89c6062c29c30a143e6b2b8268d132376
EXPECT_ARM_SHA=c464860942d815dffebba2b454e0816b7a7755ca7c7f10ca924ac14a9b8ebacc

arm_of()   { case "$1" in 1|4) echo skill-go;; 2|3) echo skill;; *) echo "RUN_MUST_BE_1_TO_4" >&2; exit 2;; esac; }
trial_of() { case "$1" in 1|2) echo 1;; 3|4) echo 2;; esac; }
need_equal() { [ "$2" = "$3" ] || { echo "MISMATCH:$1 expected $3 got $2" >&2; exit 1; }; }

driver() {  # driver ARM TRIAL [--execute]
  python3 -B -I $C/run_pilot_claude.py --arm "$1" --corpus $C/v3 --run-manifest $D/manifest.json \
    --claude-bin "$CLAUDE" --model claude-opus-5-5 --effort high --max-budget-usd 5.0 --workdir "$ROOT/work-$1" --trial "$2" ${3:-}
}
verify() {  # verify ARM TRIALS
  python3 -B -I $C/verify_run.py --arm "$1" --corpus $C/v3 --run-manifest $D/manifest.json \
    --workdir "$ROOT/work-$1" --model claude-opus-5-5 --effort high --trials "$2"
}
identity_header() {
  [ -f "$ROOT/identity.txt" ] && return
  {
    echo "commit: $(git rev-parse HEAD)"
    echo "corpus v3 manifest:        $(sha256sum $C/v3/manifest.json | cut -d' ' -f1)"
    echo "skill-go run manifest:     $(sha256sum $D/manifest.json | cut -d' ' -f1)"
    echo "skill-go arm manifest:     $(sha256sum $C/ablation/skill-go/manifest.json | cut -d' ' -f1)"
    echo "claude: $("$CLAUDE" --version)  $(sha256sum "$CLAUDE" | cut -d' ' -f1)"
    echo "host: $(uname -a)"
    echo "spend cap: 5.0"
  } > "$ROOT/identity.txt"
}

case "${1:-}" in
  checks)
    need_equal claude-version "$("$CLAUDE" --version)" "$EXPECT_CLAUDE_VERSION"
    need_equal claude-sha "$(sha256sum "$CLAUDE" | cut -d' ' -f1)" "$EXPECT_CLAUDE_SHA"
    need_equal clean-tree "$(git status --short)" ""
    need_equal corpus-manifest "$(sha256sum $C/v3/manifest.json | cut -d' ' -f1)" "$EXPECT_CORPUS_SHA"
    need_equal run-manifest "$(sha256sum $D/manifest.json | cut -d' ' -f1)" "$EXPECT_RUN_SHA"
    need_equal arm-manifest "$(sha256sum $C/ablation/skill-go/manifest.json | cut -d' ' -f1)" "$EXPECT_ARM_SHA"
    python3 -B -I tools/check_release.py
    python3 -B -I $C/v3/build_corpus.py --check
    python3 -B -I $C/ablation/skill-go/build_manifest.py --check
    python3 -B -I $D/build_manifest.py --check
    python3 -B -I $D/test_run.py
    python3 -B -I $C/test_verify_run.py
    python3 -B -I $C/test_run_pilot_claude.py
    echo "CHECKS_PASSED commit $(git rev-parse HEAD)"
    ;;
  dry)  # no model call
    mkdir -p "$ROOT"
    driver skill-go 1
    driver skill 1
    echo "--- the only difference between the two requests (expect one line, the sentence beginning 'Optional suggestions'):"
    diff "$ROOT/work-skill-go/trial1/dry-requests/Q-015661/request.txt" "$ROOT/work-skill/trial1/dry-requests/Q-015661/request.txt" || true
    ;;
  live)  # live N --go : a live model call, only with the owner's go for that run
    [ "${3:-}" = "--go" ] || { echo "REFUSED: live N --go needs the owner's go for run N" >&2; exit 2; }
    arm=$(arm_of "${2:-}"); trial=$(trial_of "$2")
    identity_header
    { echo; echo "== run $2: $arm trial $trial"; echo "start: $(date -Is)"; } >> "$ROOT/identity.txt"
    driver "$arm" "$trial" --execute | tee -a "$ROOT/identity.txt"
    echo "end: $(date -Is)" >> "$ROOT/identity.txt"
    if [ "$trial" = 1 ]; then trials=1; else trials=1,2; fi
    verify "$arm" "$trials" | tee -a "$ROOT/identity.txt"
    ;;
  bundle)
    [ -f "$ROOT/identity.txt" ] || { echo "NOTHING_TO_BUNDLE" >&2; exit 1; }
    tar czf "$HOME/v3-skill-go.tar.gz" -C "$ROOT" .
    ls -lh "$HOME/v3-skill-go.tar.gz"
    ;;
  *) echo "usage: run.sh checks | dry | live N --go | bundle" >&2; exit 2;;
esac
