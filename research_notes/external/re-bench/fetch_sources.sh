#!/usr/bin/env bash
# Fetch the pinned RE-Bench sources into a local cache (not committed) and verify them by sha256.
#
#   bash fetch_sources.sh            # cache in ./.upstream (git-ignored), or $RB_CACHE
#
# Needs network: github.com (git clone) and arxiv.org (HTTPS). Nothing is vendored: RE-Bench is MIT but
# METR asks that task material stay out of training data, eval-analysis-public has no LICENSE file, and the
# arXiv paper is under arXiv's non-exclusive distribution licence. data/ holds only numbers derived from
# these, with attribution. A hash mismatch is a finding (a source changed): the script stops.
set -euo pipefail

here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cache="${RB_CACHE:-$here/.upstream}"
mkdir -p "$cache/files/re-bench" "$cache/files/metr" "$cache/files/arxiv/v1" "$cache/files/arxiv/v2"

clone_at() {  # <url> <dir> <commit>
  if [ ! -d "$2/.git" ]; then git clone --quiet --filter=blob:none "$1" "$2"; fi
  git -C "$2" fetch --quiet origin "$3" 2>/dev/null || true
  git -C "$2" -c advice.detachedHead=false checkout --quiet "$3"
  test "$(git -C "$2" rev-parse HEAD)" = "$3"
}

# RE-Bench at its last commit (2026-10-20, deprecation notice only; task files unchanged since 93b9806, 2025-01-30).
rb_pin="a0cc6d4a91b20f84ebef505d5c72358f88b3b389"
clone_at "https://github.com/METR/RE-Bench" "$cache/RE-Bench" "$rb_pin"
for f in README.md suite_manifest.yaml \
         ai_rd_fix_embedding/README.md ai_rd_fix_embedding/assets/score.py \
         ai_rd_nanogpt_chat_rl/README.md \
         ai_rd_optimize_llm_foundry/README.md ai_rd_optimize_llm_foundry/assets/score.py \
         ai_rd_restricted_mlm/README.md ai_rd_restricted_mlm/assets/score.py \
         ai_rd_rust_codecontests_inference/README.md \
         ai_rd_small_scaling_law/README.md ai_rd_small_scaling_law/ai_rd_small_scaling_law.py \
         ai_rd_triton_cumsum/README.md ai_rd_triton_cumsum/assets/score.py; do
  mkdir -p "$cache/files/re-bench/$(dirname "$f")"
  git -C "$cache/RE-Bench" show "$rb_pin:$f" > "$cache/files/re-bench/$f"
done

# METR's released run-level data (RE-Bench rows are part of the TH1.0 and TH1.1 suites), same pin as #12.
eap_pin="52cb829c7a2efb2d659285c4b1768d191d97f8d2"   # 2026-03-05 "Sync public pipeline (#39)"
clone_at "https://github.com/METR/eval-analysis-public" "$cache/eval-analysis-public" "$eap_pin"
git -C "$cache/eval-analysis-public" show "$eap_pin:reports/time-horizon-1-0/data/raw/runs.jsonl" > "$cache/files/metr/th10_runs.jsonl"
git -C "$cache/eval-analysis-public" show "$eap_pin:reports/time-horizon-1-1/data/raw/runs.jsonl" > "$cache/files/metr/th11_runs.jsonl"
git -C "$cache/eval-analysis-public" show "$eap_pin:data/external/release_dates.yaml" > "$cache/files/metr/release_dates.yaml"

# The paper's LaTeX source, both arXiv versions (only report.tex is kept; the tarballs are not hashed).
for v in v1 v2; do
  tmp="$(mktemp -d)"
  curl -sSfL --retry 3 -o "$tmp/src.tar.gz" "https://arxiv.org/e-print/2411.15114$v"
  tar xzf "$tmp/src.tar.gz" -C "$tmp" report.tex
  mv "$tmp/report.tex" "$cache/files/arxiv/$v/report.tex"
  rm -rf "$tmp"
done

cd "$cache/files"
if ! sha256sum --check --quiet "$here/sources.sha256"; then
  echo "fetch_sources: sha256 mismatch against sources.sha256 (a source changed; record a new pin, see README)." >&2
  exit 1
fi
echo "fetch_sources: all sources present and verified in $cache/files"
