#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

APP_NAME="archive-goblin"
VERSION="$(python3 - <<'PY'
import tomllib
from pathlib import Path

payload = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
print(payload["project"]["version"])
PY
)"

./scripts/build-linux-app.sh

PACKAGE_ROOT="$ROOT_DIR/build/deb-root"
APP_BUNDLE="$ROOT_DIR/dist/$APP_NAME"
OUTPUT_DIR="$ROOT_DIR/release"

rm -rf "$PACKAGE_ROOT"
mkdir -p \
  "$PACKAGE_ROOT/DEBIAN" \
  "$PACKAGE_ROOT/opt/$APP_NAME" \
  "$PACKAGE_ROOT/usr/bin" \
  "$PACKAGE_ROOT/usr/share/applications" \
  "$PACKAGE_ROOT/usr/share/icons/hicolor/512x512/apps" \
  "$OUTPUT_DIR"

cp -R "$APP_BUNDLE"/* "$PACKAGE_ROOT/opt/$APP_NAME/"
cp packaging/archive-goblin.desktop "$PACKAGE_ROOT/usr/share/applications/archive-goblin.desktop"
cp archive_goblin/icons/large.png "$PACKAGE_ROOT/usr/share/icons/hicolor/512x512/apps/archive-goblin.png"

cat > "$PACKAGE_ROOT/usr/bin/archive-goblin" <<'EOF'
#!/usr/bin/env bash
exec /opt/archive-goblin/archive-goblin "$@"
EOF
chmod 755 "$PACKAGE_ROOT/usr/bin/archive-goblin"

cat > "$PACKAGE_ROOT/DEBIAN/control" <<EOF
Package: archive-goblin
Version: $VERSION
Section: utils
Priority: optional
Architecture: amd64
Maintainer: Archive Goblin
Depends: libgl1, libxcb-cursor0
Description: Archive.org preparation and upload workstation
 Archive Goblin helps review, rename, describe, and upload
 prepared folders to Archive.org.
EOF

dpkg-deb --build "$PACKAGE_ROOT" "$OUTPUT_DIR/${APP_NAME}_${VERSION}_amd64.deb"
echo "Debian package created at: $OUTPUT_DIR/${APP_NAME}_${VERSION}_amd64.deb"
