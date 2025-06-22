# -*- coding: utf-8 -*-
import sys
import json
import os
import re
import uuid
import time
import requests
import hashlib
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pandas as pd
import subprocess

# Firebase imports
try:
    import firebase_admin
    from firebase_admin import credentials, db
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

# Constants
FIREBASE_DATABASE_URL = "https://hv-settlement-default-rtdb.firebaseio.com/"
WINDOW_WIDTH = 2365
WINDOW_HEIGHT = 1090  # ì°??’ì´ ?˜ì •
WINDOW_WIDTH_NO_MEMO = 1715  # ë©”ëª¨?¥ì´ ?«í˜”???Œì˜ ì°??ˆë¹„
TABLE_WIDTH = 1330
MEMO_WIDTH = 640
LEFT_PANEL_WIDTH = 350

# ?…ë°?´íŠ¸ ê´€???ìˆ˜
UPDATE_CHECK_URL = "https://api.github.com/repos/HVLAB-SJ/HV-LAB/releases/latest"  # GitHub ë¦´ë¦¬ì¦?URL
CURRENT_VERSION = ""  # ?„ì¬ ë²„ì „

# Style constants
BUTTON_STYLE = """
    QPushButton {
        background-color: #7d9471;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: #6d8062; }
    QPushButton:pressed { background-color: #5d6f54; }
    QPushButton:disabled { background-color: #c0c0c0; color: #808080; }
"""

USER_BUTTON_STYLE = """
    QPushButton { 
        background-color: white; 
        color: #495057; 
        border: 2px solid #ced4da; 
        font-weight: normal; 
        font-size: 18px; 
        padding: 2px;
    } 
    QPushButton:hover { border-color: #adb5bd; } 
    QPushButton:checked { 
        border: 3px solid #7d9471; 
        background-color: #f8f9fa; 
        color: #7d9471; 
        font-weight: bold; 
        font-size: 18px;
        padding: 3px;
    }
"""

GRAY_BUTTON_STYLE = """
    QPushButton {
        background-color: #c0c0c0;
        color: #808080;
        border: none;
        padding: 8px 16px;
        border-radius: 4px;
        font-weight: bold;
    }
"""


def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def get_data_file_path():
    if getattr(sys, 'frozen', False):
        return os.path.join(os.path.dirname(sys.executable), 'interior_settlement_data.json')
    return 'interior_settlement_data.json'


class UpdateChecker(QObject):
    update_available = pyqtSignal(str, str)  # version, download_url
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def check_for_updates(self):
        try:
            # GitHub APIë¥??µí•´ ìµœì‹  ë¦´ë¦¬ì¦??•ì¸
            response = requests.get(UPDATE_CHECK_URL, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data['tag_name'].lstrip('v')
                
                if self._compare_versions(latest_version, CURRENT_VERSION) > 0:
                    download_url = release_data['assets'][0]['browser_download_url']
                    self.update_available.emit(latest_version, download_url)
                    
        except Exception as e:
            print(f"?…ë°?´íŠ¸ ?•ì¸ ?¤íŒ¨: {e}")
    
    def _compare_versions(self, version1, version2):
        """ë²„ì „ ë¹„êµ (version1 > version2 ?´ë©´ ?‘ìˆ˜ ë°˜í™˜)"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            if v1 != v2:
                return v1 - v2
        return 0


class FirebaseSync(QObject):
    data_changed = pyqtSignal(dict)
    sync_status_changed = pyqtSignal(str, str)
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.db_ref = None
        self.listener = None
        self.sync_enabled = True
        self.last_update_time = 0
        self.is_syncing = False
        self.local_update = False
        self.session_id = str(uuid.uuid4())
        self.last_data_hash = None
        
        self.data_changed.connect(self.main_window.on_firebase_data_changed)
        self.sync_status_changed.connect(self._update_sync_status)
        
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self.check_connection)
        self.reconnect_timer.start(10000)
        
    def initialize_firebase(self):
        if not FIREBASE_AVAILABLE:
            self.sync_status_changed.emit("? ï¸ ?¤í”„?¼ì¸ ëª¨ë“œ", "color: #95a5a6; font-weight: bold;")
            return False
            
        try:
            base_path = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(os.path.abspath(__file__))
            service_account_path = os.path.join(base_path, 'serviceAccountKey.json')
            
            if not os.path.exists(service_account_path):
                alt_path = os.path.join(base_path, 'serviceAccountKey.json.json')
                if os.path.exists(alt_path):
                    service_account_path = alt_path
                else:
                    self.sync_status_changed.emit("? ï¸ ?¤í”„?¼ì¸ ëª¨ë“œ", "color: #95a5a6; font-weight: bold;")
                    return False
            
            if not firebase_admin._apps:
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred, {'databaseURL': FIREBASE_DATABASE_URL})
            
            self.db_ref = db.reference('settlement_data')
            return True
            
        except Exception:
            self.sync_status_changed.emit("? ï¸ ?¤í”„?¼ì¸ ëª¨ë“œ", "color: #95a5a6; font-weight: bold;")
            return False
    
    def start_sync(self):
        try:
            if not self.initialize_firebase():
                return
            self.load_from_firebase()
            self.listener = self.db_ref.listen(self.on_firebase_change)
            self.sync_status_changed.emit("?ï¸ ?¤ì‹œê°??™ê¸°??ì¤?, "color: #27ae60; font-weight: bold;")
        except Exception:
            self.sync_status_changed.emit("? ï¸ ?™ê¸°???¤ë¥˜", "color: #e74c3c; font-weight: bold;")
    
    def stop_sync(self):
        try:
            if hasattr(self, 'reconnect_timer'):
                self.reconnect_timer.stop()
            if self.listener:
                try:
                    self.listener.close()
                except:
                    pass
                self.listener = None
        except:
            pass
    
    def load_from_firebase(self):
        try:
            self.is_syncing = True
            data = self.db_ref.get()
            
            if data:
                if '_metadata' in data:
                    del data['_metadata']
                self.data_changed.emit(data)
                self.last_data_hash = self._calculate_data_hash(data)
            else:
                if self.main_window.projects_data:
                    self.save_to_firebase(self.main_window.projects_data)
                    
            self.is_syncing = False
        except Exception:
            self.is_syncing = False
            self.sync_status_changed.emit("? ï¸ ?°ì´??ë¡œë“œ ?¤íŒ¨", "color: #e74c3c; font-weight: bold;")
    
    def save_to_firebase(self, data):
        if self.is_syncing:
            return
        
        try:
            current_time = time.time()
            if current_time - self.last_update_time < 1.0:
                return
            
            self.last_update_time = current_time
            self.local_update = True
            
            save_data = self._prepare_data_for_save(data)
            save_data['_metadata'] = {
                'last_updated': datetime.now().isoformat(),
                'session_id': self.session_id,
                'update_time': current_time
            }
            
            self.db_ref.set(save_data)
            self.last_data_hash = self._calculate_data_hash(data)
            
            current_time_str = datetime.now().strftime("%H:%M:%S")
            self.sync_status_changed.emit(f"?ï¸ ?™ê¸°???„ë£Œ ({current_time_str})", "color: #27ae60; font-weight: bold;")
            self.main_window.statusBar().showMessage(f"???´ë¼?°ë“œ ?ë™ ?€???„ë£Œ - {current_time_str}", 3000)
            
            QTimer.singleShot(2000, lambda: setattr(self, 'local_update', False))
            
            # 3ì´????¤ì‹œ ?¤ì‹œê°??™ê¸°???íƒœë¡?ë³µì›
            QTimer.singleShot(3000, lambda: self.sync_status_changed.emit("?ï¸ ?¤ì‹œê°??™ê¸°??ì¤?, "color: #27ae60; font-weight: bold;"))
            
        except Exception:
            self.local_update = False
            self.sync_status_changed.emit("? ï¸ ?™ê¸°???¤íŒ¨", "color: #e74c3c; font-weight: bold;")
            self.main_window.statusBar().showMessage("???´ë¼?°ë“œ ?€???¤íŒ¨ - ?¸í„°???°ê²°???•ì¸?˜ì„¸??, 5000)
    
    def on_firebase_change(self, event):
        try:
            if self.local_update:
                return
            
            if event.data and event.path == '/':
                data = event.data
                
                if '_metadata' in data:
                    metadata = data['_metadata']
                    if metadata.get('session_id') == self.session_id:
                        return
                    del data['_metadata']
                
                new_hash = self._calculate_data_hash(data)
                if new_hash != self.last_data_hash:
                    self.last_data_hash = new_hash
                    self.data_changed.emit(data)
                    self.sync_status_changed.emit("?ï¸ ?¤ë¥¸ ?¬ìš©?ê? ?˜ì •??, "color: #3498db; font-weight: bold;")
                    QTimer.singleShot(5000, lambda: self.sync_status_changed.emit("?ï¸ ?¤ì‹œê°??™ê¸°??ì¤?, "color: #27ae60; font-weight: bold;"))
        except:
            pass
    
    def check_connection(self):
        if not FIREBASE_AVAILABLE:
            return
        try:
            if self.db_ref and not self.is_syncing:
                try:
                    self.db_ref.child('_test_connection').get()
                except:
                    self.sync_status_changed.emit("?”„ ?¬ì—°ê²?ì¤?..", "color: #f39c12; font-weight: bold;")
                    self.start_sync()
        except:
            pass
    
    def _prepare_data_for_save(self, data):
        save_data = {}
        for project, items in data.items():
            save_data[project] = []
            for item in items:
                item_copy = item.copy()
                if hasattr(item_copy.get('date'), 'toString'):
                    item_copy['date'] = item_copy['date'].toString('yyyy-MM-dd')
                save_data[project].append(item_copy)
        return save_data
    
    def _calculate_data_hash(self, data):
        try:
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            return hash(data_str)
        except:
            return None
    
    def _update_sync_status(self, status, style):
        if hasattr(self.main_window, 'sync_status_label'):
            # ?íƒœë³??„ì´ì½˜ê³¼ ?´íŒ ?¤ì •
            icon_text = "??  # ê¸°ë³¸ ?í˜• ?„ì´ì½?            tooltip = status
            
            # ?‰ìƒë§??¤í??¼ì—??ì¶”ì¶œ
            color_match = re.search(r'color:\s*([^;]+)', style)
            color = color_match.group(1) if color_match else "#27ae60"
            
            # ê°„ë‹¨???„ì´ì½??¤í????ìš©
            icon_style = f"""
                QLabel {{
                    color: {color};
                    font-size: 9px;
                    font-weight: bold;
                    padding: 0px;
                    background-color: transparent;
                    border: none;
                    min-width: 10px;
                    max-width: 10px;
                }}
            """
            
            self.main_window.sync_status_label.setText(icon_text)
            self.main_window.sync_status_label.setStyleSheet(icon_style)
            self.main_window.sync_status_label.setToolTip(status.replace("?ï¸ ", "").replace("? ï¸ ", "").replace("?’¾ ", "").replace("?”„ ", ""))
    


class ProjectComboBox(QComboBox):
    """?„ë¡œ?íŠ¸ ?´ë¦„ê³????¸ìˆ˜ë¥???ì¤„ë¡œ ?œì‹œ?˜ëŠ” ì»¤ìŠ¤?€ ì½¤ë³´ë°•ìŠ¤"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_font_size = 14  # ?„ë¡œ?íŠ¸ëª?15px ??14px
        self.sub_font_size = 12      # ???¸ìˆ˜ 12px
        self.min_font_size = 10
    
    def paintEvent(self, event):
        painter = QStylePainter(self)
        
        # ì½¤ë³´ë°•ìŠ¤ ?„ë ˆ??ê·¸ë¦¬ê¸?        opt = QStyleOptionComboBox()
        self.initStyleOption(opt)
        painter.drawComplexControl(QStyle.CC_ComboBox, opt)
        
        # ?ìŠ¤???ì—­ ê³„ì‚°
        text_rect = self.style().subControlRect(QStyle.CC_ComboBox, opt, QStyle.SC_ComboBoxEditField, self)
        # ?ì ˆ???¬ë°±?¼ë¡œ ?ìŠ¤???ì—­ ì¡°ì •
        text_rect = text_rect.adjusted(5, 12, -5, -12)
        
        # ?„ì¬ ?ìŠ¤??ê°€?¸ì˜¤ê¸?        text = self.currentText()
        
        # ?ˆí‹°?¨ë¦¬?´ì‹± ?œì„±??        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        if text == "?„ë¡œ?íŠ¸ ê´€ë¦?:
            # ?„ë¡œ?íŠ¸ ê´€ë¦¬ëŠ” ??ì¤„ë¡œ ê°€?´ë° ?œì‹œ
            font = QFont("ë§‘ì? ê³ ë”•", self.default_font_size)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(self.palette().text().color()))
            
            # 3px ?„ë˜ë¡?ì¡°ì •???ì—­
            adjusted_rect = QRect(text_rect.x(), text_rect.y() + 3, text_rect.width(), text_rect.height())
            painter.drawText(adjusted_rect, Qt.AlignCenter, text)
        elif text and " | " in text:
            # ?„ë¡œ?íŠ¸ëª…ê³¼ ???¸ìˆ˜ ë¶„ë¦¬
            parts = text.split(" | ", 1)
            project_name = parts[0]
            unit_info = parts[1] if len(parts) > 1 else ""
            
            # ?„ì²´ ?’ì´??ì¤‘ì•™???ìŠ¤??ë°°ì¹˜
            total_height = text_rect.height()
            line_spacing = 2  # ??ì¤??¬ì´ ê°„ê²©
            
            # ?„ë¡œ?íŠ¸ëª?ê·¸ë¦¬ê¸?(?„ìª½)
            font1 = QFont("ë§‘ì? ê³ ë”•", self.default_font_size)
            font1.setBold(True)
            painter.setFont(font1)
            painter.setPen(QPen(self.palette().text().color()))
            
            # ?„ìª½ ?ìŠ¤???ì—­ - ì¤‘ì•™ ?•ë ¬ (3px ?„ë˜ë¡?
            fm1 = QFontMetrics(font1)
            text1_height = fm1.height()
            
            top_y = text_rect.center().y() - line_spacing // 2 - text1_height // 2 + 3  # 3px ?„ë˜ë¡?            top_rect = QRect(text_rect.x(), top_y - text1_height // 2, text_rect.width(), text1_height)
            painter.drawText(top_rect, Qt.AlignCenter, project_name)
            
            # ???¸ìˆ˜ ê·¸ë¦¬ê¸?(?„ë˜ìª?
            if unit_info:
                font2 = QFont("ë§‘ì? ê³ ë”•", self.sub_font_size)
                font2.setWeight(QFont.Light)  # ê°€?˜ê²Œ ?¤ì •
                painter.setFont(font2)
                
                fm2 = QFontMetrics(font2)
                text2_height = fm2.height()
                
                bottom_y = text_rect.center().y() + line_spacing // 2 + text2_height // 2 + 3  # 3px ?„ë˜ë¡?                bottom_rect = QRect(text_rect.x(), bottom_y - text2_height // 2, text_rect.width(), text2_height)
                painter.drawText(bottom_rect, Qt.AlignCenter, unit_info)
        else:
            # ???¸ìˆ˜ê°€ ?†ëŠ” ê²½ìš° ?„ë¡œ?íŠ¸ëª…ë§Œ ê°€?´ë° ?œì‹œ
            font = QFont("ë§‘ì? ê³ ë”•", self.default_font_size)
            font.setBold(True)
            painter.setFont(font)
            painter.setPen(QPen(self.palette().text().color()))
            
            # 3px ?„ë˜ë¡?ì¡°ì •???ì—­
            adjusted_rect = QRect(text_rect.x(), text_rect.y() + 3, text_rect.width(), text_rect.height())
            painter.drawText(adjusted_rect, Qt.AlignCenter, text)


class ProjectComboDelegate(QStyledItemDelegate):
    """?„ë¡œ?íŠ¸ ì½¤ë³´ë°•ìŠ¤ ?œë¡­?¤ìš´ ë¦¬ìŠ¤?¸ì˜ ê°???ª©????ì¤„ë¡œ ?œì‹œ?˜ëŠ” ?¸ë¦¬ê²Œì´??""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_font_size = 14  # ?„ë¡œ?íŠ¸ëª?15px ??14px
        self.sub_font_size = 12      # ???¸ìˆ˜ 12px
        self.min_font_size = 10
    
    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole)
        
        if text == "?„ë¡œ?íŠ¸ ê´€ë¦?:
            # ?„ë¡œ?íŠ¸ ê´€ë¦¬ëŠ” ì»¤ìŠ¤?€ ?˜ì¸???¬ìš©
            CustomDelegate.paint(self, painter, option, index)
            return
        
        painter.save()
        
        # ?ˆí‹°?¨ë¦¬?´ì‹± ?œì„±??        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.TextAntialiasing)
        
        # ë°°ê²½ ê·¸ë¦¬ê¸?        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.text().color())
        
        # ?ìŠ¤???ì—­ ê³„ì‚° - ?ì ˆ???í•˜ ?¬ë°±
        text_rect = option.rect.adjusted(5, 12, -5, -12)
        
        if text and " | " in text:
            # ?„ë¡œ?íŠ¸ëª…ê³¼ ???¸ìˆ˜ ë¶„ë¦¬
            parts = text.split(" | ", 1)
            project_name = parts[0]
            unit_info = parts[1] if len(parts) > 1 else ""
            
            total_height = text_rect.height()
            line_spacing = 2
            
            # ?„ë¡œ?íŠ¸ëª?ê·¸ë¦¬ê¸?(?„ìª½)
            font1 = QFont("ë§‘ì? ê³ ë”•", self.default_font_size)
            font1.setBold(True)
            painter.setFont(font1)
            
            fm1 = QFontMetrics(font1)
            text1_height = fm1.height()
            
            top_y = text_rect.center().y() - line_spacing // 2 - text1_height // 2 + 3  # 3px ?„ë˜ë¡?            top_rect = QRect(text_rect.x(), top_y - text1_height // 2, text_rect.width(), text1_height)
            painter.drawText(top_rect, Qt.AlignCenter, project_name)
            
            # ???¸ìˆ˜ ê·¸ë¦¬ê¸?(?„ë˜ìª?
            if unit_info:
                font2 = QFont("ë§‘ì? ê³ ë”•", self.sub_font_size)
                font2.setWeight(QFont.Light)  # ê°€?˜ê²Œ ?¤ì •
                painter.setFont(font2)
                
                fm2 = QFontMetrics(font2)
                text2_height = fm2.height()
                
                bottom_y = text_rect.center().y() + line_spacing // 2 + text2_height // 2 + 3  # 3px ?„ë˜ë¡?                bottom_rect = QRect(text_rect.x(), bottom_y - text2_height // 2, text_rect.width(), text2_height)
                painter.drawText(bottom_rect, Qt.AlignCenter, unit_info)
        else:
            # ???¸ìˆ˜ê°€ ?†ëŠ” ê²½ìš° ?„ë¡œ?íŠ¸ëª…ë§Œ ê°€?´ë° ?œì‹œ
            font = QFont("ë§‘ì? ê³ ë”•", self.default_font_size)
            font.setBold(True)
            painter.setFont(font)
            
            # 3px ?„ë˜ë¡?ì¡°ì •???ì—­
            adjusted_rect = QRect(text_rect.x(), text_rect.y() + 3, text_rect.width(), text_rect.height())
            painter.drawText(adjusted_rect, Qt.AlignCenter, text)
        
        painter.restore()
    
    def sizeHint(self, option, index):
        return QSize(option.rect.width(), 85)  # ?’ì´ë¥?85ë¡??¤ì •

class CustomDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        
    def paint(self, painter, option, index):
        text = index.data(Qt.DisplayRole)
        
        if text in ["?„ë¡œ?íŠ¸ ê´€ë¦?, "ê³µì • ê´€ë¦?]:
            painter.save()
            
            if option.state & QStyle.State_Selected:
                painter.fillRect(option.rect, QColor(125, 148, 113, 80))
            else:
                painter.fillRect(option.rect, QColor(125, 148, 113, 40))
            
            painter.setPen(QPen(QColor(206, 212, 218), 1))
            painter.drawLine(option.rect.topLeft(), option.rect.topRight())
            
            if text == "?„ë¡œ?íŠ¸ ê´€ë¦?:
                font = QFont("ë§‘ì? ê³ ë”•", 12)  # ?„ë¡œ?íŠ¸ ê´€ë¦?12pxë¡?ë³€ê²?            else:
                font = QFont("ë§‘ì? ê³ ë”•", 9)  # ê³µì • ê´€ë¦¬ëŠ” ê·¸ë?ë¡?            painter.setFont(font)
            painter.setPen(QColor(73, 80, 87))
            
            # ê³µì • ê´€ë¦¬ëŠ” ?„ë¡œ 2px, ?„ë¡œ?íŠ¸ ê´€ë¦¬ëŠ” ?„ë˜ë¡?3px ì¡°ì •
            if text == "ê³µì • ê´€ë¦?:
                adjusted_rect = QRect(option.rect.x(), option.rect.y() - 2, option.rect.width(), option.rect.height())
            else:
                adjusted_rect = QRect(option.rect.x(), option.rect.y() + 3, option.rect.width(), option.rect.height())
            painter.drawText(adjusted_rect, Qt.AlignCenter, text)
            
            painter.restore()
        else:
            super().paint(painter, option, index)
    
    def sizeHint(self, option, index):
        text = index.data(Qt.DisplayRole)
        if text in ["?„ë¡œ?íŠ¸ ê´€ë¦?, "ê³µì • ê´€ë¦?]:
            return QSize(option.rect.width(), 35)
        return super().sizeHint(option, index)


class ProcessDelegate(QStyledItemDelegate):
    def __init__(self, processes, parent=None):
        super().__init__(parent)
        self.processes = processes
    
    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.addItem("")
        combo.addItems(self.processes)
        combo.setEditable(True)
        combo.setMaxVisibleItems(20)  # ëª¨ë“  ??ª©??ë³´ì´?„ë¡ ì¦ê?
        
        combo.setStyleSheet("""
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                color: #495057;
                selection-background-color: rgba(125, 148, 113, 0.3);
                selection-color: #495057;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 3px 8px;
                border: none;
                color: #495057;
                min-height: 16px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(125, 148, 113, 0.2);
                color: #495057;
            }
            QComboBox QAbstractScrollBar:vertical {
                width: 0px;
            }
        """)
        
        return combo
    
    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.EditRole) or ""
        editor.setCurrentText(str(value))
    
    def setModelData(self, editor, model, index):
        model.setData(index, editor.currentText(), Qt.EditRole)
    
    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class ManagementDialog(QDialog):
    def __init__(self, title, button_configs, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(380, 250)
        self.selected_action = None
        self.init_ui(button_configs)
        
    def init_ui(self, button_configs):
        self.setStyleSheet("QDialog { background-color: #f8f9fa; }")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(20)
        
        button_style = """
            QPushButton {
                background-color: #7d9471;
                color: white;
                border: none;
                padding: 8px 24px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 21px;
                min-height: 35px;
                max-height: 35px;
            }
            QPushButton:hover { background-color: #6d8062; }
            QPushButton:pressed { background-color: #5d6f54; }
        """
        
        delete_style = button_style.replace("#7d9471", "#d9534f").replace("#6d8062", "#c9302c").replace("#5d6f54", "#ac2925")
        
        for text, action, style in button_configs:
            btn = QPushButton(text)
            btn.setStyleSheet(delete_style if "?? œ" in text else button_style)
            btn.clicked.connect(lambda checked, a=action: self.handle_action(a))
            layout.addWidget(btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def handle_action(self, action):
        self.selected_action = action
        action()


class ProjectManagementDialog(ManagementDialog):
    def __init__(self, projects_data, parent=None):
        self.projects_data = projects_data
        self.selected_project = None
        self.new_name = None
        
        button_configs = [
            ("???„ë¡œ?íŠ¸ ì¶”ê?", self.add_project, None),
            ("?„ë¡œ?íŠ¸ ?´ë¦„ ë³€ê²?, self.rename_project, None),
            ("?„ë¡œ?íŠ¸ ?? œ", self.delete_project, None)
        ]
        
        super().__init__("?„ë¡œ?íŠ¸ ê´€ë¦?, button_configs, parent)
    
    def add_project(self):
        dialog = QDialog(self)
        dialog.setWindowTitle('???„ë¡œ?íŠ¸')
        dialog.resize(400, 250)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # ?„ë¡œ?íŠ¸ëª??…ë ¥
        project_label = QLabel("?„ë¡œ?íŠ¸ëª?")
        project_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(project_label)
        
        project_input = QLineEdit()
        project_input.setMinimumHeight(35)
        project_input.setPlaceholderText("?? ?¬ì˜???Œí¬?ì´")
        layout.addWidget(project_input)
        
        # ???¸ìˆ˜ ?…ë ¥
        unit_label = QLabel("???¸ìˆ˜:")
        unit_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(unit_label)
        
        unit_input = QLineEdit()
        unit_input.setMinimumHeight(35)
        unit_input.setPlaceholderText("?? 101??1003??)
        layout.addWidget(unit_input)
        
        # ë²„íŠ¼
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("ì·¨ì†Œ")
        cancel_btn.setStyleSheet(BUTTON_STYLE.replace("#7d9471", "#6c757d"))
        cancel_btn.clicked.connect(dialog.reject)
        
        ok_btn = QPushButton("?•ì¸")
        ok_btn.setStyleSheet(BUTTON_STYLE)
        ok_btn.clicked.connect(dialog.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            project_name = project_input.text().strip()
            unit_info = unit_input.text().strip()
            
            if project_name:
                # ?„ë¡œ?íŠ¸ëª…ê³¼ ???¸ìˆ˜ë¥?| ë¡?êµ¬ë¶„?˜ì—¬ ?€??                full_name = project_name
                if unit_info:
                    full_name = f"{project_name} | {unit_info}"
                
                if full_name in self.projects_data:
                    QMessageBox.warning(self, "ê²½ê³ ", "?´ë? ì¡´ì¬?˜ëŠ” ?„ë¡œ?íŠ¸?…ë‹ˆ??")
                    return
                
                self.selected_project = full_name
                self.selected_action = 'add'
                self.accept()
    
    def rename_project(self):
        if not self.projects_data:
            QMessageBox.warning(self, "ê²½ê³ ", "?´ë¦„??ë³€ê²½í•  ?„ë¡œ?íŠ¸ê°€ ?†ìŠµ?ˆë‹¤.")
            return
        
        # ?„ë¡œ?íŠ¸ ? íƒ
        dialog1 = QInputDialog(self)
        dialog1.setWindowTitle('?„ë¡œ?íŠ¸ ? íƒ')
        dialog1.setLabelText('?´ë¦„??ë³€ê²½í•  ?„ë¡œ?íŠ¸ë¥?? íƒ?˜ì„¸??')
        dialog1.setComboBoxItems(sorted(self.projects_data.keys()))
        dialog1.setInputMode(QInputDialog.TextInput)
        dialog1.setOption(QInputDialog.UseListViewForComboBoxItems)
        dialog1.resize(400, 200)
        
        if dialog1.exec_() != QDialog.Accepted:
            return
        
        old_full_name = dialog1.textValue()
        
        # ê¸°ì¡´ ?„ë¡œ?íŠ¸ëª…ê³¼ ???¸ìˆ˜ ë¶„ë¦¬
        old_project = old_full_name
        old_unit = ""
        if " | " in old_full_name:
            parts = old_full_name.split(" | ", 1)
            old_project = parts[0]
            old_unit = parts[1] if len(parts) > 1 else ""
        
        # ???„ë¡œ?íŠ¸ëª…ê³¼ ???¸ìˆ˜ ?…ë ¥
        dialog2 = QDialog(self)
        dialog2.setWindowTitle('?„ë¡œ?íŠ¸ ?´ë¦„ ë³€ê²?)
        dialog2.resize(400, 250)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # ?„ë¡œ?íŠ¸ëª??…ë ¥
        project_label = QLabel("?„ë¡œ?íŠ¸ëª?")
        project_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(project_label)
        
        project_input = QLineEdit(old_project)
        project_input.setMinimumHeight(35)
        layout.addWidget(project_input)
        
        # ???¸ìˆ˜ ?…ë ¥
        unit_label = QLabel("???¸ìˆ˜:")
        unit_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(unit_label)
        
        unit_input = QLineEdit(old_unit)
        unit_input.setMinimumHeight(35)
        layout.addWidget(unit_input)
        
        # ë²„íŠ¼
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("ì·¨ì†Œ")
        cancel_btn.setStyleSheet(BUTTON_STYLE.replace("#7d9471", "#6c757d"))
        cancel_btn.clicked.connect(dialog2.reject)
        
        ok_btn = QPushButton("?•ì¸")
        ok_btn.setStyleSheet(BUTTON_STYLE)
        ok_btn.clicked.connect(dialog2.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        dialog2.setLayout(layout)
        
        if dialog2.exec_() == QDialog.Accepted:
            new_project = project_input.text().strip()
            new_unit = unit_input.text().strip()
            
            if new_project:
                # ???„ë¡œ?íŠ¸ëª…ê³¼ ???¸ìˆ˜ë¥?| ë¡?êµ¬ë¶„?˜ì—¬ ?€??                new_full_name = new_project
                if new_unit:
                    new_full_name = f"{new_project} | {new_unit}"
                
                if new_full_name != old_full_name:
                    if new_full_name in self.projects_data:
                        QMessageBox.warning(self, "ê²½ê³ ", "?´ë? ì¡´ì¬?˜ëŠ” ?„ë¡œ?íŠ¸?…ë‹ˆ??")
                        return
                    
                    self.selected_project = old_full_name
                    self.new_name = new_full_name
                    self.selected_action = 'rename'
                    self.accept()
    
    def delete_project(self):
        if not self.projects_data:
            QMessageBox.warning(self, "ê²½ê³ ", "?? œ???„ë¡œ?íŠ¸ê°€ ?†ìŠµ?ˆë‹¤.")
            return
        
        # ?„ë¡œ?íŠ¸ ? íƒ ?¤ì´?¼ë¡œê·?        dialog1 = QInputDialog(self)
        dialog1.setWindowTitle('?„ë¡œ?íŠ¸ ? íƒ')
        dialog1.setLabelText('?? œ???„ë¡œ?íŠ¸ë¥?? íƒ?˜ì„¸??')
        dialog1.setComboBoxItems(sorted(self.projects_data.keys()))
        dialog1.setInputMode(QInputDialog.TextInput)
        dialog1.setOption(QInputDialog.UseListViewForComboBoxItems)
        dialog1.resize(400, 200)
        
        if dialog1.exec_() != QDialog.Accepted:
            return
        
        project = dialog1.textValue()
        
        # ë¹„ë?ë²ˆí˜¸ ?…ë ¥ ?¤ì´?¼ë¡œê·?        dialog2 = QInputDialog(self)
        dialog2.setWindowTitle('?„ë¡œ?íŠ¸ ?? œ ?•ì¸')
        dialog2.setLabelText(f'"{project}" ?„ë¡œ?íŠ¸ë¥??? œ?˜ë ¤ë©?ë¹„ë?ë²ˆí˜¸ë¥??…ë ¥?˜ì„¸??')
        dialog2.setInputMode(QInputDialog.TextInput)
        dialog2.setTextEchoMode(QLineEdit.Password)
        dialog2.resize(400, 200)
        
        if dialog2.exec_() != QDialog.Accepted:
            return
        
        password = dialog2.textValue()
        
        if password != "0109":
            QMessageBox.critical(self, "?¤ë¥˜", "ë¹„ë?ë²ˆí˜¸ê°€ ?¬ë°”ë¥´ì? ?ŠìŠµ?ˆë‹¤.")
            return
        
        reply = QMessageBox.question(self, "?•ì¸", f'?„ë¡œ?íŠ¸ "{project}"ë¥??? œ?˜ì‹œê² ìŠµ?ˆê¹Œ?\nëª¨ë“  ?°ì´?°ê? ?¬ë¼ì§‘ë‹ˆ??',
                                    QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.selected_project = project
            self.accept()


class ProcessManagementDialog(ManagementDialog):
    def __init__(self, processes, parent=None):
        self.processes = processes.copy()
        self.result_processes = None
        
        button_configs = [
            ("??ê³µì • ì¶”ê?", self.add_process, None),
            ("ê³µì • ?œì„œ ë³€ê²?, self.change_order, None),
            ("ê³µì • ?? œ", self.delete_process, None)
        ]
        
        # ë²„íŠ¼ ?œì„±???íƒœ ?¤ì •
        for i, (text, action, style) in enumerate(button_configs):
            if "?œì„œ" in text and len(self.processes) <= 1:
                button_configs[i] = (text, lambda: None, None)
            elif "?? œ" in text and len(self.processes) == 0:
                button_configs[i] = (text, lambda: None, None)
        
        super().__init__("ê³µì • ê´€ë¦?, button_configs, parent)
    
    def add_process(self):
        process_name, ok = QInputDialog.getText(self, '??ê³µì •', 'ê³µì •ëª…ì„ ?…ë ¥?˜ì„¸??')
        if ok and process_name.strip():
            if process_name.strip() in self.processes:
                QMessageBox.warning(self, "ê²½ê³ ", "?´ë? ì¡´ì¬?˜ëŠ” ê³µì •ëª…ì…?ˆë‹¤.")
                return
            self.processes.append(process_name.strip())
            self.result_processes = self.processes
            self.accept()
    
    def change_order(self):
        dialog = ProcessOrderDialog(self.processes, self)
        if dialog.exec_() == QDialog.Accepted:
            self.processes = dialog.get_ordered_processes()
            self.result_processes = self.processes
            self.accept()
    
    def delete_process(self):
        if not self.processes:
            QMessageBox.warning(self, "ê²½ê³ ", "?? œ??ê³µì •???†ìŠµ?ˆë‹¤.")
            return
        
        process, ok = QInputDialog.getItem(self, 'ê³µì • ? íƒ', '?? œ??ê³µì •??? íƒ?˜ì„¸??', self.processes, 0, False)
        if ok:
            reply = QMessageBox.question(self, "?•ì¸", f'ê³µì • "{process}"ë¥??? œ?˜ì‹œê² ìŠµ?ˆê¹Œ?\nê¸°ì¡´ ?°ì´?°ì˜ ê³µì •ëª…ì? ? ì??©ë‹ˆ??',
                                        QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.processes.remove(process)
                self.result_processes = self.processes
                self.accept()


class ProcessOrderDialog(QDialog):
    def __init__(self, processes, parent=None):
        super().__init__(parent)
        self.processes = processes.copy()
        self.setWindowTitle("ê³µì • ?œì„œ ë³€ê²?)
        self.setModal(True)
        self.setFixedSize(400, 500)
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet("QDialog { background-color: #f8f9fa; }")
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        
        info_label = QLabel("?œë˜ê·¸í•˜???œì„œë¥?ë³€ê²½í•˜?¸ìš”")
        info_label.setStyleSheet("font-size: 14px; color: #495057; padding: 10px;")
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.InternalMove)
        self.list_widget.setDefaultDropAction(Qt.MoveAction)
        self.list_widget.addItems(self.processes)
        layout.addWidget(self.list_widget)
        
        button_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("ì·¨ì†Œ")
        cancel_btn.setStyleSheet(BUTTON_STYLE.replace("#7d9471", "#6c757d"))
        cancel_btn.clicked.connect(self.reject)
        
        confirm_btn = QPushButton("?•ì¸")
        confirm_btn.setStyleSheet(BUTTON_STYLE)
        confirm_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(confirm_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def get_ordered_processes(self):
        return [self.list_widget.item(i).text() for i in range(self.list_widget.count())]


class ProcessSummaryDialog(QDialog):
    def __init__(self, project_data, processes, parent=None):
        super().__init__(parent)
        self.project_data = project_data
        self.processes = processes
        self.setWindowTitle("ê³µì •ë³?ê¸ˆì•¡ ?”ì•½")
        self.setModal(True)
        self.resize(800, 850)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["ê³µì •", "?ì¬ë¹?, "?¸ê±´ë¹?, "ë¶€ê°€??, "ì´ì•¡"])
        
        header = self.table.horizontalHeader()
        header.setStretchLastSection(True)
        self.table.setColumnWidth(0, 150)
        for i in range(1, 4):
            self.table.setColumnWidth(i, 130)
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.table)
        
        total_layout = QHBoxLayout()
        total_layout.addStretch()
        
        self.total_label = QLabel()
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        total_layout.addWidget(self.total_label)
        
        layout.addLayout(total_layout)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.button(QDialogButtonBox.Ok).setText("?•ì¸")
        button_box.button(QDialogButtonBox.Cancel).setText("Excel ?´ë³´?´ê¸°")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.export_to_excel)
        
        layout.addWidget(button_box)
        self.setLayout(layout)
        
        self.calculate_and_display()
        
    def calculate_and_display(self):
        process_totals = {process: {'material': 0, 'labor': 0, 'vat': 0, 'total': 0} for process in self.processes}
        
        for item in self.project_data:
            process = item.get('process', 'ê¸°í?') or 'ê¸°í?'
            if process not in process_totals:
                process_totals[process] = {'material': 0, 'labor': 0, 'vat': 0, 'total': 0}
            
            process_totals[process]['material'] += item.get('material_amount', 0)
            process_totals[process]['labor'] += item.get('labor_amount', 0)
            process_totals[process]['vat'] += item.get('vat_amount', 0)
            process_totals[process]['total'] += item.get('total_amount', 0)
        
        row_count = 0
        grand_totals = {'material': 0, 'labor': 0, 'vat': 0, 'total': 0}
        
        for process in self.processes + [p for p in process_totals if p not in self.processes]:
            if process in process_totals and process_totals[process]['total'] > 0:
                self.add_row(row_count, process, process_totals[process])
                for key in grand_totals:
                    grand_totals[key] += process_totals[process][key]
                row_count += 1
        
        self.table.setRowCount(row_count)
        
        total_text = f"?„ì²´ ?©ê³„: ?ì¬ë¹?{grand_totals['material']:,}?? "
        total_text += f"?¸ê±´ë¹?{grand_totals['labor']:,}?? "
        total_text += f"ë¶€ê°€??{grand_totals['vat']:,}?? "
        total_text += f"ì´ì•¡ {grand_totals['total']:,}??
        self.total_label.setText(total_text)
        
    def add_row(self, row, process, totals):
        self.table.setRowCount(row + 1)
        
        items = [
            (process, Qt.AlignCenter, None),
            (f"{totals['material']:,}??, Qt.AlignRight | Qt.AlignVCenter, None),
            (f"{totals['labor']:,}??, Qt.AlignRight | Qt.AlignVCenter, None),
            (f"{totals['vat']:,}??, Qt.AlignRight | Qt.AlignVCenter, None),
            (f"{totals['total']:,}??, Qt.AlignRight | Qt.AlignVCenter, QFont("ë§‘ì? ê³ ë”•", 9, QFont.Bold))
        ]
        
        for col, (text, alignment, font) in enumerate(items):
            item = QTableWidgetItem(text)
            item.setTextAlignment(alignment)
            if font:
                item.setFont(font)
            self.table.setItem(row, col, item)
        
    def export_to_excel(self):
        try:
            filename, _ = QFileDialog.getSaveFileName(self, "ê³µì •ë³?ê¸ˆì•¡ Excel ?€??, "ê³µì •ë³?ê¸ˆì•¡_?”ì•½.xlsx", "Excel files (*.xlsx)")
            if not filename:
                return
            
            data = []
            for row in range(self.table.rowCount()):
                row_data = {}
                for col in range(self.table.columnCount()):
                    item = self.table.item(row, col)
                    if item:
                        header = self.table.horizontalHeaderItem(col).text()
                        text = item.text().replace(',', '').replace('??, '').strip()
                        row_data[header] = text if col == 0 else int(text) if text else 0
                data.append(row_data)
            
            pd.DataFrame(data).to_excel(filename, index=False)
            QMessageBox.information(self, "?±ê³µ", f"ê³µì •ë³?ê¸ˆì•¡??Excel ?Œì¼ë¡??€?¥ë˜?ˆìŠµ?ˆë‹¤.\n{filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "?¤ë¥˜", f"Excel ?Œì¼ ?€??ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤:\n{str(e)}")


class CustomTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.item_name_delegate = None
        self.memo_button_clicked = False
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            item = self.itemAt(event.pos())
            if item and item.column() == 3:
                rect = self.visualItemRect(item)
                button_rect = QRect(rect.right() - 28, rect.center().y() - 10, 20, 20)
                self.memo_button_clicked = button_rect.contains(event.pos())
            else:
                self.memo_button_clicked = False
        super().mousePressEvent(event)
        
    def mouseMoveEvent(self, event):
        item = self.itemAt(event.pos())
        if item and item.column() == 3:
            rect = self.visualItemRect(item)
            button_rect = QRect(rect.right() - 28, rect.center().y() - 10, 20, 20)
            
            if button_rect.contains(event.pos()):
                if self.item_name_delegate and self.item_name_delegate.main_window:
                    row = item.row()
                    memo = self.item_name_delegate.main_window.get_memo_for_row(row)
                    has_memo = self._check_has_memo(memo)
                    QToolTip.showText(event.globalPos(), "?´ë¦­: ë©”ëª¨ ë³´ê¸°/?¸ì§‘\n?°í´ë¦? ë©”ëª¨ ?? œ" if has_memo else "?´ë¦­?˜ì—¬ ë©”ëª¨ ì¶”ê?")
            else:
                QToolTip.hideText()
        else:
            QToolTip.hideText()
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        QToolTip.hideText()
        super().leaveEvent(event)
    
    def _check_has_memo(self, memo):
        if not memo:
            return False
        try:
            memo_data = json.loads(memo)
            if isinstance(memo_data, dict) and 'html' in memo_data:
                doc = QTextDocument()
                doc.setHtml(memo_data['html'])
                plain_text = doc.toPlainText().strip()
                return (plain_text and any(char not in ' \t\n\r' for char in plain_text)) or \
                       (memo_data.get('images') and len(memo_data['images']) > 0) or \
                       '<img' in memo_data['html']
        except:
            doc = QTextDocument()
            doc.setHtml(memo)
            plain_text = doc.toPlainText().strip()
            return plain_text and any(char not in ' \t\n\r' for char in plain_text)


class ItemNameDelegate(QStyledItemDelegate):
    memo_clicked = pyqtSignal(int)
    memo_delete_requested = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.button_width = 20
        self.button_height = 20
        self.button_margin = 8
        self.main_window = None
    
    def paint(self, painter, option, index):
        row = index.row()
        has_memo = False
        is_active_memo = False
        
        if self.main_window:
            memo = self.main_window.get_memo_for_row(row)
            has_memo = self._check_has_memo(memo)
            # ?„ì¬ ?‰ì´ ? íƒ?˜ì–´ ?ˆê³  ë©”ëª¨ê°€ ?¤ì œë¡??ˆì„ ?Œë§Œ active ?íƒœë¡??œì‹œ
            is_active_memo = self.main_window.memo_visible and self.main_window.current_memo_row == row and has_memo
        
        super().paint(painter, option, index)
        
        button_rect = QRect(
            option.rect.right() - self.button_width - self.button_margin,
            option.rect.center().y() - self.button_height // 2,
            self.button_width,
            self.button_height
        )
        
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        if is_active_memo:
            button_color = QColor(105, 128, 93)
            border_color = QColor(75, 98, 63)
        elif has_memo:
            button_color = QColor(125, 148, 113)
            border_color = QColor(95, 118, 83)
        else:
            button_color = QColor(200, 200, 200)
            border_color = QColor(170, 170, 170)
        
        painter.fillRect(button_rect, QBrush(button_color))
        painter.setPen(QPen(border_color, 1))
        painter.setBrush(Qt.NoBrush)
        painter.drawRect(button_rect)
        
        painter.setPen(QPen(Qt.white, 2))
        for i in range(3):
            y_pos = button_rect.top() + 4 + (i * 5)
            right_margin = 4 + (2 if i == 2 else 0)
            painter.drawLine(button_rect.left() + 4, y_pos, button_rect.right() - right_margin, y_pos)
        
        painter.restore()
    
    def editorEvent(self, event, model, option, index):
        button_rect = QRect(
            option.rect.right() - self.button_width - self.button_margin,
            option.rect.center().y() - self.button_height // 2,
            self.button_width,
            self.button_height
        )
        
        if event.type() == event.MouseButtonRelease and event.button() == Qt.LeftButton:
            if button_rect.contains(event.pos()):
                if hasattr(self.parent(), 'memo_button_clicked'):
                    self.parent().memo_button_clicked = True
                self.memo_clicked.emit(index.row())
                return True
        
        elif event.type() == event.MouseButtonPress and event.button() == Qt.RightButton:
            if button_rect.contains(event.pos()):
                row = index.row()
                has_memo = False
                
                if self.main_window:
                    memo = self.main_window.get_memo_for_row(row)
                    has_memo = self._check_has_memo(memo)
                
                if has_memo:
                    menu = QMenu()
                    delete_action = menu.addAction("ë©”ëª¨ ?? œ")
                    if menu.exec_(event.globalPos()) == delete_action:
                        self.memo_delete_requested.emit(row)
                
                return True
        
        return super().editorEvent(event, model, option, index)
    
    def _check_has_memo(self, memo):
        if not memo:
            return False
        try:
            memo_data = json.loads(memo)
            if isinstance(memo_data, dict) and 'html' in memo_data:
                doc = QTextDocument()
                doc.setHtml(memo_data['html'])
                plain_text = doc.toPlainText().strip()
                return (plain_text and any(char not in ' \t\n\r' for char in plain_text)) or \
                       (memo_data.get('images') and len(memo_data['images']) > 0) or \
                       '<img' in memo_data['html']
        except:
            doc = QTextDocument()
            doc.setHtml(memo)
            plain_text = doc.toPlainText().strip()
            return plain_text and any(char not in ' \t\n\r' for char in plain_text)


class ImageTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.viewport().installEventFilter(self)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            cursor = self.cursorForPosition(event.pos())
            document = self.document()
            
            for block in self._iterate_blocks(document):
                for fragment in self._iterate_fragments(block):
                    if fragment.charFormat().isImageFormat():
                        img_rect = self._get_image_rect(fragment, document)
                        if img_rect.contains(event.pos()):
                            self._show_image(fragment, document)
                            return
        
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        is_on_image = False
        
        for block in self._iterate_blocks(self.document()):
            for fragment in self._iterate_fragments(block):
                if fragment.charFormat().isImageFormat():
                    img_rect = self._get_image_rect(fragment, self.document())
                    if img_rect.contains(event.pos()):
                        is_on_image = True
                        break
            if is_on_image:
                break
        
        self.viewport().setCursor(Qt.PointingHandCursor if is_on_image else Qt.IBeamCursor)
        QToolTip.showText(event.globalPos(), "?´ë¦­?˜ì—¬ ?´ë?ì§€ ë³´ê¸°") if is_on_image else QToolTip.hideText()
        
        super().mouseMoveEvent(event)
    
    def canInsertFromMimeData(self, source):
        if source.hasImage():
            return True
        if source.hasUrls():
            return any(url.toLocalFile().lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')) 
                      for url in source.urls() if url.isLocalFile())
        return super().canInsertFromMimeData(source)
    
    def insertFromMimeData(self, source):
        if source.hasImage():
            self._insert_image(source.imageData())
            return
        
        if source.hasUrls():
            for url in source.urls():
                if url.isLocalFile():
                    file_path = url.toLocalFile()
                    if file_path.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.bmp')):
                        image = QImage(file_path)
                        if not image.isNull():
                            self._insert_image(image, file_path)
                            return
        
        super().insertFromMimeData(source)
    
    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Paste):
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            if mime_data.hasImage() or mime_data.hasUrls():
                self.insertFromMimeData(mime_data)
                return
        super().keyPressEvent(event)
    
    def _iterate_blocks(self, document):
        block = document.firstBlock()
        while block.isValid():
            yield block
            block = block.next()
    
    def _iterate_fragments(self, block):
        it = block.begin()
        while not it.atEnd():
            fragment = it.fragment()
            if fragment.isValid():
                yield fragment
            it += 1
    
    def _get_image_rect(self, fragment, document):
        pos = fragment.position()
        img_cursor = QTextCursor(document)
        img_cursor.setPosition(pos)
        img_rect = self.cursorRect(img_cursor)
        
        image_format = fragment.charFormat().toImageFormat()
        return QRect(img_rect.x(), img_rect.y(), int(image_format.width()), int(image_format.height()))
    
    def _show_image(self, fragment, document):
        image_format = fragment.charFormat().toImageFormat()
        image_name = image_format.name()
        
        if image_name:
            url = QUrl(image_name) if not image_name.startswith('http') else QUrl.fromLocalFile(image_name)
            image = document.resource(QTextDocument.ImageResource, url)
            
            if image and isinstance(image, QImage):
                from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea
                viewer = ImageViewer(image, self.window())
                viewer.show()
    
    def _insert_image(self, image, file_path=None):
        if not isinstance(image, QImage):
            return
        
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.Start)
        
        document = self.document()
        last_image_position = 0
        
        for block in self._iterate_blocks(document):
            for fragment in self._iterate_fragments(block):
                if fragment.charFormat().isImageFormat():
                    last_image_position = fragment.position() + fragment.length()
        
        if last_image_position > 0:
            cursor.setPosition(last_image_position)
            cursor.insertText("\n")
        
        timestamp = datetime.now().timestamp()
        image_name = file_path if file_path else f"image_{timestamp}.png"
        if file_path:
            image_name = f"file:///{file_path}".replace('\\', '/')
        
        url = QUrl(image_name)
        document.addResource(QTextDocument.ImageResource, url, image)
        
        image_format = QTextImageFormat()
        image_format.setName(image_name)
        
        max_size = 600
        if image.width() > max_size or image.height() > max_size:
            scale_ratio = min(max_size / image.width(), max_size / image.height())
            image_format.setWidth(int(image.width() * scale_ratio))
            image_format.setHeight(int(image.height() * scale_ratio))
        else:
            image_format.setWidth(image.width())
            image_format.setHeight(image.height())
        
        block_format = cursor.blockFormat()
        block_format.setAlignment(Qt.AlignLeft)
        cursor.setBlockFormat(block_format)
        
        cursor.insertImage(image_format)
        cursor.insertText("\n")
        cursor.movePosition(QTextCursor.End)
        self.setTextCursor(cursor)


class ImageViewer(QDialog):
    def __init__(self, image, parent=None):
        super().__init__(parent)
        self.image = image
        self.scale_factor = 1.0
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMinMaxButtonsHint)
        self.init_ui()
        self.center_on_screen()
        
    def init_ui(self):
        self.setWindowTitle("?´ë?ì§€ ë³´ê¸°")
        self.setWindowFlags(Qt.Window | Qt.WindowCloseButtonHint | Qt.WindowMaximizeButtonHint)
        
        screen = QApplication.primaryScreen().geometry()
        max_width = int(screen.width() * 0.9)
        max_height = int(screen.height() * 0.9)
        
        img_width = self.image.width()
        img_height = self.image.height()
        
        if img_width > max_width or img_height > max_height:
            self.scale_factor = min(max_width / img_width, max_height / img_height)
            window_width = int(img_width * self.scale_factor)
            window_height = int(img_height * self.scale_factor)
        else:
            window_width = img_width
            window_height = img_height
        
        window_width = max(window_width + 40, 400)
        window_height = max(window_height + 100, 300)
        
        self.resize(window_width, window_height)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        self.scroll_area.setStyleSheet("QScrollArea { background-color: #f0f0f0; border: 1px solid #ccc; }")
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: white;")
        
        self.zoom_label = QLabel(f"{int(self.scale_factor * 100)}%")
        self.zoom_label.setMinimumWidth(60)
        self.zoom_label.setAlignment(Qt.AlignCenter)
        
        self.update_image()
        
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area)
        
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        buttons = [
            ("ì¶•ì†Œ (-)", self.zoom_out),
            ("?•ë? (+)", self.zoom_in),
            ("ì°½ì— ë§ì¶”ê¸?, self.zoom_fit),
            ("?ë³¸ ?¬ê¸° (1:1)", self.zoom_original)
        ]
        
        for text, func in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(BUTTON_STYLE)
            btn.clicked.connect(func)
            button_layout.addWidget(btn)
        
        button_layout.addWidget(self.zoom_label)
        button_layout.addStretch()
        
        close_btn = QPushButton("?«ê¸°")
        close_btn.setStyleSheet(BUTTON_STYLE)
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
        QShortcut(QKeySequence("+"), self, self.zoom_in)
        QShortcut(QKeySequence("-"), self, self.zoom_out)
        QShortcut(QKeySequence("="), self, self.zoom_in)
        QShortcut(QKeySequence("0"), self, self.zoom_original)
    
    def update_image(self):
        scaled_image = self.image.scaled(
            int(self.image.width() * self.scale_factor),
            int(self.image.height() * self.scale_factor),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(QPixmap.fromImage(scaled_image))
        
        if hasattr(self, 'zoom_label'):
            self.zoom_label.setText(f"{int(self.scale_factor * 100)}%")
    
    def zoom_in(self):
        self.scale_factor = min(self.scale_factor * 1.25, 5.0)
        self.update_image()
    
    def zoom_out(self):
        self.scale_factor = max(self.scale_factor * 0.8, 0.1)
        self.update_image()
    
    def zoom_fit(self):
        if hasattr(self, 'scroll_area'):
            viewport_size = self.scroll_area.viewport().size()
            self.scale_factor = min(viewport_size.width() / self.image.width(), 
                                   viewport_size.height() / self.image.height()) * 0.95
            self.update_image()
    
    def zoom_original(self):
        self.scale_factor = 1.0
        self.update_image()
    
    def center_on_screen(self):
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        window_geometry.moveCenter(screen.center())
        self.move(window_geometry.topLeft())


class InteriorSettlementApp(QMainWindow):
    firebase_data_changed = pyqtSignal(dict)
    
    def __init__(self, user_email=None):
        super().__init__()
        self.user_email = user_email
        self.projects_data = {}
        self.current_project = None
        self.users = ["?ì?", "? ì• ", "?¬ì²œ", "ë¯¼ê¸°", "?¬ì„±"]
        self.current_user = None
        self.sort_column = -1
        self.sort_order = Qt.AscendingOrder
        self.undo_stack = []
        self.max_undo_stack = 20
        self.processes = ["ê°€??, "ì² ê±°", "?¤ë¹„/ë¯¸ì¥", "?„ê¸°", "ëª©ê³µ", "ì¡°ëª…", "ê°€êµ?, "ë°”ë‹¥", "?€??, "?•ì‹¤", "?„ë¦„", "?„ë°°", "?„ì¥", "ì°½í˜¸", "ê¸°í?"]
        self.memo_visible = True
        self.current_memo_row = -1
        self.original_window_size = QSize(1650, 1100)
        
        self.firebase_sync = None
        self.is_updating = False
        
        # ?…ë°?´íŠ¸ ì²´ì»¤ ì´ˆê¸°??        self.update_checker = UpdateChecker(self)
        self.update_checker.update_available.connect(self.show_update_dialog)
        
        self.init_ui()
        self.load_all_data()
        self.setup_firebase_sync()
        
        # ?…ë°?´íŠ¸ ê´€???Œì¼ ?•ë¦¬
        self.cleanup_update_files()
        
        # ?„ë¡œê·¸ë¨ ?œì‘ ???…ë°?´íŠ¸ ?•ì¸
        QTimer.singleShot(3000, self.background_update_check)
        
        if hasattr(self, 'user_guide_label') and not self.current_user:
            self.user_guide_label.setVisible(True)

    def cleanup_update_files(self):
        """?…ë°?´íŠ¸ ê´€???Œì¼ ?•ë¦¬"""
        try:
            exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
            
            # ?? œ???Œì¼ ëª©ë¡
            cleanup_files = [
                'update.bat',
                'update_silent.vbs',
                'update_in_progress.flag', 
                'update_complete.flag',
                'update_new.exe',
                'HV-L_update_temp.exe',
                'update_temp.exe'
            ]
            
            for file_name in cleanup_files:
                file_path = os.path.join(exe_dir, file_name)
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        print(f"Cleaned up: {file_name}")
                    except:
                        pass
        except:
            pass
    
    def setup_firebase_sync(self):
        USE_FIREBASE_SYNC = True
        
        if not USE_FIREBASE_SYNC:
            if hasattr(self, 'sync_status_label'):
                self.sync_status_label.setText("??)
                self.sync_status_label.setStyleSheet("color: #6c757d; font-size: 9px; font-weight: bold; padding: 0px; background-color: transparent; border: none; min-width: 10px; max-width: 10px;")
                self.sync_status_label.setToolTip("ë¡œì»¬ ëª¨ë“œ")
            return
            
        try:
            self.firebase_sync = FirebaseSync(self)
            QTimer.singleShot(1000, self.firebase_sync.start_sync)
        except:
            if hasattr(self, 'sync_status_label'):
                self.sync_status_label.setText("??)
                self.sync_status_label.setStyleSheet("color: #95a5a6; font-size: 9px; font-weight: bold; padding: 0px; background-color: transparent; border: none; min-width: 10px; max-width: 10px;")
                self.sync_status_label.setToolTip("?¤í”„?¼ì¸ ëª¨ë“œ")

    def on_firebase_data_changed(self, data):
        if self.is_updating:
            return
            
        try:
            self.is_updating = True
            
            current_project = self.current_project
            current_row = self.table.currentRow() if hasattr(self, 'table') and self.table.currentRow() >= 0 else -1
            current_memo_row = self.current_memo_row
            
            current_item_data = None
            if current_row >= 0 and current_project:
                old_data = self.get_current_data()
                if current_row < len(old_data):
                    current_item_data = old_data[current_row]
            
            if self.current_memo_row >= 0:
                self.save_current_memo()
            
            self.projects_data = data.copy()
            self.update_project_combo()
            
            if current_project and current_project in self.projects_data:
                self.project_combo.setCurrentText(current_project)
                self.current_project = current_project
                self.update_table()
                self.update_summary()
                
                if current_row >= 0 and current_row < self.table.rowCount():
                    self.table.selectRow(current_row)
                
                if current_memo_row >= 0 and current_memo_row < self.table.rowCount():
                    self.current_memo_row = current_memo_row
                    self.show_memo_dialog(current_memo_row)
            else:
                self.current_project = None
                self.current_memo_row = -1
                self.table.setRowCount(0)
                self.update_summary()
                self.memo_text_edit.clear()
            
            if hasattr(self, 'sync_status_label'):
                self.sync_status_label.setText("??)
                self.sync_status_label.setStyleSheet("color: #27ae60; font-size: 9px; font-weight: bold; padding: 0px; background-color: transparent; border: none; min-width: 10px; max-width: 10px;")
                self.sync_status_label.setToolTip("?™ê¸°?”ë¨")
            
        finally:
            self.is_updating = False

    def init_ui(self):
        self.setWindowTitle(f"?•ì‚° ?„ë¡œê·¸ë¨ Â© HV LAB (v{CURRENT_VERSION})")
        self.setWindowIcon(QIcon(resource_path('HV.ico')))
        
        screen = QApplication.primaryScreen().geometry()
        x = max((screen.width() - WINDOW_WIDTH) // 2, 50)
        y = max((screen.height() - WINDOW_HEIGHT) // 2, 50)
        self.setGeometry(x, y, WINDOW_WIDTH, WINDOW_HEIGHT)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(20, 20, 20, 20)  # ?í•˜ì¢Œìš° ëª¨ë‘ 20pxë¡??µì¼
        
        self.apply_styles()
        
        main_content_layout = QHBoxLayout()
        main_content_layout.setSpacing(5)  # 10?ì„œ 5ë¡?ì¤„ì—¬????ê· ì¼?˜ê²Œ
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        
        left_panel = self.create_left_panel()
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        main_content_layout.addWidget(left_panel)
        
        self.table_section = self.create_table_section()
        self.table_section.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        main_content_layout.addWidget(self.table_section)
        
        self.memo_section = self.create_memo_section()
        self.memo_section.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Preferred)
        main_content_layout.addWidget(self.memo_section)
        self.memo_section.show()
        self.memo_visible = True
        
        layout.addLayout(main_content_layout)
        
        self.statusBar().show()
        self.statusBar().showMessage(f"ë²„ì „ {CURRENT_VERSION}")
        self.setup_shortcuts()
        self.update_ui_state()

    def create_left_panel(self):
        """?¼ìª½ ?¨ë„ ?ì„± - ?„ë¡œ?íŠ¸, ?¬ìš©?? ?…ë ¥, ?”ì•½ ?¹ì…˜???¬í•¨"""
        left_panel = QWidget()
        left_panel.setFixedWidth(LEFT_PANEL_WIDTH)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 10, 10)  # ?˜ë‹¨ ?¬ë°± 10?¼ë¡œ ë§ì¶¤
        
        # ?„ë¡œ?íŠ¸ ?¹ì…˜
        project_section = self.create_project_section()
        left_layout.addWidget(project_section)
        
        # ?™ê¸°???íƒœ ?œì‹œ ?œê±° - ?Œì´ë¸??¹ì…˜?¼ë¡œ ?´ë™
        left_layout.addSpacing(10)
        
        # ?¬ìš©??? íƒ ?¹ì…˜
        user_section = self.create_user_section()
        left_layout.addWidget(user_section)
        
        # ?…ë ¥ ?¹ì…˜ - ê·¸ë£¹ë°•ìŠ¤ ?†ì´
        input_section = self.create_input_section()
        left_layout.addWidget(input_section)
        
        # ?¤íŠ¸?ˆì¹˜ë¥?ì¶”ê??˜ì—¬ ?”ì•½ ?¹ì…˜???„ë˜ë¡?ë°€ê¸?        left_layout.addStretch()
        
        # ?”ì•½ ?¹ì…˜ - ê·¸ë£¹ë°•ìŠ¤ ?†ì´
        summary_section = self.create_summary_section()
        left_layout.addWidget(summary_section)
        
        left_panel.setLayout(left_layout)
        return left_panel

    def setup_shortcuts(self):
        shortcuts = [
            (Qt.Key_Delete, self.delete_selected_item),
            ("Ctrl+Z", self.undo_last_action),
            (Qt.Key_Escape, lambda: None)
        ]
        
        for key, func in shortcuts:
            QShortcut(QKeySequence(key), self, func)

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #dee2e6;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 10px 0 10px;
                color: #495057;
            }
            QPushButton.secondary {
                background-color: white;
                color: #495057;
                border: 2px solid #ced4da;
            }
            QPushButton.secondary:hover { border-color: #adb5bd; }
            QLineEdit, QSpinBox, QComboBox, QDateEdit {
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                color: #495057;
            }
            QDateEdit::drop-down, QComboBox::drop-down {
                border: none;
                background-color: #7d9471;
                border-radius: 0px 4px 4px 0px;
                width: 40px;
            }
            QDateEdit::down-arrow, QComboBox::down-arrow {
                image: url(data:image/svg+xml;base64,PD94bWwgdmVyc2lvbj0iMS4wIiBlbmNvZGluZz0idXRmLTgiPz4KPHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iNiIgdmlld0JveD0iMCAwIDEwIDYiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CiAgPHBvbHlsaW5lIHBvaW50cz0iMSwxIDUsNSA5LDEiIHN0cm9rZT0id2hpdGUiIHN0cm9rZS13aWR0aD0iMiIgZmlsbD0ibm9uZSIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIi8+Cjwvc3ZnPg==);
                width: 10px;
                height: 6px;
            }
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                color: #495057;
                selection-background-color: rgba(125, 148, 113, 0.3);
                selection-color: #495057;
                outline: none;
                max-height: 600px;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px;
                border: none;
                color: #495057;
                min-height: 20px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(125, 148, 113, 0.2);
                color: #495057;
            }
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item:selected {
                background-color: rgb(220, 238, 210);
                color: black;
            }
            QHeaderView::section {
                background-color: #e9ecef;
                padding: 5px;
                border: none;
                font-weight: bold;
            }
            QLabel { color: #495057; }
            QCalendarWidget { 
                background-color: white; 
                border: 1px solid #dee2e6; 
                border-radius: 8px; 
            }
            QCalendarWidget QToolButton {
                background-color: transparent;
                color: #495057;
                border: none;
                padding: 8px;
                margin: 2px;
                border-radius: 4px;
            }
            QCalendarWidget QToolButton:hover { 
                background-color: rgba(125, 148, 113, 0.1); 
            }
            QCalendarWidget QToolButton:pressed { 
                background-color: rgba(125, 148, 113, 0.2); 
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth,
            QCalendarWidget QToolButton#qt_calendar_nextmonth {
                background-color: #7d9471;
                color: white;
                padding: 5px 10px;
                border-radius: 4px;
            }
            QCalendarWidget QToolButton#qt_calendar_prevmonth:hover,
            QCalendarWidget QToolButton#qt_calendar_nextmonth:hover {
                background-color: #6d8062;
            }
            QCalendarWidget QWidget#qt_calendar_navigationbar {
                background-color: rgba(125, 148, 113, 0.1);
            }
            QCalendarWidget QAbstractItemView:enabled {
                background-color: white;
                color: #495057;
                selection-background-color: rgba(125, 148, 113, 0.3);
                selection-color: #495057;
            }
            QCalendarWidget QAbstractItemView:disabled {
                color: #c0c0c0;
            }
            QCalendarWidget QAbstractItemView:enabled:focus {
                outline: none;
                border: 1px solid #7d9471;
            }
            QCalendarWidget QAbstractItemView:enabled:selected {
                background-color: #7d9471;
                color: white;
            }
            QCalendarWidget QAbstractItemView:enabled:hover {
                background-color: rgba(125, 148, 113, 0.1);
            }
        """)

    def create_project_section(self):
        project_widget = QWidget()
        project_layout = QHBoxLayout()
        project_layout.setContentsMargins(0, 0, 0, 5)
        project_layout.setSpacing(0)
        
        self.project_combo = ProjectComboBox()
        self.project_combo.setMinimumHeight(95)  # 100?ì„œ 95ë¡?ë³€ê²?        self.project_combo.setMaximumHeight(95)  # ìµœë? ?’ì´??95ë¡??¤ì •
        self.project_combo.setStyleSheet("""
            QComboBox { 
                font-size: 14px; 
                font-weight: bold; 
                padding: 8px;
                border: 1px solid #ced4da;
                border-radius: 4px;
                background-color: white;
                color: #495057;
            }
            QComboBox:hover { border-color: #7d9471; cursor: pointer; }
            QComboBox::drop-down { width: 0px; border: none; }
            QComboBox::down-arrow { image: none; }
            QComboBox QAbstractItemView {
                font-size: 14px;
                font-weight: bold;
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                color: #495057;
                selection-background-color: rgba(125, 148, 113, 0.3);
                selection-color: #495057;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 8px;
                min-height: 85px;
            }
        """)
        
        list_view = QListView()
        self.project_combo.setView(list_view)
        
        delegate = ProjectComboDelegate(self.project_combo)
        self.project_combo.setItemDelegate(delegate)
        
        self.project_combo.activated.connect(self.on_project_combo_activated)
        project_layout.addWidget(self.project_combo)
        
        project_widget.setLayout(project_layout)
        return project_widget
    
    def on_project_combo_activated(self, index):
        """?„ë¡œ?íŠ¸ ì½¤ë³´ë°•ìŠ¤ ? íƒ ??ì²˜ë¦¬"""
        project_name = self.project_combo.currentText()
        self.on_project_changed(project_name)
    


    def create_user_section(self):
        user_widget = QWidget()
        user_layout = QHBoxLayout()
        user_layout.setContentsMargins(0, 0, 0, 10)
        user_layout.setSpacing(5)
        
        self.user_buttons = []
        
        for user in self.users:
            btn = QPushButton(user)
            btn.clicked.connect(lambda checked, u=user: self.select_user(u))
            btn.setCheckable(True)
            btn.setMinimumWidth(55)
            btn.setMaximumWidth(65)
            btn.setMinimumHeight(40)
            btn.setStyleSheet(USER_BUTTON_STYLE)
            self.user_buttons.append(btn)
            user_layout.addWidget(btn)
        
        user_widget.setLayout(user_layout)
        return user_widget

    def create_input_section(self):
        input_widget = QWidget()
        input_layout = QGridLayout()
        input_layout.setSpacing(8)
        input_layout.setContentsMargins(10, 10, 10, 10)
        
        # ? ì§œ
        input_layout.addWidget(QLabel("? ì§œ:"), 0, 0)
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setMinimumHeight(35)
        self.date_edit.setLocale(QLocale(QLocale.Korean))
        self.date_edit.setDisplayFormat("yyyy-MM-dd (ddd)")
        self.selected_date = QDate.currentDate()
        self.date_edit.dateChanged.connect(self.on_date_changed)
        input_layout.addWidget(self.date_edit, 0, 1)
        
        # ê³µì •
        input_layout.addWidget(QLabel("ê³µì •:"), 1, 0)
        self.process_combo = QComboBox()
        self.process_combo.addItem("")
        self.process_combo.addItems(self.processes)
        self.process_combo.addItem("ê³µì • ê´€ë¦?)
        self.process_combo.setMinimumHeight(35)
        self.process_combo.setEditable(True)
        self.process_combo.setMaxVisibleItems(20)  # ëª¨ë“  ??ª©??ë³´ì´?„ë¡ ì¦ê?
        
        self.process_combo.setStyleSheet("""
            QComboBox QAbstractItemView {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 4px;
                color: #495057;
                selection-background-color: rgba(125, 148, 113, 0.3);
                selection-color: #495057;
                outline: none;
            }
            QComboBox QAbstractItemView::item {
                padding: 3px 8px;
                border: none;
                color: #495057;
                min-height: 16px;
            }
            QComboBox QAbstractItemView::item:hover {
                background-color: rgba(125, 148, 113, 0.2);
                color: #495057;
            }
            QComboBox QAbstractScrollBar:vertical {
                width: 0px;
            }
        """)
        
        process_delegate = CustomDelegate(self.process_combo)
        self.process_combo.setItemDelegate(process_delegate)
        
        self.process_combo.activated.connect(self.on_process_combo_activated)
        input_layout.addWidget(self.process_combo, 1, 1)
        
        # ??ª©ëª?        input_layout.addWidget(QLabel("??ª©ëª?"), 2, 0)
        self.item_name = QLineEdit()
        self.item_name.setMinimumHeight(35)
        self.item_name.returnPressed.connect(self.add_item)
        input_layout.addWidget(self.item_name, 2, 1)
        
        # ?ì¬ë¹?        input_layout.addWidget(QLabel("?ì¬ë¹?"), 3, 0)
        self.material_amount = self.create_amount_spinbox()
        input_layout.addWidget(self.material_amount, 3, 1)
        
        # ?¸ê±´ë¹?        input_layout.addWidget(QLabel("?¸ê±´ë¹?"), 4, 0)
        self.labor_amount = self.create_amount_spinbox()
        input_layout.addWidget(self.labor_amount, 4, 1)
        
        # ë¶€ê°€??        vat_container = QWidget()
        vat_layout = QHBoxLayout()
        vat_layout.setContentsMargins(0, 0, 0, 15)
        vat_layout.addStretch()
        self.vat_included = QCheckBox("ë¶€ê°€???¬í•¨")
        vat_layout.addWidget(self.vat_included)
        vat_container.setLayout(vat_layout)
        input_layout.addWidget(vat_container, 5, 0, 1, 2)
        
        # ì¶”ê? ë²„íŠ¼
        self.add_item_btn = QPushButton("??ª© ì¶”ê?")
        self.add_item_btn.setStyleSheet(BUTTON_STYLE)
        self.add_item_btn.clicked.connect(self.add_item)
        self.add_item_btn.setMinimumHeight(40)
        input_layout.addWidget(self.add_item_btn, 6, 0, 1, 2)
        
        self.add_item_btn.setMouseTracking(True)
        self.add_item_btn.enterEvent = self.on_add_button_hover
        
        # ?¬ìš©???ˆë‚´
        self.user_guide_label = QLabel("???‘ì„±???´ë¦„??? íƒ?˜ì„¸??)
        self.user_guide_label.setStyleSheet("""
            QLabel {
                color: #B57575;
                font-size: 18px;
                padding-top: 10px;
                padding-bottom: 5px;
            }
        """)
        self.user_guide_label.setAlignment(Qt.AlignCenter)
        input_layout.addWidget(self.user_guide_label, 7, 0, 1, 2)
        
        input_widget.setLayout(input_layout)
        return input_widget
    
    def on_process_combo_activated(self, index):
        process_name = self.process_combo.currentText()
        if process_name == "ê³µì • ê´€ë¦?:
            self.show_process_management_dialog()
            
            if hasattr(self, '_last_process_selection'):
                self.process_combo.setCurrentText(self._last_process_selection)
            else:
                self.process_combo.setCurrentText("")
        else:
            self._last_process_selection = process_name
    
    def show_process_management_dialog(self):
        try:
            dialog = ProcessManagementDialog(self.processes, self)
            dialog.setWindowModality(Qt.ApplicationModal)
            
            if self.isVisible():
                parent_rect = self.geometry()
                dialog_rect = dialog.geometry()
                x = parent_rect.center().x() - dialog_rect.width() // 2
                y = parent_rect.center().y() - dialog_rect.height() // 2
                dialog.move(x, y)
            
            if dialog.exec_() == QDialog.Accepted:
                if dialog.selected_action and dialog.result_processes:
                    self.processes = dialog.result_processes
                    self.update_process_combo()
                    
                    process_delegate = ProcessDelegate(self.processes, self.table)
                    self.table.setItemDelegateForColumn(2, process_delegate)
                    
                    self.save_all_data()
                    
                    action_messages = {
                        'add': "??ê³µì •??ì¶”ê??˜ì—ˆ?µë‹ˆ??",
                        'reorder': "ê³µì • ?œì„œê°€ ë³€ê²½ë˜?ˆìŠµ?ˆë‹¤.",
                        'delete': "ê³µì •???? œ?˜ì—ˆ?µë‹ˆ??"
                    }
                    if dialog.selected_action in action_messages:
                        QMessageBox.information(self, "?±ê³µ", action_messages[dialog.selected_action])
                        
        except Exception as e:
            QMessageBox.critical(self, "?¤ë¥˜", f"ê³µì • ê´€ë¦??¤ì´?¼ë¡œê·¸ë? ?????†ìŠµ?ˆë‹¤:\n{str(e)}")
    
    def update_process_combo(self):
        current_selection = self.process_combo.currentText()
        
        self.process_combo.clear()
        self.process_combo.addItem("")
        self.process_combo.addItems(self.processes)
        self.process_combo.addItem("ê³µì • ê´€ë¦?)
        
        if current_selection and current_selection != "ê³µì • ê´€ë¦?:
            if current_selection in self.processes:
                self.process_combo.setCurrentText(current_selection)
            else:
                self.process_combo.setCurrentText("")

    def create_amount_spinbox(self):
        spinbox = QSpinBox()
        spinbox.setRange(0, 99999999)
        spinbox.setSuffix(" ??)
        spinbox.setMinimumHeight(35)
        spinbox.setButtonSymbols(QSpinBox.NoButtons)
        spinbox.setKeyboardTracking(False)
        spinbox.setAlignment(Qt.AlignRight)
        spinbox.focusInEvent = lambda event: self.on_spinbox_focus(spinbox, event)
        return spinbox

    def create_summary_section(self):
        summary_widget = QWidget()
        summary_layout = QGridLayout()
        summary_layout.setSpacing(10)  # 12?ì„œ 10?¼ë¡œ ì¤„ì—¬??80% ê°„ê²©
        summary_layout.setContentsMargins(10, -5, 10, 0)  # ?ë‹¨ ?¬ë°±??-5ë¡??¤ì •?˜ì—¬ 5px ?„ë¡œ ?´ë™
        
        labels = [
            ("?ì¬ë¹?ì´í•©:", 0, 0),
            ("?¸ê±´ë¹?ì´í•©:", 1, 0),
            ("ë¶€ê°€??ì´í•©:", 2, 0),
            ("ì´??©ê³„:", 3, 0)
        ]
        
        for text, row, col in labels:
            label = QLabel(text)
            if "ì´??©ê³„" in text:
                label.setStyleSheet("font-size: 24px; font-weight: bold;")
            summary_layout.addWidget(label, row, col)
        
        self.material_total = QLabel("0??)
        self.labor_total = QLabel("0??)
        self.vat_total = QLabel("0??)
        self.grand_total = QLabel("0??)
        
        totals = [self.material_total, self.labor_total, self.vat_total, self.grand_total]
        
        for i, total_label in enumerate(totals):
            total_label.setAlignment(Qt.AlignRight)
            if i == 3:  # grand_total
                total_label.setStyleSheet("font-size: 24px; font-weight: bold; color: black;")
            summary_layout.addWidget(total_label, i, 1)
        
        summary_layout.setColumnStretch(0, 0)
        summary_layout.setColumnStretch(1, 1)
        
        summary_widget.setLayout(summary_layout)
        return summary_widget

    def create_memo_section(self):
        memo_widget = QWidget()
        memo_widget.setFixedWidth(MEMO_WIDTH)
        memo_layout = QVBoxLayout()
        memo_layout.setContentsMargins(10, 0, 0, 5)  # ?˜ë‹¨ ?¬ë°±??10?ì„œ 5ë¡?ì¤„ì„
        
        memo_container = QWidget()
        memo_container.setStyleSheet("""
            QWidget {
                border: 2px solid #dee2e6;
                border-radius: 8px;
                background-color: white;
            }
        """)
        
        container_layout = QVBoxLayout()
        container_layout.setContentsMargins(20, 20, 20, 15)  # ?˜ë‹¨ ?¬ë°±??20?ì„œ 15ë¡?ì¤„ì„
        
        self.memo_text_edit = ImageTextEdit()
        self.memo_text_edit.setAcceptRichText(True)
        self.memo_text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.memo_text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.memo_text_edit.setWordWrapMode(QTextOption.WordWrap)
        self.memo_text_edit.setStyleSheet("""
            QTextEdit {
                border: none;
                padding: 8px 8px 5px 8px;  /* ?˜ë‹¨ ?¨ë”©??8?ì„œ 5ë¡?ì¤„ì„ */
                background-color: white;
                selection-background-color: #3399ff;
                selection-color: white;
            }
            QTextEdit::selection { background-color: #3399ff; }
        """)
        
        font = QFont("ë§‘ì? ê³ ë”•", 14)
        self.memo_text_edit.setFont(font)
        self.memo_text_edit.textChanged.connect(self.on_memo_text_changed)
        self.memo_text_edit.setPlaceholderText("")
        
        doc = self.memo_text_edit.document()
        doc.setDefaultStyleSheet("""
            p { line-height: 1.1; margin: 0px 0; padding: 0px; } 
            img { margin: 0px 0px 4px 0px; }
        """)
        
        container_layout.addWidget(self.memo_text_edit)
        memo_container.setLayout(container_layout)
        
        memo_layout.addWidget(memo_container)
        memo_widget.setLayout(memo_layout)
        return memo_widget

    def toggle_memo_section(self):
        if self.memo_visible:
            if self.current_memo_row >= 0:
                self.save_current_memo()
            
            self.memo_section.hide()
            self.memo_visible = False
            self.memo_toggle_btn.setText("ë©”ëª¨???´ê¸°")
            
            current_pos = self.pos()
            self.setFixedSize(WINDOW_WIDTH_NO_MEMO, WINDOW_HEIGHT)
            self.move(current_pos)
        else:
            self.memo_section.show()
            self.memo_visible = True
            self.memo_toggle_btn.setText("ë©”ëª¨???«ê¸°")
            current_pos = self.pos()
            self.setFixedSize(WINDOW_WIDTH, WINDOW_HEIGHT)
            self.move(current_pos)
        
        self.update_table()

    def on_table_cell_clicked(self, row, column):
        if not self.table.memo_button_clicked:
            if self.memo_visible:
                if self.current_memo_row >= 0 and self.current_memo_row != row:
                    self.save_current_memo()
                
                self.current_memo_row = row
                data = self.get_current_data()
                if row < len(data):
                    item_info = data[row]
                    
                    current_memo = item_info.get('memo', '')
                    if current_memo:
                        try:
                            memo_data = json.loads(current_memo)
                            if isinstance(memo_data, dict) and 'html' in memo_data:
                                if 'images' in memo_data and memo_data['images']:
                                    document = self.memo_text_edit.document()
                                    for src, base64_data in memo_data['images'].items():
                                        byte_array = QByteArray.fromBase64(base64_data.encode('utf-8'))
                                        image = QImage()
                                        image.loadFromData(byte_array)
                                        if not image.isNull():
                                            url = QUrl(src)
                                            document.addResource(QTextDocument.ImageResource, url, image)
                                
                                self.memo_text_edit.setHtml(memo_data['html'])
                            else:
                                self.memo_text_edit.setHtml(current_memo)
                        except:
                            self.memo_text_edit.setHtml(current_memo)
                    else:
                        self.memo_text_edit.clear()
        
        self.table.memo_button_clicked = False

    def on_memo_text_changed(self):
        if self.current_memo_row >= 0:
            if hasattr(self, 'memo_save_timer'):
                self.memo_save_timer.stop()
            else:
                self.memo_save_timer = QTimer()
                self.memo_save_timer.timeout.connect(self.save_current_memo)
                self.memo_save_timer.setSingleShot(True)
            
            self.memo_save_timer.start(2000)

    def save_current_memo(self):
        if self.current_memo_row < 0:
            return
        
        data = self.get_current_data()
        if self.current_memo_row >= len(data):
            return
        
        old_item = data[self.current_memo_row].copy()
        
        html_content = self.memo_text_edit.toHtml()
        
        images = {}
        document = self.memo_text_edit.document()
        
        img_pattern = r'<img[^>]+src="([^"]+)"[^>]*>'
        for match in re.finditer(img_pattern, html_content):
            src = match.group(1)
            url = QUrl(src)
            
            image = document.resource(QTextDocument.ImageResource, url)
            if image and isinstance(image, QImage):
                if image.width() > 1200 or image.height() > 1200:
                    if image.width() > image.height():
                        scaled_image = image.scaledToWidth(1200, Qt.SmoothTransformation)
                    else:
                        scaled_image = image.scaledToHeight(1200, Qt.SmoothTransformation)
                else:
                    scaled_image = image
                
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.WriteOnly)
                scaled_image.save(buffer, "PNG")
                base64_data = byte_array.toBase64().data().decode('utf-8')
                images[src] = base64_data
        
        memo_data = {'html': html_content, 'images': images}
        new_memo = json.dumps(memo_data, ensure_ascii=False)
        
        if data[self.current_memo_row].get('memo', '') != new_memo:
            data[self.current_memo_row]['memo'] = new_memo
            
            self.save_undo_state('edit', {
                'old_item': old_item,
                'new_item': data[self.current_memo_row].copy()
            })
            
            if hasattr(self, 'table') and self.table:
                index = self.table.model().index(self.current_memo_row, 3)
                self.table.update(index)
            
            self.save_all_data()

    def create_table_section(self):
        table_widget = QWidget()
        table_widget.setFixedWidth(TABLE_WIDTH)
        table_layout = QVBoxLayout()
        table_layout.setContentsMargins(10, 0, 10, 10)  # ?˜ë‹¨ ?¬ë°± 10?¼ë¡œ ë§ì¶¤
        
        self.table = CustomTableWidget()
        self.table.setMinimumHeight(610)  # ìµœì†Œ ?’ì´ë¥?600?ì„œ 610?¼ë¡œ ?¤ì •
        self.table.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)  # ?¸ë¡œë¡??•ì¥ ê°€??        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["?‘ì„±??, "? ì§œ", "ê³µì •", "??ª©ëª?, "?ì¬ë¹?, "?¸ê±´ë¹?, "ë¶€ê°€??, "ì´ì•¡"])
        
        self.setup_table_columns()
        
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setSortingEnabled(False)
        self.table.horizontalHeader().sectionClicked.connect(self.sort_table)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignCenter)
        
        self.table.setEditTriggers(QAbstractItemView.DoubleClicked | 
                                   QAbstractItemView.EditKeyPressed | 
                                   QAbstractItemView.AnyKeyPressed)
        
        self.table.itemChanged.connect(self.on_table_item_changed)
        self.table.cellClicked.connect(self.on_table_cell_clicked)
        
        process_delegate = ProcessDelegate(self.processes, self.table)
        self.table.setItemDelegateForColumn(2, process_delegate)
        
        self.item_name_delegate = ItemNameDelegate(self.table)
        self.item_name_delegate.memo_clicked.connect(self.show_memo_dialog)
        self.item_name_delegate.memo_delete_requested.connect(self.delete_memo)
        self.table.setItemDelegateForColumn(3, self.item_name_delegate)
        self.item_name_delegate.main_window = self
        self.table.item_name_delegate = self.item_name_delegate
        
        table_layout.addWidget(self.table)
        table_layout.addSpacing(10)  # 20?ì„œ 10?¼ë¡œ ì¤„ì„
        
        table_buttons_layout = QHBoxLayout()
        
        buttons = [
            ("?? œ (Del)", self.delete_selected_item, BUTTON_STYLE),
            ("?¤ë¡œ (Ctrl+Z)", self.undo_last_action, BUTTON_STYLE),
            ("?´ë³´?´ê¸°", self.export_to_excel, BUTTON_STYLE),
            ("ê³µì •ë³?ê¸ˆì•¡", self.show_process_summary, BUTTON_STYLE),
            ("ë°±ì—…", self.save_data_as, BUTTON_STYLE.replace("#7d9471", "#5d4e37").replace("#6d8062", "#4a3c2a").replace("#5d6f54", "#3d3023")),
            ("?…ë°?´íŠ¸ ?•ì¸!", self.check_for_updates, BUTTON_STYLE)
        ]
        
        self.table_buttons = {}
        for text, func, style in buttons:
            btn = QPushButton(text)
            btn.setStyleSheet(style)
            btn.clicked.connect(func)
            if "ë°±ì—…" in text:
                btn.setToolTip("?„ì¬ ?°ì´?°ë? ë³„ë„ ?Œì¼ë¡?ë°±ì—…?©ë‹ˆ??)
            elif "?…ë°?´íŠ¸" in text:
                btn.setToolTip("?ˆë¡œ??ë²„ì „???ˆëŠ”ì§€ ?•ì¸?©ë‹ˆ??)
            table_buttons_layout.addWidget(btn)
            
            key = text.split()[0]
            if key == "?? œ":
                self.delete_item_btn = btn
            elif key == "?¤ë¡œ":
                self.undo_btn = btn
            elif key == "?´ë³´?´ê¸°":
                self.export_btn = btn
            elif key == "ê³µì •ë³?:
                self.process_summary_btn = btn
            elif key == "ë°±ì—…":
                self.save_btn = btn
            elif key == "?…ë°?´íŠ¸":  # "?…ë°?´íŠ¸ ?•ì¸!" ë²„íŠ¼
                self.update_btn = btn
                
                # ?…ë°?´íŠ¸ ë²„íŠ¼ ë°”ë¡œ ?¤ìŒ???™ê¸°???íƒœ ì¶”ê?
                table_buttons_layout.addSpacing(5)  # ê°„ê²© ì¡°ì •
                self.sync_status_label = QLabel("??)
                self.sync_status_label.setAlignment(Qt.AlignCenter)
                self.sync_status_label.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        font-size: 9px;
                        font-weight: bold;
                        padding: 0px;
                        background-color: transparent;
                        border: none;
                        min-width: 10px;
                        max-width: 10px;
                    }
                """)
                self.sync_status_label.setFixedSize(10, 10)  # ê³ ì • ?¬ê¸°ë¥?ë°˜ìœ¼ë¡?                self.sync_status_label.setToolTip("?¤ì‹œê°??™ê¸°??ì¤?)
                table_buttons_layout.addWidget(self.sync_status_label)
        
        table_buttons_layout.addStretch()
        
        self.memo_toggle_btn = QPushButton("ë©”ëª¨???«ê¸°")
        self.memo_toggle_btn.setStyleSheet(BUTTON_STYLE)
        self.memo_toggle_btn.clicked.connect(self.toggle_memo_section)
        table_buttons_layout.addWidget(self.memo_toggle_btn)
        
        table_layout.addLayout(table_buttons_layout)
        table_widget.setLayout(table_layout)
        return table_widget

    def show_process_summary(self):
        if not self.current_project:
            QMessageBox.warning(self, "ê²½ê³ ", "?„ë¡œ?íŠ¸ë¥?? íƒ?´ì£¼?¸ìš”.")
            return
        
        data = self.get_current_data()
        if not data:
            QMessageBox.warning(self, "ê²½ê³ ", "?œì‹œ???°ì´?°ê? ?†ìŠµ?ˆë‹¤.")
            return
        
        dialog = ProcessSummaryDialog(data, self.processes, self)
        dialog.exec_()

    def setup_table_columns(self):
        header = self.table.horizontalHeader()
        header.setStretchLastSection(False)
        
        column_widths = [100, 165, 100, None, 150, 150, 150, 150]
        for i, width in enumerate(column_widths):
            if width:
                self.table.setColumnWidth(i, width)
        
        header.setSectionResizeMode(3, header.Stretch)

    def get_memo_for_row(self, row):
        data = self.get_current_data()
        if 0 <= row < len(data):
            return data[row].get('memo', '')
        return ''

    def delete_memo(self, row):
        data = self.get_current_data()
        if not data or row >= len(data):
            return
        
        if self.memo_visible and self.current_memo_row == row:
            self.memo_text_edit.clear()
            self.current_memo_row = -1
        
        old_item = data[row].copy()
        data[row]['memo'] = ''
        
        self.save_undo_state('edit', {
            'old_item': old_item,
            'new_item': data[row].copy()
        })
        
        self.save_all_data()
        
        if hasattr(self, 'table') and self.table:
            index = self.table.model().index(row, 3)
            self.table.update(index)

    def show_memo_dialog(self, row):
        data = self.get_current_data()
        if not data or row >= len(data):
            return
        
        if self.current_memo_row >= 0 and self.current_memo_row != row:
            self.save_current_memo()
        
        self.current_memo_row = row
        item_info = data[row]
        
        current_memo = item_info.get('memo', '')
        if current_memo:
            try:
                memo_data = json.loads(current_memo)
                if isinstance(memo_data, dict) and 'html' in memo_data:
                    if 'images' in memo_data and memo_data['images']:
                        document = self.memo_text_edit.document()
                        for src, base64_data in memo_data['images'].items():
                            byte_array = QByteArray.fromBase64(base64_data.encode('utf-8'))
                            image = QImage()
                            image.loadFromData(byte_array)
                            if not image.isNull():
                                url = QUrl(src)
                                document.addResource(QTextDocument.ImageResource, url, image)
                    
                    self.memo_text_edit.setHtml(memo_data['html'])
                else:
                    self.memo_text_edit.setHtml(current_memo)
            except:
                self.memo_text_edit.setHtml(current_memo)
        else:
            self.memo_text_edit.clear()
    
    def on_spinbox_focus(self, spinbox, event):
        QSpinBox.focusInEvent(spinbox, event)
        QTimer.singleShot(0, lambda: self.select_number_part(spinbox))

    def select_number_part(self, spinbox):
        text = spinbox.lineEdit().text()
        if " ?? in text:
            spinbox.lineEdit().setSelection(0, text.find(" ??))
        else:
            spinbox.lineEdit().selectAll()

    def on_add_button_hover(self, event):
        if not self.add_item_btn.isEnabled() and not self.current_user:
            QToolTip.showText(QCursor.pos(), "?‘ì„±?ë? ë¨¼ì? ? íƒ?´ì£¼?¸ìš”")
    
    def select_user(self, user):
        if self.current_user == user:
            self.current_user = None
            for btn in self.user_buttons:
                btn.setChecked(False)
            if hasattr(self, 'user_guide_label'):
                self.user_guide_label.setVisible(True)
        else:
            self.current_user = user
            for btn in self.user_buttons:
                btn.setChecked(btn.text() == user)
            if hasattr(self, 'user_guide_label'):
                self.user_guide_label.setVisible(False)
        
        self.update_ui_state()

    def on_date_changed(self, date):
        self.selected_date = date

    def update_ui_state(self):
        has_project = self.current_project is not None
        has_user = self.current_user is not None
        can_add_item = has_project and has_user
        has_undo = len(self.undo_stack) > 0
        
        widgets_state = [
            (self.process_combo, True),
            (self.item_name, True),
            (self.material_amount, True),
            (self.labor_amount, True),
            (self.vat_included, True),
            (self.add_item_btn, can_add_item),
            (self.delete_item_btn, has_project),
            (self.undo_btn, has_undo),
            (self.export_btn, has_project),
            (self.process_summary_btn, has_project),
            (self.save_btn, True),
            (self.memo_toggle_btn, True)
        ]
        
        for widget, enabled in widgets_state:
            widget.setEnabled(enabled)

    def save_undo_state(self, action_type, data):
        undo_data = {
            'project': self.current_project,
            'action': action_type,
            'data': data,
            'timestamp': datetime.now()
        }
        
        self.undo_stack.append(undo_data)
        
        if len(self.undo_stack) > self.max_undo_stack:
            self.undo_stack.pop(0)
        
        self.update_ui_state()

    def undo_last_action(self):
        if not self.undo_stack:
            return
        
        undo_data = self.undo_stack.pop()
        project = undo_data['project']
        action = undo_data['action']
        data = undo_data['data']
        
        if action == 'add':
            if project in self.projects_data and data in self.projects_data[project]:
                self.projects_data[project].remove(data)
        
        elif action == 'delete':
            if project in self.projects_data:
                for item_data in data:
                    index = item_data['index']
                    item = item_data['item']
                    self.projects_data[project].insert(index, item)
        
        elif action == 'edit':
            if project in self.projects_data:
                for i, item in enumerate(self.projects_data[project]):
                    if item == data['new_item']:
                        self.projects_data[project][i] = data['old_item']
                        break
        
        if project == self.current_project:
            self.update_table()
            self.update_summary()
        
        self.save_all_data()
        self.update_ui_state()

    def add_item(self):
        if not self.validate_item_input():
            return
        
        material = self.material_amount.value()
        labor = self.labor_amount.value()
        
        if self.vat_included.isChecked():
            total_input = material + labor
            net_amount = round(total_input / 1.1)
            vat = total_input - net_amount
            total = total_input
            
            if material > 0 and labor > 0:
                material_ratio = material / total_input
                material_net = round(net_amount * material_ratio)
                labor_net = net_amount - material_net
            else:
                material_net = net_amount if material > 0 else 0
                labor_net = net_amount if labor > 0 else 0
        else:
            material_net = material
            labor_net = labor
            vat = 0
            total = material + labor
        
        item = {
            'user': self.current_user,
            'date': self.selected_date.toString('yyyy-MM-dd'),
            'process': self.process_combo.currentText().strip() if self.process_combo.currentText().strip() != "ê³µì • ê´€ë¦? else "",
            'name': self.item_name.text().strip() if self.item_name.text().strip() else "-",
            'material_amount': material_net,
            'labor_amount': labor_net,
            'vat_included': self.vat_included.isChecked(),
            'vat_amount': vat,
            'total_amount': total,
            'memo': '',
            'id': str(uuid.uuid4()),
            'created_at': datetime.now().isoformat()
        }
        
        self.projects_data[self.current_project].append(item)
        
        self.save_undo_state('add', item)
        self.save_all_data()
        
        self.update_table()
        self.update_summary()
        self.reset_input_fields()
        
        if self.memo_visible:
            data = self.get_current_data()
            for i, data_item in enumerate(data):
                if data_item is item:
                    self.show_memo_dialog(i)
                    break

    def validate_item_input(self):
        if not self.current_project:
            QMessageBox.warning(self, "ê²½ê³ ", "ë¨¼ì? ?„ë¡œ?íŠ¸ë¥?? íƒ?˜ê±°??ì¶”ê??´ì£¼?¸ìš”.")
            return False
        
        if not self.current_user:
            QMessageBox.warning(self, "ê²½ê³ ", "ë¨¼ì? ?‘ì„±?ë? ? íƒ?´ì£¼?¸ìš”.")
            if hasattr(self, 'user_guide_label') and self.user_guide_label.isVisible():
                original_style = self.user_guide_label.styleSheet()
                self.user_guide_label.setStyleSheet("""
                    QLabel {
                        color: #FF0000;
                        font-size: 18px;
                        padding-top: 5px;
                        padding-bottom: 10px;
                        font-weight: bold;
                    }
                """)
                QTimer.singleShot(500, lambda: self.user_guide_label.setStyleSheet(original_style))
            return False
        
        return True

    def reset_input_fields(self):
        self.item_name.clear()
        self.material_amount.setValue(0)
        self.labor_amount.setValue(0)
        self.vat_included.setChecked(False)
        self.item_name.setFocus()

    def update_table(self):
        selected_items = []
        if hasattr(self, 'table'):
            for item in self.table.selectedItems():
                row = item.row()
                data = self.get_current_data()
                if row < len(data):
                    selected_items.append(data[row])
        
        self.table.itemChanged.disconnect()
        
        data = self.get_current_data()
        
        if self.sort_column >= 0 and data:
            reverse = (self.sort_order == Qt.DescendingOrder)
            data.sort(key=lambda item: self.get_sort_key(item, self.sort_column), reverse=reverse)
        
        # ìµœì ?? ???˜ê? ê°™ìœ¼ë©??€ë§??…ë°?´íŠ¸
        current_row_count = self.table.rowCount()
        new_row_count = len(data)
        
        if current_row_count != new_row_count:
            self.table.setRowCount(new_row_count)
        
        weekdays = ['??, '??, '??, 'ëª?, 'ê¸?, '??, '??]
        
        for i, item in enumerate(data):
            cells = [
                (item.get('user', ''), Qt.AlignCenter, Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable),
                (self.format_date_with_weekday(item.get('date', ''), weekdays), Qt.AlignCenter, Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable),
                (item.get('process', ''), Qt.AlignCenter, Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable),
                (" " + item.get('name', '-'), Qt.AlignLeft | Qt.AlignVCenter, Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable),
                (self.format_amount(item.get('material_amount', 0)) + " ", Qt.AlignRight | Qt.AlignVCenter, Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable),
                (self.format_amount(item.get('labor_amount', 0)) + " ", Qt.AlignRight | Qt.AlignVCenter, Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable),
                (self.format_vat(item) + (" " if self.format_vat(item) else ""), Qt.AlignRight | Qt.AlignVCenter, Qt.NoItemFlags | Qt.ItemIsSelectable | Qt.ItemIsEnabled),
                (f"{item.get('total_amount', 0):,}??", Qt.AlignRight | Qt.AlignVCenter, Qt.NoItemFlags | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            ]
            
            for col, (text, alignment, flags) in enumerate(cells):
                # ìµœì ?? ê¸°ì¡´ ?„ì´?œì´ ?ˆê³  ?ìŠ¤?¸ê? ê°™ìœ¼ë©?ê±´ë„ˆ?°ê¸°
                existing_item = self.table.item(i, col)
                if existing_item and existing_item.text() == text:
                    continue
                    
                item_widget = QTableWidgetItem(text)
                item_widget.setTextAlignment(alignment)
                item_widget.setFlags(flags)
                self.table.setItem(i, col, item_widget)
        
        self.table.itemChanged.connect(self.on_table_item_changed)
        
        if selected_items:
            self.table.clearSelection()
            for i, row_data in enumerate(data):
                if row_data in selected_items:
                    self.table.selectRow(i)

    def format_date_with_weekday(self, date_str, weekdays):
        if not date_str:
            return ''
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            weekday = weekdays[date_obj.weekday()]
            return f"{date_str} ({weekday})"
        except:
            return date_str

    def format_amount(self, amount):
        return f"{amount:,}?? if amount > 0 else ""

    def format_vat(self, item):
        if item.get('vat_included', False) and item.get('vat_amount', 0) > 0:
            return f"{item['vat_amount']:,}??
        return ""

    def get_sort_key(self, item, column):
        sort_keys = {
            0: lambda x: x.get('user', ''),
            1: lambda x: self.parse_date(x.get('date', '')),
            2: lambda x: x.get('process', ''),
            3: lambda x: x.get('name', ''),
            4: lambda x: x.get('material_amount', 0),
            5: lambda x: x.get('labor_amount', 0),
            6: lambda x: x.get('vat_amount', 0) if x.get('vat_included', False) else 0,
            7: lambda x: x.get('total_amount', 0)
        }
        return sort_keys.get(column, lambda x: '')(item)

    def parse_date(self, date_str):
        try:
            return datetime.strptime(date_str, '%Y-%m-%d').date() if date_str else datetime.min.date()
        except:
            return datetime.min.date()

    def sort_table(self, column):
        selected_items = []
        selected_rows = set()
        for item in self.table.selectedItems():
            if item.row() not in selected_rows:
                selected_rows.add(item.row())
                data = self.get_current_data()
                if item.row() < len(data):
                    selected_items.append(data[item.row()])
        
        memo_item = None
        if self.current_memo_row >= 0:
            data = self.get_current_data()
            if self.current_memo_row < len(data):
                memo_item = data[self.current_memo_row]
        
        if self.sort_column == column:
            self.sort_order = Qt.DescendingOrder if self.sort_order == Qt.AscendingOrder else Qt.AscendingOrder
        else:
            self.sort_column = column
            self.sort_order = Qt.DescendingOrder if column == 1 else Qt.AscendingOrder
        
        self.update_table()
        
        if memo_item:
            data = self.get_current_data()
            for i, item in enumerate(data):
                if item is memo_item:
                    self.current_memo_row = i
                    break
        else:
            self.current_memo_row = -1
        
        if selected_items:
            data = self.get_current_data()
            self.table.clearSelection()
            for i, item in enumerate(data):
                if item in selected_items:
                    self.table.selectRow(i)

    def update_summary(self):
        data = self.get_current_data()
        
        totals = {
            'material': sum(item.get('material_amount', 0) for item in data),
            'labor': sum(item.get('labor_amount', 0) for item in data),
            'vat': sum(item.get('vat_amount', 0) for item in data),
            'grand': sum(item.get('total_amount', 0) for item in data)
        }
        
        self.material_total.setText(f"{totals['material']:,}??)
        self.labor_total.setText(f"{totals['labor']:,}??)
        self.vat_total.setText(f"{totals['vat']:,}??)
        self.grand_total.setText(f"{totals['grand']:,}??)

    def get_current_data(self):
        return self.projects_data.get(self.current_project, [])

    def delete_selected_item(self):
        selected_rows = set()
        for item in self.table.selectedItems():
            selected_rows.add(item.row())
        
        if not selected_rows:
            return
        
        data = self.get_current_data()
        
        deleted_items = []
        for row in sorted(selected_rows):
            if row < len(data):
                deleted_items.append({
                    'index': row,
                    'item': data[row].copy()
                })
        
        for row in sorted(selected_rows, reverse=True):
            if row < len(data):
                del data[row]
        
        if deleted_items:
            self.save_undo_state('delete', deleted_items)
        
        self.save_all_data()
        self.update_table()
        self.update_summary()

    def rename_project(self, old_name, new_name):
        if old_name in self.projects_data:
            self.projects_data[new_name] = self.projects_data[old_name]
            del self.projects_data[old_name]
            
            if self.current_project == old_name:
                self.current_project = new_name
            
            self.update_project_combo()
            self.project_combo.setCurrentText(new_name)
            self.on_project_changed(new_name)  # ????ì¤?ì¶”ê?
            
            self.save_all_data()
            
            QMessageBox.information(self, "?±ê³µ", f"?„ë¡œ?íŠ¸ ?´ë¦„??'{new_name}'?¼ë¡œ ë³€ê²½ë˜?ˆìŠµ?ˆë‹¤.")

    def show_project_management_dialog(self):
        try:
            dialog = ProjectManagementDialog(self.projects_data, self)
            dialog.setWindowModality(Qt.ApplicationModal)
            
            if self.isVisible():
                parent_rect = self.geometry()
                dialog_rect = dialog.geometry()
                x = parent_rect.center().x() - dialog_rect.width() // 2
                y = parent_rect.center().y() - dialog_rect.height() // 2
                dialog.move(x, y)
            
            if dialog.exec_() == QDialog.Accepted:
                if dialog.selected_action == 'add':
                    self.projects_data[dialog.selected_project] = []
                    self.update_project_combo()
                    self.project_combo.setCurrentText(dialog.selected_project)
                    self.on_project_changed(dialog.selected_project)
                    self.save_all_data()
                    
                elif dialog.selected_action == 'rename':
                    self.rename_project(dialog.selected_project, dialog.new_name)
                    
                elif dialog.selected_action == 'delete':
                    if dialog.selected_project == self.current_project:
                        self.current_project = None
                        
                    del self.projects_data[dialog.selected_project]
                    self.update_project_combo()
                    
                    if self.project_combo.count() > 1:
                        self.project_combo.setCurrentIndex(0)
                    
                    self.save_all_data()
                    
                    self.update_table()
                    self.update_summary()
                    self.update_ui_state()
                    QMessageBox.information(self, "?±ê³µ", f"?„ë¡œ?íŠ¸ '{dialog.selected_project}'ê°€ ?? œ?˜ì—ˆ?µë‹ˆ??")
                    
        except Exception as e:
            QMessageBox.critical(self, "?¤ë¥˜", f"?„ë¡œ?íŠ¸ ê´€ë¦??¤ì´?¼ë¡œê·¸ë? ?????†ìŠµ?ˆë‹¤:\n{str(e)}")

    def on_project_changed(self, project_name):
        if project_name == "?„ë¡œ?íŠ¸ ê´€ë¦?:
            self.show_project_management_dialog()
            
            if self.current_project and self.current_project in self.projects_data:
                self.project_combo.setCurrentText(self.current_project)
            elif len(self.projects_data) > 0:
                first_project = sorted(self.projects_data.keys())[0]
                self.project_combo.setCurrentText(first_project)
            else:
                self.current_project = None
                self.table.setRowCount(0)
                self.update_summary()
                self.update_ui_state()
                if self.memo_visible:
                    self.current_memo_row = -1
                    self.memo_text_edit.clear()
        else:
            self.current_project = project_name if project_name and project_name != "?„ë¡œ?íŠ¸ ê´€ë¦? else None
            if self.current_project:
                self.current_user = None
                for btn in self.user_buttons:
                    btn.setChecked(False)
                
                if hasattr(self, 'user_guide_label'):
                    self.user_guide_label.setVisible(True)
                
                self.current_memo_row = -1
                
                self.sort_column = 1
                self.sort_order = Qt.DescendingOrder
                self.update_table()
                self.update_summary()
                self.update_ui_state()
                
                if self.memo_visible:
                    data = self.get_current_data()
                    if data:
                        self.show_memo_dialog(0)
                    else:
                        self.memo_text_edit.clear()
            else:
                if self.memo_visible:
                    self.current_memo_row = -1
                    self.memo_text_edit.clear()

    def update_project_combo(self):
        current = self.current_project
        
        self.project_combo.clear()
        
        if self.projects_data:
            for project_name in sorted(self.projects_data.keys()):
                self.project_combo.addItem(project_name)
        
        self.project_combo.addItem("?„ë¡œ?íŠ¸ ê´€ë¦?)
        
        if current and current in self.projects_data:
            self.project_combo.setCurrentText(current)
        elif len(self.projects_data) > 0:
            first_project = sorted(self.projects_data.keys())[0]
            self.project_combo.setCurrentText(first_project)

    def export_to_excel(self):
        if not self.current_project:
            QMessageBox.warning(self, "ê²½ê³ ", "?´ë³´???„ë¡œ?íŠ¸ê°€ ?†ìŠµ?ˆë‹¤.")
            return
        
        data = self.get_current_data()
        if not data:
            QMessageBox.warning(self, "ê²½ê³ ", "?´ë³´???°ì´?°ê? ?†ìŠµ?ˆë‹¤.")
            return
        
        try:
            filename, _ = QFileDialog.getSaveFileName(
                self, "Excel ?Œì¼ë¡??€??, 
                f"{self.current_project}_?•ì‚°.xlsx",
                "Excel files (*.xlsx)"
            )
            
            if not filename:
                return
            
            df_data = []
            for item in data:
                df_data.append({
                    '?‘ì„±??: item.get('user', ''),
                    '? ì§œ': item.get('date', ''),
                    'ê³µì •': item.get('process', ''),
                    '??ª©ëª?: item.get('name', '-'),
                    '?ì¬ë¹?: item.get('material_amount', 0) if item.get('material_amount', 0) > 0 else '',
                    '?¸ê±´ë¹?: item.get('labor_amount', 0) if item.get('labor_amount', 0) > 0 else '',
                    'ë¶€ê°€??: item.get('vat_amount', 0) if item.get('vat_included', False) else '',
                    'ì´ì•¡': item.get('total_amount', 0),
                    'ë©”ëª¨': self.extract_text_from_html(item.get('memo', ''))
                })
            
            df = pd.DataFrame(df_data)
            df.to_excel(filename, index=False)
            QMessageBox.information(self, "?±ê³µ", f"Excel ?Œì¼ë¡??€?¥ë˜?ˆìŠµ?ˆë‹¤.\n{filename}")
        
        except Exception as e:
            QMessageBox.critical(self, "?¤ë¥˜", f"Excel ?Œì¼ ?€??ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤:\n{str(e)}")

    def extract_text_from_html(self, html_content):
        if not html_content:
            return ''
        
        try:
            memo_data = json.loads(html_content)
            if isinstance(memo_data, dict) and 'html' in memo_data:
                doc = QTextDocument()
                doc.setHtml(memo_data['html'])
                return doc.toPlainText()
        except:
            pass
        
        doc = QTextDocument()
        doc.setHtml(html_content)
        return doc.toPlainText()

    def save_all_data(self):
        if self.is_updating:
            return
        
        # ?€???”ë°”?´ì‹± - ì§§ì? ?œê°„ ??ë°˜ë³µ ?€??ë°©ì?
        if hasattr(self, '_save_timer') and self._save_timer.isActive():
            self._save_timer.stop()
        
        if not hasattr(self, '_save_timer'):
            self._save_timer = QTimer()
            self._save_timer.timeout.connect(self._do_save_data)
            self._save_timer.setSingleShot(True)
        
        self._save_timer.start(100)  # 100ms ???€??    
    def _do_save_data(self):
        try:
            if hasattr(self, 'firebase_sync') and self.firebase_sync:
                try:
                    self.firebase_sync.save_to_firebase(self.projects_data)
                except:
                    pass
            
            try:
                data_file = get_data_file_path()
                with open(data_file, 'w', encoding='utf-8') as f:
                    save_data = {}
                    for project, items in self.projects_data.items():
                        save_data[project] = []
                        for item in items:
                            item_copy = item.copy()
                            if isinstance(item_copy.get('date'), QDate):
                                item_copy['date'] = item_copy['date'].toString('yyyy-MM-dd')
                            save_data[project].append(item_copy)
                    
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                    
                if hasattr(self, 'sync_status_label'):
                    if not (hasattr(self, 'firebase_sync') and self.firebase_sync and self.firebase_sync.db_ref):
                        self.sync_status_label.setText("??)
                        self.sync_status_label.setStyleSheet("color: #6c757d; font-size: 9px; font-weight: bold; padding: 0px; background-color: transparent; border: none; min-width: 10px; max-width: 10px;")
                        self.sync_status_label.setToolTip("ë¡œì»¬ ?€?¥ë¨")
                        
            except:
                QMessageBox.warning(self, "ê²½ê³ ", "?°ì´???€?¥ì— ?¤íŒ¨?ˆìŠµ?ˆë‹¤.")
                
        except:
            pass

    def load_all_data(self):
        # ?…ë°?´íŠ¸ ?Œë˜ê·??•ì¸ ë°??? œ
        exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
        flag_path = os.path.join(exe_dir, "update_in_progress.flag")
        was_updated = False
        
        if os.path.exists(flag_path):
            try:
                os.remove(flag_path)
                was_updated = True
            except:
                pass
        
        # ?°ì´??ë¡œë“œ ?¬ì‹œ??        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                data_file = get_data_file_path()
                if not os.path.exists(data_file):
                    if retry_count == 0:
                        self.project_combo.addItem("?„ë¡œ?íŠ¸ ê´€ë¦?)
                        self.current_project = None
                        self.table.setRowCount(0)
                        self.update_summary()
                        self.update_ui_state()
                    return
                
                with open(data_file, 'r', encoding='utf-8') as f:
                    self.projects_data = json.load(f)
                
                # ?°ì´??ë¡œë“œ ?±ê³µ
                break
                
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    time.sleep(0.5)  # 0.5ì´??€ê¸????¬ì‹œ??                else:
                    # ìµœì¢… ?¤íŒ¨
                    if retry_count == 1:
                        self.project_combo.addItem("?„ë¡œ?íŠ¸ ê´€ë¦?)
                        self.current_project = None
                        self.table.setRowCount(0)
                        self.update_summary()
                        self.update_ui_state()
                    return
        
        # ?°ì´??ë¡œë“œ ?±ê³µ ??UI ?…ë°?´íŠ¸
        self.update_project_combo()
        
        if len(self.projects_data) > 0:
            first_project = sorted(self.projects_data.keys())[0]
            self.project_combo.setCurrentText(first_project)
            self.current_project = first_project
            self.sort_column = 1
            self.sort_order = Qt.DescendingOrder
            self.update_table()
            self.update_summary()
            self.update_ui_state()
            
            data = self.get_current_data()
            if data:
                self.show_memo_dialog(0)
        else:
            self.current_project = None
            self.table.setRowCount(0)
            self.update_summary()
            self.update_ui_state()
        
        # ?…ë°?´íŠ¸ ?„ë£Œ ë©”ì‹œì§€
        if was_updated:
            QTimer.singleShot(1000, lambda: QMessageBox.information(
                self, "?…ë°?´íŠ¸ ?„ë£Œ", 
                f"?„ë¡œê·¸ë¨???±ê³µ?ìœ¼ë¡??…ë°?´íŠ¸?˜ì—ˆ?µë‹ˆ??\n?„ì¬ ë²„ì „: {CURRENT_VERSION}"
            ))

    def on_table_item_changed(self, item):
        if not item:
            return
        
        row = item.row()
        col = item.column()
        data = self.get_current_data()
        
        if row >= len(data):
            return
        
        current_item = data[row]
        old_item = current_item.copy()
        
        try:
            if col == 0:  # ?‘ì„±??                new_user = item.text().strip()
                if new_user:
                    current_item['user'] = new_user
                else:
                    item.setText(current_item.get('user', ''))
            
            elif col == 1:  # ? ì§œ
                date_text = item.text().strip()
                if ' (' in date_text:
                    date_text = date_text.split(' (')[0]
                
                try:
                    date_obj = datetime.strptime(date_text, '%Y-%m-%d')
                    current_item['date'] = date_text
                    
                    weekdays = ['??, '??, '??, 'ëª?, 'ê¸?, '??, '??]
                    weekday = weekdays[date_obj.weekday()]
                    item.setText(f"{date_text} ({weekday})")
                except ValueError:
                    original_date = current_item.get('date', '')
                    if original_date:
                        date_obj = datetime.strptime(original_date, '%Y-%m-%d')
                        weekdays = ['??, '??, '??, 'ëª?, 'ê¸?, '??, '??]
                        weekday = weekdays[date_obj.weekday()]
                        item.setText(f"{original_date} ({weekday})")
                    else:
                        item.setText('')
            
            elif col == 2:  # ê³µì •
                new_process = item.text().strip()
                current_item['process'] = new_process
                item.setText(new_process)
            
            elif col == 3:  # ??ª©ëª?                new_name = item.text().strip()
                if new_name:
                    current_item['name'] = new_name
                    item.setText(" " + new_name)
                else:
                    item.setText(" " + current_item.get('name', '-'))
            
            elif col == 4:  # ?ì¬ë¹?                text = item.text().replace(',', '').replace('??, '').strip()
                if text:
                    new_amount = int(text)
                    if new_amount >= 0:
                        current_item['material_amount'] = new_amount
                    else:
                        new_amount = 0
                        current_item['material_amount'] = 0
                else:
                    new_amount = 0
                    current_item['material_amount'] = 0
                
                item.setText(f"{new_amount:,}??" if new_amount > 0 else "")
                self.recalculate_item_total(current_item)
                self.update_row_totals(row)
            
            elif col == 5:  # ?¸ê±´ë¹?                text = item.text().replace(',', '').replace('??, '').strip()
                if text:
                    new_amount = int(text)
                    if new_amount >= 0:
                        current_item['labor_amount'] = new_amount
                    else:
                        new_amount = 0
                        current_item['labor_amount'] = 0
                else:
                    new_amount = 0
                    current_item['labor_amount'] = 0
                
                item.setText(f"{new_amount:,}??" if new_amount > 0 else "")
                self.recalculate_item_total(current_item)
                self.update_row_totals(row)
            
            if old_item != current_item:
                self.save_undo_state('edit', {
                    'old_item': old_item,
                    'new_item': current_item.copy()
                })
                self.save_all_data()
            
        except ValueError:
            if col == 1:
                original_date = current_item.get('date', '')
                if original_date:
                    date_obj = datetime.strptime(original_date, '%Y-%m-%d')
                    weekdays = ['??, '??, '??, 'ëª?, 'ê¸?, '??, '??]
                    weekday = weekdays[date_obj.weekday()]
                    item.setText(f"{original_date} ({weekday})")
                else:
                    item.setText('')
            elif col == 4:
                amount = current_item.get('material_amount', 0)
                item.setText(f"{amount:,}??" if amount > 0 else "")
            elif col == 5:
                amount = current_item.get('labor_amount', 0)
                item.setText(f"{amount:,}??" if amount > 0 else "")
        
        self.update_summary()
    
    def recalculate_item_total(self, item):
        material = item.get('material_amount', 0)
        labor = item.get('labor_amount', 0)
        
        if item.get('vat_included', False):
            total_net = material + labor
            if total_net > 0:
                vat = round(total_net * 0.1)
                total = total_net + vat
                item['vat_amount'] = vat
                item['total_amount'] = total
            else:
                item['vat_amount'] = 0
                item['total_amount'] = 0
        else:
            item['vat_amount'] = 0
            item['total_amount'] = material + labor
    
    def update_row_totals(self, row):
        data = self.get_current_data()
        if row >= len(data):
            return
        
        item = data[row]
        
        vat_text = self.format_vat(item)
        if vat_text:
            vat_text += " "
        vat_item = QTableWidgetItem(vat_text)
        vat_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vat_item.setFlags(Qt.NoItemFlags | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.table.setItem(row, 6, vat_item)
        
        total_text = f"{item.get('total_amount', 0):,}??"
        total_item = QTableWidgetItem(total_text)
        total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        total_item.setFlags(Qt.NoItemFlags | Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.table.setItem(row, 7, total_item)

    def save_data_as(self):
        try:
            if self.current_project:
                default_filename = f"{self.current_project}_ë°±ì—…_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            else:
                default_filename = f"?•ì‚°?°ì´??ë°±ì—…_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                "?°ì´??ë°±ì—… ?€??,
                default_filename,
                "JSON ?Œì¼ (*.json);;ëª¨ë“  ?Œì¼ (*.*)"
            )
            
            if not filename:
                return
            
            if not filename.endswith('.json'):
                filename += '.json'
            
            save_data = {}
            for project, items in self.projects_data.items():
                save_data[project] = []
                for item in items:
                    item_copy = item.copy()
                    if isinstance(item_copy.get('date'), QDate):
                        item_copy['date'] = item_copy['date'].toString('yyyy-MM-dd')
                    save_data[project].append(item_copy)
            
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, ensure_ascii=False, indent=2)
            
            QMessageBox.information(
                self,
                "ë°±ì—… ?„ë£Œ",
                f"?°ì´??ë°±ì—…???„ë£Œ?˜ì—ˆ?µë‹ˆ??\n\n"
                f"?Œì¼: {filename}\n\n"
                f"?’¡ ì°¸ê³ : ?°ì´?°ëŠ” ?´ë¼?°ë“œ???¤ì‹œê°??ë™ ?€?¥ë©?ˆë‹¤.\n"
                f"??ë°±ì—… ?Œì¼?€ ì¶”ê? ?ˆì „?¥ì¹˜?…ë‹ˆ??"
            )
            
            self.statusBar().showMessage(
                f"?’¾ ë°±ì—… ?Œì¼ ?ì„± ?„ë£Œ: {os.path.basename(filename)}", 
                5000
            )
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "ë°±ì—… ?¤ë¥˜",
                f"ë°±ì—… ?Œì¼ ?ì„± ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤:\n{str(e)}"
            )
    
    def closeEvent(self, event):
        self.hide()
        
        try:
            if hasattr(self, 'memo_save_timer'):
                self.memo_save_timer.stop()
            
            if self.current_memo_row >= 0:
                data = self.get_current_data()
                if self.current_memo_row < len(data):
                    html_content = self.memo_text_edit.toHtml()
                    if html_content:
                        data[self.current_memo_row]['memo'] = json.dumps({
                            'html': html_content,
                            'images': {}
                        }, ensure_ascii=False)
            
            # ?ë™ ë°±ì—… ?ì„±
            try:
                exe_dir = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
                backup_dir = os.path.join(exe_dir, "backups")
                
                # ë°±ì—… ?´ë”ê°€ ?†ìœ¼ë©??ì„±
                if not os.path.exists(backup_dir):
                    os.makedirs(backup_dir)
                
                # ë°±ì—… ?Œì¼ëª??ì„±
                backup_filename = f"auto_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                backup_path = os.path.join(backup_dir, backup_filename)
                
                # ë°±ì—… ?°ì´???€??                save_data = {}
                for project, items in self.projects_data.items():
                    save_data[project] = []
                    for item in items:
                        item_copy = item.copy()
                        if isinstance(item_copy.get('date'), QDate):
                            item_copy['date'] = item_copy['date'].toString('yyyy-MM-dd')
                        save_data[project].append(item_copy)
                
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    if hasattr(os, 'fsync'):
                        os.fsync(f.fileno())
                
                # 7???´ìƒ ??ë°±ì—… ?Œì¼ ?? œ
                current_time = time.time()
                for filename in os.listdir(backup_dir):
                    if filename.startswith("auto_backup_") and filename.endswith(".json"):
                        file_path = os.path.join(backup_dir, filename)
                        file_time = os.path.getmtime(file_path)
                        if current_time - file_time > 7 * 24 * 60 * 60:  # 7??                            try:
                                os.remove(file_path)
                            except:
                                pass
            except:
                pass
            
            # ë©”ì¸ ?°ì´???Œì¼ ?€??            try:
                data_file = get_data_file_path()
                with open(data_file, 'w', encoding='utf-8') as f:
                    save_data = {}
                    for project, items in self.projects_data.items():
                        save_data[project] = []
                        for item in items:
                            item_copy = item.copy()
                            if isinstance(item_copy.get('date'), QDate):
                                item_copy['date'] = item_copy['date'].toString('yyyy-MM-dd')
                            save_data[project].append(item_copy)
                    
                    json.dump(save_data, f, ensure_ascii=False, indent=2)
                    f.flush()
                    if hasattr(os, 'fsync'):
                        os.fsync(f.fileno())
            except:
                pass
            
            if hasattr(self, 'firebase_sync') and self.firebase_sync:
                if hasattr(self.firebase_sync, 'reconnect_timer'):
                    self.firebase_sync.reconnect_timer.stop()
                
                if hasattr(self.firebase_sync, 'listener') and self.firebase_sync.listener:
                    try:
                        self.firebase_sync.listener.close()
                    except:
                        pass
            
        except:
            pass
        
        event.accept()

    def check_for_updates(self):
        """?…ë°?´íŠ¸ ?•ì¸"""
        try:
            # ?…ë°?´íŠ¸ ë²„íŠ¼ ë¹„í™œ?±í™”
            if hasattr(self, 'update_btn'):
                self.update_btn.setEnabled(False)
                self.update_btn.setText("?•ì¸ ì¤?..")
            
            # GitHub APIë¥??µí•´ ìµœì‹  ë¦´ë¦¬ì¦??•ì¸
            response = requests.get(UPDATE_CHECK_URL, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data['tag_name'].lstrip('v')
                
                if self._compare_versions(latest_version, CURRENT_VERSION) > 0:
                    # ?…ë°?´íŠ¸ ê°€??                    download_url = release_data['assets'][0]['browser_download_url']
                    self.show_update_dialog(latest_version, download_url)
                    # ?…ë°?´íŠ¸ ë²„íŠ¼ ?œì„±??ë°??ìŠ¤??ë³€ê²?                    if hasattr(self, 'update_btn'):
                        self.update_btn.setEnabled(True)
                        self.update_btn.setText("?…ë°?´íŠ¸ ?•ì¸!")
                        self.update_btn.setStyleSheet(BUTTON_STYLE)
                else:
                    # ìµœì‹  ë²„ì „
                    if latest_version == CURRENT_VERSION:
                        # ?„ì „???™ì¼??ë²„ì „
                        QMessageBox.information(
                            self, 
                            "?…ë°?´íŠ¸ ?•ì¸", 
                            f"ë²„ì „ {CURRENT_VERSION}\n\nìµœì‹  ë²„ì „?…ë‹ˆ??"
                        )
                    else:
                        # ?„ì¬ ë²„ì „?????’ê±°???¤ë¥¸ ê²½ìš°
                        QMessageBox.information(
                            self, 
                            "?…ë°?´íŠ¸ ?•ì¸", 
                            f"?„ì¬ ë²„ì „: {CURRENT_VERSION}\nìµœì‹  ë²„ì „: {latest_version}\n\n?„ì¬ ?¬ìš© ì¤‘ì¸ ë²„ì „????ìµœì‹ ?…ë‹ˆ??"
                        )
                    # ë²„íŠ¼??"ìµœì‹  ë²„ì „"?¼ë¡œ ë³€ê²½í•˜ê³?ë¹„í™œ?±í™”
                    if hasattr(self, 'update_btn'):
                        self.update_btn.setEnabled(False)
                        self.update_btn.setText("ìµœì‹  ë²„ì „")
                        self.update_btn.setStyleSheet(GRAY_BUTTON_STYLE)
            else:
                QMessageBox.warning(self, "?…ë°?´íŠ¸ ?•ì¸", "?…ë°?´íŠ¸ ?œë²„???°ê²°?????†ìŠµ?ˆë‹¤.")
                # ?…ë°?´íŠ¸ ë²„íŠ¼ ?¤ì‹œ ?œì„±??                if hasattr(self, 'update_btn'):
                    self.update_btn.setEnabled(True)
                    self.update_btn.setText("?…ë°?´íŠ¸ ?•ì¸!")
                    self.update_btn.setStyleSheet(BUTTON_STYLE)
                
        except Exception as e:
            QMessageBox.critical(self, "?…ë°?´íŠ¸ ?•ì¸", f"?…ë°?´íŠ¸ ?•ì¸ ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤:\n{str(e)}")
            # ?…ë°?´íŠ¸ ë²„íŠ¼ ?¤ì‹œ ?œì„±??            if hasattr(self, 'update_btn'):
                self.update_btn.setEnabled(True)
                self.update_btn.setText("?…ë°?´íŠ¸ ?•ì¸!")
                self.update_btn.setStyleSheet(BUTTON_STYLE)
    
    def _compare_versions(self, version1, version2):
        """ë²„ì „ ë¹„êµ (version1 > version2 ?´ë©´ ?‘ìˆ˜ ë°˜í™˜)"""
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]
        
        for i in range(max(len(v1_parts), len(v2_parts))):
            v1 = v1_parts[i] if i < len(v1_parts) else 0
            v2 = v2_parts[i] if i < len(v2_parts) else 0
            if v1 != v2:
                return v1 - v2
        return 0

    def show_update_dialog(self, version, download_url):
        dialog = QDialog(self)
        dialog.setWindowTitle("?…ë°?´íŠ¸ ?Œë¦¼")
        dialog.setModal(True)
        dialog.setFixedSize(800, 600)  # ?¬ê¸°ë¥?2ë°°ë¡œ ì¦ê?
        
        layout = QVBoxLayout()
        layout.setSpacing(30)  # ?¬ë°±??ì¦ê?
        
        # ?œëª©
        title_label = QLabel("?ˆë¡œ??ë²„ì „???ˆìŠµ?ˆë‹¤!")
        title_label.setStyleSheet("font-size: 32px; font-weight: bold; color: #2c3e50;")  # 2ë°??¬ê¸°
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # ë²„ì „ ?•ë³´
        version_info_widget = QWidget()
        version_layout = QVBoxLayout()
        version_layout.setSpacing(20)  # 2ë°??¬ê¸°
        
        current_version_label = QLabel(f"?„ì¬ ë²„ì „: {CURRENT_VERSION}")
        current_version_label.setStyleSheet("font-size: 28px; color: #7f8c8d;")  # 2ë°??¬ê¸°
        current_version_label.setAlignment(Qt.AlignCenter)
        version_layout.addWidget(current_version_label)
        
        arrow_label = QLabel("??)
        arrow_label.setStyleSheet("font-size: 36px; color: #27ae60;")  # 2ë°??¬ê¸°
        arrow_label.setAlignment(Qt.AlignCenter)
        version_layout.addWidget(arrow_label)
        
        new_version_label = QLabel(f"??ë²„ì „: {version}")
        new_version_label.setStyleSheet("font-size: 28px; color: #27ae60; font-weight: bold;")  # 2ë°??¬ê¸°
        new_version_label.setAlignment(Qt.AlignCenter)
        version_layout.addWidget(new_version_label)
        
        version_info_widget.setLayout(version_layout)
        layout.addWidget(version_info_widget)
        
        layout.addStretch()
        
        # ?ˆë‚´ ë©”ì‹œì§€
        info_label = QLabel("?…ë°?´íŠ¸?˜ì‹œê² ìŠµ?ˆê¹Œ?")
        info_label.setStyleSheet("font-size: 24px; color: #7f8c8d;")  # 2ë°??¬ê¸°
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        # ë²„íŠ¼
        button_layout = QHBoxLayout()
        button_layout.setSpacing(20)  # 2ë°??¬ê¸°
        
        cancel_btn = QPushButton("?˜ì¤‘??)
        cancel_btn.setStyleSheet(GRAY_BUTTON_STYLE.replace("12px", "24px").replace("32px", "64px"))  # ?°íŠ¸?€ ?’ì´ 2ë°?        cancel_btn.setMinimumHeight(64)
        cancel_btn.clicked.connect(dialog.reject)
        
        ok_btn = QPushButton("ì§€ê¸??…ë°?´íŠ¸")
        ok_btn.setStyleSheet(BUTTON_STYLE.replace("12px", "24px").replace("32px", "64px"))  # ?°íŠ¸?€ ?’ì´ 2ë°?        ok_btn.setMinimumHeight(64)
        ok_btn.clicked.connect(lambda: (self.download_update(download_url), dialog.accept()))
        
        button_layout.addWidget(cancel_btn)
        button_layout.addWidget(ok_btn)
        
        layout.addLayout(button_layout)
        dialog.setLayout(layout)
        
        dialog.exec_()

    def download_update(self, download_url):
        try:
            import os
            import sys
            import subprocess
            
            # ?¤ìš´ë¡œë“œ URL ?•ì¸
            url_filename = download_url.split('/')[-1].split('?')[0]  # ì¿¼ë¦¬ ?Œë¼ë¯¸í„° ?œê±°
            
            # GitHub ë¦´ë¦¬ì¦??Œì¼ëª…ì´ ?¬ë°”ë¥¸ì? ?•ì¸
            if url_filename not in ['HV-L.exe', 'HV-L.zip']:
                QMessageBox.warning(
                    self, 
                    "?…ë°?´íŠ¸ ?¤ì • ?¤ë¥˜", 
                    f"GitHub ë¦´ë¦¬ì¦ˆì˜ ?Œì¼ëª…ì´ ?¬ë°”ë¥´ì? ?ŠìŠµ?ˆë‹¤.\n"
                    f"?„ì¬ ?Œì¼ëª? {url_filename}\n"
                    f"?•ìƒ ?Œì¼ëª? HV-L.exe\n\n"
                    f"GitHub ë¦´ë¦¬ì¦??¤ì •???•ì¸?´ì£¼?¸ìš”."
                )
                return
            
            # PyInstallerë¡?ë¹Œë“œ??exe ?¤í–‰ ì¤‘ì¸ì§€ ?•ì¸
            if getattr(sys, 'frozen', False):
                # exeë¡??¤í–‰ ì¤?                current_exe = sys.executable
                current_pid = os.getpid()
            else:
                # Python?¼ë¡œ ?¤í–‰ ì¤?- HV-L.exe ê²½ë¡œ ì°¾ê¸°
                current_dir = os.path.dirname(os.path.abspath(__file__))
                current_exe = os.path.join(current_dir, "HV-L.exe")
                current_pid = os.getpid()
                if not os.path.exists(current_exe):
                    QMessageBox.warning(self, "?…ë°?´íŠ¸ ?¤ë¥˜", "HV-L.exe ?Œì¼??ì°¾ì„ ???†ìŠµ?ˆë‹¤.\nê°œë°œ ?˜ê²½?ì„œ???…ë°?´íŠ¸ë¥??¬ìš©?????†ìŠµ?ˆë‹¤.")
                    return
            
            exe_dir = os.path.dirname(current_exe)
            # ?„ì‹œ ?Œì¼ëª…ì? ??ƒ ?™ì¼?˜ê²Œ (GitHub ?Œì¼ëª…ê³¼ ë¬´ê??˜ê²Œ)
            temp_exe_path = os.path.join(exe_dir, "HV-L_update_temp.exe")

            # ì§„í–‰ë¥??œì‹œ ?¤ì´?¼ë¡œê·?(?¬ê¸° 2ë°°ë¡œ ì¦ê?)
            progress_dialog = QProgressDialog("?…ë°?´íŠ¸ ?¤ìš´ë¡œë“œ ì¤?..", "ì·¨ì†Œ", 0, 100, self)
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setWindowTitle("?…ë°?´íŠ¸")
            progress_dialog.setMinimumWidth(800)  # 2ë°??¬ê¸°
            progress_dialog.setMinimumHeight(300)  # 2ë°??¬ê¸°
            progress_dialog.setStyleSheet("""
                QProgressDialog {
                    font-size: 20px;
                }
                QProgressBar {
                    min-height: 40px;
                    font-size: 18px;
                }
                QPushButton {
                    min-height: 50px;
                    font-size: 18px;
                    padding: 10px;
                }
            """)
            progress_dialog.show()

            # ê¸°ì¡´ ?„ì‹œ ?Œì¼ ?? œ
            if os.path.exists(temp_exe_path):
                try:
                    os.remove(temp_exe_path)
                except:
                    pass
            
            # ?¤ìš´ë¡œë“œ
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            downloaded = 0
            
            # ?Œì¼ ?¤ìš´ë¡œë“œ ë°??€??            with open(temp_exe_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if progress_dialog.wasCanceled():
                        os.remove(temp_exe_path)
                        return
                    
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    if total_size > 0:
                        progress = int((downloaded / total_size) * 100)
                        progress_dialog.setValue(progress)
                    
                    QApplication.processEvents()
                
                f.flush()
                os.fsync(f.fileno())  # ?Œì¼ ?œìŠ¤???™ê¸°??            
            progress_dialog.close()
            
            # ?¤ìš´ë¡œë“œ???Œì¼ ?•ì¸
            if not os.path.exists(temp_exe_path):
                QMessageBox.critical(self, "?¤ë¥˜", "?…ë°?´íŠ¸ ?Œì¼ ?¤ìš´ë¡œë“œ???¤íŒ¨?ˆìŠµ?ˆë‹¤.")
                return

            # ?…ë°?´íŠ¸ ?Œë˜ê·??Œì¼ ?ì„±
            flag_path = os.path.join(exe_dir, "update_in_progress.flag")
            with open(flag_path, "w") as f:
                f.write("updating")

            # ?„ì¬ ?°ì´???€??            self.save_all_data()
            
            # ë©”ëª¨ ?€??            if self.current_memo_row >= 0:
                self.save_current_memo()
            
            # ?Œì¼ ?œìŠ¤???™ê¸°??            if hasattr(os, 'sync'):
                os.sync()
            
            time.sleep(1)  # ?€???„ë£Œ ?€ê¸?
            # bat ?Œì¼ ?ì„± (???ˆì •?ì¸ ë²„ì „)
            bat_path = os.path.join(exe_dir, "update.bat")
            vbs_path = os.path.join(exe_dir, "update_silent.vbs")
            
            bat_content = f'''@echo off
chcp 65001 > nul 2>&1
title HV-L Update

REM 3ì´??€ê¸?timeout /t 3 /nobreak > nul 2>&1

REM ?„ì¬ ?„ë¡œ?¸ìŠ¤ ì¢…ë£Œ
if {current_pid} NEQ 0 (
    taskkill /F /PID {current_pid} > nul 2>&1
    timeout /t 2 /nobreak > nul 2>&1
)

REM HV-L.exe ?„ë¡œ?¸ìŠ¤ ê°•ì œ ì¢…ë£Œ
:kill_process
tasklist /FI "IMAGENAME eq HV-L.exe" 2>NUL | find /I "HV-L.exe" >NUL
if "%ERRORLEVEL%"=="0" (
    taskkill /F /IM HV-L.exe > nul 2>&1
    timeout /t 2 /nobreak > nul 2>&1
    goto kill_process
)

REM ê¸°ì¡´ ?Œì¼ ?? œ
if exist "{current_exe}" (
    attrib -R -H -S "{current_exe}" > nul 2>&1
    del /F /Q "{current_exe}" > nul 2>&1
    if exist "{current_exe}" (
        timeout /t 2 /nobreak > nul 2>&1
        del /F /Q "{current_exe}" > nul 2>&1
    )
)

REM ???Œì¼ë¡?êµì²´
move /Y "{temp_exe_path}" "{current_exe}" > nul 2>&1
if not exist "{current_exe}" (
    copy /Y "{temp_exe_path}" "{current_exe}" > nul 2>&1
    del /F /Q "{temp_exe_path}" > nul 2>&1
)

REM ?Œë˜ê·??Œì¼ ?? œ
if exist "{flag_path}" del /F /Q "{flag_path}" > nul 2>&1

REM ?Œì¼ ?œìŠ¤???™ê¸°??timeout /t 2 /nobreak > nul 2>&1

REM ê¸°í? ?…ë°?´íŠ¸ ê´€???Œì¼ ?•ë¦¬
if exist "{exe_dir}\\update_new.exe" del /F /Q "{exe_dir}\\update_new.exe" > nul 2>&1
if exist "{exe_dir}\\update.exe" del /F /Q "{exe_dir}\\update.exe" > nul 2>&1
if exist "{exe_dir}\\HV-L.exe.new" del /F /Q "{exe_dir}\\HV-L.exe.new" > nul 2>&1

REM ?„ì‹œ ?´ë” ?•ë¦¬ë¥??„í•œ ì¶”ê? ?€ê¸?timeout /t 5 /nobreak > nul 2>&1

REM ?„ë¡œê·¸ë¨ ?¬ì‹œ??(??ì°½ì—?? ?…ë¦½?ìœ¼ë¡?
cd /d "{exe_dir}"
start /B "" cmd /c "timeout /t 2 /nobreak > nul 2>&1 && "{current_exe}""

REM VBS ?Œì¼ ?? œ
timeout /t 1 /nobreak > nul 2>&1
if exist "{vbs_path}" del /F /Q "{vbs_path}" > nul 2>&1

REM bat ?Œì¼ ?ì²´ ?? œ
(goto) 2>nul & del "%~f0"
'''
            with open(bat_path, "w", encoding="utf-8") as f:
                f.write(bat_content)

            # VBScript ?Œì¼ ?ì„± (bat ?Œì¼??ë°±ê·¸?¼ìš´?œì—???¤í–‰)
            vbs_path = os.path.join(exe_dir, "update_silent.vbs")
            vbs_content = f'''Set objShell = CreateObject("WScript.Shell")
objShell.Run """{bat_path}""", 0, False'''
            with open(vbs_path, "w", encoding="utf-8") as f:
                f.write(vbs_content)
            
            # VBScript ?¤í–‰ (?„ì „??ë°±ê·¸?¼ìš´?œì—??
            subprocess.Popen(['wscript.exe', vbs_path], 
                           creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS)
            
            QMessageBox.information(self, "?…ë°?´íŠ¸", "?…ë°?´íŠ¸ê°€ ?„ë£Œ?©ë‹ˆ??\n\n? ì‹œ ???„ë¡œê·¸ë¨???ë™?¼ë¡œ ?¬ì‹œ?‘ë©?ˆë‹¤.\n?¬ì‹œ?‘ë˜ì§€ ?Šìœ¼ë©??˜ë™?¼ë¡œ ?¤í–‰?´ì£¼?¸ìš”.")
            
            # ?„ë¡œê·¸ë¨ ì¢…ë£Œ
            self.close()
            QApplication.quit()

        except Exception as e:
            if 'progress_dialog' in locals():
                progress_dialog.close()
            QMessageBox.critical(self, "?¤ë¥˜", f"?…ë°?´íŠ¸ ?¤ìš´ë¡œë“œ ì¤??¤ë¥˜ê°€ ë°œìƒ?ˆìŠµ?ˆë‹¤:\n{str(e)}")

    def background_update_check(self):
        try:
            response = requests.get(UPDATE_CHECK_URL, timeout=10)
            if response.status_code == 200:
                release_data = response.json()
                latest_version = release_data['tag_name'].lstrip('v')
                if self._compare_versions(latest_version, CURRENT_VERSION) > 0:
                    # ?…ë°?´íŠ¸ ?„ìš”: ë²„íŠ¼ ?œì„±?? ?ìŠ¤???‰ìƒ ë³€ê²?                    self.update_btn.setEnabled(True)
                    self.update_btn.setText("?…ë°?´íŠ¸ ?„ìš”!")
                    self.update_btn.setStyleSheet(BUTTON_STYLE.replace("#7d9471", "#d9534f").replace("#6d8062", "#c9302c").replace("#5d6f54", "#ac2925"))
                else:
                    # ìµœì‹  ë²„ì „: ë²„íŠ¼ ë¹„í™œ?±í™”, 'ìµœì‹  ë²„ì „' ?ìŠ¤?? ?Œìƒ‰ ì²˜ë¦¬
                    self.update_btn.setEnabled(False)
                    self.update_btn.setText("ìµœì‹  ë²„ì „")
                    self.update_btn.setStyleSheet(GRAY_BUTTON_STYLE)
        except:
            pass


def main():
    app = QApplication(sys.argv)
    
    font = QFont("ë§‘ì? ê³ ë”•", 9)
    app.setFont(font)
    
    USE_LOGIN = False
    
    window = InteriorSettlementApp()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
