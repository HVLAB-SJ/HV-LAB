# -*- mode: python ; coding: utf-8 -*-

import os
import sys

block_cipher = None

# 현재 디렉토리
current_dir = os.path.dirname(os.path.abspath(SPEC))

a = Analysis(
    ['HV-L.py'],
    pathex=[current_dir],
    binaries=[],
    datas=[
        ('HV.ico', '.'),
        ('login_dialog.py', '.')
    ] + ([('serviceAccountKey.json', '.')] if os.path.exists('serviceAccountKey.json') else []),
    hiddenimports=[
        'google.cloud.firestore',
        'google.cloud.firestore_v1',
        'google.cloud.firestore_bundle',
        'google.auth',
        'google.auth.transport',
        'google.auth.transport.requests',
        'google.oauth2',
        'google.oauth2.service_account',
        'google.api_core',
        'google.api_core.gapic_v1',
        'google.api_core.retry',
        'google.api_core.grpc',
        'google.api_core.grpc_helpers',
        'google.protobuf',
        'grpc',
        'grpc._channel',
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtNetwork',
        'PyQt5.QtPrintSupport',
        'PyQt5.sip',
        'pandas',
        'pandas.io.excel',
        'pandas.io.excel._base',
        'pandas.io.excel._openpyxl',
        'numpy',
        'numpy.core',
        'openpyxl',
        'openpyxl.workbook',
        'openpyxl.worksheet',
        'openpyxl.cell',
        'openpyxl.styles',
        'dateutil',
        'urllib3',
        'requests',
        'certifi',
        'charset_normalizer',
        'idna'
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pandas.tests',
        'numpy.tests',
        'PyQt5.QtTest',
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtQuick',
        'PyQt5.QtQml',
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtOpenGL',
        'PyQt5.QtSql',
        'PyQt5.QtXml',
        'PyQt5.QtSvg',
        'matplotlib',
        'scipy',
        'sklearn',
        'IPython',
        'jupyter',
        'notebook'
    ],
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
    name='HV-L',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 콘솔 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(current_dir, 'HV.ico')
) 