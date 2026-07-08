# -*- mode: python ; coding: utf-8 -*-
#
# Portable PyInstaller spec for MacHuna.
# Resolves ffmpeg/ffprobe from PATH and all assets relative to this spec file,
# so it builds on any Apple Silicon Mac regardless of the Homebrew ffmpeg
# version or the username. Build with:  python3.12 -m PyInstaller MacHuna.spec -y

import os
import shutil

# Directory containing this spec file (provided by PyInstaller as SPECPATH;
# fall back to the current working directory just in case).
try:
    PROJECT_DIR = SPECPATH
except NameError:
    PROJECT_DIR = os.path.abspath(os.getcwd())


def _resolve_binary(name):
    """Find ffmpeg/ffprobe on PATH and return the real (symlink-resolved) path."""
    path = shutil.which(name)
    if not path:
        raise SystemExit(
            f"MacHuna build: '{name}' not found on PATH. "
            f"Install it first with:  brew install ffmpeg"
        )
    return os.path.realpath(path)


FFMPEG  = _resolve_binary('ffmpeg')
FFPROBE = _resolve_binary('ffprobe')

ICON = os.path.join(PROJECT_DIR, 'machuna.icns')
ICON_PNG = os.path.join(PROJECT_DIR, 'machuna_final_1024.png')
MAIN = os.path.join(PROJECT_DIR, 'machuna.py')


a = Analysis(
    [MAIN],
    pathex=[],
    binaries=[(FFMPEG, '.'), (FFPROBE, '.')],
    datas=[(ICON_PNG, '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MacHuna',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[ICON],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MacHuna',
)
app = BUNDLE(
    coll,
    name='MacHuna.app',
    icon=ICON,
    bundle_identifier=None,
)
