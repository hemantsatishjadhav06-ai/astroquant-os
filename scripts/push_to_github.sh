#!/usr/bin/env bash
# Push this repository to a GitHub repo you have created (empty: no README/license).
#
#   1) Create an empty repo on GitHub, e.g.  https://github.com/<you>/astroquant-os
#   2) Run:  bash scripts/push_to_github.sh git@github.com:<you>/astroquant-os.git
#      (or the https URL:  https://github.com/<you>/astroquant-os.git )
#
# Re-runnable: updates the remote if it already exists.
set -euo pipefail
REMOTE_URL="${1:-}"
if [[ -z "$REMOTE_URL" ]]; then
  echo "usage: bash scripts/push_to_github.sh <git-remote-url>" >&2
  exit 1
fi
if git remote | grep -q '^origin$'; then
  git remote set-url origin "$REMOTE_URL"
else
  git remote add origin "$REMOTE_URL"
fi
git branch -M main
git push -u origin main
echo "Pushed to $REMOTE_URL (branch: main)."
