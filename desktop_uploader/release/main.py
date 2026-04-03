#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版主界面 - 验证一次，启动多个浏览器
"""

import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QProgressBar, QTextEdit, QFileDialog, QGroupBox, QLineEdit,
    QDialog, QFormLayout, QSpinBox, QDoubleSpinBox, QCheckBox,
    QComboBox
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QTextCursor, QColor

# 导入上传核心
try:
    from fanqie_uploader_impl import FanqieUploaderImpl
    UPLOADER_AVAILABLE = True
except ImportError:
    UPLOADER_AVAILABLE = False


class LoginDialog(QDialog):
    """登录对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("登录 - 大文娱小说发布助手")
        self.setMinimumWidth(350)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # 标题
        title = QLabel("🔑 官网账户登录")
        title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # 表单
        form = QFormLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("官网用户名")
        form.addRow("用户名:", self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setPlaceholderText("官网密码")
        form.addRow("密码:", self.password_input)
        
        layout.addLayout(form)
        
        # 提示
        hint = QLabel("💡 登录后即可启动多个浏览器上传")
        hint.setStyleSheet("color: #666;")
        layout.addWidget(hint)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.login_btn = QPushButton("登录")
        self.login_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
        """)
        self.login_btn.clicked.connect(self.do_login)
        btn_layout.addWidget(self.login_btn)
        
        layout.addLayout(btn_layout)
        
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: red;")
        layout.addWidget(self.status_label)
    
    def do_login(self):
        """执行登录"""
        import requests
        
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status_label.setText("请输入用户名和密码")
            return
        
        self.status_label.setText("登录中...")
        self.login_btn.setEnabled(False)
        
        try:
            response = requests.post(
                "https://novel-ai.online/login",
                json={"username": username, "password": password},
                timeout=30
            )
            
            data = response.json()
            if data.get("success"):
                # 保存会话
                session_file = Path(__file__).parent / "session.json"
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        "username": username,
                        "token": data.get("access_token"),
                        "saved_at": datetime.now().isoformat()
                    }, f)
                
                self.accept()
            else:
                self.status_label.setText(f"登录失败: {data.get('error', '未知错误')}")
                self.login_btn.setEnabled(True)
                
        except Exception as e:
            self.status_label.setText(f"登录异常: {e}")
            self.login_btn.setEnabled(True)


class BrowserManager:
    """简单的浏览器管理器"""
    
    def __init__(self):
        self.instances = {}
        self.next_port = 10000
        self.chrome_path = self._find_chrome()
    
    def _find_chrome(self) -> str:
        """只检查固定路径"""
        paths = [
            Path(__file__).parent / "chrome" / "chrome-win64" / "chrome.exe",
        ]
        for p in paths:
            if p.exists():
                return str(p)
        return None
    
    def start_browser(self) -> dict:
        """启动浏览器"""
        port = self.next_port
        self.next_port += 1
        
        # 创建数据目录
        data_dir = Path(__file__).parent / f"chrome_data_{port}"
        data_dir.mkdir(exist_ok=True)
        
        # 检查 Chrome
        if not self.chrome_path:
            return {"success": False, "error": "未找到 Chrome，请先下载"}
        
        # 启动 Chrome
        cmd = [
            self.chrome_path,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "https://fanqienovel.com/main/writer/book-manage"
        ]
        
        try:
            process = subprocess.Popen(cmd)
            self.instances[port] = {
                "port": port,
                "process": process,
                "data_dir": data_dir,
                "status": "running"
            }
            return {"success": True, "port": port}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def stop_browser(self, port: int):
        """停止浏览器"""
        if port in self.instances:
            info = self.instances[port]
            if info.get("process"):
                info["process"].terminate()
            del self.instances[port]
    
    def get_running_count(self) -> int:
        return len(self.instances)


class MainWindowSimple(QMainWindow):
    """简化版主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("大文娱小说发布助手 v1.3.6")
        self.setGeometry(100, 100, 1200, 800)
        
        self.browser_manager = BrowserManager()
        self.username = None
        
        self.init_ui()
        self.check_login()
    
    def init_ui(self):
        """初始化界面"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        
        # 左侧面板
        left = QVBoxLayout()
        
        # 用户信息
        self.user_group = QGroupBox("用户信息")
        user_layout = QVBoxLayout()
        self.user_label = QLabel("未登录")
        user_layout.addWidget(self.user_label)
        
        self.login_btn = QPushButton("🔑 登录")
        self.login_btn.clicked.connect(self.show_login)
        user_layout.addWidget(self.login_btn)
        
        self.user_group.setLayout(user_layout)
        left.addWidget(self.user_group)
        
        # 浏览器管理
        browser_group = QGroupBox("浏览器管理")
        browser_layout = QVBoxLayout()
        
        self.browser_list = QListWidget()
        browser_layout.addWidget(self.browser_list)
        
        btn_layout = QHBoxLayout()
        
        self.add_browser_btn = QPushButton("+ 启动浏览器")
        self.add_browser_btn.clicked.connect(self.start_browser)
        self.add_browser_btn.setEnabled(False)
        btn_layout.addWidget(self.add_browser_btn)
        
        self.stop_browser_btn = QPushButton("- 停止")
        self.stop_browser_btn.clicked.connect(self.stop_selected_browser)
        btn_layout.addWidget(self.stop_browser_btn)
        
        browser_layout.addLayout(btn_layout)
        browser_group.setLayout(browser_layout)
        left.addWidget(browser_group)
        
        layout.addLayout(left, 1)
        
        # 右侧面板 - 上传控制
        right = QVBoxLayout()
        
        upload_group = QGroupBox("上传控制")
        upload_layout = QVBoxLayout()
        
        # 项目选择
        upload_layout.addWidget(QLabel("选择项目:"))
        self.project_combo = QComboBox()
        upload_layout.addWidget(self.project_combo)
        
        # 章节列表
        upload_layout.addWidget(QLabel("章节列表:"))
        self.chapter_list = QListWidget()
        upload_layout.addWidget(self.chapter_list)
        
        # 上传按钮
        self.upload_btn = QPushButton("🚀 开始上传")
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 15px;
                font-size: 16px;
            }
        """)
        self.upload_btn.setEnabled(False)
        upload_layout.addWidget(self.upload_btn)
        
        upload_group.setLayout(upload_layout)
        right.addWidget(upload_group)
        
        # 日志
        log_group = QGroupBox("运行日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        right.addWidget(log_group)
        
        layout.addLayout(right, 2)
    
    def check_login(self):
        """检查是否已登录"""
        session_file = Path(__file__).parent / "session.json"
        if session_file.exists():
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.username = data.get("username")
                    self.update_login_state()
            except:
                pass
    
    def update_login_state(self):
        """更新登录状态"""
        if self.username:
            self.user_label.setText(f"👤 {self.username}")
            self.login_btn.setText("🚪 退出")
            self.login_btn.clicked.disconnect()
            self.login_btn.clicked.connect(self.logout)
            self.add_browser_btn.setEnabled(True)
            self.upload_btn.setEnabled(True)
        else:
            self.user_label.setText("未登录")
            self.login_btn.setText("🔑 登录")
            self.add_browser_btn.setEnabled(False)
            self.upload_btn.setEnabled(False)
    
    def show_login(self):
        """显示登录对话框"""
        dialog = LoginDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.check_login()
    
    def logout(self):
        """退出登录"""
        session_file = Path(__file__).parent / "session.json"
        if session_file.exists():
            session_file.unlink()
        self.username = None
        self.update_login_state()
    
    def start_browser(self):
        """启动浏览器"""
        if not self.username:
            QMessageBox.warning(self, "提示", "请先登录")
            return
        
        result = self.browser_manager.start_browser()
        
        if result["success"]:
            port = result["port"]
            item = QListWidgetItem(f"浏览器 #{port} (端口: {port})")
            item.setData(Qt.UserRole, port)
            self.browser_list.addItem(item)
            self.log(f"✅ 启动浏览器成功 (端口: {port})")
        else:
            QMessageBox.warning(self, "启动失败", result.get("error", "未知错误"))
    
    def stop_selected_browser(self):
        """停止选中的浏览器"""
        item = self.browser_list.currentItem()
        if item:
            port = item.data(Qt.UserRole)
            self.browser_manager.stop_browser(port)
            self.browser_list.takeItem(self.browser_list.row(item))
            self.log(f"🛑 停止浏览器 (端口: {port})")
    
    def log(self, message: str):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.append(f"[{timestamp}] {message}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = MainWindowSimple()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
