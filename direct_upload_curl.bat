@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo =========================================
echo   HV-L 자동 빌드 및 업로드 (curl 버전)
echo =========================================
echo.

REM curl 설치 확인
echo [1/8] curl 확인 중...
where curl >nul 2>nul
if %errorlevel% neq 0 (
    echo curl을 다운로드하고 있습니다...
    powershell -Command "Invoke-WebRequest -Uri 'https://curl.se/windows/dl-8.5.0_1/curl-8.5.0_1-win64-mingw.zip' -OutFile 'curl.zip'"
    powershell -Command "Expand-Archive -Path 'curl.zip' -DestinationPath 'curl_temp' -Force"
    copy "curl_temp\curl-8.5.0_1-win64-mingw\bin\curl.exe" "%WINDIR%\System32\" >nul 2>nul
    if %errorlevel% neq 0 (
        echo 관리자 권한이 필요합니다. curl을 수동으로 설치해주세요.
        pause
        exit /b 1
    )
    rmdir /s /q curl_temp
    del curl.zip
)
echo ✓ curl 준비 완료
echo.

REM GitHub Token 확인
echo [2/8] GitHub 인증 확인 중...
for /f "tokens=*" %%i in ('gh auth token 2^>nul') do set GITHUB_TOKEN=%%i
if "%GITHUB_TOKEN%"=="" (
    echo ❌ GitHub 인증이 필요합니다.
    echo gh auth login 명령을 실행하여 로그인하세요.
    pause
    exit /b 1
)
echo ✓ GitHub 인증 확인 완료
echo.

REM 현재 버전 확인
echo [3/8] 현재 버전 확인 중...
for /f "tokens=3 delims= " %%a in ('findstr /C:"CURRENT_VERSION" HV-L.py') do (
    set CURRENT_VER=%%a
    set CURRENT_VER=!CURRENT_VER:"=!
)
echo 현재 버전: %CURRENT_VER%
echo.

REM 새 버전 입력
set /p NEW_VERSION="새 버전 번호 입력 (예: 1.6.10): "
echo.

REM Python 스크립트를 사용하여 버전 업데이트
echo [4/8] 소스 코드 버전 업데이트 중...
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
echo [5/8] 로컬에서 exe 빌드 중... (시간이 걸릴 수 있습니다)
if exist "dist\HV-L.exe" del "dist\HV-L.exe"
pyinstaller HV-L.spec --clean --noconfirm
if not exist "dist\HV-L.exe" (
    echo ❌ 빌드 실패!
    pause
    exit /b 1
)

REM 파일 크기 확인
for %%F in ("dist\HV-L.exe") do (
    set FILE_SIZE=%%~zF
    set /a FILE_SIZE_MB=!FILE_SIZE! / 1048576
)
echo ✓ 빌드 완료 (크기: !FILE_SIZE! bytes / 약 !FILE_SIZE_MB! MB)
echo.

REM Git 커밋 및 푸시
echo [6/8] 변경사항 커밋 중...
git add .
git commit -m "Update to v%NEW_VERSION%"
git push origin master
git tag v%NEW_VERSION%
git push origin v%NEW_VERSION%
echo ✓ 완료
echo.

REM Release 생성
echo [7/8] GitHub Release 생성 중...
echo {"tag_name":"v%NEW_VERSION%","name":"HV-L v%NEW_VERSION%","body":"## 변경사항\n\n- 업데이트된 기능들\n- 버그 수정\n\n## 다운로드\n\n아래 Assets에서 HV-L.exe를 다운로드하세요.","draft":false,"prerelease":false} > release.json

curl -X POST ^
  -H "Authorization: token %GITHUB_TOKEN%" ^
  -H "Accept: application/vnd.github.v3+json" ^
  -H "Content-Type: application/json" ^
  -d @release.json ^
  https://api.github.com/repos/HVLAB-SJ/HV-LAB/releases > release_response.json

REM Release ID 추출
for /f "tokens=2 delims=:, " %%a in ('findstr /C:"\"id\"" release_response.json') do (
    set RELEASE_ID=%%a
    goto :found_id
)
:found_id

del release.json
echo ✓ Release 생성 완료 (ID: %RELEASE_ID%)
echo.

REM 파일 업로드
echo [8/8] exe 파일 업로드 중...
curl -X POST ^
  -H "Authorization: token %GITHUB_TOKEN%" ^
  -H "Content-Type: application/octet-stream" ^
  --data-binary @"dist\HV-L.exe" ^
  "https://uploads.github.com/repos/HVLAB-SJ/HV-LAB/releases/%RELEASE_ID%/assets?name=HV-L.exe" > upload_response.json

REM 업로드된 파일 크기 확인
for /f "tokens=2 delims=:, " %%a in ('findstr /C:"\"size\"" upload_response.json') do (
    set UPLOADED_SIZE=%%a
    goto :found_size
)
:found_size

echo ✓ 파일 업로드 완료
echo.
echo 원본 파일 크기: !FILE_SIZE! bytes
echo 업로드된 크기: %UPLOADED_SIZE% bytes
echo.

if "%FILE_SIZE%"=="%UPLOADED_SIZE%" (
    echo ✅ 파일 크기가 일치합니다!
) else (
    echo ⚠️  경고: 파일 크기가 다릅니다!
)

del release_response.json
del upload_response.json

echo.
echo =========================================
echo   ✅ 모든 작업 완료!
echo =========================================
echo.
echo Release 확인: https://github.com/HVLAB-SJ/HV-LAB/releases/tag/v%NEW_VERSION%
echo.
pause 