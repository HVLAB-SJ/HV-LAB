@echo off
echo.
echo =========================================
echo   GitHub CLI 설치 스크립트
echo =========================================
echo.

echo [1/3] GitHub CLI 다운로드 중...
powershell -Command "Start-BitsTransfer -Source 'https://github.com/cli/cli/releases/download/v2.40.1/gh_2.40.1_windows_amd64.msi' -Destination 'gh_installer.msi'"

if not exist "gh_installer.msi" (
    echo.
    echo 다운로드 실패! 브라우저에서 직접 다운로드하세요:
    echo https://github.com/cli/cli/releases/latest
    echo.
    start https://github.com/cli/cli/releases/latest
    pause
    exit /b 1
)

echo.
echo [2/3] GitHub CLI 설치 중...
echo 설치 창이 열리면 "Next"를 클릭하여 진행하세요.
start /wait msiexec /i gh_installer.msi

echo.
echo [3/3] 설치 파일 정리 중...
del gh_installer.msi

echo.
echo ✅ 설치 완료!
echo.
echo 이제 새 PowerShell 창을 열고 다음 명령을 실행하세요:
echo.
echo   gh auth login
echo.
echo 인증 과정:
echo 1. GitHub.com 선택
echo 2. HTTPS 선택  
echo 3. Y (Git 자격 증명 사용)
echo 4. Login with a web browser 선택
echo 5. 브라우저에서 코드 입력
echo.
pause 