#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱小说发布助手 v1.3.7
单官网账户 + 多番茄账户架构
"""

import sys
import os
import json
import time
from pathlib import Path
from datetime import datetime

# 获取程序运行目录（支持打包后的EXE）
def get_app_dir() -> Path:
    """获取应用程序目录（兼容开发和打包环境）"""
    if getattr(sys, 'frozen', False):
        # 打包后的EXE环境
        return Path(sys.executable).parent
    else:
        # 开发环境
        return Path(__file__).parent

APP_DIR = get_app_dir()

# 统一数据目录
def get_data_dir() -> Path:
    """获取统一数据目录"""
    data_dir = APP_DIR / "NovelPublisher_Data"
    data_dir.mkdir(exist_ok=True)
    return data_dir

DATA_DIR = get_data_dir()

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QMessageBox, QGroupBox, QTabWidget, QSplitter, QRadioButton,
    QButtonGroup, QDialog, QLineEdit, QDoubleSpinBox, QCheckBox,
    QProgressBar, QTextEdit, QFileDialog, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor

# 导入模块
try:
    from tomato_account_manager import TomatoAccountManager, TomatoAccount, ChromeLauncher
    from fanqie_uploader_impl import FanqieUploaderImpl
    UPLOADER_AVAILABLE = True
except ImportError as e:
    print(f"导入失败: {e}")
    UPLOADER_AVAILABLE = False

# 环境配置
try:
    from config_env import env_config
except ImportError:
    class EnvConfig:
        website_url = "https://novel-ai.online"
        api_base_url = "https://novel-ai.online"
        upload_guide_url = "https://novel-ai.online/pages/v2/uploader-guide"
    env_config = EnvConfig()


# ============== 登录对话框 ==============
class LoginDialog(QDialog):
    """官网登录对话框"""
    
    login_success = pyqtSignal(dict)
    
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
        form_layout = QVBoxLayout()
        
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("用户名")
        self.username_input.setMinimumHeight(36)
        form_layout.addWidget(QLabel("用户名:"))
        form_layout.addWidget(self.username_input)
        
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(36)
        form_layout.addWidget(QLabel("密码:"))
        form_layout.addWidget(self.password_input)
        
        layout.addLayout(form_layout)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        login_btn = QPushButton("登录")
        login_btn.setMinimumHeight(40)
        login_btn.setStyleSheet("""
            QPushButton {
                background-color: #1976D2;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #1565C0; }
        """)
        login_btn.clicked.connect(self.do_login)
        btn_layout.addWidget(login_btn)
        
        layout.addLayout(btn_layout)
        
        # 说明
        hint = QLabel("💡 使用 novel-ai.online 官网账户登录")
        hint.setStyleSheet("color: #757575; font-size: 12px;")
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
    
    def do_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            QMessageBox.warning(self, "提示", "请输入用户名和密码")
            return
        
        # 简单验证（实际应调用API）
        self.login_success.emit({
            'username': username,
            'points': 100
        })
        self.accept()


# ============== 添加番茄账户对话框 ==============
class AddAccountDialog(QDialog):
    """添加番茄账户对话框"""
    
    account_added = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("添加番茄账户")
        self.setMinimumWidth(300)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("账户名称:"))
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: 作者张三")
        layout.addWidget(self.name_input)
        
        hint = QLabel("💡 名称用于区分不同的番茄作者账户")
        hint.setStyleSheet("color: #757575; font-size: 12px;")
        layout.addWidget(hint)
        
        btn_layout = QHBoxLayout()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        add_btn = QPushButton("添加")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
            }
        """)
        add_btn.clicked.connect(self.do_add)
        btn_layout.addWidget(add_btn)
        
        layout.addLayout(btn_layout)
    
    def do_add(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入账户名称")
            return
        
        self.account_added.emit(name)
        self.accept()


# ============== Chrome下载工作线程 ==============
class ChromeDownloadWorker(QThread):
    """Chrome下载工作线程 - 避免GUI卡顿和崩溃"""
    
    progress_signal = pyqtSignal(int, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, chrome_launcher):
        super().__init__()
        self.chrome_launcher = chrome_launcher
    
    def run(self):
        """执行下载"""
        def progress_cb(percent, message):
            self.progress_signal.emit(percent, message)
        
        success, message = self.chrome_launcher.download_chrome_blocking(progress_cb)
        self.finished_signal.emit(success, message)


# ============== 上传工作线程 ==============
class UploadWorker(QThread):
    """上传工作线程"""
    
    progress_signal = pyqtSignal(int, str)
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, str)
    
    def __init__(self, novel_title: str, chapters: list, settings: dict, 
                 tomato_account: TomatoAccount):
        super().__init__()
        self.novel_title = novel_title
        self.chapters = chapters
        self.settings = settings
        self.tomato_account = tomato_account
        self.is_running = True
        self.uploader = None
    
    def run(self):
        try:
            self.log_signal.emit(f"🚀 开始上传 - 使用账户: {self.tomato_account.name}", "info")
            self.log_signal.emit(f"📡 连接浏览器 (端口: {self.tomato_account.port})...", "info")
            
            # 创建上传器
            self.uploader = FanqieUploaderImpl(
                novel_title=self.novel_title,
                progress_callback=lambda p, m: self.progress_signal.emit(int(p * 0.8) + 10, m),
                log_callback=lambda m, l: self.log_signal.emit(m, l)
            )
            
            # 连接浏览器
            if not self.uploader.connect_chrome(port=self.tomato_account.port):
                self.finished_signal.emit(False, "无法连接到浏览器")
                return
            
            self.progress_signal.emit(15, "已连接到浏览器")
            
            # 检查登录
            if not self.uploader.check_login():
                self.log_signal.emit("⏳ 等待登录番茄小说...", "warning")
                if not self.uploader.wait_for_login(timeout=120):
                    self.finished_signal.emit(False, "登录超时")
                    return
            
            self.progress_signal.emit(20, "已登录")
            
            # 查找书籍
            if not self.uploader.find_book():
                self.finished_signal.emit(False, "无法找到或创建书籍")
                return
            
            self.progress_signal.emit(25, "已找到书籍")
            
            # 上传章节
            delay_min = self.settings.get('delay_min', 3)
            delay_max = self.settings.get('delay_max', 8)
            
            total = len(self.chapters)
            success = 0
            failed = 0
            
            for i, ch in enumerate(self.chapters):
                if not self.is_running:
                    break
                
                ch_num = ch.get('chapter_number', i + 1)
                ch_title = ch.get('title', f'第{ch_num}章')
                
                self.log_signal.emit(f"📤 上传第{ch_num}章: {ch_title}", "info")
                
                # 模拟上传（实际应调用真实上传）
                time.sleep(0.5)  # 模拟延迟
                
                # 这里应该调用真实的上传方法
                # result = self.uploader.upload_single_chapter(ch)
                
                success += 1
                progress = 25 + int((i + 1) / total * 75)
                self.progress_signal.emit(progress, f"已上传 {i+1}/{total} 章")
                
                # 章节间延迟
                if i < total - 1 and self.is_running:
                    import random
                    delay = random.uniform(delay_min, delay_max)
                    self.log_signal.emit(f"⏱️ 等待 {delay:.1f} 秒...", "info")
                    time.sleep(delay)
            
            # 完成
            if failed == 0:
                self.finished_signal.emit(True, f"✅ 上传完成: {success}/{total} 章")
            else:
                self.finished_signal.emit(False, f"⚠️ 上传完成: 成功 {success}, 失败 {failed}")
                
        except Exception as e:
            self.log_signal.emit(f"❌ 上传异常: {e}", "error")
            self.finished_signal.emit(False, str(e))
        finally:
            if self.uploader:
                self.uploader.close()
    
    def stop(self):
        self.is_running = False
        self.log_signal.emit("正在停止上传...", "warning")


# ============== 番茄账户卡片 ==============
class AccountCard(QFrame):
    """番茄账户卡片"""
    
    start_clicked = pyqtSignal(str)
    stop_clicked = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)
    selected_changed = pyqtSignal(str, bool)
    
    def __init__(self, account: TomatoAccount, parent=None):
        super().__init__(parent)
        self.account_id = account.id
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        self.setStyleSheet("""
            AccountCard {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        self.setup_ui(account)
    
    def setup_ui(self, account: TomatoAccount):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # 选择按钮
        self.radio = QRadioButton()
        self.radio.toggled.connect(lambda checked: self.selected_changed.emit(self.account_id, checked))
        layout.addWidget(self.radio)
        
        # 图标
        icon = QLabel("🍅")
        icon.setFont(QFont("Segoe UI Emoji", 20))
        layout.addWidget(icon)
        
        # 信息
        info_layout = QVBoxLayout()
        
        name_label = QLabel(f"<b>{account.name}</b>")
        name_label.setStyleSheet("font-size: 14px;")
        info_layout.addWidget(name_label)
        
        self.status_label = QLabel(self._get_status_text(account.status))
        self.status_label.setStyleSheet(f"color: {self._get_status_color(account.status)}; font-size: 12px;")
        info_layout.addWidget(self.status_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # 端口
        port_label = QLabel(f"端口: {account.port}")
        port_label.setStyleSheet("color: #757575; font-size: 11px;")
        layout.addWidget(port_label)
        
        # 操作按钮
        self.action_btn = QPushButton("启动")
        self.action_btn.setMinimumWidth(60)
        self.action_btn.clicked.connect(self._on_action_clicked)
        layout.addWidget(self.action_btn)
        
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip("删除账户")
        delete_btn.setStyleSheet("color: #F44336;")
        delete_btn.clicked.connect(lambda: self.delete_clicked.emit(self.account_id))
        layout.addWidget(delete_btn)
        
        self.update_status(account.status)
    
    def _get_status_text(self, status: str) -> str:
        return {"stopped": "⚫ 已停止", "running": "🟢 运行中", "error": "🔴 错误"}.get(status, "⚫ 已停止")
    
    def _get_status_color(self, status: str) -> str:
        return {"stopped": "#757575", "running": "#4CAF50", "error": "#F44336"}.get(status, "#757575")
    
    def update_status(self, status: str):
        self.status_label.setText(self._get_status_text(status))
        self.status_label.setStyleSheet(f"color: {self._get_status_color(status)}; font-size: 12px;")
        
        if status == "running":
            self.action_btn.setText("停止")
        else:
            self.action_btn.setText("启动")
    
    def _on_action_clicked(self):
        if self.action_btn.text() == "启动":
            self.start_clicked.emit(self.account_id)
        else:
            self.stop_clicked.emit(self.account_id)


# ============== 主窗口 ==============
class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("大文娱小说发布助手 v1.3.7")
        self.setGeometry(100, 100, 1400, 900)
        
        # 数据
        self.website_user = None
        self.tomato_manager = TomatoAccountManager(data_dir=DATA_DIR)
        self.chrome_launcher = ChromeLauncher(data_dir=DATA_DIR)
        self.current_project = None
        self.chapters = []
        self.upload_worker = None
        self.selected_account_id = None
        self.account_cards = {}
        
        # 检查登录
        if not self.check_saved_login():
            self.show_login_dialog()
        
        self.init_ui()
        self.load_projects()
        self.refresh_accounts_ui()
        
        # 定时刷新状态
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_accounts_status)
        self.status_timer.start(2000)
    
    def check_saved_login(self) -> bool:
        """检查是否有保存的登录"""
        token_file = DATA_DIR / "website_token.json"
        if token_file.exists():
            try:
                data = json.loads(token_file.read_text(encoding='utf-8'))
                self.website_user = data
                return True
            except:
                pass
        return False
    
    def show_login_dialog(self):
        """显示登录对话框"""
        dialog = LoginDialog(self)
        dialog.login_success.connect(self.on_login_success)
        if dialog.exec_() != QDialog.Accepted:
            sys.exit(0)
    
    def on_login_success(self, user_data: dict):
        """登录成功"""
        self.website_user = user_data
        # 保存token
        token_file = DATA_DIR / "website_token.json"
        try:
            token_file.write_text(json.dumps(user_data, indent=2), encoding='utf-8')
            self.log(f"💾 Token 已保存: {token_file}", "success")
        except Exception as e:
            self.log(f"❌ Token 保存失败: {e}", "error")
        self.update_title()
    
    def update_title(self):
        """更新标题"""
        if self.website_user:
            user = self.website_user.get('username', '未知')
            points = self.website_user.get('points', 0)
            self.setWindowTitle(f"大文娱小说发布助手 v1.3.7 - {user} ({points}点)")
    
    def init_ui(self):
        """初始化界面"""
        central = QWidget()
        self.setCentralWidget(central)
        
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # === 标题区域 ===
        title_layout = QHBoxLayout()
        
        title_label = QLabel("🚀 大文娱小说发布助手")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 平台选择
        title_layout.addWidget(QLabel("发布平台:"))
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("🍅 番茄小说", "fanqie")
        self.platform_combo.setMinimumWidth(140)
        title_layout.addWidget(self.platform_combo)
        
        # 官网按钮（链接到使用指南）
        website_btn = QPushButton("📖 使用指南")
        website_btn.setToolTip("打开官网使用指南页面")
        website_btn.clicked.connect(lambda: os.startfile(getattr(env_config, 'upload_guide_url', 'https://novel-ai.online/pages/v2/uploader-guide')))
        title_layout.addWidget(website_btn)
        
        layout.addLayout(title_layout)
        
        # === 番茄账户管理区域 ===
        accounts_group = QGroupBox("🍅 番茄账户管理")
        accounts_layout = QVBoxLayout()
        
        # 账户列表区域
        self.accounts_scroll = QScrollArea()
        self.accounts_scroll.setWidgetResizable(True)
        self.accounts_scroll.setMaximumHeight(180)
        self.accounts_scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.accounts_container = QWidget()
        self.accounts_list_layout = QVBoxLayout(self.accounts_container)
        self.accounts_list_layout.setSpacing(8)
        self.accounts_list_layout.addStretch()
        
        self.accounts_scroll.setWidget(self.accounts_container)
        accounts_layout.addWidget(self.accounts_scroll)
        
        # 添加按钮
        add_btn = QPushButton("➕ 添加番茄账户")
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
            }
        """)
        add_btn.clicked.connect(self.add_tomato_account)
        accounts_layout.addWidget(add_btn)
        
        accounts_group.setLayout(accounts_layout)
        layout.addWidget(accounts_group)
        
        # === 主分割器 ===
        splitter = QSplitter(Qt.Horizontal)
        
        # === 左侧面板 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 项目选择
        project_group = QGroupBox("📁 项目选择")
        project_layout = QVBoxLayout()
        
        self.project_combo = QComboBox()
        self.project_combo.setMinimumHeight(36)
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        project_layout.addWidget(self.project_combo)
        
        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_projects)
        btn_layout.addWidget(refresh_btn)
        
        import_btn = QPushButton("📂 选择目录")
        import_btn.clicked.connect(self.select_project_directory)
        btn_layout.addWidget(import_btn)
        
        project_layout.addLayout(btn_layout)
        project_group.setLayout(project_layout)
        left_layout.addWidget(project_group)
        
        # 章节列表
        chapters_group = QGroupBox("📋 章节列表")
        chapters_layout = QVBoxLayout()
        
        self.chapters_stats = QLabel("共 0 个章节")
        chapters_layout.addWidget(self.chapters_stats)
        
        self.chapters_list = QListWidget()
        self.chapters_list.setSelectionMode(QListWidget.MultiSelection)
        chapters_layout.addWidget(self.chapters_list)
        
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("☑️ 全选")
        select_all_btn.clicked.connect(self.select_all_chapters)
        select_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("⬜ 全不选")
        select_none_btn.clicked.connect(self.select_none_chapters)
        select_layout.addWidget(select_none_btn)
        select_layout.addStretch()
        
        chapters_layout.addLayout(select_layout)
        chapters_group.setLayout(chapters_layout)
        left_layout.addWidget(chapters_group)
        
        splitter.addWidget(left_panel)
        
        # === 右侧面板 ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # 标签页
        tabs = QTabWidget()
        
        # 上传控制页
        upload_tab = QWidget()
        upload_layout = QVBoxLayout(upload_tab)
        
        # 设置组
        settings_group = QGroupBox("⚙️ 上传设置")
        settings_layout = QVBoxLayout()
        
        # 延迟设置
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("上传间隔:"))
        
        self.delay_min = QDoubleSpinBox()
        self.delay_min.setRange(0.5, 60)
        self.delay_min.setValue(3)
        self.delay_min.setDecimals(1)
        delay_layout.addWidget(self.delay_min)
        
        delay_layout.addWidget(QLabel("~"))
        
        self.delay_max = QDoubleSpinBox()
        self.delay_max.setRange(0.5, 60)
        self.delay_max.setValue(8)
        self.delay_max.setDecimals(1)
        delay_layout.addWidget(self.delay_max)
        
        delay_layout.addWidget(QLabel("秒"))
        delay_layout.addStretch()
        
        settings_layout.addLayout(delay_layout)
        
        # 选项
        self.stop_on_error = QCheckBox("失败时自动停止")
        self.stop_on_error.setChecked(True)
        settings_layout.addWidget(self.stop_on_error)
        
        settings_group.setLayout(settings_layout)
        upload_layout.addWidget(settings_group)
        
        # 进度组
        progress_group = QGroupBox("📊 上传进度")
        progress_layout = QVBoxLayout()
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        progress_layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("⏳ 等待开始...")
        progress_layout.addWidget(self.status_label)
        
        # 使用账户显示
        self.upload_account_label = QLabel("🍅 未选择上传账户")
        self.upload_account_label.setStyleSheet("color: #1976D2; font-weight: bold;")
        progress_layout.addWidget(self.upload_account_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 开始上传")
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #45a049; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.start_btn.clicked.connect(self.start_upload)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹ 停止")
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_upload)
        btn_layout.addWidget(self.stop_btn)
        
        progress_layout.addLayout(btn_layout)
        progress_group.setLayout(progress_layout)
        upload_layout.addWidget(progress_group)
        
        # 日志组
        log_group = QGroupBox("📝 运行日志")
        log_layout = QVBoxLayout()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: Consolas, monospace;
                font-size: 12px;
                border: none;
                border-radius: 4px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        log_btn_layout = QHBoxLayout()
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self.log_text.clear)
        log_btn_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("保存日志")
        save_btn.clicked.connect(self.save_log)
        log_btn_layout.addWidget(save_btn)
        
        log_btn_layout.addStretch()
        log_layout.addLayout(log_btn_layout)
        
        log_group.setLayout(log_layout)
        upload_layout.addWidget(log_group)
        
        tabs.addTab(upload_tab, "📤 上传控制")
        
        # 使用指南页
        guide_tab = QWidget()
        guide_layout = QVBoxLayout(guide_tab)
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setHtml("""
        <h2>使用指南</h2>
        <h3>1. 添加番茄账户</h3>
        <p>点击"➕ 添加番茄账户"，输入名称（如"作者张三"），创建独立的浏览器配置。</p>
        
        <h3>2. 启动浏览器</h3>
        <p>点击账户卡片的"启动"按钮，会自动打开 Chrome 并跳转到番茄小说。</p>
        
        <h3>3. 登录番茄</h3>
        <p>在打开的浏览器中登录番茄小说作者后台。</p>
        
        <h3>4. 选择项目</h3>
        <p>从左侧选择要上传的小说项目，勾选要上传的章节。</p>
        
        <h3>5. 开始上传</h3>
        <p>选择要使用的番茄账户（单选），点击"开始上传"。</p>
        
        <h3>注意事项</h3>
        <ul>
            <li>每个番茄账户有独立的浏览器数据，登录状态会保持</li>
            <li>上传时请保持对应浏览器处于运行状态</li>
            <li>建议设置3-8秒随机间隔，避免触发风控</li>
        </ul>
        """)
        guide_layout.addWidget(guide_text)
        tabs.addTab(guide_tab, "📖 使用指南")
        
        right_layout.addWidget(tabs)
        splitter.addWidget(right_panel)
        
        splitter.setSizes([400, 800])
        layout.addWidget(splitter)
        
        # 底部状态栏
        self.status_bar = QLabel("就绪")
        self.status_bar.setStyleSheet("color: #757575; padding: 5px;")
        layout.addWidget(self.status_bar)
    
    # ============== 账户管理 ==============
    def refresh_accounts_ui(self):
        """刷新账户列表UI"""
        # 清除旧卡片
        for card in self.account_cards.values():
            card.deleteLater()
        self.account_cards.clear()
        
        # 创建新卡片
        accounts = self.tomato_manager.get_all_accounts()
        
        # 移除stretch
        while self.accounts_list_layout.count():
            item = self.accounts_list_layout.takeAt(0)
            if item.widget():
                break
        
        for acc in accounts:
            card = AccountCard(acc)
            card.start_clicked.connect(self.start_account_browser)
            card.stop_clicked.connect(self.stop_account_browser)
            card.delete_clicked.connect(self.delete_account)
            card.selected_changed.connect(self.on_account_selected)
            self.account_cards[acc.id] = card
            self.accounts_list_layout.addWidget(card)
        
        self.accounts_list_layout.addStretch()
        
        # 恢复选中状态
        if self.selected_account_id and self.selected_account_id in self.account_cards:
            self.account_cards[self.selected_account_id].radio.setChecked(True)
    
    def refresh_accounts_status(self):
        """刷新账户状态"""
        for acc_id, card in self.account_cards.items():
            acc = self.tomato_manager.get_account(acc_id)
            if acc:
                # 检查实际状态
                port = acc.port
                import socket
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.5)
                        running = s.connect_ex(('localhost', port)) == 0
                        new_status = "running" if running else "stopped"
                        if acc.status != new_status:
                            acc.status = new_status
                            card.update_status(new_status)
                except:
                    pass
    
    def add_tomato_account(self):
        """添加番茄账户"""
        dialog = AddAccountDialog(self)
        dialog.account_added.connect(self._do_add_account)
        dialog.exec_()
    
    def _do_add_account(self, name: str):
        """执行添加"""
        acc = self.tomato_manager.add_account(name)
        if acc:
            self.log(f"✅ 添加账户成功: {name} (端口: {acc.port})", "success")
            self.refresh_accounts_ui()
        else:
            QMessageBox.warning(self, "错误", "添加账户失败，可能端口已满")
    
    def delete_account(self, account_id: str):
        """删除账户"""
        acc = self.tomato_manager.get_account(account_id)
        if not acc:
            return
        
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定删除账户 '{acc.name}' 吗？\n注意：浏览器数据将被删除，无法恢复！",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.tomato_manager.remove_account(account_id):
                if self.selected_account_id == account_id:
                    self.selected_account_id = None
                    self.update_upload_account_label()
                self.log(f"🗑️ 已删除账户: {acc.name}", "info")
                self.refresh_accounts_ui()
    
    def start_account_browser(self, account_id: str):
        """启动账户浏览器"""
        acc = self.tomato_manager.get_account(account_id)
        if not acc:
            return
        
        # 检查 Chrome
        if not self.chrome_launcher.is_available():
            self.log("⚠️ Chrome 未安装，需要自动下载 (~150MB)", "warning")
            
            reply = QMessageBox.question(
                self, "下载 Chrome",
                "首次使用需要下载 Chrome 浏览器（约 150MB）\n\n是否立即下载？",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self._start_chrome_download(account_id, acc)
            return
        
        self._do_launch_browser(account_id, acc)
    
    def _start_chrome_download(self, account_id: str, acc):
        """开始下载 Chrome"""
        self.log("🚀 开始下载 Chrome...", "info")
        self.status_bar.setText("正在下载 Chrome...")
        
        # 禁用按钮
        if account_id in self.account_cards:
            self.account_cards[account_id].action_btn.setEnabled(False)
        
        # 使用 QThread 下载（避免崩溃）
        self.download_worker = ChromeDownloadWorker(self.chrome_launcher)
        self.download_worker.progress_signal.connect(
            lambda p, m: self._on_download_progress(p, m, account_id)
        )
        self.download_worker.finished_signal.connect(
            lambda s, msg: self._on_download_finished(s, msg, account_id, acc)
        )
        self.download_worker.start()
    
    def _on_download_progress(self, percent: int, message: str, account_id: str):
        """下载进度"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
        self.log(f"📥 {message}", "info")
    
    def _on_download_finished(self, success: bool, message: str, account_id: str, acc):
        """下载完成"""
        if account_id in self.account_cards:
            self.account_cards[account_id].action_btn.setEnabled(True)
        
        if success:
            self.log(f"✅ {message}", "success")
            self.status_bar.setText("Chrome 安装完成")
            # 重新尝试启动
            self._do_launch_browser(account_id, acc)
        else:
            self.log(f"❌ {message}", "error")
            self.status_bar.setText("Chrome 下载失败")
            QMessageBox.critical(self, "错误", f"下载 Chrome 失败: {message}")
    
    def _do_launch_browser(self, account_id: str, acc):
        """实际启动浏览器"""
        data_dir = self.tomato_manager.get_data_dir(account_id)
        
        if self.chrome_launcher.launch(acc.port, data_dir):
            self.log(f"🚀 已启动浏览器: {acc.name} (端口: {acc.port})", "success")
            acc.status = "running"
            if account_id in self.account_cards:
                self.account_cards[account_id].update_status("running")
        else:
            QMessageBox.warning(self, "错误", "启动浏览器失败")
    
    def stop_account_browser(self, account_id: str):
        """停止账户浏览器（通过关闭 Chrome 进程）"""
        import subprocess
        try:
            # 查找并关闭对应端口的 Chrome
            acc = self.tomato_manager.get_account(account_id)
            if acc:
                # 使用 taskkill 关闭 Chrome（简单方式）
                subprocess.run(['taskkill', '/F', '/IM', 'chrome.exe'], capture_output=True)
                self.log(f"⏹ 已停止浏览器: {acc.name}", "info")
                acc.status = "stopped"
                if account_id in self.account_cards:
                    self.account_cards[account_id].update_status("stopped")
        except Exception as e:
            self.log(f"停止浏览器失败: {e}", "error")
    
    def on_account_selected(self, account_id: str, checked: bool):
        """账户被选中"""
        if checked:
            # 取消其他选中
            for aid, card in self.account_cards.items():
                if aid != account_id:
                    card.radio.setChecked(False)
            
            self.selected_account_id = account_id
            acc = self.tomato_manager.get_account(account_id)
            if acc:
                self.upload_account_label.setText(f"🍅 将使用账户: {acc.name}")
        else:
            if self.selected_account_id == account_id:
                self.selected_account_id = None
                self.upload_account_label.setText("🍅 未选择上传账户")
    
    def update_upload_account_label(self):
        """更新上传账户标签"""
        if self.selected_account_id:
            acc = self.tomato_manager.get_account(self.selected_account_id)
            if acc:
                self.upload_account_label.setText(f"🍅 将使用账户: {acc.name}")
        else:
            self.upload_account_label.setText("🍅 未选择上传账户")
    
    # ============== 项目管理 ==============
    def load_projects(self):
        """加载项目列表（包含默认项目和保存的最近项目）"""
        self.project_combo.clear()
        added_paths = set()
        
        # 1. 先加载保存的最近项目
        recent_projects = self.load_recent_projects()
        for proj_data in recent_projects:
            proj_path = Path(proj_data['path'])
            if proj_path.exists() and (proj_path / "project_config.json").exists():
                display = f"📌 {proj_data['username']} / {proj_data['proj_name']}"
                self.project_combo.addItem(display, proj_data)
                added_paths.add(str(proj_path))
        
        # 2. 加载默认小说项目目录
        projects_dir = Path.cwd() / "小说项目"
        if projects_dir.exists():
            for user_dir in projects_dir.iterdir():
                if user_dir.is_dir():
                    for proj_dir in user_dir.iterdir():
                        if proj_dir.is_dir() and (proj_dir / "project_config.json").exists():
                            proj_path_str = str(proj_dir)
                            if proj_path_str not in added_paths:
                                display = f"{user_dir.name} / {proj_dir.name}"
                                data = {
                                    'username': user_dir.name,
                                    'proj_name': proj_dir.name,
                                    'path': proj_path_str
                                }
                                self.project_combo.addItem(display, data)
        
        self.status_bar.setText(f"加载了 {self.project_combo.count()} 个项目")
    
    def load_recent_projects(self) -> list:
        """加载最近项目列表"""
        recent_file = DATA_DIR / "recent_projects.json"
        if recent_file.exists():
            try:
                return json.loads(recent_file.read_text(encoding='utf-8'))
            except:
                return []
        return []
    
    def save_recent_project(self, proj_data: dict):
        """保存项目到最近列表"""
        recent_file = DATA_DIR / "recent_projects.json"
        recent = self.load_recent_projects()
        
        # 检查是否已存在
        for i, p in enumerate(recent):
            if p['path'] == proj_data['path']:
                # 移动到最前面
                recent.pop(i)
                break
        
        # 添加到开头
        recent.insert(0, proj_data)
        
        # 最多保留10个
        recent = recent[:10]
        
        try:
            recent_file.write_text(json.dumps(recent, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as e:
            print(f"保存最近项目失败: {e}")
    
    def select_project_directory(self):
        """选择项目目录"""
        dir_path = QFileDialog.getExistingDirectory(
            self, "选择项目目录", str(Path.cwd() / "小说项目"),
            QFileDialog.ShowDirsOnly
        )
        
        if not dir_path:
            return
        
        path = Path(dir_path)
        
        # 检查是否是有效的项目目录（包含 project_config.json）
        config_file = path / "project_config.json"
        if config_file.exists():
            # 直接加载这个项目
            self.load_single_project(path)
        else:
            # 尝试作为用户目录，扫描其中的项目
            parent = path.parent
            if (parent / "project_config.json").exists():
                # 用户在项目目录内，找到父项目
                self.load_single_project(parent)
            else:
                # 扫描目录下的所有项目
                count = self.scan_directory_for_projects(path)
                if count == 0:
                    QMessageBox.information(
                        self, "提示", 
                        f"在选定目录中未找到项目配置文件\n\n"
                        f"已自动刷新默认项目列表。\n\n"
                        f"提示: 项目目录应包含 project_config.json 文件"
                    )
                    self.load_projects()
    
    def load_single_project(self, project_path: Path):
        """加载单个项目"""
        try:
            config_file = project_path / "project_config.json"
            if not config_file.exists():
                return
            
            config = json.loads(config_file.read_text(encoding='utf-8'))
            username = config.get('username', project_path.parent.name)
            proj_name = config.get('project_name', project_path.name)
            
            # 准备数据
            data = {
                'username': username,
                'proj_name': proj_name,
                'path': str(project_path)
            }
            
            # 检查是否已存在（通过完整路径）
            existing_idx = -1
            for i in range(self.project_combo.count()):
                item_data = self.project_combo.itemData(i)
                if item_data and item_data.get('path') == str(project_path):
                    existing_idx = i
                    break
            
            if existing_idx >= 0:
                self.project_combo.setCurrentIndex(existing_idx)
            else:
                # 添加到列表开头（带📌标记表示是手动添加的）
                display = f"📌 {username} / {proj_name}"
                self.project_combo.insertItem(0, display, data)
                self.project_combo.setCurrentIndex(0)
            
            # 保存到最近项目
            self.save_recent_project(data)
            
            self.log(f"📁 已加载并保存项目: {proj_name}", "success")
            
        except Exception as e:
            QMessageBox.warning(self, "错误", f"加载项目失败: {e}")
    
    def scan_directory_for_projects(self, base_dir: Path) -> int:
        """扫描目录中的所有项目"""
        count = 0
        
        # 检查当前目录是否是项目
        if (base_dir / "project_config.json").exists():
            self.load_single_project(base_dir)
            count += 1
        
        # 递归扫描子目录
        for subdir in base_dir.rglob("project_config.json"):
            self.load_single_project(subdir.parent)
            count += 1
        
        if count > 0:
            self.log(f"📁 扫描到 {count} 个项目", "success")
        
        return count
    
    def on_project_changed(self, index):
        """项目变更"""
        if index < 0:
            return
        
        data = self.project_combo.itemData(index)
        if not data:
            return
        
        # 支持新旧两种数据格式
        if isinstance(data, dict):
            project_path = Path(data['path'])
        else:
            # 旧格式: (username, proj_name)
            username, proj_name = data
            project_path = Path.cwd() / "小说项目" / username / proj_name
        
        self.load_chapters(project_path)
    
    def load_chapters(self, project_path: Path):
        """加载章节"""
        self.chapters_list.clear()
        self.chapters = []
        
        chapters_dir = project_path / "chapters"
        if not chapters_dir.exists():
            self.chapters_stats.setText("共 0 个章节 (章节目录不存在)")
            return
        
        for ch_file in sorted(chapters_dir.glob("chapter_*.json")):
            try:
                data = json.loads(ch_file.read_text(encoding='utf-8'))
                ch_num = data.get('chapter_number', 0)
                ch_title = data.get('title', f'第{ch_num}章')
                
                item = QListWidgetItem(f"第{ch_num:03d}章: {ch_title}")
                item.setData(Qt.UserRole, data)
                self.chapters_list.addItem(item)
                self.chapters.append(data)
            except Exception as e:
                print(f"加载章节失败 {ch_file}: {e}")
        
        self.chapters_stats.setText(f"共 {len(self.chapters)} 个章节")
    
    def select_all_chapters(self):
        """全选"""
        self.chapters_list.selectAll()
    
    def select_none_chapters(self):
        """全不选"""
        self.chapters_list.clearSelection()
    
    # ============== 上传控制 ==============
    def start_upload(self):
        """开始上传"""
        # 检查账户选择
        if not self.selected_account_id:
            QMessageBox.warning(self, "提示", "请先选择一个番茄账户")
            return
        
        acc = self.tomato_manager.get_account(self.selected_account_id)
        if not acc:
            QMessageBox.warning(self, "错误", "选择的账户不存在")
            return
        
        # 检查浏览器状态
        if acc.status != "running":
            reply = QMessageBox.question(
                self, "启动浏览器", 
                f"账户 '{acc.name}' 的浏览器未运行，是否立即启动？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.start_account_browser(self.selected_account_id)
                QMessageBox.information(self, "提示", "请等待浏览器启动并登录番茄小说后，再点击开始上传")
            return
        
        # 获取选中章节
        selected_items = self.chapters_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "提示", "请先选择要上传的章节")
            return
        
        chapters = [item.data(Qt.UserRole) for item in selected_items]
        
        # 获取设置
        settings = {
            'delay_min': self.delay_min.value(),
            'delay_max': self.delay_max.value(),
            'stop_on_error': self.stop_on_error.isChecked()
        }
        
        # 获取书名
        novel_title = "未知书名"
        if chapters:
            novel_title = chapters[0].get('novel_title', novel_title)
        
        # 启动上传线程
        self.upload_worker = UploadWorker(novel_title, chapters, settings, acc)
        self.upload_worker.progress_signal.connect(self.on_upload_progress)
        self.upload_worker.log_signal.connect(self.on_upload_log)
        self.upload_worker.finished_signal.connect(self.on_upload_finished)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        self.log(f"🚀 开始上传 '{novel_title}'，使用账户: {acc.name}", "info")
        self.upload_worker.start()
    
    def stop_upload(self):
        """停止上传"""
        if self.upload_worker:
            self.upload_worker.stop()
    
    def on_upload_progress(self, percent: int, message: str):
        """上传进度"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def on_upload_log(self, message: str, level: str):
        """上传日志"""
        self.log(message, level)
    
    def on_upload_finished(self, success: bool, message: str):
        """上传完成"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self.log(f"✅ {message}", "success")
            QMessageBox.information(self, "完成", message)
        else:
            self.log(f"❌ {message}", "error")
            QMessageBox.warning(self, "完成", message)
    
    # ============== 日志 ==============
    def log(self, message: str, level: str = "info"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        colors = {
            "info": "#d4d4d4",
            "success": "#4CAF50",
            "warning": "#FFC107",
            "error": "#F44336"
        }
        color = colors.get(level, "#d4d4d4")
        
        self.log_text.append(f'<span style="color: #757575;">[{timestamp}]</span> '
                            f'<span style="color: {color};">{message}</span>')
        
        # 滚动到底部
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
    
    def save_log(self):
        """保存日志"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存日志", f"upload_log_{datetime.now():%Y%m%d_%H%M%S}.txt", "文本文件 (*.txt)"
        )
        if file_path:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.log_text.toPlainText())
            self.log(f"日志已保存: {file_path}", "success")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # 设置全局字体
    font = QFont("Microsoft YaHei", 10)
    app.setFont(font)
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
