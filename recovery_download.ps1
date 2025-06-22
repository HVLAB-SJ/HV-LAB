# HV-L.exe 복구 스크립트
# 이 스크립트를 손상된 PC에서 실행하세요

Write-Host "HV-L.exe 복구 스크립트" -ForegroundColor Green
Write-Host "========================" -ForegroundColor Green

# 기존 파일 백업
if (Test-Path "HV-L.exe") {
    Write-Host "기존 파일 백업 중..." -ForegroundColor Yellow
    Move-Item "HV-L.exe" "HV-L_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').exe" -Force
}

# GitHub에서 최신 릴리스 정보 가져오기
Write-Host "최신 버전 확인 중..." -ForegroundColor Yellow
$apiUrl = "https://api.github.com/repos/HVLAB-SJ/HV-LAB/releases/latest"
$release = Invoke-RestMethod -Uri $apiUrl

# 다운로드 URL 추출
$downloadUrl = $release.assets[0].browser_download_url
$fileName = $release.assets[0].name
$version = $release.tag_name

Write-Host "최신 버전: $version" -ForegroundColor Cyan
Write-Host "다운로드 중..." -ForegroundColor Yellow

# 파일 다운로드
try {
    Invoke-WebRequest -Uri $downloadUrl -OutFile $fileName
    Write-Host "다운로드 완료!" -ForegroundColor Green
    Write-Host "프로그램을 실행할 수 있습니다: .\$fileName" -ForegroundColor Green
} catch {
    Write-Host "다운로드 실패! 수동으로 다운로드하세요:" -ForegroundColor Red
    Write-Host $downloadUrl -ForegroundColor Yellow
}

Read-Host "엔터를 눌러 종료..." 