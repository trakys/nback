# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['nback_experiment.py'],
    pathex=[],
    binaries=[],
    datas=[('sample_sheet.csv', '.'), ('entitlements.plist', '.')],
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
    name='NBackExperiment',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file='entitlements.plist',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='NBackExperiment',
)
app = BUNDLE(
    coll,
    name='NBackExperiment.app',
    icon=None,
    bundle_identifier='com.yourcompany.nback',
)
