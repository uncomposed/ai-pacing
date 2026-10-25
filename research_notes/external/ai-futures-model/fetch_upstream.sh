#!/usr/bin/env bash
# Fetch the AI Futures Model at the pinned commit. Nothing is vendored into this repo.
# Usage: fetch_upstream.sh [DEST]   (default DEST: .upstream next to this script, git-ignored)
# Idempotent. Verifies the commit and refuses a checkout with local modifications.
set -euo pipefail
AIFM_URL="https://github.com/AI-Futures-Project/aifm-public"
# "Initial release", committed 2026-09-09. Keep in sync with SOURCES.yaml (checked by the tests).
AIFM_COMMIT="1c40ecdb246c25980515441a66571931c5604e11"
dest="${1:-$(cd "$(dirname "$0")" && pwd)/.upstream}"

if [ ! -d "$dest/.git" ]; then
  git init -q "$dest"
  git -C "$dest" remote add origin "$AIFM_URL"
fi
if [ "$(git -C "$dest" rev-parse -q --verify HEAD 2>/dev/null || true)" != "$AIFM_COMMIT" ]; then
  git -C "$dest" fetch -q --depth 1 origin "$AIFM_COMMIT"
  git -C "$dest" checkout -q --detach FETCH_HEAD
fi
got="$(git -C "$dest" rev-parse HEAD)"
if [ "$got" != "$AIFM_COMMIT" ]; then
  echo "fetch_upstream: expected $AIFM_COMMIT, got $got" >&2
  exit 1
fi
if [ -n "$(git -C "$dest" status --porcelain --untracked-files=no)" ]; then
  echo "fetch_upstream: $dest has local modifications; refusing to use it" >&2
  exit 1
fi
echo "$dest"
