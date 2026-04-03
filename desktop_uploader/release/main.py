#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱小说发布助手 - 统一的桌面GUI版本
支持多平台配置：番茄小说、起点、纵横等

使用方法:
1. 运行源码: python main.py
2. 运行EXE: 双击 NovelPublisher.exe

官网: https://novel-ai.online/
"""

import sys
import os
import json
import time
import random
import threading
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# 添加本地库路径（打包时使用）
_current_dir = os.path.dirname(os.path.abspath(__file__))
_libs_path = os.path.join(_current_dir, 'libs')
if os.path.exists(_libs_path):
    sys.path.insert(0, _libs_path)

# 添加项目路径，复用现有代码
sys.path.insert(0, os.path.join(_current_dir, '..'))
sys.path.insert(0, os.path.join(_current_dir, '..', 'src'))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QFileDialog, QMessageBox, QGroupBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QTabWidget, QSplitter,
    QSystemTrayIcon, QMenu, QAction, QStyle
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QColor

# 导入上传核心模块
try:
    from chrome_manager import ChromeManager
    from fanqie_uploader_impl import FanqieUploaderImpl
    UPLOADER_AVAILABLE = True
except ImportError as e:
    print(f"[ERROR] Failed to import uploader modules: {e}")
    UPLOADER_AVAILABLE = False
    ChromeManager = None
    FanqieUploaderImpl = None

# 导入样式
try:
    from styles import get_application_style, PRIMARY_COLOR, SUCCESS_COLOR, ERROR_COLOR, WARNING_COLOR, TEXT_SECONDARY
except ImportError:
    # 如果样式文件不存在，使用空样式
    def get_application_style():
        return ""
    PRIMARY_COLOR = "#1976D2"
    SUCCESS_COLOR = "#4CAF50"
    ERROR_COLOR = "#F44336"
    WARNING_COLOR = "#FFC107"
    TEXT_SECONDARY = "#757575"


class UploadWorker(QThread):
    """上传工作线程 - 防止UI卡顿"""
    
    # 信号定义
    progress_signal = pyqtSignal(int, str)  # 进度百分比, 消息
    log_signal = pyqtSignal(str, str)  # 消息, 级别(info/warning/error)
    chapter_status_signal = pyqtSignal(int, str)  # 章节索引, 状态
    finished_signal = pyqtSignal(bool, str)  # 成功/失败, 消息
    browser_started_signal = pyqtSignal(bool, str)  # 浏览器启动状态
    login_required_signal = pyqtSignal()  # 需要用户登录
    
    def __init__(self, novel_title: str, chapters: List[Dict], settings: Dict, config: Dict = None):
        super().__init__()
        self.novel_title = novel_title
        self.chapters = chapters
        self.settings = settings
        self.config = config or {}
        self.is_running = True
        self.current_index = 0
        self.chrome_manager = None
        self.uploader = None
        
    def run(self):
        """执行上传"""
        try:
            if not UPLOADER_AVAILABLE:
                self.log_signal.emit("上传模块未正确加载", "error")
                self.finished_signal.emit(False, "模块加载失败")
                return
            
            # 第1步：启动 Chrome
            self.log_signal.emit("🚀 正在启动 Chrome...", "info")
            self.chrome_manager = ChromeManager()
            
            if not self.chrome_manager.start_chrome(progress_callback=self._on_chrome_progress):
                self.log_signal.emit("❌ Chrome 启动失败", "error")
                self.log_signal.emit("💡 解决方案：访问官网 https://novel-ai.online/ 获取帮助", "info")
                self.finished_signal.emit(False, "Chrome 启动失败，请检查网络连接或手动安装 Chrome")
                return
            
            self.browser_started_signal.emit(True, "Chrome 已启动")
            self.log_signal.emit("✅ Chrome 启动成功，请登录番茄小说", "success")
            
            # 第2步：连接 Chrome 并上传
            self.uploader = FanqieUploaderImpl(
                novel_title=self.novel_title,
                progress_callback=self._on_progress,
                log_callback=self._on_log
            )
            
            # 连接 Chrome
            if not self.uploader.connect_chrome():
                self.finished_signal.emit(False, "无法连接到 Chrome")
                return
            
            # 检查登录
            if not self.uploader.check_login():
                self.login_required_signal.emit()
                self.log_signal.emit("⏳ 等待用户登录番茄小说...", "warning")
                if not self.uploader.wait_for_login(timeout=120):
                    self.finished_signal.emit(False, "登录超时")
                    return
            
            # 查找书籍
            if not self.uploader.find_book():
                self.log_signal.emit("⚠️ 未找到书籍，请先手动创建", "warning")
                self.finished_signal.emit(False, "未找到书籍")
                return
            
            # 上传章节
            result = self.uploader.upload_chapters(
                self.chapters,
                delay_min=self.settings.get('delay_min', 3),
                delay_max=self.settings.get('delay_max', 8),
                stop_on_error=self.settings.get('stop_on_error', False)
            )
            
            # 完成
            if result['failed'] == 0:
                self.finished_signal.emit(True, f"✅ 全部上传成功！共 {result['total']} 章")
            else:
                self.finished_signal.emit(False, f"⚠️ 上传完成：成功 {result['success']}/{result['total']} 章，失败 {result['failed']} 章")
            
        except Exception as e:
            self.log_signal.emit(f"上传异常: {str(e)}", "error")
            self.finished_signal.emit(False, str(e))
        finally:
            if self.uploader:
                self.uploader.close()
    
    def _on_chrome_progress(self, percent: int, message: str):
        """Chrome启动进度回调"""
        self.progress_signal.emit(int(percent * 0.2), message)  # Chrome启动占20%进度
    
    def _on_progress(self, percent: int, message: str):
        """上传进度回调"""
        # 上传占80%进度（20-100）
        adjusted_percent = 20 + int(percent * 0.8)
        self.progress_signal.emit(adjusted_percent, message)
        
        # 更新章节状态
        if "第" in message and "章" in message:
            try:
                import re
                match = re.search(r'第(\d+)章', message)
                if match:
                    ch_num = int(match.group(1))
                    for i, ch in enumerate(self.chapters):
                        if ch.get('chapter_number', ch.get('number')) == ch_num:
                            if "成功" in message:
                                self.chapter_status_signal.emit(i, "success")
                            elif "失败" in message:
                                self.chapter_status_signal.emit(i, "error")
                            break
            except:
                pass
    
    def _on_log(self, message: str, level: str):
        """日志回调"""
        self.log_signal.emit(message, level)
    
    def stop(self):
        """停止上传"""
        self.is_running = False
        self.log_signal.emit("正在停止上传...", "warning")
        if self.uploader:
            self.uploader.stop()


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("大文娱小说发布助手 v1.2")
        self.setGeometry(100, 100, 1280, 840)
        
        # 应用现代化样式
        self.setStyleSheet(get_application_style())
        
        # 数据
        self.current_project = None
        self.chapters = []
        self.upload_worker = None
        self.config = self.load_config()
        
        self.init_ui()
        self.init_tray()
        self.load_projects()
        
    def init_ui(self):
        """初始化界面"""
        # 中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # === 标题区域 ===
        title_layout = QHBoxLayout()
        title_layout.setSpacing(15)
        
        # Logo 和标题
        title_container = QHBoxLayout()
        title_container.setSpacing(10)
        
        # 使用 QLabel 显示 Emoji 作为图标
        icon_label = QLabel("🚀")
        icon_font = QFont("Segoe UI Emoji", 28)
        icon_label.setFont(icon_font)
        title_container.addWidget(icon_label)
        
        title_text_layout = QVBoxLayout()
        title_text_layout.setSpacing(2)
        
        title_label = QLabel("大文娱小说发布助手")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet(f"color: {PRIMARY_COLOR};")
        title_text_layout.addWidget(title_label)
        
        subtitle_label = QLabel("智能 · 高效 · 多平台支持")
        subtitle_font = QFont()
        subtitle_font.setPointSize(10)
        subtitle_label.setFont(subtitle_font)
        subtitle_label.setStyleSheet("color: #757575;")
        title_text_layout.addWidget(subtitle_label)
        
        title_container.addLayout(title_text_layout)
        title_layout.addLayout(title_container)
        
        title_layout.addStretch()
        
        # 平台选择（带标签）
        platform_container = QHBoxLayout()
        platform_container.setSpacing(8)
        
        platform_icon = QLabel("🌐")
        platform_font = QFont("Segoe UI Emoji", 12)
        platform_icon.setFont(platform_font)
        platform_container.addWidget(platform_icon)
        
        platform_label = QLabel("发布平台:")
        platform_label.setStyleSheet("font-weight: 600; color: #424242;")
        platform_container.addWidget(platform_label)
        
        self.platform_combo = QComboBox()
        self.platform_combo.setMinimumWidth(160)
        self.platform_combo.addItem("🍅 番茄小说", "fanqie")
        self.platform_combo.addItem("📖 起点中文网", "qidian")
        self.platform_combo.addItem("✏️ 纵横中文网", "zongheng")
        platform_container.addWidget(self.platform_combo)
        
        # 官网链接按钮
        website_btn = QPushButton("🌐 官网")
        website_btn.setToolTip("访问官方网站: https://novel-ai.online/")
        website_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {PRIMARY_COLOR};
                border: 1px solid {PRIMARY_COLOR};
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: 500;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background-color: #E3F2FD;
            }}
        """)
        website_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://novel-ai.online/")))
        platform_container.addWidget(website_btn)
        
        title_layout.addLayout(platform_container)
        
        main_layout.addLayout(title_layout)
        
        # === 分割器 ===
        splitter = QSplitter(Qt.Horizontal)
        
        # === 左侧面板 ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # 项目选择组
        project_group = QGroupBox("📁 项目选择")
        project_layout = QVBoxLayout()
        project_layout.setSpacing(12)
        
        # 项目选择提示
        project_hint = QLabel("选择要发布的小说项目：")
        project_hint.setStyleSheet("color: #757575; font-size: 12px;")
        project_layout.addWidget(project_hint)
        
        self.project_combo = QComboBox()
        self.project_combo.setMinimumHeight(36)
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        project_layout.addWidget(self.project_combo)
        
        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        
        refresh_btn = QPushButton("🔄 刷新列表")
        refresh_btn.setToolTip("重新扫描项目目录")
        refresh_btn.clicked.connect(self.load_projects)
        btn_layout.addWidget(refresh_btn)
        
        import_btn = QPushButton("📂 导入配置")
        import_btn.setToolTip("从文件导入项目配置")
        import_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {PRIMARY_COLOR};
                border: 2px solid {PRIMARY_COLOR};
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #E3F2FD;
            }}
        """)
        import_btn.clicked.connect(self.import_config)
        btn_layout.addWidget(import_btn)
        
        project_layout.addLayout(btn_layout)
        project_group.setLayout(project_layout)
        left_layout.addWidget(project_group)
        
        # 章节列表组
        chapters_group = QGroupBox("📋 章节列表")
        chapters_layout = QVBoxLayout()
        chapters_layout.setSpacing(10)
        
        # 统计信息
        self.chapters_stats_label = QLabel("共 0 个章节")
        self.chapters_stats_label.setStyleSheet("color: #757575; font-size: 12px;")
        chapters_layout.addWidget(self.chapters_stats_label)
        
        # 章节列表
        self.chapters_list = QListWidget()
        self.chapters_list.setSelectionMode(QListWidget.MultiSelection)
        self.chapters_list.setMinimumHeight(300)
        chapters_layout.addWidget(self.chapters_list)
        
        # 全选/反选按钮
        select_layout = QHBoxLayout()
        select_layout.setSpacing(10)
        
        select_all_btn = QPushButton("☑️ 全选")
        select_all_btn.setToolTip("选择所有章节")
        select_all_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #E8F5E9;
                color: {SUCCESS_COLOR};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #C8E6C9;
            }}
        """)
        select_all_btn.clicked.connect(self.select_all_chapters)
        select_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("⬜ 全不选")
        select_none_btn.setToolTip("取消所有选择")
        select_none_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFEBEE;
                color: {ERROR_COLOR};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #FFCDD2;
            }}
        """)
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
        
        # 创建标签页
        tabs = QTabWidget()
        
        # === 上传控制页 ===
        upload_tab = QWidget()
        upload_layout = QVBoxLayout(upload_tab)
        
        # 设置组
        settings_group = QGroupBox("⚙️ 上传设置")
        settings_layout = QVBoxLayout()
        settings_layout.setSpacing(15)
        
        # 风控设置卡片
        fengkong_card = QWidget()
        fengkong_card.setStyleSheet("""
            QWidget {
                background-color: #FFF3E0;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        fengkong_layout = QVBoxLayout(fengkong_card)
        fengkong_layout.setContentsMargins(12, 12, 12, 12)
        
        fengkong_title = QLabel("🛡️ 风控策略")
        fengkong_title.setStyleSheet("font-weight: 700; color: #E65100; font-size: 13px;")
        fengkong_layout.addWidget(fengkong_title)
        
        fengkong_desc = QLabel("设置上传间隔，模拟人工操作，避免触发平台风控")
        fengkong_desc.setStyleSheet("color: #757575; font-size: 11px;")
        fengkong_desc.setWordWrap(True)
        fengkong_layout.addWidget(fengkong_desc)
        
        # 延迟设置
        delay_layout = QHBoxLayout()
        delay_layout.setSpacing(10)
        
        delay_icon = QLabel("⏱️")
        delay_font = QFont("Segoe UI Emoji", 14)
        delay_icon.setFont(delay_font)
        delay_layout.addWidget(delay_icon)
        
        delay_label = QLabel("上传间隔:")
        delay_label.setStyleSheet("font-weight: 500;")
        delay_layout.addWidget(delay_label)
        
        self.delay_min_spin = QDoubleSpinBox()
        self.delay_min_spin.setRange(0.5, 60)
        self.delay_min_spin.setValue(self.config.get('delay_min', 3))
        self.delay_min_spin.setDecimals(1)
        self.delay_min_spin.setSuffix(" 秒")
        self.delay_min_spin.setMinimumWidth(80)
        delay_layout.addWidget(self.delay_min_spin)
        
        delay_to_label = QLabel("~")
        delay_to_label.setStyleSheet("font-weight: 500; color: #757575;")
        delay_layout.addWidget(delay_to_label)
        
        self.delay_max_spin = QDoubleSpinBox()
        self.delay_max_spin.setRange(1, 120)
        self.delay_max_spin.setValue(self.config.get('delay_max', 8))
        self.delay_max_spin.setDecimals(1)
        self.delay_max_spin.setSuffix(" 秒")
        self.delay_max_spin.setMinimumWidth(80)
        delay_layout.addWidget(self.delay_max_spin)
        
        delay_layout.addStretch()
        fengkong_layout.addLayout(delay_layout)
        settings_layout.addWidget(fengkong_card)
        
        # 选项卡片
        options_card = QWidget()
        options_card.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        options_layout = QVBoxLayout(options_card)
        options_layout.setContentsMargins(12, 12, 12, 12)
        options_layout.setSpacing(10)
        
        # 错误处理
        self.stop_on_error_check = QCheckBox("❌ 上传失败时自动停止")
        self.stop_on_error_check.setChecked(self.config.get('stop_on_error', False))
        self.stop_on_error_check.setStyleSheet("font-size: 13px;")
        options_layout.addWidget(self.stop_on_error_check)
        
        # 后台运行
        self.minimize_to_tray_check = QCheckBox("🔄 上传时最小化到系统托盘")
        self.minimize_to_tray_check.setChecked(True)
        self.minimize_to_tray_check.setStyleSheet("font-size: 13px;")
        options_layout.addWidget(self.minimize_to_tray_check)
        
        settings_layout.addWidget(options_card)
        
        settings_group.setLayout(settings_layout)
        upload_layout.addWidget(settings_group)
        
        # 进度组
        progress_group = QGroupBox("📊 上传进度")
        progress_layout = QVBoxLayout()
        progress_layout.setSpacing(15)
        
        # 状态卡片
        status_card = QWidget()
        status_card.setStyleSheet(f"""
            QWidget {{
                background-color: #E3F2FD;
                border-radius: 8px;
                border-left: 4px solid {PRIMARY_COLOR};
                padding: 12px;
            }}
        """)
        status_card_layout = QHBoxLayout(status_card)
        status_card_layout.setContentsMargins(12, 8, 12, 8)
        
        self.status_icon = QLabel("⏳")
        status_icon_font = QFont("Segoe UI Emoji", 20)
        self.status_icon.setFont(status_icon_font)
        status_card_layout.addWidget(self.status_icon)
        
        self.status_label = QLabel("准备就绪，请选择项目和章节后开始上传")
        self.status_label.setStyleSheet("font-size: 14px; font-weight: 500; color: #1565C0;")
        status_card_layout.addWidget(self.status_label, 1)
        
        progress_layout.addWidget(status_card)
        
        # 进度条
        progress_bar_layout = QVBoxLayout()
        progress_bar_label = QLabel("总体进度:")
        progress_bar_label.setStyleSheet("font-weight: 500; color: #757575;")
        progress_bar_layout.addWidget(progress_bar_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p% (%v/%m)")
        self.progress_bar.setMinimumHeight(24)
        progress_bar_layout.addWidget(self.progress_bar)
        
        progress_layout.addLayout(progress_bar_layout)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(15)
        
        self.start_btn = QPushButton("🚀 开始上传")
        self.start_btn.setMinimumHeight(48)
        self.start_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {SUCCESS_COLOR};
                color: white;
                font-size: 15px;
                font-weight: 700;
                padding: 12px 32px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #66BB6A;
            }}
            QPushButton:pressed {{
                background-color: #388E3C;
            }}
            QPushButton:disabled {{
                background-color: #C8E6C9;
                color: #81C784;
            }}
        """)
        self.start_btn.clicked.connect(self.start_upload)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止上传")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setMinimumHeight(48)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {ERROR_COLOR};
                color: white;
                font-size: 15px;
                font-weight: 700;
                padding: 12px 32px;
                border-radius: 8px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: #EF5350;
            }}
            QPushButton:pressed {{
                background-color: #D32F2F;
            }}
            QPushButton:disabled {{
                background-color: #FFCDD2;
                color: #EF9A9A;
            }}
        """)
        self.stop_btn.clicked.connect(self.stop_upload)
        btn_layout.addWidget(self.stop_btn)
        
        progress_layout.addLayout(btn_layout)
        
        progress_group.setLayout(progress_layout)
        upload_layout.addWidget(progress_group)
        
        # 日志组
        log_group = QGroupBox("📝 运行日志")
        log_layout = QVBoxLayout()
        log_layout.setSpacing(10)
        
        # 日志说明
        log_hint = QLabel("实时显示上传状态和错误信息")
        log_hint.setStyleSheet("color: #757575; font-size: 11px;")
        log_layout.addWidget(log_hint)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_font = QFont("JetBrains Mono", 10)
        log_font.setStyleHint(QFont.Monospace)
        self.log_text.setFont(log_font)
        self.log_text.setMinimumHeight(200)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #263238;
                color: #EEFFFF;
                border: none;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        log_layout.addWidget(self.log_text)
        
        # 日志按钮
        log_btn_layout = QHBoxLayout()
        log_btn_layout.setSpacing(10)
        
        clear_log_btn = QPushButton("🗑️ 清空日志")
        clear_log_btn.setToolTip("清空当前日志内容")
        clear_log_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #F5F5F5;
                color: {TEXT_SECONDARY};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 500;
            }}
            QPushButton:hover {{
                background-color: #EEEEEE;
            }}
        """)
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_btn_layout.addWidget(clear_log_btn)
        
        save_log_btn = QPushButton("💾 保存日志")
        save_log_btn.setToolTip("将日志保存到文件")
        save_log_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #E3F2FD;
                color: {PRIMARY_COLOR};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: #BBDEFB;
            }}
        """)
        save_log_btn.clicked.connect(self.save_log)
        log_btn_layout.addWidget(save_log_btn)
        
        log_btn_layout.addStretch()
        
        # 官网链接
        website_link = QLabel('<a href="https://novel-ai.online/" style="color: #1976D2; text-decoration: none;">🌐 访问官网获取更多帮助</a>')
        website_link.setOpenExternalLinks(True)
        website_link.setStyleSheet("font-size: 12px;")
        log_btn_layout.addWidget(website_link)
        
        log_layout.addLayout(log_btn_layout)
        
        log_group.setLayout(log_layout)
        upload_layout.addWidget(log_group)
        
        tabs.addTab(upload_tab, "📤 上传控制")
        
        # === 账号设置页 ===
        account_tab = QWidget()
        account_layout = QVBoxLayout(account_tab)
        account_layout.setSpacing(20)
        
        # 使用说明卡片
        guide_card = QWidget()
        guide_card.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }
        """)
        guide_layout = QVBoxLayout(guide_card)
        guide_layout.setContentsMargins(24, 24, 24, 24)
        guide_layout.setSpacing(16)
        
        # 标题
        guide_title = QLabel("📖 使用指南")
        guide_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #212121;")
        guide_layout.addWidget(guide_title)
        
        # 步骤
        steps_text = QLabel("""
        <ol style="line-height: 2; font-size: 13px; color: #424242;">
            <li><b>首次使用</b>：工具会自动检测 Chrome，如未安装会提示下载（约 150MB）</li>
            <li><b>选择平台</b>：在顶部下拉框选择要发布的平台（番茄/起点/纵横）</li>
            <li><b>登录账号</b>：在打开的 Chrome 中登录对应平台的作者账号</li>
            <li><b>创建书籍</b>：在平台作者中心创建或打开要上传的书籍</li>
            <li><b>选择项目</b>：在本工具中选择对应的小说项目</li>
            <li><b>开始上传</b>：勾选章节，点击"开始上传"按钮</li>
        </ol>
        """)
        steps_text.setWordWrap(True)
        steps_text.setTextFormat(Qt.RichText)
        guide_layout.addWidget(steps_text)
        
        # 提示
        tip_label = QLabel("💡 提示：登录状态会自动保存，下次无需重复登录")
        tip_label.setStyleSheet("background-color: #E3F2FD; color: #1565C0; padding: 12px; border-radius: 8px; font-size: 12px;")
        guide_layout.addWidget(tip_label)
        
        account_layout.addWidget(guide_card)
        
        # Chrome 说明卡片
        chrome_card = QWidget()
        chrome_card.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }
        """)
        chrome_layout = QVBoxLayout(chrome_card)
        chrome_layout.setContentsMargins(24, 24, 24, 24)
        chrome_layout.setSpacing(16)
        
        chrome_title = QLabel("🌐 关于 Chrome 浏览器")
        chrome_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #212121;")
        chrome_layout.addWidget(chrome_title)
        
        chrome_text = QLabel("""
        <p style="font-size: 13px; color: #424242; line-height: 1.8;">
        本工具使用 Chrome 浏览器进行自动化上传操作。
        </p>
        <ul style="font-size: 13px; color: #424242; line-height: 1.8;">
            <li>如已安装 Chrome，工具会自动检测并使用</li>
            <li>如未安装 Chrome，首次使用会提示下载（约 150MB）</li>
            <li>下载完成后，下次使用无需重复下载</li>
            <li>请保持 Chrome 窗口在后台运行</li>
        </ul>
        """)
        chrome_text.setWordWrap(True)
        chrome_text.setTextFormat(Qt.RichText)
        chrome_layout.addWidget(chrome_text)
        
        account_layout.addWidget(chrome_card)
        
        account_layout.addStretch()
        
        tabs.addTab(account_tab, "📖 使用指南")
        
        # === 关于页 ===
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        about_layout.setSpacing(20)
        
        # 主卡片
        main_card = QWidget()
        main_card.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #1976D2,
                    stop: 1 #1565C0
                );
                border-radius: 16px;
            }
        """)
        main_card_layout = QVBoxLayout(main_card)
        main_card_layout.setContentsMargins(40, 40, 40, 40)
        main_card_layout.setSpacing(20)
        
        # Logo 区域
        logo_label = QLabel("🚀")
        logo_font = QFont("Segoe UI Emoji", 64)
        logo_label.setFont(logo_font)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("color: white;")
        main_card_layout.addWidget(logo_label)
        
        # 标题
        title_label = QLabel("大文娱小说发布助手")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 28px; font-weight: 700; color: white;")
        main_card_layout.addWidget(title_label)
        
        # 版本
        version_label = QLabel("Version 1.2.0")
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("font-size: 14px; color: rgba(255,255,255,0.8);")
        main_card_layout.addWidget(version_label)
        
        # 标语
        slogan_label = QLabel("智能 · 高效 · 多平台支持")
        slogan_label.setAlignment(Qt.AlignCenter)
        slogan_label.setStyleSheet("font-size: 16px; color: rgba(255,255,255,0.9); margin-top: 8px;")
        main_card_layout.addWidget(slogan_label)
        
        about_layout.addWidget(main_card)
        
        # 功能特点卡片
        features_card = QWidget()
        features_card.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }
        """)
        features_layout = QVBoxLayout(features_card)
        features_layout.setContentsMargins(24, 24, 24, 24)
        features_layout.setSpacing(16)
        
        features_title = QLabel("✨ 功能特点")
        features_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #212121;")
        features_layout.addWidget(features_title)
        
        features_grid = QWidget()
        features_grid_layout = QHBoxLayout(features_grid)
        features_grid_layout.setSpacing(20)
        
        features = [
            ("🍅", "多平台支持", "番茄、起点、纵横等"),
            ("🛡️", "智能风控", "模拟人工，安全上传"),
            ("⚡", "批量上传", "自动延迟，后台运行"),
            ("🔄", "断点续传", "失败重试，稳定可靠"),
        ]
        
        for icon, title, desc in features:
            feature_item = QWidget()
            feature_item.setStyleSheet("background-color: #F5F5F5; border-radius: 8px;")
            feature_item_layout = QVBoxLayout(feature_item)
            feature_item_layout.setContentsMargins(16, 16, 16, 16)
            feature_item_layout.setSpacing(4)
            
            item_icon = QLabel(icon)
            item_icon_font = QFont("Segoe UI Emoji", 24)
            item_icon.setFont(item_icon_font)
            item_icon.setAlignment(Qt.AlignCenter)
            feature_item_layout.addWidget(item_icon)
            
            item_title = QLabel(title)
            item_title.setAlignment(Qt.AlignCenter)
            item_title.setStyleSheet("font-weight: 600; color: #212121;")
            feature_item_layout.addWidget(item_title)
            
            item_desc = QLabel(desc)
            item_desc.setAlignment(Qt.AlignCenter)
            item_desc.setStyleSheet("font-size: 11px; color: #757575;")
            feature_item_layout.addWidget(item_desc)
            
            features_grid_layout.addWidget(feature_item)
        
        features_layout.addWidget(features_grid)
        about_layout.addWidget(features_card)
        
        # 官网卡片
        website_card = QWidget()
        website_card.setStyleSheet("""
            QWidget {
                background-color: white;
                border-radius: 12px;
                border: 1px solid #E0E0E0;
            }
        """)
        website_card_layout = QVBoxLayout(website_card)
        website_card_layout.setContentsMargins(24, 24, 24, 24)
        website_card_layout.setSpacing(12)
        
        website_title = QLabel("🌐 官方网站")
        website_title.setStyleSheet("font-size: 16px; font-weight: 700; color: #212121;")
        website_card_layout.addWidget(website_title)
        
        website_text = QLabel("""
        <p style="font-size: 13px; color: #424242; line-height: 1.8;">
        访问官方网站获取更多功能和帮助：<br>
        <a href="https://novel-ai.online/" style="color: #1976D2; font-weight: 600; font-size: 14px;">https://novel-ai.online/</a>
        </p>
        <p style="font-size: 12px; color: #757575; margin-top: 12px;">
        • 最新版本下载<br>
        • 使用教程和文档<br>
        • 技术支持与反馈
        </p>
        """)
        website_text.setWordWrap(True)
        website_text.setTextFormat(Qt.RichText)
        website_text.setOpenExternalLinks(True)
        website_card_layout.addWidget(website_text)
        
        about_layout.addWidget(website_card)
        
        about_layout.addStretch()
        
        tabs.addTab(about_tab, "ℹ️ 关于")
        
        right_layout.addWidget(tabs)
        
        splitter.addWidget(right_panel)
        splitter.setSizes([350, 650])  # 设置初始分割比例
        
        main_layout.addWidget(splitter)
        
        # 状态栏
        self.statusBar().showMessage("就绪")
        
    def init_tray(self):
        """初始化系统托盘"""
        self.tray_icon = QSystemTrayIcon(self)
        
        # 使用系统默认图标
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        # 托盘菜单
        tray_menu = QMenu()
        
        show_action = QAction("显示窗口", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        tray_menu.addSeparator()
        
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(self.quit_application)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_activated)
        self.tray_icon.show()
        
    def on_tray_activated(self, reason):
        """托盘图标被点击"""
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            
    def closeEvent(self, event):
        """关闭事件 - 最小化到托盘"""
        if self.upload_worker and self.upload_worker.isRunning():
            # 上传中，最小化到托盘
            self.hide()
            self.tray_icon.showMessage(
                "上传进行中",
                "程序已最小化到系统托盘，上传将继续在后台运行。",
                QSystemTrayIcon.Information,
                3000
            )
            event.ignore()
        else:
            event.accept()
            
    def quit_application(self):
        """完全退出"""
        if self.upload_worker and self.upload_worker.isRunning():
            reply = QMessageBox.question(
                self, "确认退出",
                "上传正在进行中，确定要退出吗？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.stop_upload()
                QApplication.quit()
        else:
            QApplication.quit()
            
    def load_config(self) -> Dict:
        """加载配置文件"""
        config_file = Path(__file__).parent / "config.json"
        if config_file.exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                pass
        return {
            'delay_min': 3,
            'delay_max': 8,
            'stop_on_error': False
        }
        
    def save_config(self):
        """保存配置"""
        config_file = Path(__file__).parent / "config.json"
        self.config = {
            'delay_min': self.delay_min_spin.value(),
            'delay_max': self.delay_max_spin.value(),
            'stop_on_error': self.stop_on_error_check.isChecked()
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.config, f, indent=2)
            
    def load_projects(self):
        """加载项目列表"""
        self.project_combo.clear()
        
        # 查找小说项目目录
        novel_dirs = [
            Path("小说项目"),
            Path("../小说项目"),
            Path(__file__).parent.parent / "小说项目"
        ]
        
        found_projects = []
        
        for base_dir in novel_dirs:
            if base_dir.exists():
                self.log(f"扫描目录: {base_dir}", "info")
                for item in base_dir.iterdir():
                    if item.is_dir():
                        # 检查是否有章节文件
                        chapters_dir = item / "chapters"
                        if chapters_dir.exists():
                            chapter_count = len(list(chapters_dir.glob("chapter_*.json")))
                            if chapter_count > 0:
                                found_projects.append({
                                    'name': item.name,
                                    'path': str(item),
                                    'chapters': chapter_count
                                })
                                
        if found_projects:
            for project in found_projects:
                self.project_combo.addItem(
                    f"📖 {project['name']} ({project['chapters']}章)",
                    project
                )
            self.log(f"找到 {len(found_projects)} 个项目", "info")
        else:
            self.project_combo.addItem("未找到项目", None)
            # 获取程序所在目录和推荐的项目目录
            app_dir = Path(__file__).parent.resolve()
            expected_dirs = [
                app_dir / "小说项目",
                app_dir.parent / "小说项目"
            ]
            
            help_msg = (
                "未找到任何项目。请将小说项目放置在以下目录之一：\n"
                f"📁 1. {expected_dirs[0]}\n"
                f"📁 2. {expected_dirs[1]}\n\n"
                "项目结构应为：小说项目/小说名称/chapters/chapter_XXX.json"
            )
            self.log(help_msg, "warning")
            
    def on_project_changed(self, index):
        """项目选择变化"""
        if index < 0:
            return
            
        data = self.project_combo.itemData(index)
        if data:
            self.current_project = data
            self.load_chapters(data['path'])
            
    def load_chapters(self, project_path: str):
        """加载章节列表"""
        self.chapters_list.clear()
        self.chapters = []
        
        chapters_dir = Path(project_path) / "chapters"
        if not chapters_dir.exists():
            self.log("未找到章节目录", "warning")
            return
            
        chapter_files = sorted(chapters_dir.glob("chapter_*.json"))
        
        for file in chapter_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    chapter = {
                        'file': str(file),
                        'number': data.get('chapter_number', 0),
                        'title': data.get('title', '未知标题'),
                        'word_count': data.get('word_count', 0),
                        'selected': True
                    }
                    self.chapters.append(chapter)
                    
                    item = QListWidgetItem(
                        f"第{chapter['number']:03d}章 - {chapter['title']} "
                        f"({chapter['word_count']}字)"
                    )
                    item.setCheckState(Qt.Checked)
                    item.setData(Qt.UserRole, len(self.chapters) - 1)
                    self.chapters_list.addItem(item)
                    
            except Exception as e:
                self.log(f"读取章节失败 {file}: {e}", "error")
                
        self.log(f"已加载 {len(self.chapters)} 个章节", "info")
        
    def select_all_chapters(self):
        """全选章节"""
        for i in range(self.chapters_list.count()):
            item = self.chapters_list.item(i)
            item.setCheckState(Qt.Checked)
            
    def select_none_chapters(self):
        """全不选章节"""
        for i in range(self.chapters_list.count()):
            item = self.chapters_list.item(i)
            item.setCheckState(Qt.Unchecked)
            
    def get_selected_chapters(self) -> List[Dict]:
        """获取选中的章节"""
        selected = []
        for i in range(self.chapters_list.count()):
            item = self.chapters_list.item(i)
            if item.checkState() == Qt.Checked:
                idx = item.data(Qt.UserRole)
                if idx is not None and 0 <= idx < len(self.chapters):
                    selected.append(self.chapters[idx])
        return selected
        
    def import_config(self):
        """导入配置文件"""
        file, _ = QFileDialog.getOpenFileName(
            self, "选择配置文件", "", "JSON Files (*.json)"
        )
        if file:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                self.log(f"已导入配置: {config.get('project', {}).get('name', '未知')}", "info")
                QMessageBox.information(self, "成功", "配置导入成功！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {e}")
                
    def start_upload(self):
        """开始上传"""
        selected_chapters = self.get_selected_chapters()
        
        if not selected_chapters:
            QMessageBox.warning(self, "警告", "请先选择要上传的章节！")
            return
        
        # 获取当前项目名称
        project_name = self.project_combo.currentText() if self.project_combo.count() > 0 else ""
        if not project_name or project_name == "未找到项目":
            QMessageBox.warning(self, "警告", "请先选择有效的项目！")
            return
        
        # 检查 Chrome（首次使用需要下载）
        if UPLOADER_AVAILABLE:
            chrome_manager = ChromeManager()
            exists, _ = chrome_manager.get_chrome_executable()
            
            if not exists and not chrome_manager.check_chrome_running():
                # Chrome 未安装，询问用户是否下载
                reply = QMessageBox.question(
                    self,
                    "首次使用提示",
                    "首次使用需要下载 Chrome 浏览器（约 150MB）\n\n"
                    "下载完成后即可使用，下次无需重复下载。\n\n"
                    "是否立即下载？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )
                
                if reply != QMessageBox.Yes:
                    self.log("用户取消下载 Chrome", "warning")
                    QMessageBox.information(
                        self,
                        "提示",
                        "您可以选择以下方式之一：\n\n"
                        "1. 重新点击上传，同意下载 Chrome\n"
                        "2. 自行安装 Chrome 浏览器后再使用\n\n"
                        "官网：https://novel-ai.online/"
                    )
                    return
        
        # 保存配置
        self.save_config()
        
        # 准备设置
        settings = {
            'delay_min': self.delay_min_spin.value(),
            'delay_max': self.delay_max_spin.value(),
            'stop_on_error': self.stop_on_error_check.isChecked()
        }
        
        # 创建工作线程 - 使用真实的上传核心
        self.upload_worker = UploadWorker(
            novel_title=project_name,
            chapters=selected_chapters,
            settings=settings,
            config=self.config
        )
        
        # 连接信号
        self.upload_worker.progress_signal.connect(self.on_upload_progress)
        self.upload_worker.log_signal.connect(self.on_upload_log)
        self.upload_worker.chapter_status_signal.connect(self.on_chapter_status)
        self.upload_worker.finished_signal.connect(self.on_upload_finished)
        
        # 更新UI状态
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # 最小化到托盘（如果选中）
        if self.minimize_to_tray_check.isChecked():
            self.hide()
            self.tray_icon.showMessage(
                "开始上传",
                f"正在上传 {len(selected_chapters)} 个章节",
                QSystemTrayIcon.Information,
                2000
            )
        
        # 开始上传
        self.upload_worker.start()
        self.log(f"🚀 开始上传 {len(selected_chapters)} 个章节到 {project_name}", "info")
        self.log("🌐 正在启动浏览器，请稍候...", "info")
        
    def stop_upload(self):
        """停止上传"""
        if self.upload_worker and self.upload_worker.isRunning():
            self.upload_worker.stop()
            self.log("正在停止上传...", "warning")
            
    def on_upload_progress(self, percent: int, message: str):
        """上传进度回调"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
        self.statusBar().showMessage(message)
        
    def on_upload_log(self, message: str, level: str):
        """上传日志回调"""
        self.log(message, level)
        
    def on_chapter_status(self, index: int, status: str):
        """章节状态回调"""
        if 0 <= index < self.chapters_list.count():
            item = self.chapters_list.item(index)
            if status == "success":
                item.setBackground(QColor("#dcfce7"))  # 绿色
            elif status == "error":
                item.setBackground(QColor("#fee2e2"))  # 红色
                
    def on_upload_finished(self, success: bool, message: str):
        """上传完成回调"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if success:
            self.progress_bar.setValue(100)
            self.log(message, "success")
            QMessageBox.information(self, "上传完成", message)
        else:
            self.log(message, "error")
            QMessageBox.critical(self, "上传失败", message)
            
        # 显示窗口（如果最小化了）
        if self.isHidden():
            self.show()
        
    def log(self, message: str, level: str = "info"):
        """添加日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # 颜色
        colors = {
            "info": "#000000",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "success": "#22c55e"
        }
        color = colors.get(level, "#000000")
        
        # 添加到日志框
        self.log_text.append(
            f'<span style="color: #6b7280;">[{timestamp}]</span> '
            f'<span style="color: {color};">{message}</span>'
        )
        
        # 自动滚动
        self.log_text.moveCursor(QTextCursor.End)
        
    def save_log(self):
        """保存日志"""
        file, _ = QFileDialog.getSaveFileName(
            self, "保存日志", f"upload_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            "Text Files (*.txt)"
        )
        if file:
            try:
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.toPlainText())
                QMessageBox.information(self, "成功", "日志已保存！")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")


def main():
    """主函数"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # 使用Fusion风格
    
    # 设置应用信息
    app.setApplicationName("小说自动上传工具")
    app.setApplicationVersion("1.0")
    
    window = MainWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
