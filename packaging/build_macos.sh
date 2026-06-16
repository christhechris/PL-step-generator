#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
cd "$HERE/.."
python -m PyInstaller --noconfirm --clean packaging/lantern_step.spec
echo "Built dist/LanternStep.app"
# Optional DMG packaging (skipped if hdiutil is unavailable)
if command -v hdiutil >/dev/null 2>&1; then
  hdiutil create -volname "Lantern STEP" \
    -srcfolder "dist/LanternStep.app" -ov -format UDZO "dist/LanternStep.dmg"
  echo "Built dist/LanternStep.dmg"
fi
