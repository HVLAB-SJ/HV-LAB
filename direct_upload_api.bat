@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo =========================================
echo   HV-L 직접 빌드 및 업로드 스크립트 (API)
echo =========================================
echo.

REM 현재 버전 확인
echo [1/8] 현재 버전 확인 중...
for /f "tokens=3 delims= " %%a in ('findstr /C:"CURRENT_VERSION" HV-L.py') do (
    set CURRENT_VER=%%a
    set CURRENT_VER=!CURRENT_VER:"=!
)
echo 현재 버전: %CURRENT_VER%
echo.

REM 새 버전 입력
set /p NEW_VERSION="새 버전 번호 입력 (예: 1.6.10): "
echo.

REM Python 스크립트를 사용하여 버전 업데이트 (인코딩 보존)
echo [2/8] 소스 코드 버전 업데이트 중...
echo import re > update_version.py
echo with open('HV-L.py', 'r', encoding='utf-8') as f: >> update_version.py
echo     content = f.read() >> update_version.py
echo content = re.sub(r'CURRENT_VERSION = ".*"', 'CURRENT_VERSION = "%NEW_VERSION%"', content) >> update_version.py
echo with open('HV-L.py', 'w', encoding='utf-8') as f: >> update_version.py
echo     f.write(content) >> update_version.py
python update_version.py
del update_version.py
echo ✓ 완료
echo.

REM 로컬에서 exe 빌드
echo [3/8] 로컬에서 exe 빌드 중... (시간이 걸릴 수 있습니다)
if exist "dist\HV-L.exe" del "dist\HV-L.exe"
pyinstaller HV-L.spec --clean --noconfirm
if not exist "dist\HV-L.exe" (
    echo ❌ 빌드 실패! pyinstaller가 설치되어 있는지 확인하세요.
    pause
    exit /b 1
)
echo ✓ 빌드 완료
echo.

REM 파일 크기 확인
echo [4/8] 빌드된 파일 정보...
for %%F in ("dist\HV-L.exe") do (
    set FILE_SIZE=%%~zF
    set /a FILE_SIZE_MB=!FILE_SIZE! / 1048576
    echo 파일 크기: !FILE_SIZE! bytes (약 !FILE_SIZE_MB! MB)
)
echo.

REM 빌드된 파일 백업
echo [5/8] 릴리스 파일 백업 중...
if not exist "releases" mkdir "releases"
copy "dist\HV-L.exe" "releases\HV-L_v%NEW_VERSION%.exe"
echo ✓ releases\HV-L_v%NEW_VERSION%.exe 생성 완료
echo.

REM Git 커밋 및 푸시
echo [6/8] 변경사항 커밋 중...
git add .
git commit -m "Update to v%NEW_VERSION%"
git push origin master
echo ✓ 완료
echo.

REM 태그 생성 및 푸시
echo [7/8] Git 태그 생성 중...
git tag v%NEW_VERSION%
git push origin v%NEW_VERSION%
echo ✓ 완료
echo.

REM 수동 업로드 안내
echo [8/8] 수동 업로드 안내
echo.
echo =========================================
echo   ✅ 빌드 및 Git 업데이트 완료!
echo =========================================
echo.
echo 이제 수동으로 GitHub Release를 생성하세요:
echo.
echo 1. 아래 링크를 브라우저에서 열기:
echo    https://github.com/HVLAB-SJ/HV-LAB/releases/new
echo.
echo 2. 다음 정보 입력:
echo    - Choose a tag: v%NEW_VERSION% 선택
echo    - Release title: HV-L v%NEW_VERSION%
echo    - Description: 변경사항 작성
echo.
echo 3. 파일 업로드:
echo    - 아래 파일을 드래그 앤 드롭:
echo      %CD%\dist\HV-L.exe
echo    - 또는 백업 파일 사용:
echo      %CD%\releases\HV-L_v%NEW_VERSION%.exe
echo.
echo 4. "Publish release" 클릭
echo.
echo 주의: 업로드 전후 파일 크기가 동일한지 확인하세요!
echo 원본 파일 크기: !FILE_SIZE! bytes (약 !FILE_SIZE_MB! MB)
echo.

REM 파일 탐색기 열기
start explorer "dist"

pause 