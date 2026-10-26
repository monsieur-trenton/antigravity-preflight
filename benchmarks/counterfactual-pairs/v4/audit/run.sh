#!/usr/bin/env bash
# Gated helper for the blind audit of a built v4 corpus (see HANDOFF.md). Subcommands: checks | dry [PAIRS] | live N --go [PAIRS] | bundle.
# Stops at the first failure; never retries. A live call is made only by `live N --go`, at most N calls per invocation.
#   CORPUS      the corpus directory to audit (required; the one the owner names)
#   CORPUS_SHA  SHA-256 of CORPUS/manifest.json that the owner names (required)
#   ROOT        working root, new and outside the repository (default /tmp/v4audit)
#   CLAUDE      absolute path to the claude binary (default /home/john/.local/bin/claude)
#   MODEL       exact model id (default claude-opus-5-5)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

C=benchmarks/counterfactual-pairs
D=$C/v4/audit
ROOT=${ROOT:-/tmp/v4audit}
CLAUDE=${CLAUDE:-/home/john/.local/bin/claude}
MODEL=${MODEL:-claude-opus-5-5}
EXPECT_CLAUDE_VERSION="2.1.306 (Claude Code)"
EXPECT_CLAUDE_SHA=520bc6c1f40af466bd03a278b5ae1af1a2938bc7de5b9e5cb15526da20d71cfe
EXPECT_SYSTEM_SHA=0203fc245a19e49e7d8c12a5cdd6c5f7b015ff9a6f1a4178c622d0b2189bfd7d
EXPECT_MEMBER_SHA=b7e17fd16ca150518b40d5615e7d29257326644285b38a1360540677791e9116
EXPECT_PAIR_SHA=85220f2882e6925fd76c8219aa83271a79722fb66123d316440056aaa7532f45
EXPECT_CLAIM_SHA=076d5a60acfffab0ee8c4e6c2108a7b743bc96daf2822a33186abd09b88ab08a

need_equal() { [ "$2" = "$3" ] || { echo "MISMATCH:$1 expected $3 got $2" >&2; exit 1; }; }
need_corpus() {
  [ -n "${CORPUS:-}" ] && [ -n "${CORPUS_SHA:-}" ] || { echo "CORPUS_AND_CORPUS_SHA_REQUIRED" >&2; exit 2; }
  need_equal corpus-manifest "$(sha256sum "$CORPUS/manifest.json" | cut -d' ' -f1)" "$CORPUS_SHA"
}
audit() { python3 -B -I $D/audit.py --claude-bin "$CLAUDE" --model "$MODEL" --effort high --corpus "$CORPUS" --max-budget-usd 2.0 --workdir "$ROOT/work" "$@"; }

case "${1:-}" in
  checks)  # no model call
    need_corpus
    need_equal claude-version "$("$CLAUDE" --version)" "$EXPECT_CLAUDE_VERSION"
    need_equal claude-sha "$(sha256sum "$CLAUDE" | cut -d' ' -f1)" "$EXPECT_CLAUDE_SHA"
    need_equal clean-tree "$(git status --short)" ""
    need_equal system-prompt "$(sha256sum $D/system-prompt.txt | cut -d' ' -f1)" "$EXPECT_SYSTEM_SHA"
    need_equal member-request "$(sha256sum $D/member-request.txt | cut -d' ' -f1)" "$EXPECT_MEMBER_SHA"
    need_equal pair-request "$(sha256sum $D/pair-request.txt | cut -d' ' -f1)" "$EXPECT_PAIR_SHA"
    need_equal claim-request "$(sha256sum $D/claim-request.txt | cut -d' ' -f1)" "$EXPECT_CLAIM_SHA"
    python3 -B -I tools/check_release.py
    python3 -B -I $D/test_audit.py
    python3 -B -I $C/v4/test_score_v4.py
    echo "CHECKS_PASSED commit $(git rev-parse HEAD)"
    ;;
  dry)  # dry [PAIR,PAIR]: no model call: writes every request (of the named pairs, if any) and counts them
    need_corpus
    mkdir -p "$ROOT"
    audit ${2:+--pairs "$2"}
    ;;
  live)  # live N --go [PAIR,PAIR]: at most N calls in this invocation (of the named pairs, if any), only with the owner's go
    [ "${3:-}" = "--go" ] || { echo "REFUSED: live N --go needs the owner's go for N calls" >&2; exit 2; }
    case "${2:-}" in ''|*[!0-9]*) echo "N_MUST_BE_A_NUMBER" >&2; exit 2;; esac
    need_corpus
    mkdir -p "$ROOT"
    if [ ! -f "$ROOT/identity.txt" ]; then
      {
        echo "commit: $(git rev-parse HEAD)"
        echo "corpus manifest: $CORPUS_SHA"
        echo "claude: $("$CLAUDE" --version)  $(sha256sum "$CLAUDE" | cut -d' ' -f1)"
        echo "model: $MODEL  effort: high  per-call spend cap: 2.0"
        echo "host: $(uname -a)"
      } > "$ROOT/identity.txt"
    fi
    { echo; echo "== live $2 calls: start $(date -Is)"; } >> "$ROOT/identity.txt"
    audit --execute --max-calls "$2" ${4:+--pairs "$4"} | tee -a "$ROOT/identity.txt"
    echo "end: $(date -Is)" >> "$ROOT/identity.txt"
    ;;
  bundle)
    [ -f "$ROOT/identity.txt" ] && [ -f "$ROOT/work/audit-answers.jsonl" ] || { echo "NOTHING_TO_BUNDLE" >&2; exit 1; }
    out="$HOME/v4-audit.tar.gz"
    stage=$(mktemp -d)
    mkdir -p "$stage/audit"
    cp "$ROOT/identity.txt" "$ROOT/work/audit-answers.jsonl" "$stage/audit/"
    mkdir "$stage/audit/attempts"
    for d in "$ROOT"/work/attempts/*/; do
      n=$(basename "$d"); mkdir "$stage/audit/attempts/$n"
      cp "$d/request.txt" "$d/ANSWER.md" "$d/claude-output.json" "$stage/audit/attempts/$n/" 2>/dev/null || true
    done
    tar czf "$out" -C "$stage" audit
    rm -rf "$stage"
    ls -lh "$out"
    ;;
  *) echo "usage: run.sh checks | dry [PAIRS] | live N --go [PAIRS] | bundle" >&2; exit 2;;
esac
