#!/usr/bin/env bash
set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIST_DIR="${APP_DIR}/dist"
BUILD_DIR="${APP_DIR}/build/local-appimage"
APP_DIR_STAGE="${BUILD_DIR}/AppDir"

mkdir -p "${DIST_DIR}" "${BUILD_DIR}"
rm -rf "${APP_DIR_STAGE}"
mkdir -p "${APP_DIR_STAGE}/usr/bin" "${APP_DIR_STAGE}/usr/share/icons/hicolor/scalable/apps"

echo "--- BUILDING LINUX APPIMAGE FOR VIDEO PRIVACY STUDIO ---"

cp -r "${APP_DIR}/app" "${APP_DIR_STAGE}/usr/bin/"
cp -r "${APP_DIR}/scripts" "${APP_DIR_STAGE}/usr/bin/"
cp -r "${APP_DIR}/static" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/product.toml" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/requirements-core.txt" "${APP_DIR_STAGE}/usr/bin/"

if [[ -f "${APP_DIR}/static/icon.png" ]]; then
  cp "${APP_DIR}/static/icon.png" "${APP_DIR_STAGE}/usr/share/icons/hicolor/scalable/apps/video-privacy-studio.png"
  cp "${APP_DIR}/static/icon.png" "${APP_DIR_STAGE}/video-privacy-studio.png"
fi

cat <<'EOF' > "${APP_DIR_STAGE}/video-privacy-studio.desktop"
[Desktop Entry]
Version=1.0
Type=Application
Name=Video Privacy Studio
Comment=Workstation locale per l'oscuramento automatico di volti e targhe nei video su CPU
Exec=AppRun
Icon=video-privacy-studio
Categories=Utility;Security;AudioVideo;
Terminal=false
StartupNotify=true
EOF

cat <<'EOF' > "${APP_DIR_STAGE}/AppRun"
#!/usr/bin/env bash
HERE="$(dirname "$(readlink -f "${0}")")"
export PATH="${HERE}/usr/bin:${PATH}"
cd "${HERE}/usr/bin"
exec python3 scripts/start.py "$@"
EOF
chmod +x "${APP_DIR_STAGE}/AppRun"

APPIMAGETOOL="${APP_DIR}/.tools/appimagetool"
if [[ ! -x "${APPIMAGETOOL}" ]]; then
  echo "Downloading appimagetool..."
  mkdir -p "${APP_DIR}/.tools"
  curl -sSL "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage" -o "${APPIMAGETOOL}" || \
  curl -sSL "https://github.com/AppImage/AppImageKit/releases/download/13/appimagetool-x86_64.AppImage" -o "${APPIMAGETOOL}"
  chmod +x "${APPIMAGETOOL}"
fi

OUTPUT_APPIMAGE="${DIST_DIR}/Video-Privacy-Studio-v1.0.0-x86_64.AppImage"
ARCH=x86_64 "${APPIMAGETOOL}" "${APP_DIR_STAGE}" "${OUTPUT_APPIMAGE}"

echo "Linux AppImage created successfully: ${OUTPUT_APPIMAGE}"
