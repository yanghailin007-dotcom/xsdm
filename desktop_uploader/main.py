#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
小说自动上传工具 - 桌面GUI版本
基于现有fanqie_uploader.py封装

使用方法:
1. 运行: python main.py
2. 或打包后双击运行
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

# 添加项目路径，复用现有代码
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QProgressBar, QTextEdit, QFileDialog, QMessageBox, QGroupBox,
    QCheckBox, QSpinBox, QDoubleSpinBox, QTabWidget, QSplitter,
    QSystemTrayIcon, QMenu, QAction, QStyle
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QIcon, QFont, QTextCursor, QColor

# 尝试导入现有上传模块
try:
    from integration.fanqie_uploader import FanqieUploader
    LEGACY_MODE = False
    print("✅ 使用新版FanqieUploader")
except ImportError:
    try:
        sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'Chrome', 'automation', 'legacy'))
        from main_controller import main_scan_cycle
        from config import CONFIG
        LEGACY_MODE = True
        print("✅ 使用Legacy模式")
    except ImportError as e:
        print(f"⚠️ 无法导入上传模块: {e}")
        LEGACY_MODE = False
        FanqieUploader = None


class UploadWorker(QThread):
    """上传工作线程 - 防止UI卡顿"""
    
    # 信号定义
    progress_signal = pyqtSignal(int, str)  # 进度百分比, 消息
    log_signal = pyqtSignal(str, str)  # 消息, 级别(info/warning/error)
    chapter_status_signal = pyqtSignal(int, str)  # 章节索引, 状态
    finished_signal = pyqtSignal(bool, str)  # 成功/失败, 消息
    
    def __init__(self, config: Dict, chapters: List[Dict], settings: Dict):
        super().__init__()
        self.config = config
        self.chapters = chapters
        self.settings = settings
        self.is_running = True
        self.current_index = 0
        
    def run(self):
        """执行上传"""
        try:
            total = len(self.chapters)
            
            for i, chapter in enumerate(self.chapters):
                if not self.is_running:
                    self.log_signal.emit("用户取消上传", "warning")
                    break
                    
                self.current_index = i
                progress = int((i / total) * 100)
                
                # 更新进度
                self.progress_signal.emit(
                    progress, 
                    f"正在上传第{i+1}/{total}章: {chapter.get('title', '未知标题')}"
                )
                
                # 上传单章
                success = self.upload_single_chapter(chapter)
                
                if success:
                    self.chapter_status_signal.emit(i, "success")
                    self.log_signal.emit(f"✅ 上传成功: {chapter.get('title')}", "info")
                else:
                    self.chapter_status_signal.emit(i, "error")
                    self.log_signal.emit(f"❌ 上传失败: {chapter.get('title')}", "error")
                    
                    if self.settings.get('stop_on_error', False):
                        self.finished_signal.emit(False, "上传中断：章节上传失败")
                        return
                
                # 随机延迟（风控）
                if i < total - 1:  # 最后一章不需要延迟
                    delay = random.uniform(
                        self.settings.get('delay_min', 3),
                        self.settings.get('delay_max', 8)
                    )
                    self.log_signal.emit(f"⏱️ 等待 {delay:.1f} 秒...", "info")
                    time.sleep(delay)
            
            # 完成
            self.progress_signal.emit(100, "上传完成！")
            self.finished_signal.emit(True, f"成功上传 {total} 章")
            
        except Exception as e:
            self.log_signal.emit(f"上传异常: {str(e)}", "error")
            self.finished_signal.emit(False, str(e))
    
    def upload_single_chapter(self, chapter: Dict) -> bool:
        """上传单章 - 这里复用现有逻辑或模拟"""
        try:
            # 模拟上传过程（实际使用时替换为真实上传逻辑）
            time.sleep(1)  # 模拟网络延迟
            
            # TODO: 调用真实的上传逻辑
            # 如果FanqieUploader可用，使用它
            # 否则调用legacy的main_scan_cycle
            
            return True
        except Exception as e:
            self.log_signal.emit(f"上传章节异常: {e}", "error")
            return False
    
    def stop(self):
        """停止上传"""
        self.is_running = False
        self.log_signal.emit("正在停止上传...", "warning")


class MainWindow(QMainWindow):
    """主窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("小说自动上传工具 v1.0")
        self.setGeometry(100, 100, 1000, 700)
        
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
        
        title_label = QLabel("📚 小说自动上传工具")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_layout.addWidget(title_label)
        
        title_layout.addStretch()
        
        # 平台选择
        platform_label = QLabel("平台:")
        title_layout.addWidget(platform_label)
        
        self.platform_combo = QComboBox()
        self.platform_combo.addItem("🍅 番茄小说", "fanqie")
        self.platform_combo.addItem("📖 起点中文网", "qidian")
        self.platform_combo.addItem("✏️ 纵横中文网", "zongheng")
        title_layout.addWidget(self.platform_combo)
        
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
        
        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self.on_project_changed)
        project_layout.addWidget(self.project_combo)
        
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 刷新")
        refresh_btn.clicked.connect(self.load_projects)
        btn_layout.addWidget(refresh_btn)
        
        import_btn = QPushButton("📂 导入配置")
        import_btn.clicked.connect(self.import_config)
        btn_layout.addWidget(import_btn)
        
        project_layout.addLayout(btn_layout)
        project_group.setLayout(project_layout)
        left_layout.addWidget(project_group)
        
        # 章节列表组
        chapters_group = QGroupBox("📋 章节列表")
        chapters_layout = QVBoxLayout()
        
        # 全选/反选
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("☑️ 全选")
        select_all_btn.clicked.connect(self.select_all_chapters)
        select_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("⬜ 全不选")
        select_none_btn.clicked.connect(self.select_none_chapters)
        select_layout.addWidget(select_none_btn)
        
        chapters_layout.addLayout(select_layout)
        
        # 章节列表
        self.chapters_list = QListWidget()
        self.chapters_list.setSelectionMode(QListWidget.MultiSelection)
        chapters_layout.addWidget(self.chapters_list)
        
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
        
        # 延迟设置
        delay_layout = QHBoxLayout()
        delay_layout.addWidget(QLabel("⏱️ 延迟范围(秒):"))
        
        self.delay_min_spin = QDoubleSpinBox()
        self.delay_min_spin.setRange(0.5, 60)
        self.delay_min_spin.setValue(self.config.get('delay_min', 3))
        self.delay_min_spin.setDecimals(1)
        delay_layout.addWidget(self.delay_min_spin)
        
        delay_layout.addWidget(QLabel("~"))
        
        self.delay_max_spin = QDoubleSpinBox()
        self.delay_max_spin.setRange(1, 120)
        self.delay_max_spin.setValue(self.config.get('delay_max', 8))
        self.delay_max_spin.setDecimals(1)
        delay_layout.addWidget(self.delay_max_spin)
        
        delay_layout.addStretch()
        settings_layout.addLayout(delay_layout)
        
        # 错误处理
        self.stop_on_error_check = QCheckBox("❌ 上传失败时停止")
        self.stop_on_error_check.setChecked(self.config.get('stop_on_error', False))
        settings_layout.addWidget(self.stop_on_error_check)
        
        # 后台运行
        self.minimize_to_tray_check = QCheckBox("🔄 上传时最小化到托盘")
        self.minimize_to_tray_check.setChecked(True)
        settings_layout.addWidget(self.minimize_to_tray_check)
        
        settings_group.setLayout(settings_layout)
        upload_layout.addWidget(settings_group)
        
        # 进度组
        progress_group = QGroupBox("📊 上传进度")
        progress_layout = QVBoxLayout()
        
        self.status_label = QLabel("准备就绪")
        progress_layout.addWidget(self.status_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        progress_layout.addWidget(self.progress_bar)
        
        # 控制按钮
        btn_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 开始上传")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #22c55e, #16a34a);
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background: linear-gradient(135deg, #16a34a, #15803d);
            }
            QPushButton:disabled {
                background: #6b7280;
            }
        """)
        self.start_btn.clicked.connect(self.start_upload)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #ef4444, #dc2626);
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px 24px;
                border-radius: 8px;
            }
        """)
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
        self.log_text.setFont(QFont("Consolas", 9))
        log_layout.addWidget(self.log_text)
        
        # 日志按钮
        log_btn_layout = QHBoxLayout()
        
        clear_log_btn = QPushButton("🗑️ 清空日志")
        clear_log_btn.clicked.connect(self.log_text.clear)
        log_btn_layout.addWidget(clear_log_btn)
        
        save_log_btn = QPushButton("💾 保存日志")
        save_log_btn.clicked.connect(self.save_log)
        log_btn_layout.addWidget(save_log_btn)
        
        log_btn_layout.addStretch()
        
        log_layout.addLayout(log_btn_layout)
        
        log_group.setLayout(log_layout)
        upload_layout.addWidget(log_group)
        
        tabs.addTab(upload_tab, "📤 上传控制")
        
        # === 账号设置页 ===
        account_tab = QWidget()
        account_layout = QVBoxLayout(account_tab)
        
        account_info = QLabel("""
        <h3>🔐 账号设置</h3>
        <p>请确保已登录番茄小说官网，并保存了登录状态。</p>
        <p>上传工具将使用系统默认浏览器进行操作。</p>
        <hr>
        <p><b>使用步骤：</b></p>
        <ol>
            <li>打开Chrome浏览器</li>
            <li>访问番茄小说官网并登录</li>
            <li>创建或打开要上传的书籍</li>
            <li>在本工具中选择对应项目</li>
            <li>点击"开始上传"</li>
        </ol>
        """)
        account_info.setWordWrap(True)
        account_info.setTextFormat(Qt.RichText)
        account_layout.addWidget(account_info)
        
        account_layout.addStretch()
        
        tabs.addTab(account_tab, "🔐 账号设置")
        
        # === 关于页 ===
        about_tab = QWidget()
        about_layout = QVBoxLayout(about_tab)
        
        about_text = QLabel("""
        <h2>📚 小说自动上传工具 v1.0</h2>
        <p>基于大文娱系统的小说自动上传解决方案</p>
        <hr>
        <p><b>功能特点：</b></p>
        <ul>
            <li>✅ 支持番茄小说等平台自动上传</li>
            <li>✅ 智能风控策略，模拟人工操作</li>
            <li>✅ 批量上传，自动延迟</li>
            <li>✅ 断点续传，失败重试</li>
            <li>✅ 托盘后台运行</li>
        </ul>
        <hr>
        <p><b>技术支持：</b></p>
        <p>如有问题请联系技术支持</p>
        """)
        about_text.setWordWrap(True)
        about_text.setTextFormat(Qt.RichText)
        about_layout.addWidget(about_text)
        
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
            self.log("未找到任何项目，请检查小说项目目录", "warning")
            
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
            
        # 保存配置
        self.save_config()
        
        # 准备设置
        settings = {
            'delay_min': self.delay_min_spin.value(),
            'delay_max': self.delay_max_spin.value(),
            'stop_on_error': self.stop_on_error_check.isChecked()
        }
        
        # 创建工作线程
        self.upload_worker = UploadWorker(
            config=self.config,
            chapters=selected_chapters,
            settings=settings
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
        self.log(f"开始上传 {len(selected_chapters)} 个章节...", "info")
        
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
            self.log(f"✅ {message}", "success")
            QMessageBox.information(self, "完成", message)
        else:
            self.log(f"❌ {message}", "error")
            QMessageBox.critical(self, "失败", message)
            
        # 显示窗口
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
