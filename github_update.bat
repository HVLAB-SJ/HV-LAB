@echo off
chcp 65001 > nul
echo.
echo ===================================
echo   GitHub 자동 업데이트 스크립트
echo ===================================
echo.

REM 현재 버전 확인
echo 현재 버전 확인 중...
findstr /C:"CURRENT_VERSION" HV-L.py
echo.

REM 새 버전 입력
set /p NEW_VERSION="새 버전 번호 입력 (예: 1.6.10): "

REM HV-L.py에서 버전 업데이트
echo.
echo 버전 업데이트 중...
powershell -Command "(Get-Content HV-L.py) -replace 'CURRENT_VERSION = \".*\"', 'CURRENT_VERSION = \"%NEW_VERSION%\"' | Set-Content HV-L.py"

REM Git 명령어 실행
echo.
echo GitHub에 업로드 중...
git add .
git commit -m "Update to v%NEW_VERSION%"
git push

REM 태그 생성 및 푸시
echo.
echo 태그 생성 중...
git tag v%NEW_VERSION%
git push origin v%NEW_VERSION%

REM 완료 메시지
echo.
echo ===================================
echo   ✅ 업데이트 완료!
echo ===================================
echo.
echo 버전 v%NEW_VERSION%이(가) GitHub에 업로드되었습니다.
echo GitHub Actions에서 자동으로 exe 파일을 빌드 중입니다.
echo.
echo 빌드 상태 확인: https://github.com/HVLAB-SJ/HV-LAB/actions
echo.
pause 