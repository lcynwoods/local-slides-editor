# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for slides_editor.
Builds a Windows executable with all dependencies bundled.
"""
import os
import sys

# Find site-packages in current environment
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # Virtual environment
    site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')
else:
    # Conda or system
    site_packages = os.path.join(sys.prefix, 'Lib', 'site-packages')

block_cipher = None

a = Analysis(
    ['slides_editor.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include NiceGUI static files (auto-detect from environment)
        (os.path.join(site_packages, 'nicegui'), 'nicegui'),
    ],
    hiddenimports=[
        'nicegui',
        'aiohttp',
        'pyperclip',
        'appdirs',
        'cryptography',
        'bs4',
        'lxml',
        'app.config',
        'app.local_server',
        'app.https_server',
        'app.slides_api',
        'app.ui.home',
        'app.ui.plots',
        'app.ui.advanced',
        'app.utils.zip_utils',
        'app.utils.file_utils',
        'app.utils.find_replace',
        'app.utils.reveal_detector',
        'app.utils.html_to_json',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='SlidesEditor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # Set to False for GUI app (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add path to .ico file if you have one
)
