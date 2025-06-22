@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo =========================================
echo   HV-L 자동 빌드 및 업로드 (Token 버전)
echo =========================================
echo.

REM GitHub Token 입력
echo [1/7] GitHub Personal Access Token이 필요합니다.
echo.
echo Token 생성 방법:
echo 1. https://github.com/settings/tokens 접속
echo 2. "Generate new token (classic)" 클릭
echo 3. 권한 선택: repo (전체 체크)
echo 4. "Generate token" 클릭
echo.
set /p GITHUB_TOKEN="GitHub Personal Access Token 입력: "
echo.

REM 현재 버전 확인
echo [2/7] 현재 버전 확인 중...
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
echo [3/7] 소스 코드 버전 업데이트 중...
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
echo [4/7] 로컬에서 exe 빌드 중... (시간이 걸릴 수 있습니다)
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
echo [5/7] 변경사항 커밋 중...
git add .
git commit -m "Update to v%NEW_VERSION%"
git push origin master
git tag v%NEW_VERSION%
git push origin v%NEW_VERSION%
echo ✓ 완료
echo.

REM Python으로 Release 생성 및 업로드
echo [6/7] GitHub Release 생성 및 업로드 중...
echo import requests > github_upload.py
echo import os >> github_upload.py
echo import json >> github_upload.py
echo. >> github_upload.py
echo token = "%GITHUB_TOKEN%" >> github_upload.py
echo headers = {"Authorization": f"token {token}"} >> github_upload.py
echo. >> github_upload.py
echo # Release 생성 >> github_upload.py
echo release_data = { >> github_upload.py
echo     "tag_name": "v%NEW_VERSION%", >> github_upload.py
echo     "name": "HV-L v%NEW_VERSION%", >> github_upload.py
echo     "body": "## 변경사항\\n\\n- 업데이트된 기능들\\n- 버그 수정\\n\\n## 다운로드\\n\\n아래 Assets에서 HV-L.exe를 다운로드하세요.", >> github_upload.py
echo     "draft": False, >> github_upload.py
echo     "prerelease": False >> github_upload.py
echo } >> github_upload.py
echo. >> github_upload.py
echo resp = requests.post("https://api.github.com/repos/HVLAB-SJ/HV-LAB/releases", headers=headers, json=release_data) >> github_upload.py
echo if resp.status_code == 201: >> github_upload.py
echo     print("✓ Release 생성 완료") >> github_upload.py
echo     release = resp.json() >> github_upload.py
echo     upload_url = release["upload_url"].replace("{?name,label}", "") >> github_upload.py
echo     >> github_upload.py
echo     # 파일 업로드 >> github_upload.py
echo     with open("dist/HV-L.exe", "rb") as f: >> github_upload.py
echo         file_data = f.read() >> github_upload.py
echo     >> github_upload.py
echo     upload_headers = { >> github_upload.py
echo         "Authorization": f"token {token}", >> github_upload.py
echo         "Content-Type": "application/octet-stream" >> github_upload.py
echo     } >> github_upload.py
echo     >> github_upload.py
echo     upload_resp = requests.post(f"{upload_url}?name=HV-L.exe", headers=upload_headers, data=file_data) >> github_upload.py
echo     if upload_resp.status_code == 201: >> github_upload.py
echo         print("✓ 파일 업로드 완료") >> github_upload.py
echo         asset = upload_resp.json() >> github_upload.py
echo         print(f"업로드된 파일 크기: {asset['size']:,} bytes") >> github_upload.py
echo     else: >> github_upload.py
echo         print(f"❌ 업로드 실패: {upload_resp.status_code}") >> github_upload.py
echo else: >> github_upload.py
echo     print(f"❌ Release 생성 실패: {resp.status_code}") >> github_upload.py
echo     print(resp.text) >> github_upload.py

python github_upload.py
del github_upload.py

echo.
echo [7/7] 완료!
echo.
echo 원본 파일 크기: !FILE_SIZE! bytes
echo.
echo =========================================
echo   ✅ 모든 작업 완료!
echo =========================================
echo.
echo Release 확인: https://github.com/HVLAB-SJ/HV-LAB/releases/tag/v%NEW_VERSION%
echo.
pause 