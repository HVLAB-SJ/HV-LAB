@echo off
chcp 65001 > nul
setlocal enabledelayedexpansion

echo.
echo =========================================
echo   HV-L 자동 빌드 및 업로드 스크립트
echo =========================================
echo.

REM GitHub Token 확인
echo [1/7] GitHub 인증 확인 중...
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
echo ✓ 빌드 완료
echo.

REM Git 커밋 및 푸시
echo [5/7] 변경사항 커밋 중...
git add .
git commit -m "Update to v%NEW_VERSION%"
git push origin master

REM 태그 생성 및 푸시
git tag v%NEW_VERSION%
git push origin v%NEW_VERSION%
echo ✓ 완료
echo.

REM Python 스크립트로 GitHub Release 생성 및 파일 업로드
echo [6/7] GitHub Release 생성 중...
echo import requests > upload_release.py
echo import os >> upload_release.py
echo import sys >> upload_release.py
echo. >> upload_release.py
echo token = "%GITHUB_TOKEN%" >> upload_release.py
echo repo = "HVLAB-SJ/HV-LAB" >> upload_release.py
echo tag = "v%NEW_VERSION%" >> upload_release.py
echo. >> upload_release.py
echo # Release 생성 >> upload_release.py
echo url = f"https://api.github.com/repos/{repo}/releases" >> upload_release.py
echo headers = { >> upload_release.py
echo     "Authorization": f"token {token}", >> upload_release.py
echo     "Accept": "application/vnd.github.v3+json" >> upload_release.py
echo } >> upload_release.py
echo data = { >> upload_release.py
echo     "tag_name": tag, >> upload_release.py
echo     "name": f"HV-L {tag}", >> upload_release.py
echo     "body": "## 변경사항\\n\\n- 업데이트된 기능들\\n- 버그 수정\\n\\n## 다운로드\\n\\n아래 Assets에서 HV-L.exe를 다운로드하세요.", >> upload_release.py
echo     "draft": False, >> upload_release.py
echo     "prerelease": False >> upload_release.py
echo } >> upload_release.py
echo. >> upload_release.py
echo response = requests.post(url, headers=headers, json=data) >> upload_release.py
echo if response.status_code == 201: >> upload_release.py
echo     print("✓ Release 생성 완료") >> upload_release.py
echo     release_data = response.json() >> upload_release.py
echo     upload_url = release_data["upload_url"].replace("{?name,label}", "") >> upload_release.py
echo     >> upload_release.py
echo     # 파일 업로드 >> upload_release.py
echo     file_path = "dist/HV-L.exe" >> upload_release.py
echo     file_size = os.path.getsize(file_path) >> upload_release.py
echo     print(f"업로드할 파일 크기: {file_size:,} bytes ({file_size/1048576:.1f} MB)") >> upload_release.py
echo     >> upload_release.py
echo     with open(file_path, "rb") as f: >> upload_release.py
echo         upload_headers = { >> upload_release.py
echo             "Authorization": f"token {token}", >> upload_release.py
echo             "Content-Type": "application/octet-stream", >> upload_release.py
echo             "Content-Length": str(file_size) >> upload_release.py
echo         } >> upload_release.py
echo         upload_response = requests.post( >> upload_release.py
echo             f"{upload_url}?name=HV-L.exe", >> upload_release.py
echo             headers=upload_headers, >> upload_release.py
echo             data=f.read() >> upload_release.py
echo         ) >> upload_release.py
echo         >> upload_release.py
echo         if upload_response.status_code == 201: >> upload_release.py
echo             print("✓ 파일 업로드 완료") >> upload_release.py
echo             asset_data = upload_response.json() >> upload_release.py
echo             print(f"업로드된 파일 크기: {asset_data['size']:,} bytes") >> upload_release.py
echo         else: >> upload_release.py
echo             print(f"❌ 파일 업로드 실패: {upload_response.status_code}") >> upload_release.py
echo             print(upload_response.text) >> upload_release.py
echo else: >> upload_release.py
echo     print(f"❌ Release 생성 실패: {response.status_code}") >> upload_release.py
echo     print(response.text) >> upload_release.py

python upload_release.py
del upload_release.py

echo.
echo [7/7] 완료!
echo.
echo Release 확인: https://github.com/HVLAB-SJ/HV-LAB/releases/tag/v%NEW_VERSION%
echo.
pause 