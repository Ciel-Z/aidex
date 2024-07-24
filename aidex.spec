# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['aidex.py'],
    pathex=['.'],  # 确保当前目录在路径中
    binaries=[],
    datas=[('icon.png', '.')],
    hiddenimports=['pyotp', 'pyperclip', 'qt_material', 'PyQt5'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt6'],  # 确保排除 PyQt6
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
    icon='icon.png',  # 确保这是一个字符串
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
    name='aidex.app',  # 确保名称带有 .app 后缀
    icon='icon.png',
    bundle_identifier=None,
)