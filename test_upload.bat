@echo off
echo GitHub CLI와 직접 API 업로드 비교 테스트
echo.

REM 테스트 파일 생성
echo Creating test file...
fsutil file createnew test_file.bin 1048576 >nul 2>&1
certutil -hashfile test_file.bin MD5

echo.
echo 1. GitHub CLI로 업로드 테스트
gh release create test-v1.0.0 test_file.bin --title "Test Release" --notes "Test"

echo.
echo 2. 업로드된 파일 다운로드 및 비교
curl -L https://github.com/HVLAB-SJ/HV-LAB/releases/download/test-v1.0.0/test_file.bin -o downloaded.bin
certutil -hashfile downloaded.bin MD5

echo.
echo 파일이 동일하면 MD5 해시가 같아야 합니다.
echo.

REM 정리
del test_file.bin
del downloaded.bin
gh release delete test-v1.0.0 --yes

pause 