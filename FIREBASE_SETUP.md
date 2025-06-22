# Firebase 실시간 동기화 설정 가이드

## 개요
HV-L 프로그램은 Firebase를 통한 실시간 동기화 기능을 지원합니다.
이 기능을 사용하려면 `serviceAccountKey.json` 파일이 필요합니다.

## 설정 방법

### 1. serviceAccountKey.json 파일 받기
- 관리자로부터 `serviceAccountKey.json` 파일을 받습니다
- 이 파일은 보안상 중요하므로 절대 공유하지 마세요

### 2. 파일 위치
`serviceAccountKey.json` 파일을 `HV-L.exe`와 **같은 폴더**에 넣어주세요.

```📁 HV 폴더
├── HV-L.exe
└── serviceAccountKey.json  ← 여기에 위치
```

### 3. 프로그램 실행
- 파일이 있으면 자동으로 Firebase 연결
- 상태표시: 🟢 "실시간 동기화 중"
- 파일이 없으면 오프라인 모드로 작동

## 동기화 상태 확인
프로그램 하단 상태바에서 동기화 상태를 확인할 수 있습니다:
- 🟢 실시간 동기화 중
- 🟡 오프라인 모드
- 🔴 동기화 오류

## 주의사항
- `serviceAccountKey.json` 파일은 절대 다른 사람과 공유하지 마세요
- 이 파일이 없어도 프로그램은 정상 작동하며, 로컬 저장만 사용합니다
- 여러 컴퓨터에서 동시 작업 시 반드시 실시간 동기화를 사용하세요 