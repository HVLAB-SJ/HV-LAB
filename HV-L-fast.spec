# -*- mode: python ; coding: utf-8 -*-
# 빠른 빌드를 위한 개발용 spec 파일

import os
import sys

block_cipher = None
current_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['HV-L.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('HV.ico', '.'),
    ] + ([('serviceAccountKey.json', '.')] if os.path.exists('serviceAccountKey.json') else []),
    hiddenimports=[
        'google.cloud.firestore',
        'PyQt5',
        'pandas',
        'requests',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'notebook', 'tkinter'],  # 불필요한 모듈 제외
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
    name='HV-L-dev',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX 비활성화로 빌드 시간 단축
    runtime_tmpdir=None,
    console=True,  # 개발 중 디버깅용 콘솔 표시
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(current_dir, 'HV.ico')
) 