#!/usr/bin/env bash
# Real X11 root captures, not composited interfaces. Requires Xvfb, Pillow/XCB, Inkscape.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export DISPLAY=:97 NO_AT_BRIDGE=1
Xvfb "$DISPLAY" -screen 0 1600x1100x24 -nolisten tcp >"$ROOT/tests/xvfb.log" 2>&1 & XPID=$!
trap 'kill -9 "$XPID" 2>/dev/null || true' EXIT
sleep 2
for state in closed open; do
  OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python "$ROOT/source/viewer.py" --state "$state" >"$ROOT/tests/viewer_${state}.log" 2>&1 & VP=$!
  sleep 10
  python "$ROOT/source/grab_x11.py" "$ROOT/screenshots/VTK_actual_${state}.png"
  kill -9 "$VP" 2>/dev/null || true
  wait "$VP" 2>/dev/null || true
  sleep 1
done
inkscape --with-gui --app-id-tag=R04proof "$ROOT/patterns/pieces/HC_OUTER.svg" >"$ROOT/tests/inkscape_view.log" 2>&1 & IP=$!
sleep 7
python "$ROOT/source/prepare_inkscape_window.py" >"$ROOT/tests/inkscape_window.log"
sleep 3
python "$ROOT/source/grab_x11.py" "$ROOT/screenshots/Inkscape_actual_HC_OUTER.png"
kill -9 "$IP" 2>/dev/null || true
wait "$IP" 2>/dev/null || true
