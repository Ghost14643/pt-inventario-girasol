#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

"$PYTHON_BIN" -m PyInstaller --clean --name tienda-api --onefile --exclude-module _mysql_connector --collect-submodules mysql.connector.plugins --collect-submodules mysql.connector.locales --collect-data mysql.connector --paths "$ROOT_DIR" server.py
TARGET_TRIPLE="${TAURI_TARGET_TRIPLE:-$(rustc --print host-tuple 2>/dev/null || rustc -vV | sed -n 's/^host: //p')}"
if [[ -z "$TARGET_TRIPLE" ]]; then
  echo "No se pudo detectar el target triple de Rust" >&2
  exit 1
fi

mkdir -p src-tauri/binaries
case "$TARGET_TRIPLE" in
  *windows*) EXT=".exe" ;;
  *) EXT="" ;;
esac
cp "dist/tienda-api${EXT}" "src-tauri/binaries/tienda-api-${TARGET_TRIPLE}${EXT}"
echo "Sidecar actualizado: src-tauri/binaries/tienda-api-${TARGET_TRIPLE}${EXT}"
