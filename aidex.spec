# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['aidex.py'],
    pathex=['.'], 
    binaries=[],
    datas=[('icon.icns',  '.')],
    hiddenimports=['pyotp', 'pyperclip', 'qt_material', 'PyQt5', 'AppKit'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6'], 
    noarchive=True,
    optimize=0,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='aidex',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='icon.icns',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='aidex'
)

app = BUNDLE(
    coll,
    name='aidex.app',  # .app 后缀
    icon='icon.icns',
    bundle_identifier=None,
)
