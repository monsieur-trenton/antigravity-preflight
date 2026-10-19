#!/usr/bin/env bash
# Publish only this prepared repository. Requires a valid GitHub CLI login.
set -euo pipefail
task_repo_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$task_repo_root"
python3 -B -I tools/check_release.py
test -z "$(git status --porcelain)"
test "$(git branch --show-current)" = main
test "$(git rev-parse v0.3.0)" = "$(git rev-parse HEAD)"
gh auth status --hostname github.com
if git remote get-url origin >/dev/null 2>&1; then
  task_origin="$(git remote get-url origin)"
  case "$task_origin" in
    https://github.com/monsieur-trenton/antigravity-preflight.git|git@github.com:monsieur-trenton/antigravity-preflight.git) ;;
    *) echo 'Refusing unexpected origin.' >&2; exit 1 ;;
  esac
else
  gh repo create monsieur-trenton/antigravity-preflight --public --source . --remote origin --push \
    --description 'Bounded Gemini Flash / High and Argon / High preflight, exact citations and adjudication before independent review.'
fi
git push origin main v0.3.0
if ! gh release view v0.3.0 --repo monsieur-trenton/antigravity-preflight >/dev/null 2>&1; then
  gh release create v0.3.0 --repo monsieur-trenton/antigravity-preflight --verify-tag \
    --title 'Antigravity Preflight 0.3.0 — Full Argon native support' \
    --notes-file docs/release-v0.3.0.md
fi
gh repo view monsieur-trenton/antigravity-preflight --json nameWithOwner,isPrivate,url
gh release view v0.3.0 --repo monsieur-trenton/antigravity-preflight --json tagName,url,isDraft,isPrerelease
