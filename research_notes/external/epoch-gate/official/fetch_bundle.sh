#!/usr/bin/env bash
# Fetch Epoch's GATE playground bundle and check it against the pinned hash.
#
#   official/fetch_bundle.sh <dest-dir>
#
# The bundle is served at a mutable URL with no version in its path, so the SHA-256 is
# the pin. A mismatch means Epoch has redeployed the playground: that is a finding to
# record (new hash, date, what changed), not something to paper over by editing the pin.
# The bundle is not vendored: its code carries no license statement (see SOURCES.yaml).
set -euo pipefail

URL="https://epoch.ai/generated/gate.js"
SHA256="c2104290dc486c27e07b6614dd306604bd98a095d660369d3ce356f481e72731"

dest="${1:?usage: fetch_bundle.sh <dest-dir>}"
mkdir -p "$dest"
curl -sSfL --retry 3 -o "$dest/gate.js" "$URL"
got="$(sha256sum "$dest/gate.js" | cut -d' ' -f1)"
if [ "$got" != "$SHA256" ]; then
  echo "gate.js hash mismatch: expected $SHA256, got $got" >&2
  echo "The playground was redeployed after 2026-10-25. Record the new hash as a finding." >&2
  exit 1
fi
echo "gate.js OK ($SHA256)"
