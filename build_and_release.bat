@echo off
echo === HV-L 빌드 및 릴리스 스크립트 ===
echo.

REM 버전 입력 받기
set /p VERSION="새 버전 번호 입력 (예: 1.6.1): "

REM HV-L.py에서 버전 업데이트
echo 버전 업데이트 중...
powershell -Command "(Get-Content HV-L.py) -replace 'CURRENT_VERSION = \".*\"', 'CURRENT_VERSION = \"%VERSION%\"' | Set-Content HV-L.py"

REM Git 커밋
echo.
echo Git 커밋 중...
git add HV-L.py
git commit -m "버전 %VERSION% 업데이트"

REM 빌드 (빠른 빌드 옵션)
echo.
echo EXE 빌드 중... (약 1-2분 소요)
pyinstaller HV-L-fast.spec --clean

REM 정식 빌드 여부 확인
echo.
set /p BUILD_FULL="정식 빌드도 진행하시겠습니까? (y/n): "
if /i "%BUILD_FULL%"=="y" (
    echo 정식 빌드 중... (약 3-5분 소요)
    pyinstaller HV-L.spec --clean
    set EXE_FILE=dist\HV-L.exe
) else (
    echo 개발 빌드 사용
    copy dist\HV-L-dev.exe dist\HV-L.exe
    set EXE_FILE=dist\HV-L.exe
)

REM GitHub 푸시 및 태그
echo.
echo GitHub에 푸시 중...
git push
git tag v%VERSION%
git push origin v%VERSION%

echo.
echo === 완료! ===
echo GitHub Actions가 자동으로 릴리스를 생성합니다.
echo 수동 릴리스: https://github.com/HVLAB-SJ/HV-LAB/releases/new
pause 