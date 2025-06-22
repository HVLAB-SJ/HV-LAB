@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo =========================================
echo   HV-L 간편 빌드 스크립트
echo =========================================
echo.

REM 현재 버전 확인
echo [1/5] 현재 버전 확인 중...
for /f "tokens=3 delims= " %%a in ('findstr /C:"CURRENT_VERSION" HV-L.py') do (
    set CURRENT_VER=%%a
    set CURRENT_VER=!CURRENT_VER:"=!
)
echo 현재 버전: %CURRENT_VER%
echo.

REM 새 버전 입력
set /p NEW_VERSION="새 버전 번호 입력 (예: 1.6.10): "
echo.

REM HV-L.py에서 버전 업데이트
echo [2/5] 소스 코드 버전 업데이트 중...
powershell -Command "(Get-Content HV-L.py) -replace 'CURRENT_VERSION = \".*\"', 'CURRENT_VERSION = \"%NEW_VERSION%\"' | Set-Content HV-L.py"
echo ✓ 완료
echo.

REM 로컬에서 exe 빌드
echo [3/5] 로컬에서 exe 빌드 중... (시간이 걸릴 수 있습니다)
if exist "dist\HV-L.exe" del "dist\HV-L.exe"
pyinstaller HV-L.spec --clean --noconfirm
if not exist "dist\HV-L.exe" (
    echo ❌ 빌드 실패! pyinstaller가 설치되어 있는지 확인하세요.
    echo.
    echo PyInstaller 설치 방법:
    echo pip install pyinstaller
    pause
    exit /b 1
)
echo ✓ 빌드 완료
echo.

REM 빌드된 파일 백업
echo [4/5] 릴리스 파일 준비 중...
if not exist "releases" mkdir "releases"
copy "dist\HV-L.exe" "releases\HV-L_v%NEW_VERSION%.exe"
echo ✓ releases\HV-L_v%NEW_VERSION%.exe 생성 완료
echo.

REM Git 커밋 및 푸시
echo [5/5] Git 업데이트 중...
git add .
git commit -m "Update to v%NEW_VERSION%"
git push origin master

REM 태그 생성 및 푸시
git tag v%NEW_VERSION%
git push origin v%NEW_VERSION%
echo ✓ 완료
echo.

echo =========================================
echo   ✅ 빌드 완료!
echo =========================================
echo.
echo 이제 수동으로 GitHub Release를 생성하세요:
echo.
echo 1. 아래 링크 클릭 (Ctrl+클릭):
echo    https://github.com/HVLAB-SJ/HV-LAB/releases/new
echo.
echo 2. Choose a tag: v%NEW_VERSION% 선택
echo.
echo 3. Release title: HV-L v%NEW_VERSION%
echo.
echo 4. 파일 업로드:
echo    releases\HV-L_v%NEW_VERSION%.exe 파일을 드래그 앤 드롭
echo.
echo 5. "Publish release" 클릭
echo.
echo 빌드된 파일 위치: %CD%\releases\HV-L_v%NEW_VERSION%.exe
echo.

REM 파일 탐색기 열기
start explorer "releases"

pause 