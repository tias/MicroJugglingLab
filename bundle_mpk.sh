#!/bin/sh
# Build a MicroPythonOS .mpk for org.microjugglinglab.solo (BadgeHub-ready).
# See https://docs.micropythonos.com/apps/bundling-apps/

set -e
ROOT="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
APP="org.microjugglinglab.solo"
VERSION="$(python3 -c "import json; print(json.load(open('$ROOT/$APP/MANIFEST.JSON'))['version'])")"
OUT_DIR="$ROOT/dist"
OUT="$OUT_DIR/${APP}_${VERSION}.mpk"

mkdir -p "$OUT_DIR"
rm -f "$OUT"
rm -rf "$ROOT/$APP/__pycache__"

# Fixed timestamps for deterministic packages
find "$ROOT/$APP" -exec touch -t 202501010000.00 {} \;

(
  cd "$ROOT"
  # Directories first, then files; stored (no compression); no extra attrs
  (find "$APP" -type d; find "$APP" -type f) | sort | TZ=CET zip -X -r -0 "$OUT" -@
)

echo "Wrote $OUT"
unzip -l "$OUT"
