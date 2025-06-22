import codecs
import shutil

# 백업 생성
shutil.copy('HV-L.py', 'HV-L_backup.py')
print("백업 파일 생성: HV-L_backup.py")

# 여러 인코딩 시도
encodings = ['cp949', 'euc-kr', 'utf-8', 'utf-8-sig', 'latin-1']

for encoding in encodings:
    try:
        with open('HV-L.py', 'r', encoding=encoding) as f:
            content = f.read()
        print(f"✓ {encoding} 인코딩으로 읽기 성공")
        
        # UTF-8로 다시 저장
        with open('HV-L.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("✓ UTF-8로 저장 완료")
        break
    except Exception as e:
        print(f"✗ {encoding} 실패: {e}")
        continue

print("\n인코딩 수정 완료!") 