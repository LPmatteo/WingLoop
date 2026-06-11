#!/usr/bin/env bash
set -euo pipefail

# Run from:
#   WingLoop_Library/wingloop_testrun/
#
# It creates:
#   aswing_cases/t_tail_HALE/
#
# The folder contains:
#   t_tail_HALE.asw
#   t_tail_HALE.pnt
#   t_tail_HALE.set
#   t_tail_HALE.state
#   gust_H40.gust

DEST_DIR="$(pwd)/aswing_cases/t_tail_HALE"

OLD_ASWING_WORK_DIR="/home/lpmatteo/Internship_INCARBONE_2026/LQR_first_controller_study/LQR_WL_simulation/aswing_geometry"
OLD_GEOMETRY_FILE="/home/lpmatteo/Internship_INCARBONE_2026/Geometries/t_tail_HALE.asw"

echo "[setup] Destination:"
echo "$DEST_DIR"

rm -rf "$DEST_DIR"
mkdir -p "$DEST_DIR"

echo "[setup] Copying old ASWING working directory..."
cp -a "$OLD_ASWING_WORK_DIR"/. "$DEST_DIR"/

echo "[setup] Copying old ASWING geometry file..."
cp -a "$OLD_GEOMETRY_FILE" "$DEST_DIR"/

echo "[setup] Final case contents:"
ls -lh "$DEST_DIR"

echo "[setup] Done."
