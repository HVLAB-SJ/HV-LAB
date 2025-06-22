import os
import sys

# 파일을 바이너리로 읽기
with open('HV-L.py', 'rb') as f:
    content = f.read()

# UTF-8 BOM 추가 (0xEF, 0xBB, 0xBF)
if not content.startswith(b'\xef\xbb\xbf'):
    content = b'\xef\xbb\xbf' + content

# 새 파일로 저장
with open('HV-L_utf8.py', 'wb') as f:
    f.write(content)

# 원본 파일 교체
os.replace('HV-L_utf8.py', 'HV-L.py')

print("✓ UTF-8 BOM으로 변환 완료")
print("이제 다시 빌드를 시도해보세요.") 