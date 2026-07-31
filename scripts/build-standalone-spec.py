#!/usr/bin/env python3
"""PyInstaller spec builder for Video Privacy Studio executables."""

from __future__ import annotations

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
DIST_DIR = APP_DIR / "dist"
DIST_DIR.mkdir(parents=True, exist_ok=True)

SPEC_CONTENT = f"""# -*- mode: python ; coding: utf-8 -*-

datas = [
    ('{APP_DIR}/app', 'app'),
    ('{APP_DIR}/static', 'static'),
    ('{APP_DIR}/product.toml', '.'),
    ('{APP_DIR}/requirements-core.txt', '.'),
    ('{APP_DIR}/LICENSE', '.'),
    ('{APP_DIR}/README.md', '.'),
]

blockcipher = None

a = Analysis(
    ['{APP_DIR}/scripts/start.py'],
    pathex=['{APP_DIR}'],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'cv2',
        'PIL',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=blockcipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=blockcipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Video-Privacy-Studio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='{APP_DIR}/static/icon.png',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='Video-Privacy-Studio',
)
"""

spec_path = APP_DIR / "Video-Privacy-Studio.spec"
spec_path.write_text(SPEC_CONTENT, encoding="utf-8")
print(f"Created PyInstaller specification file: {spec_path}")
