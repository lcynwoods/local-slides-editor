# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for slides_editor.
Builds a Windows executable with all dependencies bundled.
"""

block_cipher = None

a = Analysis(
    ['slides_editor.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Include NiceGUI static files
        ('venv/Lib/site-packages/nicegui', 'nicegui'),
    ],
    hiddenimports=[
        'nicegui',
        'aiohttp',
        'pyperclip',
        'appdirs',
        'app.config',
        'app.local_server',
        'app.slides_api',
        'app.ui.home',
        'app.ui.plots',
        'app.ui.advanced',
        'app.utils.zip_utils',
        'app.utils.file_utils',
        'app.utils.find_replace',
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
