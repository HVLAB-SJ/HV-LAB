@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo =========================================
echo   HV-L 직접 빌드 및 업로드 스크립트
echo =========================================
echo.

REM 현재 버전 확인
echo [1/7] 현재 버전 확인 중...
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
echo [2/7] 소스 코드 버전 업데이트 중...
powershell -Command "(Get-Content HV-L.py) -replace 'CURRENT_VERSION = \".*\"', 'CURRENT_VERSION = \"%NEW_VERSION%\"' | Set-Content HV-L.py"
echo ✓ 완료
echo.

REM 로컬에서 exe 빌드
echo [3/7] 로컬에서 exe 빌드 중... (시간이 걸릴 수 있습니다)
if exist "dist\HV-L.exe" del "dist\HV-L.exe"
pyinstaller HV-L.spec --clean --noconfirm
if not exist "dist\HV-L.exe" (
    echo ❌ 빌드 실패! pyinstaller가 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)
echo ✓ 빌드 완료
echo.

REM Git 커밋 및 푸시
echo [4/7] 변경사항 커밋 중...
git add .
git commit -m "Update to v%NEW_VERSION%"
git push origin master
echo ✓ 완료
echo.

REM 태그 생성 및 푸시
echo [5/7] Git 태그 생성 중...
git tag v%NEW_VERSION%
git push origin v%NEW_VERSION%
echo ✓ 완료
echo.

REM GitHub CLI 설치 확인
echo [6/7] GitHub CLI 확인 중...
where gh >nul 2>nul
if %errorlevel% neq 0 (
    echo ❌ GitHub CLI가 설치되어 있지 않습니다.
    echo.
    echo GitHub CLI 설치 방법:
    echo 1. https://cli.github.com/ 에서 다운로드
    echo 2. 또는 PowerShell에서: winget install --id GitHub.cli
    echo.
    echo 설치 후 'gh auth login' 명령으로 인증하세요.
    pause
    exit /b 1
)

REM GitHub 인증 확인
gh auth status >nul 2>nul
if %errorlevel% neq 0 (
    echo GitHub 인증이 필요합니다. 다음 명령을 실행하세요:
    echo gh auth login
    pause
    exit /b 1
)
echo ✓ GitHub CLI 준비 완료
echo.

REM Release 생성 및 exe 업로드
echo [7/7] GitHub Release 생성 및 exe 업로드 중...
gh release create v%NEW_VERSION% "dist\HV-L.exe" ^
    --title "HV-L v%NEW_VERSION%" ^
    --notes "## 변경사항`n`n- 업데이트된 기능들`n- 버그 수정`n`n## 다운로드`n`n아래 Assets에서 HV-L.exe를 다운로드하세요." ^
    --latest

if %errorlevel% equ 0 (
    echo.
    echo =========================================
    echo   ✅ 업로드 완료!
    echo =========================================
    echo.
    echo 버전 v%NEW_VERSION%이(가) 성공적으로 업로드되었습니다.
    echo.
    echo Release 확인: https://github.com/HVLAB-SJ/HV-LAB/releases/tag/v%NEW_VERSION%
    echo.
) else (
    echo.
    echo ❌ Release 생성 실패!
    echo 수동으로 업로드하려면:
    echo 1. https://github.com/HVLAB-SJ/HV-LAB/releases/new 접속
    echo 2. Tag: v%NEW_VERSION% 선택
    echo 3. dist\HV-L.exe 파일 드래그 앤 드롭
    echo.
)

pause 