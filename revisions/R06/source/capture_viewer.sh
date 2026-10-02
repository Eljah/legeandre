#!/usr/bin/env bash
set -eu
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
Xvfb :96 -screen 0 1550x1000x24 > "$ROOT/tests/xvfb.log" 2>&1 & XVFB_PID=$!
trap 'kill "$VIEW_PID" "$XVFB_PID" 2>/dev/null || true' EXIT
sleep 1
DISPLAY=:96 python "$ROOT/source/render_r06.py" --viewer > "$ROOT/tests/viewer.log" 2>&1 & VIEW_PID=$!
sleep 8
ROOT="$ROOT" python - <<'PY'
from PIL import ImageGrab
from pathlib import Path
import os,hashlib,json
root=Path(os.environ['ROOT'])
p=root/'screenshots/VTK_R06_actual.png'
ImageGrab.grab(xdisplay=':96').save(p)
(root/'tests/screenshot_provenance.json').write_text(json.dumps({'method':'Pillow ImageGrab from actual Xvfb X11 display :96','application':'source/render_r06.py --viewer','image':str(p.relative_to(root)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'synthetic_UI_image_generation':False},indent=2))
PY
