@echo off
echo 정산 프로그램 업데이트 중...

REM 현재 실행 중인 프로그램 종료
taskkill /f /im "정산프로그램.exe" 2>nul
timeout /t 2 /nobreak >nul

REM 백업 생성
if exist "정산프로그램.exe" (
    copy "정산프로그램.exe" "정산프로그램_backup.exe"
    echo 백업 파일이 생성되었습니다.
)

REM 새 버전 복사
if exist "정산프로그램_new.exe" (
    copy "정산프로그램_new.exe" "정산프로그램.exe"
    del "정산프로그램_new.exe"
    echo 업데이트가 완료되었습니다.
) else (
    echo 새 버전 파일을 찾을 수 없습니다.
    pause
    exit /b 1
)

REM 프로그램 재시작
start "" "정산프로그램.exe"

echo 업데이트가 완료되었습니다.
pause 