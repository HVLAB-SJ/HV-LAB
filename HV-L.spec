# -*- mode: python ; coding: utf-8 -*-

import os
import sys
import shutil
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# 현재 디렉토리
current_dir = os.path.dirname(os.path.abspath(SPEC))

# 데이터 파일들
datas = [
    ('HV.ico', '.'),
    ('login_dialog.py', '.')
]

# serviceAccountKey.json이 있으면 포함
if os.path.exists('serviceAccountKey.json'):
    datas.append(('serviceAccountKey.json', '.'))

# numpy의 모든 DLL 수집
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all('numpy')
datas += numpy_datas
binaries = numpy_binaries

a = Analysis(
    ['HV-L.py'],
    pathex=[current_dir],
    binaries=binaries,
    datas=datas,
    hiddenimports=[
        # Firebase 관련
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
        'google.protobuf',
        'grpc',
        'grpc._channel',
        # PyQt5 관련
        'PyQt5',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtNetwork',
        'PyQt5.QtPrintSupport',
        'PyQt5.sip',
        # pandas/numpy 관련
        'pandas',
        'pandas.io.excel',
        'pandas.io.excel._base',
        'pandas.io.excel._openpyxl',
        'pandas.io.parsers',
        'pandas.io.parsers.readers',
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'numpy.random',
        'numpy.random._pickle',
        # 기타
        'openpyxl',
        'dateutil',
        'pytz',
        'six',
        'urllib3',
        'requests',
        'certifi',
        'charset_normalizer',
        'idna'
    ] + numpy_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # 테스트 모듈 제외
        'test',
        'tests',
        'pandas.tests',
        'numpy.tests',
        'numpy.distutils.tests',
        'numpy.f2py.tests',
        # 불필요한 PyQt5 모듈 제외
        'PyQt5.QtBluetooth',
        'PyQt5.QtDBus',
        'PyQt5.QtDesigner',
        'PyQt5.QtHelp',
        'PyQt5.QtLocation',
        'PyQt5.QtMacExtras',
        'PyQt5.QtMultimedia',
        'PyQt5.QtMultimediaWidgets',
        'PyQt5.QtNfc',
        'PyQt5.QtOpenGL',
        'PyQt5.QtPositioning',
        'PyQt5.QtQml',
        'PyQt5.QtQuick',
        'PyQt5.QtQuickWidgets',
        'PyQt5.QtRemoteObjects',
        'PyQt5.QtScript',
        'PyQt5.QtSensors',
        'PyQt5.QtSerialPort',
        'PyQt5.QtSql',
        'PyQt5.QtSvg',
        'PyQt5.QtTest',
        'PyQt5.QtWebChannel',
        'PyQt5.QtWebEngine',
        'PyQt5.QtWebEngineCore',
        'PyQt5.QtWebEngineWidgets',
        'PyQt5.QtWebSockets',
        'PyQt5.QtWinExtras',
        'PyQt5.QtX11Extras',
        'PyQt5.QtXml',
        'PyQt5.QtXmlPatterns',
        # 기타 불필요한 모듈
        'matplotlib',
        'scipy',
        'sklearn',
        'IPython',
        'jupyter',
        'notebook',
        'tkinter',
        'win32com',
        'pythoncom'
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
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join(current_dir, 'HV.ico'),
    onefile=True,  # 단일 파일로 생성
) 