#!/usr/bin/env bash
# Gated helper for authoring corpus v4 (see HANDOFF.md). Subcommands: checks | diag | host | dry | live N --go [PAIRS] | reword N --go [PAIRS] | status | bundle.
# Stops at the first failure. A live call is made only by live/reword, only with --go, and at most N calls per invocation.
#   SPLIT  dev or test (default dev)
#   ROOT   working root, new and outside the repository (default /tmp/v4author-$SPLIT)
#   AGY    absolute path to the agy binary (default /home/john/.local/bin/agy)
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"

C=benchmarks/counterfactual-pairs
A=$C/v4/author
SPLIT=${SPLIT:-dev}
ROOT=${ROOT:-/tmp/v4author-$SPLIT}
AGY=${AGY:-/home/john/.local/bin/agy}
EXPECT_AGY_SHA=16e228cb243fa098eeb27b3b2aca963caec84e4a8ac49e3821b00c56f99f7508
EXPECT_RUN_SHA=d853fee334b39a42d8b1b20b87a9dc27d68f108a9a4b4afa8e28c48e901ff5d2
EXPECT_AUTHOR_TEMPLATE_SHA=44fe442e270f5bc6f8e7672d1f1e2945064f6b6be8d24a8245fca60e70498bb0
EXPECT_REWORD_TEMPLATE_SHA=5ee054df5a23cfba5a7258011d36113d28d0b3eeb03bae620fdf29fc1fcaf5f0
EXPECT_FAMILIES_SHA=3e2da8f672febc1d3f855012ee69010e7c2ac97a768a420314024a59b25a53d3
EXPECT_DOMAINS_SHA=f712ce97d0ed6873a7702b466ec2a6633ff600d3fa9649b25012bbbec30db692
EXPECT_DEV_ASSIGNMENTS_SHA=d4274305e993fbf6d97acaa9830f9f664ce33ca58d9f419439e9d7e7579302e4
EXPECT_TEST_ASSIGNMENTS_SHA=eacf1417293682d5dccd430d10de6d015b796de7c54bf9cfed4d1ef122f1b65f

need_equal() { [ "$2" = "$3" ] || { echo "MISMATCH:$1 expected $3 got $2" >&2; exit 1; }; }
case "$SPLIT" in dev|test) ;; *) echo "SPLIT_MUST_BE_dev_OR_test" >&2; exit 2;; esac
author() {  # author [author.py options]
  python3 -B -I $A/author.py --split "$SPLIT" --runtime-dir runtime/flash-high --capabilities "$ROOT/caps" \
    --qualification "$ROOT/qual/DUAL-OFFLINE-QUALIFICATION.json" --workdir "$ROOT/work" "$@"
}
count() { case "$1" in ''|*[!0-9]*) echo "N_MUST_BE_A_NUMBER" >&2; exit 2;; esac; [ "$1" -ge 1 ] && [ "$1" -le 40 ] || { echo "N_MUST_BE_1_TO_40" >&2; exit 2; }; }
host_done() { [ -f "$ROOT/caps/RESULT.json" ] || { echo "RUN_HOST_FIRST" >&2; exit 2; }; }

case "${1:-}" in
  checks)  # no model call
    need_equal clean-tree "$(git status --short)" ""
    need_equal run-manifest "$(sha256sum $C/v3-run-gemini/manifest.json | cut -d' ' -f1)" "$EXPECT_RUN_SHA"
    need_equal author-template "$(sha256sum $A/author-template.txt | cut -d' ' -f1)" "$EXPECT_AUTHOR_TEMPLATE_SHA"
    need_equal reword-template "$(sha256sum $A/reword-template.txt | cut -d' ' -f1)" "$EXPECT_REWORD_TEMPLATE_SHA"
    need_equal families "$(sha256sum $C/v4/families.json | cut -d' ' -f1)" "$EXPECT_FAMILIES_SHA"
    need_equal domains "$(sha256sum $C/v4/domains.json | cut -d' ' -f1)" "$EXPECT_DOMAINS_SHA"
    need_equal dev-assignments "$(sha256sum $A/assignments-dev.json | cut -d' ' -f1)" "$EXPECT_DEV_ASSIGNMENTS_SHA"
    need_equal test-assignments "$(sha256sum $A/assignments-test.json | cut -d' ' -f1)" "$EXPECT_TEST_ASSIGNMENTS_SHA"
    need_equal agy-sha "$(sha256sum "$AGY" | cut -d' ' -f1)" "$EXPECT_AGY_SHA"
    python3 -B -I tools/check_release.py
    python3 -B -I $C/v3-run-gemini/build_manifest.py --check
    python3 -B -I $C/v4/check_families.py
    python3 -B -I $A/assign.py --split dev --check
    python3 -B -I $A/assign.py --split test --check
    python3 -B -I $A/test_author.py
    python3 -B -I $C/test_run_pilot.py
    echo "CHECKS_PASSED commit $(git rev-parse HEAD)"
    ;;
  diag)  # no model call: how slow is this machine right now? (the offline controls have a 0.5 s window)
    python3 -B -I -c "
import statistics, subprocess, sys, time, os
times = []
for _ in range(30):
    t = time.monotonic(); subprocess.run([sys.executable, '-B', '-I', '-c', 'pass'], check=True); times.append((time.monotonic() - t) * 1000)
print('DIAG python start-up ms: median %.0f, p90 %.0f, max %.0f; load average %s; cpus %d' % (statistics.median(times), sorted(times)[26], max(times), ' '.join('%.2f' % x for x in os.getloadavg()), os.cpu_count()))"
    ;;
  host)  # the offline qualification and the capabilities probe: no review turn; once per ROOT
    mkdir -p "$ROOT"
    python3 -B -I tools/qualify_offline.py "$ROOT/qual"
    python3 -B -I runtime/flash-high/scripts/cli_capabilities.py "$AGY" "$ROOT/caps"
    python3 -B -I -c "
import json
q=json.load(open('$ROOT/qual/DUAL-OFFLINE-QUALIFICATION.json')); c=json.load(open('$ROOT/caps/RESULT.json'))
assert q['status']=='PASS', q['status']
assert c['status']=='PASS_METADATA_CAPABILITIES_ONLY' and c['binaryStable'] is True, c['status']
print('HOST_OK qualification', q['status'], 'capabilities', c['status'], 'version', c.get('observedVersion'))"
    {
      echo "commit: $(git rev-parse HEAD)"
      echo "split: $SPLIT"
      echo "run manifest (v3 gemini): $(sha256sum $C/v3-run-gemini/manifest.json | cut -d' ' -f1)"
      echo "author template: $(sha256sum $A/author-template.txt | cut -d' ' -f1)"
      echo "reword template: $(sha256sum $A/reword-template.txt | cut -d' ' -f1)"
      echo "families: $(sha256sum $C/v4/families.json | cut -d' ' -f1)"
      echo "assignments-$SPLIT: $(sha256sum $A/assignments-$SPLIT.json | cut -d' ' -f1)"
      echo "agy: $AGY  $(sha256sum "$AGY" | cut -d' ' -f1)"
      echo "agy version: $(cat "$ROOT/caps/VERSION.stdout")"
      echo "host: $(uname -a)"
    } > "$ROOT/identity.txt"
    ;;
  dry)  # no model call: builds every prompt of the split
    host_done
    author
    ls "$ROOT/work/prompts" | wc -l
    echo "--- the first lines of one prompt:"; head -8 "$(ls -d "$ROOT"/work/prompts/*.A.txt | head -1)"
    ;;
  live)  # live N --go [PAIR,PAIR]: at most N authoring calls, each pair at most once in this invocation
    [ "${3:-}" = "--go" ] || { echo "REFUSED: live N --go needs the owner's go for N calls" >&2; exit 2; }
    count "${2:-}"; host_done
    { echo; echo "== live $2 calls (author): start $(date -Is)"; } >> "$ROOT/identity.txt"
    author --execute --max-calls "$2" ${4:+--pairs "$4"} | tee -a "$ROOT/identity.txt"
    echo "end: $(date -Is)" >> "$ROOT/identity.txt"
    ;;
  reword)  # reword N --go [PAIR,PAIR]: at most N wording-B calls (test split only; needs the accepted wording A of each pair)
    [ "${3:-}" = "--go" ] || { echo "REFUSED: reword N --go needs the owner's go for N calls" >&2; exit 2; }
    [ "$SPLIT" = test ] || { echo "REWORDING_IS_TEST_ONLY" >&2; exit 2; }
    count "${2:-}"; host_done
    { echo; echo "== live $2 calls (reword): start $(date -Is)"; } >> "$ROOT/identity.txt"
    author --reword --execute --max-calls "$2" ${4:+--pairs "$4"} | tee -a "$ROOT/identity.txt"
    echo "end: $(date -Is)" >> "$ROOT/identity.txt"
    ;;
  status)  # no model call: what is accepted, what failed, what is left
    [ -f "$ROOT/work/calls.jsonl" ] || { echo "NO_CALLS_YET" >&2; exit 1; }
    python3 -B -I -c "
import json, glob, os
rows=[json.loads(l) for l in open('$ROOT/work/calls.jsonl') if l.strip()]
doc=json.load(open('$A/assignments-$SPLIT.json'))['instances']
acc=lambda k:{os.path.basename(p).split('.')[0] for p in glob.glob('$ROOT/work/accepted/*.%s.md'%k)}
a,b=acc('A'),acc('B'); need_b={i['pair'] for i in doc if i['wordingB']}
used=lambda purpose,p:sum(1 for r in rows if r['pair']==p and r['purpose']==purpose)
print(json.dumps({'calls':len(rows),'stops':sum(1 for r in rows if r.get('technicalStop')),'failedChecks':sum(1 for r in rows if r.get('allPassed') is False),
  'acceptedA':len(a),'pairs':len(doc),'acceptedB':len(b),'wordingBNeeded':len(need_b),
  'notAcceptedA':sorted({i['pair'] for i in doc}-a),'attemptsUsedA':sorted(p for p in {i['pair'] for i in doc}-a if used('author',p)>=2)}))"
    ;;
  bundle)
    [ -f "$ROOT/identity.txt" ] && [ -f "$ROOT/work/calls.jsonl" ] || { echo "NOTHING_TO_BUNDLE" >&2; exit 1; }
    out="$HOME/v4-author-$SPLIT-$(basename "$ROOT").tar.gz"
    stage=$(mktemp -d)
    mkdir -p "$stage/author"
    cp "$ROOT/identity.txt" "$ROOT/work/calls.jsonl" "$stage/author/"
    cp -r "$ROOT/work/accepted" "$ROOT/work/prompts" "$stage/author/"
    mkdir "$stage/author/calls"
    for d in "$ROOT"/work/calls/*/; do
      n=$(basename "$d"); mkdir "$stage/author/calls/$n"
      cp "$d/REPORT.md" "$stage/author/calls/$n/" 2>/dev/null || true
      cp "$d/attempt/CLI-RECEIPT.json" "$d/attempt/CLI-INIT.json" "$stage/author/calls/$n/" 2>/dev/null || true
    done
    cp "$ROOT/caps/RESULT.json" "$stage/author/CAPABILITIES-RESULT.json"
    cp "$ROOT/qual/DUAL-OFFLINE-QUALIFICATION.json" "$stage/author/"
    tar czf "$out" -C "$stage" author
    rm -rf "$stage"
    ls -lh "$out"
    ;;
  *) echo "usage: run.sh checks | diag | host | dry | live N --go [PAIRS] | reword N --go [PAIRS] | status | bundle" >&2; exit 2;;
esac
