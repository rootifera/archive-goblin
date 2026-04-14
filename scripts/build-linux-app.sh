#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

python3 -m PyInstaller \
  --noconfirm \
  --clean \
  --windowed \
  --name "archive-goblin" \
  --icon "archive_goblin/icons/large.png" \
  --add-data "archive_goblin/icons:archive_goblin/icons" \
  archive_goblin/main.py

echo "Standalone app bundle created in: $ROOT_DIR/dist/archive-goblin"
