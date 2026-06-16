#!/usr/bin/env bash
set -euo pipefail

# Run from:
#   WingLoop_Library/wingloop_testrun/
#
# It creates or refreshes:
#   aswing_geometry/
#
# The folder contains:
#   t_tail_HALE.asw
#   t_tail_HALE.pnt
#   t_tail_HALE.set
#   t_tail_HALE.state
#   gust_H40.gust

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST_DIR="${WINGLOOP_ASWING_CASE_DEST:-$SCRIPT_DIR/aswing_geometry}"

OLD_ASWING_WORK_DIR="${OLD_ASWING_WORK_DIR:-}"
OLD_GEOMETRY_FILE="${OLD_GEOMETRY_FILE:-}"

if [[ -z "$OLD_ASWING_WORK_DIR" || -z "$OLD_GEOMETRY_FILE" ]]; then
    echo "[setup] ERROR: set OLD_ASWING_WORK_DIR and OLD_GEOMETRY_FILE first."
    echo "[setup] Example:"
    echo "        OLD_ASWING_WORK_DIR=/path/to/aswing_geometry \\"
    echo "        OLD_GEOMETRY_FILE=/path/to/t_tail_HALE.asw \\"
    echo "        ./setup_aswing_case_from_old.sh"
    exit 2
fi

echo "[setup] Destination:"
echo "$DEST_DIR"

mkdir -p "$DEST_DIR"

echo "[setup] Copying old ASWING working directory..."
cp -a "$OLD_ASWING_WORK_DIR"/. "$DEST_DIR"/

echo "[setup] Copying old ASWING geometry file..."
cp -a "$OLD_GEOMETRY_FILE" "$DEST_DIR"/

echo "[setup] Final case contents:"
ls -lh "$DEST_DIR"

echo "[setup] Done."
