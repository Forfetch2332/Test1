# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all

# collect_all возвращает (binaries, datas, hiddenimports)
binaries, datas, hiddenimports = collect_all("PyQt5")

block_cipher = None

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas + [
        ('content', 'content'),
        ('ui', 'ui'),
        ('assets', 'assets'),
    ],
    hiddenimports=hiddenimports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InteractiveTutorial',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,   # True если нужна консоль для отладки
    icon='assets/icon.ico'
)
