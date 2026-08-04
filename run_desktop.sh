#!/bin/sh
# Run MicroJugglingLab on desktop MicroPythonOS (no badge required).
#
# Expects MicroPythonOS/ inside this repo (or set MPOS_ROOT).
#
# Usage:
#   ./run_desktop.sh                 # start org.microjugglinglab.solo
#   ./run_desktop.sh --launcher      # start full OS launcher only
#   MPOS_ROOT=/other/path ./run_desktop.sh

set -e

ROOT="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
APP="org.microjugglinglab.solo"
APP_DIR="$ROOT/$APP"

# Prefer in-repo MicroPythonOS/; allow MPOS_ROOT override
if [ -n "${MPOS_ROOT:-}" ]; then
  :
elif [ -d "$ROOT/MicroPythonOS/scripts" ]; then
  MPOS_ROOT="$ROOT/MicroPythonOS"
else
  echo "MicroPythonOS/ not found in this repo." >&2
  echo "Clone it here, then install the desktop binary (see README.md):" >&2
  echo "  git clone --recurse-submodules --depth 1 --shallow-submodules \\" >&2
  echo "    https://github.com/MicroPythonOS/MicroPythonOS.git MicroPythonOS" >&2
  exit 1
fi

RUNNER="$MPOS_ROOT/scripts/run_desktop.sh"
if [ ! -f "$RUNNER" ]; then
  echo "Missing $RUNNER" >&2
  exit 1
fi

os_name="$(uname -s)"
if [ "$os_name" = "Darwin" ]; then
  BINARY="$MPOS_ROOT/lvgl_micropython/build/lvgl_micropy_macOS"
else
  BINARY="$MPOS_ROOT/lvgl_micropython/build/lvgl_micropy_unix"
fi
if [ ! -f "$BINARY" ]; then
  echo "Desktop binary not found: $BINARY" >&2
  echo "Download from https://github.com/MicroPythonOS/MicroPythonOS/releases" >&2
  echo "and place it there (chmod +x)." >&2
  exit 1
fi
chmod +x "$BINARY" 2>/dev/null || true

APPS_DIR="$MPOS_ROOT/internal_filesystem/apps"
mkdir -p "$APPS_DIR"
LINK="$APPS_DIR/$APP"
if [ -e "$LINK" ] && [ ! -L "$LINK" ]; then
  echo "Warning: $LINK exists and is not a symlink; leaving it alone." >&2
else
  ln -sfn "$APP_DIR" "$LINK"
fi

echo "MPOS_ROOT=$MPOS_ROOT"

if [ "${1:-}" = "--launcher" ]; then
  shift
  echo "Starting MicroPythonOS launcher (open MicroJugglingLab from the menu)."
  exec bash "$RUNNER" "$@"
fi

echo "Starting $APP ..."
exec bash "$RUNNER" "$APP" "$@"
