# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, 
                            QMessageBox, QApplication)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon
import pyrebase
from firebase_config import FIREBASE_CONFIG, SHARED_ACCOUNT, COMPANY_PASSWORD

class LoginThread(QThread):
    """Firebase 로그인을 처리하는 별도 스레드"""
    login_success = pyqtSignal(str)  # 이메일을 전달하도록 수정
    login_failed = pyqtSignal(str)
    
    def __init__(self, password):
        super().__init__()
        self.password = password
        
    def run(self):
        try:
            # 디버깅: 입력된 비밀번호 확인
            print(f"입력된 비밀번호: '{self.password}'")
            print(f"설정된 비밀번호: '{COMPANY_PASSWORD}'")
            
            # 회사 비밀번호 확인
            if self.password != COMPANY_PASSWORD:
                self.login_failed.emit("비밀번호가 틀렸습니다.")
                return
                
            print("회사 비밀번호 확인 완료")
            
            # Firebase 초기화
            firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
            auth = firebase.auth()
            print("Firebase 초기화 완료")
            
            # 공용 계정으로 로그인
            print(f"Firebase 로그인 시도: {SHARED_ACCOUNT['email']}")
            user = auth.sign_in_with_email_and_password(
                SHARED_ACCOUNT['email'], 
                SHARED_ACCOUNT['password']
            )
            
            # 로그인 성공 - 이메일 전달
            print("Firebase 로그인 성공!")
            self.login_success.emit(SHARED_ACCOUNT['email'])  # 이메일 전달
            
        except Exception as e:
            error_msg = str(e)
            print(f"에러 발생: {error_msg}")  # 디버깅용 출력
            
            # Firebase 에러 메시지를 사용자 친화적으로 변환
            if "INVALID_PASSWORD" in error_msg or "verifyPassword" in error_msg:
                self.login_failed.emit("Firebase 계정 비밀번호 오류")
            elif "EMAIL_NOT_FOUND" in error_msg:
                self.login_failed.emit("등록되지 않은 계정입니다.")
            elif "INVALID_EMAIL" in error_msg:
                self.login_failed.emit("잘못된 이메일 형식입니다.")
            elif "NETWORK_REQUEST_FAILED" in error_msg:
                self.login_failed.emit("인터넷 연결을 확인하세요.")
            elif "TOO_MANY_ATTEMPTS" in error_msg:
                self.login_failed.emit("너무 많은 시도. 잠시 후 다시 시도하세요.")
            else:
                # 긴 에러 메시지는 짧게 표시
                if len(error_msg) > 50:
                    self.login_failed.emit("로그인 실패: 연결 오류")
                else:
                    self.login_failed.emit(f"로그인 실패: {error_msg}")

class LoginDialog(QDialog):
    """로그인 다이얼로그"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_email = None  # 사용자 이메일 저장 변수 추가
        self.setup_ui()
        self.login_thread = None
        
    def setup_ui(self):
        """UI 구성"""
        self.setWindowTitle("HV 정산 - 로그인")
        self.setFixedSize(450, 280)  # 높이를 줄임
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        
        # 메인 레이아웃
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # 제목 라벨
        title_label = QLabel("HV 정산")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # 비밀번호 입력
        self.password_edit = QLineEdit()
        self.password_edit.setPlaceholderText("비밀번호")
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setStyleSheet("""
            QLineEdit {
                padding: 10px;
                font-size: 14px;
                border: 2px solid #ddd;
                border-radius: 5px;
            }
            QLineEdit:focus {
                border-color: #7d9471;
            }
        """)
        layout.addWidget(self.password_edit)
        
        # 로그인 버튼만 (취소 버튼 제거)
        self.login_button = QPushButton("로그인")
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #7d9471;
                color: white;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #6d8062;
            }
            QPushButton:pressed {
                background-color: #5d6f54;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.login_button.clicked.connect(self.on_login_clicked)
        layout.addWidget(self.login_button)
        
        # 상태 라벨
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: red;")
        self.status_label.setWordWrap(True)  # 긴 텍스트 자동 줄바꿈
        self.status_label.setMaximumHeight(60)  # 최대 높이 제한
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Enter 키로 로그인
        self.password_edit.returnPressed.connect(self.on_login_clicked)
        
        # 포커스 설정
        self.password_edit.setFocus()
        
    def on_login_clicked(self):
        """로그인 버튼 클릭 시"""
        password = self.password_edit.text().strip()
        
        if not password:
            self.show_error("비밀번호를 입력하세요.")
            return
            
        # UI 비활성화
        self.set_ui_enabled(False)
        self.status_label.setText("로그인 중...")
        self.status_label.setStyleSheet("color: blue;")
        
        # 로그인 스레드 시작
        self.login_thread = LoginThread(password)
        self.login_thread.login_success.connect(self.on_login_success)
        self.login_thread.login_failed.connect(self.on_login_failed)
        self.login_thread.start()
        
    def on_login_success(self, email):
        """로그인 성공 시"""
        self.user_email = email  # 로그인한 이메일 저장
        self.accept()
        
    def on_login_failed(self, error_msg):
        """로그인 실패 시"""
        self.show_error(error_msg)
        self.set_ui_enabled(True)
        self.password_edit.clear()
        self.password_edit.setFocus()
        
    def show_error(self, message):
        """에러 메시지 표시"""
        self.status_label.setText(message)
        self.status_label.setStyleSheet("color: red;")
        
    def set_ui_enabled(self, enabled):
        """UI 활성화/비활성화"""
        self.password_edit.setEnabled(enabled)
        self.login_button.setEnabled(enabled)
        
def show_login_dialog():
    """로그인 다이얼로그 표시 (독립 실행용)"""
    app = QApplication(sys.argv)
    dialog = LoginDialog()
    
    if dialog.exec_() == QDialog.Accepted:
        print("로그인 성공!")
        print(f"로그인한 이메일: {dialog.user_email}")  # 이메일 출력 추가
        return True
    else:
        print("로그인 취소됨")
        return False

# 테스트용 (직접 실행 시)
if __name__ == "__main__":
    if show_login_dialog():
        # 로그인 성공 후 메인 프로그램 실행
        print("메인 프로그램을 시작합니다...")
    else:
        print("프로그램을 종료합니다.")