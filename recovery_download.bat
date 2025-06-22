@echo off
chcp 65001 > nul
echo HV-L.exe 복구 도구
echo ========================
echo.
echo 이 도구는 손상된 HV-L.exe를 최신 버전으로 교체합니다.
echo.
pause

REM 기존 파일 백업
if exist HV-L.exe (
    echo 기존 파일 백업 중...
    move HV-L.exe HV-L_backup_%date:~0,4%%date:~5,2%%date:~8,2%_%time:~0,2%%time:~3,2%%time:~6,2%.exe
)

echo.
echo GitHub에서 최신 버전을 다운로드합니다...
echo 브라우저가 열립니다. HV-L.exe를 다운로드하세요.
echo.
start https://github.com/HVLAB-SJ/HV-LAB/releases/latest

echo.
echo 다운로드가 완료되면 다운로드 폴더에서 
echo HV-L.exe 파일을 이 폴더로 복사하세요.
echo.
pause 