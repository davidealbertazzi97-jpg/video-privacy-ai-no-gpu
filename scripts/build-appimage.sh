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
cp -r "${APP_DIR}/native" "${APP_DIR_STAGE}/usr/bin/"
cp -r "${APP_DIR}/runtime_guard" "${APP_DIR_STAGE}/usr/bin/"
cp -r "${APP_DIR}/scripts" "${APP_DIR_STAGE}/usr/bin/"
cp -r "${APP_DIR}/static" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/product.toml" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/pyproject.toml" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/requirements-core.txt" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/install.sh" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/start.sh" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/README.md" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/LICENSE" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/NOTICE" "${APP_DIR_STAGE}/usr/bin/"
cp "${APP_DIR}/THIRD_PARTY_NOTICES.md" "${APP_DIR_STAGE}/usr/bin/"

# Never ship local bytecode: .pyc files embed the builder's absolute paths.
find "${APP_DIR_STAGE}" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.DS_Store' \) -delete
find "${APP_DIR_STAGE}" -depth -type d -name '__pycache__' -empty -delete

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
set -euo pipefail
HERE="$(dirname "$(readlink -f "${0}")")"
SOURCE_PAYLOAD="${HERE}/usr/bin"
DATA_HOME="${XDG_DATA_HOME:-${HOME}/.local/share}"
APP_PAYLOAD="${DATA_HOME}/video-privacy-studio/app-1.0.0"
MARKER="${APP_PAYLOAD}/.install-complete"
mkdir -p "${APP_PAYLOAD}"
chmod 700 "${APP_PAYLOAD}"
cp -a "${SOURCE_PAYLOAD}/." "${APP_PAYLOAD}/"
cd "${APP_PAYLOAD}"
if [[ ! -f "${MARKER}" ]]; then
  ./install.sh
  touch "${MARKER}"
fi
exec ./start.sh "$@"
EOF
chmod +x "${APP_DIR_STAGE}/AppRun"

APPIMAGETOOL="${APP_DIR}/.tools/appimagetool"
RUNTIME_FILE="${APPIMAGE_RUNTIME_FILE:-${APP_DIR}/.tools/runtime-x86_64}"
RUNTIME_SHA256="1cc49bcf1e2ccd593c379adb17c9f85a36d619088296504de95b1d06215aebbf"
if [[ ! -x "${APPIMAGETOOL}" ]]; then
  echo "Downloading appimagetool..."
  mkdir -p "${APP_DIR}/.tools"
  curl --fail --location --proto '=https' --tlsv1.2 \
    "https://github.com/AppImage/appimagetool/releases/download/1.9.1/appimagetool-x86_64.AppImage" \
    --output "${APPIMAGETOOL}"
  chmod +x "${APPIMAGETOOL}"
fi
echo "ed4ce84f0d9caff66f50bcca6ff6f35aae54ce8135408b3fa33abfc3cb384eb0  ${APPIMAGETOOL}" | sha256sum --check -

if [[ ! -f "${RUNTIME_FILE}" ]]; then
  curl --fail --location --proto '=https' --tlsv1.2 \
    "https://github.com/AppImage/type2-runtime/releases/download/continuous/runtime-x86_64" \
    --output "${RUNTIME_FILE}"
fi
echo "${RUNTIME_SHA256}  ${RUNTIME_FILE}" | sha256sum --check -

OUTPUT_APPIMAGE="${DIST_DIR}/Video-Privacy-Studio-v1.0.0-x86_64.AppImage"
ARCH=x86_64 APPIMAGE_EXTRACT_AND_RUN=1 \
  "${APPIMAGETOOL}" --runtime-file "${RUNTIME_FILE}" \
  "${APP_DIR_STAGE}" "${OUTPUT_APPIMAGE}"

echo "Linux AppImage created successfully: ${OUTPUT_APPIMAGE}"
