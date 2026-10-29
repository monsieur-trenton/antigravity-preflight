#!/usr/bin/env bash
# Thin wrapper for the v4 block run: reads the owner's settings once, then calls the Python tools. Makes no model call by itself;
# `next` is a dry run unless --execute is passed through. See HANDOFF.md.
#
#   blocks.sh status  claude|gemini
#   blocks.sh next    claude|gemini [--execute] [--steps N] [--max-cases N] [--max-minutes M] ...
#   blocks.sh verify  claude|gemini
#   blocks.sh bundle  OUT.tar.gz [--redacted]
#   blocks.sh analyze [OUTPUT_JSON]
#   blocks.sh stop | resume          create / remove the workdir's STOP file (stops at the next case boundary)
#
# Settings come from $V4_BENCH_ENV (default ~/.v4-bench.env), a shell file that sets:
#   V4_WORKDIR (outside the repository), V4_CORPUS (the corpus directory, with text), V4_RUN_MANIFEST (the frozen run manifest), V4_SPLIT (test; dev to rehearse)
#   claude: V4_CLAUDE_BIN [V4_CLAUDE_MODEL V4_CLAUDE_EFFORT]    gemini: V4_RUNTIME_DIR V4_CAPABILITIES V4_QUALIFICATION
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
conf=${V4_BENCH_ENV:-$HOME/.v4-bench.env}
if [ -f "$conf" ]; then . "$conf"; fi
: "${V4_WORKDIR:?set V4_WORKDIR in $conf}"
split=${V4_SPLIT:-test}
py=(python3 -B -I)
cmd=${1:-help}
shift || true
route_args() {
  case "$1" in
    claude) printf '%s\0' --claude-bin "${V4_CLAUDE_BIN:?set V4_CLAUDE_BIN}" --model "${V4_CLAUDE_MODEL:-claude-opus-5-5}" --effort "${V4_CLAUDE_EFFORT:-high}" ;;
    gemini) printf '%s\0' --runtime-dir "${V4_RUNTIME_DIR:?set V4_RUNTIME_DIR}" --capabilities "${V4_CAPABILITIES:?set V4_CAPABILITIES}" --qualification "${V4_QUALIFICATION:?set V4_QUALIFICATION}" ;;
    *) echo "route must be claude or gemini" >&2; exit 2 ;;
  esac
}
case "$cmd" in
  status)
    route=${1:?route}; shift
    exec "${py[@]}" "$here/run_v4.py" status --route "$route" --workdir "$V4_WORKDIR" --split "$split" "$@" ;;
  next)
    route=${1:?route}; shift
    mapfile -d '' extra < <(route_args "$route")
    exec "${py[@]}" "$here/run_v4.py" next --route "$route" --workdir "$V4_WORKDIR" --split "$split" --corpus "${V4_CORPUS:?set V4_CORPUS}" \
      --run-manifest "${V4_RUN_MANIFEST:?set V4_RUN_MANIFEST}" "${extra[@]}" "$@" ;;
  verify)
    route=${1:?route}; shift
    exec "${py[@]}" "$here/verify_v4.py" --corpus "${V4_CORPUS:?}" --run-manifest "${V4_RUN_MANIFEST:?}" --workdir "$V4_WORKDIR" --route "$route" "$@" ;;
  bundle)
    out=${1:?output file}; shift
    exec "${py[@]}" "$here/run_v4.py" bundle --workdir "$V4_WORKDIR" --out "$out" "$@" ;;
  analyze)
    exec "${py[@]}" "$here/analyze_v4.py" --corpus "${V4_CORPUS:?}" --run-manifest "${V4_RUN_MANIFEST:?}" --workdir "$V4_WORKDIR" "$@" ;;
  stop) mkdir -p "$V4_WORKDIR"; : > "$V4_WORKDIR/STOP"; echo "STOP file created: the running block stops after its current case" ;;
  resume) rm -f "$V4_WORKDIR/STOP"; echo "STOP file removed" ;;
  *) sed -n '2,13p' "$0"; exit 2 ;;
esac
