#!/usr/bin/env bash
# Fetch the pinned METR sources into a local cache (not committed) and verify them by sha256.
#
#   bash fetch_sources.sh            # cache in ./.cache (git-ignored), or $METR_CACHE
#
# Needs network: github.com (git clone) and metr.org (HTTPS). Nothing here is vendored into the
# repository: METR's repository has no LICENSE file, so raw run data stays in the cache.
# A hash mismatch is a finding (the source changed), not something to paper over: the script
# stops, and the README says how to record a new pin.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cache="${METR_CACHE:-$here/.cache}"
repo_url="https://github.com/METR/eval-analysis-public"
pin="52cb829c7a2efb2d659285c4b1768d191d97f8d2"   # 2026-03-05 "Sync public pipeline (#39)"
up="$cache/eval-analysis-public"

mkdir -p "$cache/vintages" "$cache/metr.org"

if [ ! -d "$up/.git" ]; then
  # Full history is needed: earlier commits are the data vintages used for the real-time table.
  git clone --quiet "$repo_url" "$up"
fi
git -C "$up" fetch --quiet origin "$pin" 2>/dev/null || true
git -C "$up" -c advice.detachedHead=false checkout --quiet "$pin"
test "$(git -C "$up" rev-parse HEAD)" = "$pin"

# Data vintages: <name> <commit> <path in that commit>
while read -r name commit path; do
  [ -z "$name" ] && continue
  git -C "$up" show "$commit:$path" > "$cache/vintages/$name.jsonl"
done <<'EOF'
th10_2025-03-18 4f79669581d765c77ed66057cd3773839b9c4863 data/external/all_runs.jsonl
th10_2026-01-20 52d6b564d243aeb7531f1cbdc7c33a5a2cc98aaf reports/time-horizon-1-0/data/raw/runs.jsonl
th10_2026-03-05 52cb829c7a2efb2d659285c4b1768d191d97f8d2 reports/time-horizon-1-0/data/raw/runs.jsonl
th11_2026-01-20 52d6b564d243aeb7531f1cbdc7c33a5a2cc98aaf reports/time-horizon-1-1/data/raw/runs.jsonl
th11_2026-01-30 8d68adbed39022587b3d624f0ef2c6ca93e3f089 reports/time-horizon-1-1/data/raw/runs.jsonl
th11_2026-02-12 571a941b2336c417731001229281a5d2202c1e0e reports/time-horizon-1-1/data/raw/runs.jsonl
th11_2026-03-05 52cb829c7a2efb2d659285c4b1768d191d97f8d2 reports/time-horizon-1-1/data/raw/runs.jsonl
EOF
git -C "$up" show "$pin:data/external/release_dates.yaml" > "$cache/vintages/release_dates_2026-03-05.yaml"

# Published results (metr.org/time-horizons, page "no longer actively updated" since 2026-09-08).
for f in benchmark_results_1_1.yaml benchmark_results_1_0.yaml; do
  curl -sSfL --retry 3 -o "$cache/metr.org/$f" "https://metr.org/assets/$f"
done

cd "$cache"
if ! sha256sum --check --quiet "$here/sources.sha256"; then
  echo "fetch_sources: sha256 mismatch against sources.sha256 (a source changed; see README, 'Re-pinning')." >&2
  exit 1
fi
echo "fetch_sources: all sources present and verified in $cache"
