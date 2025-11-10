# snake.spec
# -*- mode: python ; coding: utf-8 -*-
import sys
block_cipher = None
project_dir = r"D:\projects\Games\Snake"

a = Analysis(
    [r"%s\snake.py" % project_dir],
    pathex=[project_dir],
    binaries=[],
    datas=[(r"%s\snake_head.ico" % project_dir, '.' )],
    hiddenimports=[],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='snake',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=r"%s\snake_head.ico" % project_dir
)
coll = COLLECT(exe, a.binaries, a.zipfiles, a.datas, strip=False, upx=True, name='snake')
