#!/usr/bin/env bash
set -euo pipefail

: "${MOON_DASHBOARD_DIR:?Set the existing dashboard directory}"
: "${MOON_PYTHON:?Set the dashboard Python executable}"
repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
if ! "$MOON_PYTHON" "$repo_dir/scripts/push_window.py"; then
  echo "Outside publishing hours (Asia/Shanghai); skipped."
  exit 0
fi
git -C "$repo_dir" pull --ff-only origin main
"$MOON_PYTHON" "$repo_dir/scripts/export_snapshot.py" \
  --dashboard-dir "$MOON_DASHBOARD_DIR" --output-dir "$repo_dir/site/data"
git -C "$repo_dir" add -- site/data/moon.json
if git -C "$repo_dir" diff --cached --quiet -- site/data/moon.json; then
  exit 0
fi
git -C "$repo_dir" commit --only -m "Update MOON performance snapshot" -- site/data/moon.json
git -C "$repo_dir" push origin main
