#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
大文娱小说发布助手
单官网账户 + 多番茄账户架构
"""

import sys
import os
import json
import time
import threading
from pathlib import Path
from datetime import datetime, timedelta

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
    """获取统一数据目录
    
    打包后安装在 Program Files 时无写入权限，
    因此 Windows 上优先使用 %LOCALAPPDATA% 用户目录。
    """
    if sys.platform == 'win32':
        # Windows: 使用 C:\Users\<user>\AppData\Local\大文娱小说发布助手
        local_appdata = os.environ.get('LOCALAPPDATA')
        if local_appdata:
            data_dir = Path(local_appdata) / "大文娱小说发布助手"
        else:
            data_dir = Path.home() / "AppData" / "Local" / "大文娱小说发布助手"
    else:
        # macOS/Linux: 使用 ~/.local/share/大文娱小说发布助手
        data_dir = Path.home() / ".local" / "share" / "大文娱小说发布助手"
    
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir

DATA_DIR = get_data_dir()

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem,
    QMessageBox, QGroupBox, QTabWidget, QSplitter, QRadioButton,
    QButtonGroup, QDialog, QLineEdit, QDoubleSpinBox, QSpinBox, QCheckBox,
    QProgressBar, QTextEdit, QFileDialog, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont, QTextCursor, QColor

# 导入模块（延迟重载，加快启动）
UPLOADER_AVAILABLE = True
try:
    from tomato_account_manager import TomatoAccountManager, TomatoAccount, ChromeLauncher
except ImportError as e:
    print(f"导入失败: {e}")
    UPLOADER_AVAILABLE = False

# FanqieUploaderImpl 延迟导入，避免启动时加载 playwright
FanqieUploaderImpl = None
def get_uploader_impl():
    global FanqieUploaderImpl
    if FanqieUploaderImpl is None:
        try:
            from fanqie_uploader_impl import FanqieUploaderImpl as _impl
            FanqieUploaderImpl = _impl
        except ImportError as e:
            print(f"导入上传模块失败: {e}")
    return FanqieUploaderImpl

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


# ============== 项目加载工作线程 ==============
class LoadProjectsWorker(QThread):
    """后台加载项目列表，避免UI卡顿"""
    
    finished_signal = pyqtSignal(list)  # [(display, data), ...]
    
    def __init__(self, scan_callback):
        super().__init__()
        self.scan_callback = scan_callback
    
    def run(self):
        try:
            projects = self.scan_callback()
            self.finished_signal.emit(projects)
        except Exception as e:
            print(f"加载项目失败: {e}")
            self.finished_signal.emit([])


# ============== 上传工作线程 ==============
class UploadWorker(QThread):
    """上传工作线程"""
    
    progress_signal = pyqtSignal(int, str)
    log_signal = pyqtSignal(str, str)
    finished_signal = pyqtSignal(bool, str)
    chapter_uploaded_signal = pyqtSignal(dict)  # 单个章节上传成功信号
    
    def __init__(self, novel_title: str, chapters: list, settings: dict, 
                 tomato_account: TomatoAccount, novel_config: dict = None,
                 project_path: Path = None):
        super().__init__()
        self.novel_title = novel_title
        self.chapters = chapters
        self.settings = settings
        self.tomato_account = tomato_account
        self.novel_config = novel_config or {}
        self.project_path = project_path
        self.is_running = True
        self.uploader = None
        self.uploaded_chapters = []  # 记录成功上传的章节
        self.is_paused = False  # 暂停状态
        self.pause_event = threading.Event()  # 用于暂停的线程事件
        self.pause_event.set()  # 默认不暂停
    
    def run(self):
        try:
            self.log_signal.emit(f"🚀 开始上传 - 使用账户: {self.tomato_account.name}", "info")
            self.log_signal.emit(f"📡 连接浏览器 (端口: {self.tomato_account.port})...", "info")
            
            # 创建上传器（延迟导入）
            UploaderImpl = get_uploader_impl()
            self.uploader = UploaderImpl(
                novel_title=self.novel_title,
                novel_config=self.novel_config,
                progress_callback=lambda p, m: self.progress_signal.emit(int(p * 0.8) + 10, m),
                log_callback=lambda m, l: self.log_signal.emit(m, l),
                pause_check_callback=self._check_pause_for_uploader
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
            
            # 计算定时发布计划
            self._apply_publish_schedule()
            
            # 逐个上传章节，失败立即停止
            delay_min = self.settings.get('delay_min', 3)
            delay_max = self.settings.get('delay_max', 8)
            
            self.progress_signal.emit(30, "开始上传章节...")
            
            total = len(self.chapters)
            success_count = 0
            
            for i, chapter in enumerate(self.chapters):
                if not self.is_running:
                    self.log_signal.emit("用户取消上传", "warning")
                    break
                
                # 检查暂停状态（带超时防止死锁）
                if self.is_paused:
                    self.log_signal.emit("⏸️ 上传已暂停，点击继续可恢复...", "warning")
                    while self.is_paused and self.is_running:
                        if self.pause_event.wait(timeout=1.0):  # 1秒超时
                            break
                    if not self.is_running:
                        break
                    self.log_signal.emit("▶️ 上传继续...", "info")
                
                chapter_num = chapter.get('chapter_number', i + 1)
                chapter_title = chapter.get('chapter_title', f'第{chapter_num}章')
                
                progress = 30 + int((i / total) * 70)
                self.progress_signal.emit(progress, f"正在上传第{i+1}/{total}章: {chapter_title[:30]}...")
                
                # 上传单个章节
                try:
                    result = self.uploader.upload_chapter(chapter)
                    if result:
                        success_count += 1
                        self.uploaded_chapters.append(chapter)
                        self.chapter_uploaded_signal.emit(chapter)
                        self.log_signal.emit(f"✅ 第{chapter_num}章上传成功", "success")
                    else:
                        # 上传失败，立即停止等待用户处理
                        error_msg = f"❌ 第{chapter_num}章《{chapter_title}》上传失败"
                        self.log_signal.emit(error_msg, "error")
                        self.log_signal.emit("⏸️ 上传已停止，请检查浏览器状态，修复问题后重新选择剩余章节上传", "warning")
                        self.finished_signal.emit(False, f"第{chapter_num}章上传失败，已停止。请手动处理后重试。")
                        return
                except Exception as e:
                    # 异常立即停止
                    error_msg = f"❌ 第{chapter_num}章《{chapter_title}》上传异常: {str(e)[:100]}"
                    self.log_signal.emit(error_msg, "error")
                    self.log_signal.emit("⏸️ 上传已停止，请检查浏览器状态，修复问题后重新选择剩余章节上传", "warning")
                    self.finished_signal.emit(False, f"第{chapter_num}章上传异常，已停止。请手动处理后重试。")
                    return
                
                # 章节间延迟（可中断）- 使用随机值
                if i < total - 1:
                    import random
                    delay = random.uniform(delay_min, delay_max)
                    self.log_signal.emit(f"  等待 {delay:.1f}s...", "debug")
                    # 使用可中断的延迟
                    self._sleep_with_pause_check(delay)
            
            # 完成
            failed = total - success_count
            if failed == 0:
                self.finished_signal.emit(True, f"✅ 上传完成: {success_count}/{total} 章")
            else:
                self.finished_signal.emit(False, f"⚠️ 上传完成: 成功 {success_count}, 失败 {failed}")
                
        except Exception as e:
            self.log_signal.emit(f"❌ 上传异常: {e}", "error")
            self.log_signal.emit("⏸️ 上传已停止，请检查浏览器状态后重试", "warning")
            self.finished_signal.emit(False, str(e))
        finally:
            if self.uploader:
                self.uploader.close()
    
    def _check_pause_for_uploader(self):
        """供UploaderImpl调用的暂停检查（带超时防止死锁）"""
        if self.is_paused:
            self.log_signal.emit("⏸️ 上传已暂停（章节处理中）...", "warning")
            # 等待暂停事件，但最多等待30秒检查一次
            while self.is_paused and self.is_running:
                if self.pause_event.wait(timeout=5.0):  # 5秒超时
                    break
            if not self.is_running:
                raise InterruptedError("上传已停止")
            self.log_signal.emit("▶️ 上传继续...", "info")
    
    def _sleep_with_pause_check(self, seconds: float, check_interval: float = 0.5):
        """可暂停检查的睡眠"""
        elapsed = 0
        while elapsed < seconds and self.is_running:
            # 检查暂停
            if self.is_paused:
                self.log_signal.emit("⏸️ 上传已暂停...", "warning")
                while self.is_paused and self.is_running:
                    if self.pause_event.wait(timeout=1.0):  # 1秒超时
                        break
                if not self.is_running:
                    return
                self.log_signal.emit("▶️ 上传继续...", "info")
            # 小睡一下
            time.sleep(min(check_interval, seconds - elapsed))
            elapsed += check_interval
    
    def _apply_publish_schedule(self):
        """应用定时发布计划到章节数据 - 使用时间点槽位机制，支持跨月"""
        try:
            # 调试：输出完整的 novel_config
            self.log_signal.emit(f"DEBUG: novel_config keys = {list(self.novel_config.keys())}", "debug")
            
            # 获取发布配置
            publish_config = self.novel_config.get('publish_config', {})
            self.log_signal.emit(f"DEBUG: publish_config = {publish_config}", "debug")
            
            if not publish_config:
                self.log_signal.emit("未找到发布配置，所有章节将立即发布", "warning")
                return
            
            first_publish_count = publish_config.get('first_publish_count', 20)
            daily_count = publish_config.get('daily_count', 8)  # 每日总章节数
            
            # 优先从 settings 读取发布时段配置（用户UI输入）
            settings_publish_times = self.settings.get('publish_times', '')
            if settings_publish_times:
                publish_times = [t.strip() for t in settings_publish_times.split(',') if t.strip()]
            else:
                # 从配置文件读取
                publish_time = publish_config.get('publish_time', '06:00')
                publish_times = [t.strip() for t in str(publish_time).split(',') if t.strip()]
            
            if not publish_times:
                publish_times = ['06:00']
            
            # 每个时间点的章节数 = daily_count / 时间点数量
            chapters_per_slot = max(1, daily_count // len(publish_times))
            
            # 获取章节号列表
            chapter_numbers = [ch.get('chapter_number', i+1) for i, ch in enumerate(self.chapters)]
            max_chapter = max(chapter_numbers) if chapter_numbers else 0
            min_chapter = min(chapter_numbers) if chapter_numbers else 0
            
            self.log_signal.emit(f"发布配置: 前{first_publish_count}章直接发布, 之后{daily_count}章/日", "info")
            self.log_signal.emit(f"时间点: {publish_times}, 每时间点{chapters_per_slot}章", "info")
            
            # 检查是否需要定时
            needs_schedule = any(ch_num > first_publish_count for ch_num in chapter_numbers)
            if not needs_schedule:
                self.log_signal.emit(f"所有章节({min_chapter}-{max_chapter})均≤{first_publish_count}，全部立即发布", "info")
                return
            
            # 🔥 优先检查手动设置的发布日期
            manual_date = publish_config.get('manual_publish_date')
            manual_time = publish_config.get('manual_publish_time')
            manual_count = publish_config.get('manual_chapter_count', daily_count)
            
            if manual_date and manual_time:
                self.log_signal.emit(f"🔥 使用手动设置的基准时间: {manual_date} {manual_time}", "info")
                self._apply_manual_publish_schedule(manual_date, manual_time, manual_count, 
                                                     first_publish_count, daily_count, chapters_per_slot)
                return
            
            # 从平台同步最后发布时间
            self.log_signal.emit("同步平台发布时间数据...", "info")
            last_published_time, today_published_count = self._get_last_published_time_from_page()
            
            # 初始化日期-时间点使用跟踪
            now = datetime.now()
            date_time_slot_usage = {}
            
            # 如果平台有已发布章节，恢复时间点使用情况
            if last_published_time:
                last_date = last_published_time.strftime('%Y-%m-%d')
                last_time = last_published_time.strftime('%H:%M')
                # 找到对应的时间点
                for time_slot in publish_times:
                    if time_slot == last_time:
                        if last_date not in date_time_slot_usage:
                            date_time_slot_usage[last_date] = {}
                        date_time_slot_usage[last_date][time_slot] = today_published_count % chapters_per_slot
                        break
                start_date = last_published_time.date()
                self.log_signal.emit(f"基于平台数据: 最后发布 {last_date} {last_time}, 今天已发{today_published_count}章", "info")
            else:
                start_date = now.date() + timedelta(days=1)  # 从明天开始
                self.log_signal.emit(f"无平台数据，从明天 {publish_times[0]} 开始", "info")
            
            # 应用定时计划到章节
            scheduled_count = 0
            
            for chapter in self.chapters:
                ch_num = chapter.get('chapter_number', 0)
                
                # 只对大于 first_publish_count 的章节设置定时
                if ch_num <= first_publish_count:
                    continue
                
                # 查找可用的时间点（支持跨月，最多搜索90天）
                found_slot = False
                target_date = None
                target_time = None
                
                for day_offset in range(90):  # 最多搜索90天（3个月）
                    search_date = start_date + timedelta(days=day_offset)
                    date_str = search_date.strftime('%Y-%m-%d')
                    
                    if date_str not in date_time_slot_usage:
                        date_time_slot_usage[date_str] = {}
                    
                    # 检查该日期的每个时间点
                    for time_slot in publish_times:
                        current_count = date_time_slot_usage[date_str].get(time_slot, 0)
                        
                        if current_count < chapters_per_slot:
                            # 验证时间是否有效（必须比现在晚至少5分钟缓冲）
                            slot_datetime = datetime.strptime(f"{date_str} {time_slot}", "%Y-%m-%d %H:%M")
                            if slot_datetime > now + timedelta(minutes=5):
                                target_date = search_date
                                target_time = time_slot
                                found_slot = True
                                # 更新使用计数
                                date_time_slot_usage[date_str][time_slot] = current_count + 1
                                break
                    
                    if found_slot:
                        break
                
                if found_slot:
                    chapter['scheduled_time'] = f"{target_date.strftime('%Y-%m-%d')} {target_time}"
                    scheduled_count += 1
                else:
                    self.log_signal.emit(f"⚠ 未找到可用时间点给第{ch_num}章", "warning")
            
            # 显示发布计划摘要
            if scheduled_count > 0:
                first_scheduled = next((ch for ch in self.chapters if ch.get('scheduled_time')), None)
                last_scheduled = None
                for ch in reversed(self.chapters):
                    if ch.get('scheduled_time'):
                        last_scheduled = ch
                        break
                
                if first_scheduled and last_scheduled:
                    self.log_signal.emit(f"定时发布计划: {scheduled_count}章", "info")
                    self.log_signal.emit(f"  首章: 第{first_scheduled.get('chapter_number')}章 @ {first_scheduled.get('scheduled_time')}", "info")
                    self.log_signal.emit(f"  末章: 第{last_scheduled.get('chapter_number')}章 @ {last_scheduled.get('scheduled_time')}", "info")
            
        except Exception as e:
            self.log_signal.emit(f"计算定时计划失败: {e}", "warning")
    
    def _apply_manual_publish_schedule(self, manual_date: str, manual_time: str, manual_count: int,
                                        first_publish_count: int, daily_count: int, chapters_per_slot: int):
        """应用手动设置的发布时间计划"""
        try:
            from datetime import datetime, timedelta
            
            # 解析基准时间
            base_time = datetime.strptime(f"{manual_date} {manual_time}", "%Y-%m-%d %H:%M")
            hour, minute = map(int, manual_time.split(':'))
            
            scheduled_count = 0
            today_chapters = 0
            current_date = base_time.date()
            next_time = base_time
            
            for chapter in self.chapters:
                ch_num = chapter.get('chapter_number', 0)
                
                # 只对大于 first_publish_count 的章节设置定时
                if ch_num <= first_publish_count:
                    continue
                
                # 检查是否需要跨天（超过 daily_count 章）
                if today_chapters >= daily_count:
                    # 跳到明天同一时间
                    current_date += timedelta(days=1)
                    next_time = datetime(current_date.year, current_date.month, current_date.day, hour, minute)
                    today_chapters = 0
                
                # 设置定时时间
                scheduled_time = next_time.strftime('%Y-%m-%d %H:%M')
                chapter['scheduled_time'] = scheduled_time
                
                # 准备下一个时间（+30分钟）
                next_time += timedelta(minutes=30)
                today_chapters += 1
                scheduled_count += 1
            
            # 输出计划
            self.log_signal.emit(f"=" * 50, "info")
            self.log_signal.emit(f"定时发布计划: {scheduled_count}章 (手动设置)", "info")
            
            # 找出首章和末章
            scheduled_chapters = [ch for ch in self.chapters if ch.get('scheduled_time')]
            if scheduled_chapters:
                first_scheduled = min(scheduled_chapters, key=lambda x: x['chapter_number'])
                last_scheduled = max(scheduled_chapters, key=lambda x: x['chapter_number'])
                self.log_signal.emit(f"  首章: 第{first_scheduled['chapter_number']}章 @ {first_scheduled['scheduled_time']}", "info")
                self.log_signal.emit(f"  末章: 第{last_scheduled['chapter_number']}章 @ {last_scheduled['scheduled_time']}", "info")
            self.log_signal.emit(f"=" * 50, "info")
            
        except Exception as e:
            self.log_signal.emit(f"应用手动定时计划失败: {e}", "warning")
    
    def _get_last_published_time_from_page(self) -> tuple:
        """从页面获取最后发布时间和今天发布数量"""
        try:
            if not self.uploader or not self.uploader.book_id:
                return None, 0
            
            # 从书籍管理页点击"章节管理"按钮进入（模拟真实用户操作）
            book_manage_url = f"https://fanqienovel.com/main/writer/book-manage"
            self.log_signal.emit(f"访问书籍管理页: {book_manage_url}", "debug")
            self.uploader.page.goto(book_manage_url, wait_until="domcontentloaded", timeout=20000)
            import time
            time.sleep(3)
            
            # 查找并点击"章节管理"按钮
            try:
                # 等待书籍卡片加载
                self.uploader.page.wait_for_selector(f"#long-article-table-item-{self.uploader.book_id}", timeout=15000)
                
                # 在当前书籍卡片中查找"章节管理"按钮
                book_card = self.uploader.page.locator(f"#long-article-table-item-{self.uploader.book_id}").first
                chapter_manage_btn = book_card.locator('button:has-text("章节管理"), a:has-text("章节管理")').first
                
                if chapter_manage_btn.count() > 0:
                    self.log_signal.emit("点击'章节管理'按钮...", "debug")
                    chapter_manage_btn.click()
                    time.sleep(3)  # 等待页面跳转和加载
                else:
                    self.log_signal.emit("未找到'章节管理'按钮，尝试直接访问URL", "warning")
                    # 备用方案：直接访问
                    chapter_manage_url = f"https://fanqienovel.com/main/writer/chapter-manage/{self.uploader.book_id}"
                    self.uploader.page.goto(chapter_manage_url, wait_until="domcontentloaded", timeout=20000)
                    time.sleep(3)
            except Exception as e:
                self.log_signal.emit(f"点击章节管理失败: {e}，尝试直接访问URL", "warning")
                chapter_manage_url = f"https://fanqienovel.com/main/writer/chapter-manage/{self.uploader.book_id}"
                self.uploader.page.goto(chapter_manage_url, wait_until="domcontentloaded", timeout=20000)
                time.sleep(3)
            
            # 等待表格加载（增加重试，使用多种选择器）
            rows = []
            for attempt in range(3):
                try:
                    # 尝试多种选择器
                    selectors = [".arco-table-tbody tr", "table tbody tr", ".chapter-table tbody tr", ".arco-table tr"]
                    for selector in selectors:
                        try:
                            self.uploader.page.wait_for_selector(selector, state="attached", timeout=8000)
                            rows = self.uploader.page.locator(selector).all()
                            if len(rows) > 0:
                                self.log_signal.emit(f"成功获取到 {len(rows)} 行数据 (选择器: {selector})", "debug")
                                break
                        except:
                            continue
                    if rows:
                        break
                    time.sleep(2)
                except Exception as e:
                    self.log_signal.emit(f"等待表格尝试 {attempt+1}/3 失败: {e}", "debug")
                    time.sleep(2)
            
            if not rows:
                self.log_signal.emit("无法获取章节列表，使用默认时间", "warning")
                return None, 0
            
            last_published_time = None
            today_published_count = 0
            today = datetime.now().date()
            
            for row in rows:
                try:
                    status_cell = row.locator("td:nth-child(4)").first
                    if status_cell.count() == 0:
                        continue
                    
                    status = status_cell.text_content().strip()
                    
                    if status == "已发布":
                        time_cell = row.locator("td:nth-child(5)").first
                        if time_cell.count() == 0:
                            continue
                        
                        time_text = time_cell.text_content().strip()
                        if not time_text or time_text == "-":
                            continue
                        
                        try:
                            publish_dt = datetime.strptime(time_text, "%Y-%m-%d %H:%M")
                            
                            if last_published_time is None or publish_dt > last_published_time:
                                last_published_time = publish_dt
                            
                            if publish_dt.date() == today:
                                today_published_count += 1
                        except ValueError:
                            continue
                except:
                    continue
            
            if last_published_time:
                self.log_signal.emit(f"最后发布时间: {last_published_time.strftime('%Y-%m-%d %H:%M')}, 今天已发布: {today_published_count}章", "info")
            
            return last_published_time, today_published_count
            
        except Exception as e:
            self.log_signal.emit(f"获取发布时间失败: {e}", "warning")
            return None, 0
    
    def pause(self):
        """暂停上传"""
        if not self.is_paused:
            self.is_paused = True
            self.pause_event.clear()
            self.log_signal.emit("⏸️ 用户请求暂停上传", "warning")
    
    def resume(self):
        """继续上传"""
        if self.is_paused:
            self.is_paused = False
            self.pause_event.set()
            self.log_signal.emit("▶️ 用户请求继续上传", "info")
    
    def stop(self):
        self.is_running = False
        self.resume()  # 确保从暂停状态退出
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
        self.setWindowTitle("大文娱小说发布助手 v1.3.33")
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
        self.is_upload_paused = False
        
        # 检查登录
        if not self.check_saved_login():
            self.show_login_dialog()
        
        self.init_ui()
        self.refresh_accounts_ui()
        
        # 🔥 异步加载项目列表，避免UI卡顿
        self.status_bar.setText("正在扫描项目目录...")
        self.project_loader = LoadProjectsWorker(self._scan_projects)
        self.project_loader.finished_signal.connect(self._on_projects_loaded)
        self.project_loader.start()
        
        # 定时刷新状态（延长至5秒，减少卡顿）
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self.refresh_accounts_status)
        self.status_timer.start(5000)
    
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
            self.setWindowTitle(f"大文娱小说发布助手 v1.3.33 - {user} ({points}点)")
    
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
        
        # 💡 提示信息
        hint_label = QLabel("💡 提示：每个账户有独立的浏览器数据，登录状态互不干扰")
        hint_label.setStyleSheet("color: #757575; font-size: 12px; padding: 5px;")
        hint_label.setWordWrap(True)
        accounts_layout.addWidget(hint_label)
        
        # ⚠️ 重要提示
        important_hint = QLabel("⚠️ 保留登录：直接关闭Chrome窗口(X)，不要点停止按钮")
        important_hint.setStyleSheet("color: #E65100; font-size: 12px; padding: 5px; background-color: #FFF3E0; border-radius: 4px;")
        important_hint.setWordWrap(True)
        accounts_layout.addWidget(important_hint)
        
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
        # 使用 NoSelection 模式，用勾选框控制选中状态
        self.chapters_list.setSelectionMode(QListWidget.NoSelection)
        # 设置样式
        self.chapters_list.setStyleSheet("""
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background-color: #f5f5f5;
            }
        """)
        # 连接勾选框变化信号
        self.chapters_list.itemChanged.connect(self.on_chapter_check_changed)
        chapters_layout.addWidget(self.chapters_list)
        
        select_layout = QHBoxLayout()
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all_chapters)
        select_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("全不选")
        select_none_btn.clicked.connect(self.select_none_chapters)
        select_layout.addWidget(select_none_btn)
        
        # 添加"只选未发布"按钮
        select_unpublished_btn = QPushButton("只选未发布")
        select_unpublished_btn.clicked.connect(self.select_unpublished_chapters)
        select_unpublished_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        select_layout.addWidget(select_unpublished_btn)
        
        select_layout.addSpacing(20)
        
        # 添加"从第X章开始"功能
        from_label = QLabel("从第")
        select_layout.addWidget(from_label)
        
        self.start_chapter_spin = QSpinBox()
        self.start_chapter_spin.setRange(1, 9999)
        self.start_chapter_spin.setValue(1)
        self.start_chapter_spin.setFixedWidth(60)
        self.start_chapter_spin.setToolTip("设置起始章节号，加载时会自动勾选大于等于此章号的未发布章节")
        select_layout.addWidget(self.start_chapter_spin)
        
        chapter_label = QLabel("章开始")
        select_layout.addWidget(chapter_label)
        
        apply_start_btn = QPushButton("应用")
        apply_start_btn.clicked.connect(self.apply_start_chapter)
        apply_start_btn.setStyleSheet("background-color: #FF9800; color: white;")
        apply_start_btn.setToolTip("根据输入的起始章节号重新选择")
        select_layout.addWidget(apply_start_btn)
        
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
        
        # 发布时段设置
        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("发布时段:"))
        
        self.publish_times_edit = QLineEdit()
        self.publish_times_edit.setPlaceholderText("06:00,12:00,18:00,22:00")
        self.publish_times_edit.setText("06:00")
        self.publish_times_edit.setToolTip("多个时段用逗号分隔，如: 06:00,12:00,18:00,22:00")
        time_layout.addWidget(self.publish_times_edit)
        
        time_layout.addWidget(QLabel("(逗号分隔)"))
        time_layout.addStretch()
        
        settings_layout.addLayout(time_layout)
        
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
        
        # 暂停/继续按钮
        self.pause_btn = QPushButton("⏸️ 暂停")
        self.pause_btn.setMinimumHeight(45)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 20px;
            }
            QPushButton:hover { background-color: #F57C00; }
            QPushButton:disabled { background-color: #cccccc; }
        """)
        self.pause_btn.clicked.connect(self.toggle_pause_upload)
        btn_layout.addWidget(self.pause_btn)
        
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
        
        <h3>📁 数据目录结构</h3>
        <pre style="background:#f5f5f5;padding:10px;border-radius:4px;">
NovelPublisher_Data/              ← 统一数据目录
├── chrome/                       ← Chrome程序（所有账户共用）
│   └── chrome-win64/chrome.exe
├── tomato_accounts/              ← 各账户数据（完全独立）
│   ├── tomato_001/               ← 账户A的数据
│   │   ├── Cookies               ← 独立的登录态
│   │   ├── Local Storage/        ← 独立的本地存储
│   │   └── ...
│   ├── tomato_002/               ← 账户B的数据
│   └── ...
└── ...
        </pre>
        
        <h3>1. 添加番茄账户</h3>
        <p>点击"➕ 添加番茄账户"，输入名称（如"作者张三"），创建<b>完全独立的浏览器配置</b>。</p>
        <p>每个账户都有：</p>
        <ul>
            <li>独立的端口号（10001, 10002...）</li>
            <li>独立的用户数据目录</li>
            <li>独立的 Cookie 和登录状态</li>
        </ul>
        
        <h3>2. 启动浏览器</h3>
        <p>点击账户卡片的"启动"按钮，会自动打开 Chrome 并跳转到番茄小说。</p>
        <p>同一个 Chrome 程序，加载不同的用户数据。</p>
        
        <h3>3. 登录番茄</h3>
        <p>在打开的浏览器中登录番茄小说作者后台。</p>
        
        <h3>4. 选择项目</h3>
        <p>从左侧选择要上传的小说项目，勾选要上传的章节。</p>
        
        <h3>5. 开始上传</h3>
        <p>选择要使用的番茄账户（单选），点击"开始上传"。</p>
        
        <h3>⚠️ 重要：如何保留登录状态</h3>
        <ul>
            <li><b style="color:green">✓ 推荐做法</b>：直接关闭 Chrome 窗口（点击右上角的 X）
                <br>→ 下次点击"启动"会自动恢复登录状态</li>
            <li><b style="color:red">✗ 不推荐</b>：点击本软件的"停止"按钮
                <br>→ 强制关闭可能导致登录状态损坏</li>
        </ul>
        <p><b>原理</b>：Chrome 关闭时会自动保存用户数据（包括登录态），
        强制终止可能导致数据写入不完整。</p>
        
        <h3>💡 多账户说明</h3>
        <ul>
            <li>可以创建多个番茄账户（如：作者A、作者B、作者C）</li>
            <li>每个账户需要单独登录不同的番茄账号</li>
            <li>账户之间的数据完全隔离，互不干扰</li>
            <li>上传时必须选择其中一个账户</li>
        </ul>
        
        <h3>🛡️ 风控建议</h3>
        <ul>
            <li>建议设置3-8秒随机间隔，避免触发平台风控</li>
            <li>每个账户的操作都是独立的浏览器环境</li>
            <li>长期保持登录状态可减少频繁登录引起的风控</li>
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
        import socket
        
        # 先检查是否已经有浏览器在运行
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                if s.connect_ex(('localhost', acc.port)) == 0:
                    # 浏览器已经在运行，尝试访问 CDP 确认
                    try:
                        import urllib.request
                        url = f"http://localhost:{acc.port}/json/version"
                        with urllib.request.urlopen(url, timeout=2) as response:
                            self.log(f"✅ 浏览器已在运行: {acc.name} (端口: {acc.port})", "success")
                            acc.status = "running"
                            if account_id in self.account_cards:
                                self.account_cards[account_id].update_status("running")
                            return
                    except:
                        # 端口被占用但无法访问 CDP，可能是僵尸进程
                        self.log(f"⚠️ 端口 {acc.port} 被占用，尝试清理...", "warning")
        except:
            pass
        
        # 启动新浏览器
        data_dir = self.tomato_manager.get_data_dir(account_id)
        
        if self.chrome_launcher.launch(acc.port, data_dir):
            self.log(f"🚀 已启动浏览器: {acc.name} (端口: {acc.port})", "success")
            acc.status = "running"
            if account_id in self.account_cards:
                self.account_cards[account_id].update_status("running")
        else:
            QMessageBox.warning(self, "错误", "启动浏览器失败")
    
    def stop_account_browser(self, account_id: str):
        """停止账户浏览器（通过 CDP 优雅关闭）"""
        import subprocess
        import urllib.request
        import json
        
        try:
            acc = self.tomato_manager.get_account(account_id)
            if not acc:
                return
            
            # 弹出确认对话框
            reply = QMessageBox.warning(
                self,
                "⚠️ 确认停止浏览器",
                f"停止浏览器 '{acc.name}' 可能导致登录状态丢失！\n\n"
                f"💡 建议：直接关闭 Chrome 窗口(X)可保留登录状态\n\n"
                f"确定要强制停止吗？",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            
            if reply != QMessageBox.Yes:
                return
            
            self.log(f"⏹ 正在停止浏览器: {acc.name}...", "info")
            
            # 方法1: 尝试通过 CDP 优雅关闭浏览器
            try:
                url = f"http://localhost:{acc.port}/json/version"
                with urllib.request.urlopen(url, timeout=2) as response:
                    # 如果能访问，尝试关闭页面
                    try:
                        close_url = f"http://localhost:{acc.port}/json/close"
                        urllib.request.urlopen(close_url, timeout=2)
                    except:
                        pass
            except:
                pass
            
            # 方法2: 通过进程用户数据目录关闭特定 Chrome
            # 查找使用特定 user-data-dir 的 Chrome 进程
            data_dir = self.tomato_manager.get_data_dir(account_id)
            try:
                # 使用 wmic 查找包含特定数据目录的 Chrome 进程
                result = subprocess.run(
                    ['wmic', 'process', 'where', f'commandline like "%{data_dir}%"', 'get', 'processid', '/format:csv'],
                    capture_output=True, text=True, timeout=5
                )
                
                # 解析输出获取 PID
                for line in result.stdout.strip().split('\n'):
                    if 'chrome.exe' in line.lower() or line.strip().isdigit():
                        parts = line.strip().split(',')
                        for part in parts:
                            pid = part.strip()
                            if pid.isdigit():
                                # 优雅关闭进程
                                subprocess.run(['taskkill', '/PID', pid], capture_output=True)
                                
            except Exception as e:
                # wmic 可能不可用，降级处理：只关闭当前调试端口的 Chrome
                self.log(f"优雅关闭失败，尝试强制关闭: {e}", "warning")
                # 关闭使用特定端口的进程
                try:
                    result = subprocess.run(
                        ['netstat', '-ano', '|', 'findstr', f':{acc.port}'],
                        capture_output=True, text=True, shell=True
                    )
                    for line in result.stdout.split('\n'):
                        if f":{acc.port}" in line:
                            parts = line.strip().split()
                            if len(parts) >= 5:
                                pid = parts[-1]
                                subprocess.run(['taskkill', '/PID', pid, '/T'], capture_output=True)
                except:
                    pass
            
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
    def _scan_projects(self) -> list:
        """扫描项目目录，返回 (display, data) 列表（可在后台线程执行）"""
        projects = []
        added_paths = set()
        
        # 1. 先加载保存的最近项目
        recent_projects = self.load_recent_projects()
        for proj_data in recent_projects:
            proj_path = Path(proj_data['path'])
            if proj_path.exists() and ((proj_path / "project_config.json").exists() or (proj_path / "project_info.json").exists()):
                display = f"📌 {proj_data['username']} / {proj_data['proj_name']}"
                # 重新提取配置以确保获取最新数据（包括 publish_config）
                novel_config = self._extract_novel_config(proj_path)
                # 合并保存的数据和新提取的配置
                merged_data = {**proj_data, **novel_config}
                projects.append((display, merged_data))
                added_paths.add(str(proj_path))
        
        # 2. 加载默认小说项目目录
        projects_dir = Path.cwd() / "小说项目"
        if projects_dir.exists():
            for user_dir in projects_dir.iterdir():
                if user_dir.is_dir():
                    for proj_dir in user_dir.iterdir():
                        if proj_dir.is_dir():
                            is_project = (proj_dir / "project_config.json").exists() or (proj_dir / "project_info.json").exists()
                            if is_project:
                                proj_path_str = str(proj_dir)
                                if proj_path_str not in added_paths:
                                    display = f"{user_dir.name} / {proj_dir.name}"
                                    novel_config = self._extract_novel_config(proj_dir)
                                    data = {
                                        'username': user_dir.name,
                                        'proj_name': proj_dir.name,
                                        'path': proj_path_str,
                                        **novel_config
                                    }
                                    projects.append((display, data))
        
        return projects
    
    def _on_projects_loaded(self, projects: list):
        """项目加载完成后更新UI"""
        self.project_combo.clear()
        for display, data in projects:
            self.project_combo.addItem(display, data)
        self.status_bar.setText(f"加载了 {self.project_combo.count()} 个项目")
        
        # 如果当前有选中的项目，触发一次章节加载
        if self.project_combo.count() > 0:
            self.project_combo.setCurrentIndex(0)
    
    def load_projects(self):
        """加载项目列表（同步版本，供手动刷新时使用）"""
        self.project_combo.clear()
        projects = self._scan_projects()
        for display, data in projects:
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
    
    def _extract_novel_config(self, project_path: Path) -> dict:
        """从项目配置中提取小说元数据（兼容自由创意模式和市场导向模式）"""
        result = {
            'novel_title': '',
            'synopsis': '',
            'main_character': '未知主角',
            'tags_info': {},
            'publish_config': {},  # 添加 publish_config
            'project_dir': str(project_path),
        }
        
        configs = []
        # 先读取 project_info.json（可能包含完整的 selected_plan）
        for fname in ['project_info.json']:
            fpath = project_path / fname
            if fpath.exists():
                try:
                    configs.append(json.loads(fpath.read_text(encoding='utf-8')))
                except Exception:
                    pass
        
        # 再读取自由创意模式的 "*_项目信息.json"（通常有最完整的正确标签）
        # 注意：目录名可能是 project_data_xxx，但文件名是 xxx_项目信息.json，所以用通配符查找
        legacy_found = False
        for legacy_info in project_path.glob('*_项目信息.json'):
            try:
                configs.append(json.loads(legacy_info.read_text(encoding='utf-8')))
                legacy_found = True
            except Exception:
                pass
        
        # fallback: 如果 glob 因编码问题未匹配到，直接遍历目录查找
        if not legacy_found:
            for f in project_path.iterdir():
                if f.is_file() and '_项目信息.json' in f.name:
                    try:
                        configs.append(json.loads(f.read_text(encoding='utf-8')))
                        legacy_found = True
                    except Exception:
                        pass
        
        # 最后再读取 project_config.json（Web 端保存时可能把标签扁平化污染）
        config_file = project_path / 'project_config.json'
        if config_file.exists():
            try:
                configs.append(json.loads(config_file.read_text(encoding='utf-8')))
            except Exception:
                pass
        
        for config in configs:
            # 1. fanqie_upload_data 结构
            upload_data = config.get('fanqie_upload_data')
            if isinstance(upload_data, dict):
                result['novel_title'] = result['novel_title'] or upload_data.get('title', '')
                result['synopsis'] = result['synopsis'] or upload_data.get('synopsis', '')
                tags = upload_data.get('tags', {})
                if isinstance(tags, dict) and tags:
                    result['tags_info'] = {**result['tags_info'], **tags}
                # 提取 publish_config
                publish_config = upload_data.get('publish_config')
                if isinstance(publish_config, dict) and publish_config:
                    result['publish_config'] = {**result['publish_config'], **publish_config}
            
            # 2. 顶层字段
            result['novel_title'] = result['novel_title'] or config.get('title', '') or config.get('novel_title', '')
            result['synopsis'] = result['synopsis'] or config.get('synopsis', '')
            
            # 3. novel_info 结构（自由创意模式）
            novel_info = config.get('novel_info')
            if isinstance(novel_info, dict):
                result['novel_title'] = result['novel_title'] or novel_info.get('title', '')
                result['synopsis'] = result['synopsis'] or novel_info.get('synopsis', '')
                
                char_design = novel_info.get('character_design', {})
                if isinstance(char_design, dict):
                    mc = char_design.get('main_character', {})
                    if isinstance(mc, dict) and mc.get('name'):
                        result['main_character'] = mc['name']
                
                selected_plan = novel_info.get('selected_plan', {})
                if isinstance(selected_plan, dict):
                    result['novel_title'] = result['novel_title'] or selected_plan.get('title', '')
                    result['synopsis'] = result['synopsis'] or selected_plan.get('synopsis', '')
                    tags = selected_plan.get('tags', {})
                    if isinstance(tags, dict) and tags:
                        result['tags_info'] = {**result['tags_info'], **tags}
                    suggestions = selected_plan.get('suggestions', {})
                    if isinstance(suggestions, dict) and suggestions.get('name'):
                        result['main_character'] = suggestions['name']
            
            # 4. 顶层 selected_plan（市场导向模式兼容）
            selected_plan = config.get('selected_plan', {})
            if isinstance(selected_plan, dict):
                result['novel_title'] = result['novel_title'] or selected_plan.get('title', '')
                result['synopsis'] = result['synopsis'] or selected_plan.get('synopsis', '')
                tags = selected_plan.get('tags', {})
                if isinstance(tags, dict) and tags:
                    result['tags_info'] = {**result['tags_info'], **tags}
                suggestions = selected_plan.get('suggestions', {})
                if isinstance(suggestions, dict) and suggestions.get('name'):
                    result['main_character'] = suggestions['name']
            
            # 5. 顶层 character_design
            char_design = config.get('character_design', {})
            if isinstance(char_design, dict):
                mc = char_design.get('main_character', {})
                if isinstance(mc, dict) and mc.get('name'):
                    result['main_character'] = mc['name']
            
            # 6. 市场导向模式 - generation_metadata.mode_specific.info.fanqie_upload_data
            fanqie_data = (
                config.get('generation_metadata', {})
                .get('mode_specific', {})
                .get('info', {})
                .get('fanqie_upload_data', {})
            )
            if isinstance(fanqie_data, dict):
                result['novel_title'] = result['novel_title'] or fanqie_data.get('title', '')
                result['synopsis'] = result['synopsis'] or fanqie_data.get('synopsis', '')
                tags = fanqie_data.get('tags', {})
                if isinstance(tags, dict) and tags:
                    result['tags_info'] = {**result['tags_info'], **tags}
                # 提取 publish_config
                publish_config = fanqie_data.get('publish_config')
                if isinstance(publish_config, dict) and publish_config:
                    result['publish_config'] = {**result['publish_config'], **publish_config}
            
            # 7. 市场导向模式 - category_tags 转换
            category_tags = config.get('category_tags', {})
            if isinstance(category_tags, dict) and category_tags.get('main_category'):
                if not result['tags_info'].get('main_category'):
                    result['tags_info']['main_category'] = category_tags.get('main_category', '')
                if not result['tags_info'].get('target_audience'):
                    result['tags_info']['target_audience'] = category_tags.get('target_audience', '男频')
                if not result['tags_info'].get('themes') and category_tags.get('tags'):
                    result['tags_info']['themes'] = category_tags.get('tags', [])[:3]
                if not result['tags_info'].get('roles'):
                    result['tags_info']['roles'] = ['主角', '反派', '队友']
                if not result['tags_info'].get('plots'):
                    result['tags_info']['plots'] = ['系统流', '打脸', '逆袭']
            
            # 🔥 8. 提取顶层的 publish_config（包含手动设置）
            top_level_publish_config = config.get('publish_config')
            if isinstance(top_level_publish_config, dict) and top_level_publish_config:
                result['publish_config'] = {**result['publish_config'], **top_level_publish_config}
        
        # 🔥 数据清洗：如果最终 tags_info 的 themes 被扁平化了（包含了 roles/plots 的标签），尝试拆分回来
        themes = result['tags_info'].get('themes', [])
        roles = result['tags_info'].get('roles', [])
        plots = result['tags_info'].get('plots', [])
        if isinstance(themes, list) and len(themes) > 3:
            role_keywords = {"全能", "腹黑", "冷酷", "果断", "善良", "温柔", "傲娇", "高冷", "机智", "勇敢", "胆小", "自私", "无私", "奶爸", "萌娃", "宝妈", "男主", "女主", "美女", "反派", "屌丝", "神豪", "主播", "选手", "观众", "扮演者", "历史人物"}
            plot_keywords = {"系统", "系统流", "升级流", "爽文", "打脸", "逆袭", "无敌流", "直播流", "国运流", "召唤流", "扮演流", "带娃流", "温馨流", "日常流", "末日", "囤货", "求生", "神豪", "花钱", "震惊", "装逼", "国运", "直播", "温馨", "搞笑", "日常", "甜宠", "豪门", "重生", "穿越", "快穿"}
            
            new_themes, new_roles, new_plots = [], [], []
            for tag in themes:
                if tag in role_keywords:
                    new_roles.append(tag)
                elif tag in plot_keywords:
                    new_plots.append(tag)
                else:
                    new_themes.append(tag)
            
            result['tags_info']['themes'] = new_themes[:3] if new_themes else themes[:3]
            result['tags_info']['roles'] = new_roles[:3] if new_roles else roles[:3]
            result['tags_info']['plots'] = new_plots[:3] if new_plots else plots[:3]
        
        # 补齐 tags_info 中缺失的基础字段
        tags_info = result['tags_info']
        if not tags_info.get('target_audience'):
            tags_info['target_audience'] = '男频'
        if 'themes' not in tags_info:
            tags_info['themes'] = []
        if 'roles' not in tags_info:
            tags_info['roles'] = []
        if 'plots' not in tags_info:
            tags_info['plots'] = []
        
        result['tags_info'] = tags_info
        
        # 🔥 读取手动发布配置（覆盖自动计算的日期）
        config_file = project_path / 'project_config.json'
        if config_file.exists():
            try:
                config = json.loads(config_file.read_text(encoding='utf-8'))
                publish_config = config.get('publish_config', {})
                
                # 检查是否有手动设置
                manual_date = publish_config.get('manual_publish_date')
                manual_time = publish_config.get('manual_publish_time')
                
                if manual_date and manual_time:
                    # 将手动设置添加到 publish_config 中
                    if 'publish_config' not in result:
                        result['publish_config'] = {}
                    
                    result['publish_config']['manual_publish_date'] = manual_date
                    result['publish_config']['manual_publish_time'] = manual_time
                    result['publish_config']['publish_time'] = manual_time
                    
                    # 设置日期槽，让上传worker使用这个日期
                    date_slots = {
                        manual_date: {manual_time: publish_config.get('manual_chapter_count', 1)}
                    }
                    result['publish_config']['date_slots'] = date_slots
                    
                    # 记录日志
                    print(f"[Config] 使用手动发布配置: {manual_date} {manual_time}")
            except Exception as e:
                print(f"[Config] 读取手动发布配置失败: {e}")
        
        return result
    
    def load_single_project(self, project_path: Path):
        """加载单个项目"""
        try:
            config_file = project_path / "project_config.json"
            if not config_file.exists():
                return
            
            config = json.loads(config_file.read_text(encoding='utf-8'))
            username = config.get('username', project_path.parent.name)
            proj_name = config.get('project_name', project_path.name)
            
            # 提取小说元数据
            novel_config = self._extract_novel_config(project_path)
            
            # 准备数据
            data = {
                'username': username,
                'proj_name': proj_name,
                'path': str(project_path),
                **novel_config
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
        """加载章节（兼容市场导向JSON和自由创意TXT）"""
        import re
        
        self.chapters_list.clear()
        self.chapters = []
        
        chapters_dir = project_path / "chapters"
        if not chapters_dir.exists():
            self.chapters_stats.setText("共 0 个章节 (章节目录不存在)")
            return
        
        # 加载已发布章节记录
        published_chapters = self._load_published_chapters(project_path)
        
        # 同时支持 JSON（市场导向）和 TXT（自由创意）格式
        json_files = list(chapters_dir.glob("chapter_*.json")) + list(chapters_dir.glob("第*.json"))
        txt_files = list(chapters_dir.glob("第*.txt")) + list(chapters_dir.glob("chapter_*.txt"))
        
        all_files = json_files + txt_files
        
        def _extract_sort_key(ch_file: Path):
            """从文件名提取章节号用于排序"""
            name = ch_file.name
            # 尝试匹配 "第001章" 或 "第1章"
            m = re.search(r'第(\d+)章', name)
            if m:
                return int(m.group(1))
            # 尝试匹配 "chapter_001"
            m = re.search(r'chapter_(\d+)', name)
            if m:
                return int(m.group(1))
            return 0
        
        chapter_files = sorted(all_files, key=_extract_sort_key)
        
        # 临时断开信号，避免初始化时触发频繁更新
        try:
            self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
        except:
            pass  # 可能还没连接
        
        # 存储需要选中的 items
        items_to_select = []
        skipped_count = 0
        
        for ch_file in chapter_files:
            try:
                if ch_file.suffix == '.json':
                    # 市场导向模式：从 JSON 内容读取
                    data = json.loads(ch_file.read_text(encoding='utf-8'))
                    ch_num = data.get('chapter_number', 0)
                    # 兼容自由创意 JSON：可能只有 chapter_title 没有 title
                    ch_title = data.get('title') or data.get('chapter_title') or f'第{ch_num}章'
                else:
                    # 自由创意模式：从 TXT 文件名和内容读取
                    content = ch_file.read_text(encoding='utf-8')
                    name = ch_file.stem  # 去掉扩展名，如 "第1章_绝境求生" 或 "第1章"
                    
                    m = re.search(r'第(\d+)章', name)
                    ch_num = int(m.group(1)) if m else 0
                    
                    # 标题：去掉 "第X章_" 前缀，剩余部分作为标题
                    title_part = re.sub(r'^第\d+章[_\s]*', '', name).strip()
                    if title_part:
                        ch_title = title_part
                    else:
                        ch_title = f"第{ch_num}章"
                    
                    # 兼容上传器期望的字段名
                    data = {
                        "chapter_number": ch_num,
                        "chapter_title": ch_title,
                        "title": ch_title,
                        "content": content
                    }
                
                # 检查是否已发布
                is_published = ch_num in published_chapters
                
                # 避免显示 "第010章: 第10章" 这种重复
                display_num = f"第{ch_num:03d}章"
                if ch_title and ch_title != f"第{ch_num}章" and ch_title != display_num:
                    display_text = f"{display_num}: {ch_title}"
                else:
                    display_text = display_num
                
                # 已发布的章节标记
                if is_published:
                    display_text += " ✓"
                    skipped_count += 1
                
                item = QListWidgetItem(display_text)
                item.setData(Qt.UserRole, data)
                
                # 启用勾选框
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                
                # 获取起始章节号设置（如果有的话）
                start_chapter = getattr(self, 'start_chapter_spin', None)
                start_num = start_chapter.value() if start_chapter else 1
                
                # 已发布的章节用灰色，不勾选
                if is_published:
                    item.setForeground(Qt.gray)
                    item.setCheckState(Qt.Unchecked)
                elif ch_num >= start_num:
                    # 未发布且章号大于等于起始章号的，默认勾选
                    item.setCheckState(Qt.Checked)
                    items_to_select.append(item)
                else:
                    # 未发布但章号小于起始章号的，不勾选
                    item.setCheckState(Qt.Unchecked)
                
                self.chapters_list.addItem(item)
                self.chapters.append(data)
            except Exception as e:
                print(f"加载章节失败 {ch_file}: {e}")
        
        # 重新连接信号（先确保断开，避免重复连接）
        try:
            self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
        except:
            pass
        self.chapters_list.itemChanged.connect(self.on_chapter_check_changed)
        
        # 统计勾选数量（未发布的默认已勾选）
        selected_count = len(items_to_select)
        self.chapters_stats.setText(f"共 {len(self.chapters)} 个章节，已选 {selected_count} 个，已发布 {skipped_count} 个")
        
        # 显示提示
        if skipped_count > 0:
            self.log(f"📂 已加载 {len(self.chapters)} 章，跳过 {skipped_count} 个已发布章节，默认勾选 {selected_count} 个待发布章节", "info")
            self.log(f"ℹ️ 提示：已发布的章节（带✓标记）默认未勾选，如需重新上传请手动勾选", "info")
        else:
            self.log(f"📂 已加载 {len(self.chapters)} 个章节，全部默认勾选", "info")
        
        # 🔥 续发检测
        self._check_resume_and_show_dialog(project_path)
    
    def _check_resume_and_show_dialog(self, project_path: Path):
        """检测并显示续发弹窗"""
        try:
            resume_info = self.check_resume_publish(project_path)
            
            if not resume_info.get('need_resume'):
                return
            
            # 检查下一章是否存在
            next_chapter = resume_info.get('next_chapter')
            has_next_chapter = any(
                ch.get('chapter_number') == next_chapter 
                for ch in self.chapters
            )
            
            if not has_next_chapter:
                return
            
            # 构建弹窗消息
            msg = f"""<b>📊 续发检测</b><br><br>
            
<b>发布记录分析：</b><br>
• 最后发布: 第{resume_info['last_chapter']}章<br>
• 今天已发: {resume_info['today_published']} 章<br>
• 今天剩余额度: <b>{resume_info['today_remaining']} 章</b><br><br>

<b>建议操作：</b><br>
• 下一章: 第{resume_info['next_chapter']}章<br>
• 发布时间: {resume_info['next_publish_date']} {resume_info['next_publish_time']}<br>
• 今天还能发 {resume_info['today_remaining']} 章（{resume_info['next_chapter']}-{resume_info['next_chapter'] + resume_info['today_remaining'] - 1}章）<br><br>

是否自动设置续发？"""
            
            # 显示弹窗
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("续发检测")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(msg)
            msg_box.setIcon(QMessageBox.Information)
            
            resume_btn = msg_box.addButton("🚀 自动续发", QMessageBox.AcceptRole)
            manual_btn = msg_box.addButton("⚙️ 手动设置", QMessageBox.RejectRole)
            cancel_btn = msg_box.addButton("取消", QMessageBox.DestructiveRole)
            
            msg_box.exec_()
            
            clicked_btn = msg_box.clickedButton()
            
            if clicked_btn == resume_btn:
                # 自动续发
                self._auto_setup_resume(resume_info)
            elif clicked_btn == manual_btn:
                # 手动设置：只选中下一章，并弹出设置对话框
                self._select_next_chapter_only(resume_info['next_chapter'], resume_info)
            # 取消则不做任何操作
            
        except Exception as e:
            self.log(f"⚠️ 续发检测失败: {e}", "warning")
    
    def _auto_setup_resume(self, resume_info: dict):
        """自动设置续发"""
        try:
            next_chapter = resume_info['next_chapter']
            today_remaining = resume_info['today_remaining']
            
            # 1. 选中今天剩余的章节
            selected_count = 0
            for i in range(self.chapters_list.count()):
                item = self.chapters_list.item(i)
                ch_num = self._extract_chapter_num(item.text())
                
                if ch_num and next_chapter <= ch_num < next_chapter + today_remaining:
                    item.setCheckState(Qt.Checked)
                    item.setBackground(QColor("#E3F2FD"))  # 蓝色高亮
                    selected_count += 1
                else:
                    item.setCheckState(Qt.Unchecked)
            
            # 2. 设置"从第X章开始"
            self.start_chapter_spin.setValue(next_chapter)
            self.apply_start_chapter()
            
            # 3. 更新发布时间配置
            next_date = resume_info['next_publish_date']
            next_time = resume_info['next_publish_time']
            
            # 自动计算定时发布（如果今天有剩余额度）
            if today_remaining > 0:
                self._setup_publish_schedule(resume_info)
            
            self.log(f"🚀 已自动设置续发: 选中第{next_chapter}-{next_chapter + today_remaining - 1}章，共{selected_count}章", "success")
            self.log(f"⏰ 发布时间: {next_date} {next_time}开始", "info")
            
        except Exception as e:
            self.log(f"⚠️ 自动设置续发失败: {e}", "warning")
    
    def _setup_publish_schedule(self, resume_info: dict):
        """设置发布时间表"""
        try:
            next_date = datetime.strptime(resume_info['next_publish_date'], '%Y-%m-%d')
            publish_times = resume_info.get('publish_times', ['06:00'])
            today_remaining = resume_info['today_remaining']
            
            # 构建日期-时间点分配
            date_slots = {}
            
            # 今天的分配
            if today_remaining > 0:
                date_str = next_date.strftime('%Y-%m-%d')
                date_slots[date_str] = {}
                
                # 每个时间点均匀分配
                chapters_per_slot = max(1, today_remaining // len(publish_times))
                remaining = today_remaining
                
                for time_slot in publish_times:
                    if remaining <= 0:
                        break
                    count = min(chapters_per_slot, remaining)
                    date_slots[date_str][time_slot] = count
                    remaining -= count
            
            # 保存到配置
            self.publish_date_slots = date_slots
            self.log(f"📅 定时发布已设置: {date_slots}", "info")
            
        except Exception as e:
            self.log(f"⚠️ 设置发布时间表失败: {e}", "warning")
    
    def _select_next_chapter_only(self, next_chapter: int, resume_info: dict = None):
        """只选中下一章，并弹出手动设置对话框"""
        # 1. 选中下一章
        for i in range(self.chapters_list.count()):
            item = self.chapters_list.item(i)
            ch_num = self._extract_chapter_num(item.text())
            
            if ch_num == next_chapter:
                item.setCheckState(Qt.Checked)
                item.setBackground(QColor("#FFF9C4"))  # 黄色高亮提示
            else:
                item.setCheckState(Qt.Unchecked)
                item.setBackground(QColor("transparent"))
        
        self.start_chapter_spin.setValue(next_chapter)
        self.apply_start_chapter()
        
        # 2. 弹出手动设置对话框
        self._show_manual_publish_dialog(next_chapter, resume_info)
    
    def _show_manual_publish_dialog(self, chapter_num: int, resume_info: dict = None):
        """显示手动发布设置对话框"""
        from PyQt5.QtWidgets import QDialog, QFormLayout, QLineEdit, QSpinBox, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle(f"手动设置 - 从第{chapter_num}章开始发布")
        dialog.setMinimumWidth(450)
        
        layout = QFormLayout()
        
        # 发布日期输入
        publish_date_label = QLabel("发布日期 (YYYY-MM-DD):")
        publish_date_edit = QLineEdit()
        publish_date_edit.setPlaceholderText("2026-04-24")
        if resume_info:
            publish_date_edit.setText(resume_info.get('next_publish_date', ''))
        else:
            publish_date_edit.setText(datetime.now().strftime('%Y-%m-%d'))
        layout.addRow(publish_date_label, publish_date_edit)
        
        # 发布时间输入
        publish_time_label = QLabel("发布时间 (HH:MM):")
        publish_time_edit = QLineEdit()
        publish_time_edit.setPlaceholderText("06:00")
        if resume_info:
            publish_time_edit.setText(resume_info.get('next_publish_time', '06:00'))
        else:
            publish_time_edit.setText(self.publish_times_edit.text().split(',')[0])
        layout.addRow(publish_time_label, publish_time_edit)
        
        # 🔥 今天发布章节数设置
        today_max = resume_info.get('today_remaining', 8) if resume_info else 8
        daily_limit = resume_info.get('daily_limit', 8) if resume_info else 8
        
        chapter_count_label = QLabel(f"今天发布章节数 (最多{daily_limit}章):")
        chapter_count_spin = QSpinBox()
        chapter_count_spin.setRange(1, daily_limit)
        chapter_count_spin.setValue(min(2, today_max))  # 默认选2章或剩余数量
        chapter_count_spin.setSuffix(" 章")
        layout.addRow(chapter_count_label, chapter_count_spin)
        
        # 提示信息
        if resume_info:
            info_text = f"💡 今天还能发 {today_max} 章 | 将从第{chapter_num}章连续发布"
            info_label = QLabel(info_text)
            info_label.setStyleSheet("color: #2196F3; font-size: 12px;")
            layout.addRow(info_label)
        
        # 按钮
        btn_layout = QHBoxLayout()
        ok_btn = QPushButton("✅ 确认设置")
        cancel_btn = QPushButton("❌ 取消")
        btn_layout.addWidget(ok_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addRow(btn_layout)
        
        dialog.setLayout(layout)
        
        # 按钮事件
        def on_ok():
            time_str = publish_time_edit.text().strip()
            date_str = publish_date_edit.text().strip()
            chapter_count = chapter_count_spin.value()
            
            # 验证格式
            try:
                datetime.strptime(time_str, '%H:%M')
                datetime.strptime(date_str, '%Y-%m-%d')
            except ValueError:
                QMessageBox.warning(dialog, "格式错误", "时间格式应为 HH:MM，日期格式应为 YYYY-MM-DD")
                return
            
            # 保存到配置
            self.publish_times_edit.setText(time_str)
            
            # 🔥 根据用户设置的章节数，选中对应数量的章节
            selected_count = 0
            start_ch = chapter_num
            for i in range(self.chapters_list.count()):
                item = self.chapters_list.item(i)
                ch_num = self._extract_chapter_num(item.text())
                
                if ch_num and start_ch <= ch_num < start_ch + chapter_count:
                    item.setCheckState(Qt.Checked)
                    item.setBackground(QColor("#E3F2FD"))  # 蓝色高亮
                    selected_count += 1
                else:
                    item.setCheckState(Qt.Unchecked)
                    item.setBackground(QColor("transparent"))
            
            # 构建日期槽（根据用户设置的章节数）
            date_slots = {
                date_str: {time_str: chapter_count}
            }
            self.publish_date_slots = date_slots
            
            # 🔥 保存到项目配置，确保上传worker能读取到
            self._save_manual_publish_config(date_str, time_str, chapter_count)
            
            # 更新"从第X章开始"
            self.start_chapter_spin.setValue(chapter_num)
            self.apply_start_chapter()
            
            self.log(f"✅ 已手动设置: 第{chapter_num}-{chapter_num + chapter_count - 1}章 ({chapter_count}章) {date_str} {time_str}", "success")
            dialog.accept()
        
        def on_cancel():
            dialog.reject()
        
        ok_btn.clicked.connect(on_ok)
        cancel_btn.clicked.connect(on_cancel)
        
        dialog.exec_()
    
    def _save_manual_publish_config(self, date_str: str, time_str: str, chapter_count: int):
        """保存手动发布配置到项目配置"""
        try:
            # 获取当前项目路径
            proj_idx = self.project_combo.currentIndex()
            if proj_idx < 0:
                return
            
            proj_data = self.project_combo.itemData(proj_idx)
            if not isinstance(proj_data, dict):
                return
            
            project_path = proj_data.get('path')
            if not project_path:
                return
            
            # 读取现有配置
            config_path = Path(project_path) / "project_config.json"
            config = {}
            if config_path.exists():
                config = json.loads(config_path.read_text(encoding='utf-8'))
            
            # 更新发布配置
            if 'publish_config' not in config:
                config['publish_config'] = {}
            
            config['publish_config']['manual_publish_date'] = date_str
            config['publish_config']['manual_publish_time'] = time_str
            config['publish_config']['manual_chapter_count'] = chapter_count
            config['publish_config']['manual_set_at'] = datetime.now().isoformat()
            
            # 保存回文件
            config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
            self.log(f"💾 手动发布配置已保存到项目", "debug")
            
        except Exception as e:
            self.log(f"⚠️ 保存手动发布配置失败: {e}", "warning")
    
    def _extract_chapter_num(self, text: str) -> int:
        """从列表项文本中提取章节号"""
        import re
        # 尝试匹配 "第001章" 或 "第1章"
        m = re.search(r'第(\d+)章', text)
        if m:
            return int(m.group(1))
        # 尝试匹配 "chapter_001"
        m = re.search(r'chapter_(\d+)', text)
        if m:
            return int(m.group(1))
        return 0

    def select_all_chapters(self):
        """全选（包括已发布的）"""
        # 临时断开信号，避免触发 on_chapter_check_changed
        try:
            self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
        except:
            pass
        try:
            for i in range(self.chapters_list.count()):
                item = self.chapters_list.item(i)
                if item:
                    item.setCheckState(Qt.Checked)
        finally:
            # 重新连接信号（先确保断开，避免重复连接）
            try:
                self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
            except:
                pass
            self.chapters_list.itemChanged.connect(self.on_chapter_check_changed)
        
        # 更新状态显示
        selected = sum(1 for i in range(self.chapters_list.count()) 
                      if self.chapters_list.item(i).checkState() == Qt.Checked)
        total = self.chapters_list.count()
        self.chapters_stats.setText(f"共 {total} 个章节，已选 {selected} 个")
        self.log(f"☑️ 已全选 {selected} 个章节", "info")
    
    def select_none_chapters(self):
        """全不选"""
        # 临时断开信号
        try:
            self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
        except:
            pass
        try:
            for i in range(self.chapters_list.count()):
                item = self.chapters_list.item(i)
                if item:
                    item.setCheckState(Qt.Unchecked)
        finally:
            # 重新连接信号
            try:
                self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
            except:
                pass
            self.chapters_list.itemChanged.connect(self.on_chapter_check_changed)
        
        total = self.chapters_list.count()
        self.chapters_stats.setText(f"共 {total} 个章节，已选 0 个")
        self.log(f"⬜ 已取消全选", "info")
    
    def select_unpublished_chapters(self):
        """只选未发布的（排除已标记✓的）"""
        # 临时断开信号
        try:
            self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
        except:
            pass
        try:
            selected_count = 0
            for i in range(self.chapters_list.count()):
                item = self.chapters_list.item(i)
                if item:
                    if "✓" not in item.text():
                        item.setCheckState(Qt.Checked)
                        selected_count += 1
                    else:
                        item.setCheckState(Qt.Unchecked)
        finally:
            # 重新连接信号
            try:
                self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
            except:
                pass
            self.chapters_list.itemChanged.connect(self.on_chapter_check_changed)
        
        total = self.chapters_list.count()
        self.chapters_stats.setText(f"共 {total} 个章节，已选 {selected_count} 个")
        self.log(f"📋 已选中 {selected_count} 个未发布章节", "info")
    
    def apply_start_chapter(self):
        """根据起始章节号选择（只选大于等于起始章号的未发布章节）"""
        start_num = self.start_chapter_spin.value()
        
        # 临时断开信号
        try:
            self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
        except:
            pass
        
        selected_count = 0
        skipped_published = 0
        skipped_before = 0
        
        try:
            for i in range(self.chapters_list.count()):
                item = self.chapters_list.item(i)
                if not item:
                    continue
                
                # 获取章节数据
                data = item.data(Qt.UserRole)
                if not data:
                    continue
                
                ch_num = data.get('chapter_number', 0)
                is_published = "✓" in item.text()
                
                if is_published:
                    # 已发布的保持未勾选
                    item.setCheckState(Qt.Unchecked)
                    skipped_published += 1
                elif ch_num >= start_num:
                    # 未发布且章号大于等于起始章号的，勾选
                    item.setCheckState(Qt.Checked)
                    selected_count += 1
                else:
                    # 未发布但章号小于起始章号的，不勾选
                    item.setCheckState(Qt.Unchecked)
                    skipped_before += 1
        finally:
            # 重新连接信号
            try:
                self.chapters_list.itemChanged.disconnect(self.on_chapter_check_changed)
            except:
                pass
            self.chapters_list.itemChanged.connect(self.on_chapter_check_changed)
        
        total = self.chapters_list.count()
        self.chapters_stats.setText(f"共 {total} 个章节，已选 {selected_count} 个")
        self.log(f"🎯 从第 {start_num} 章开始：选中 {selected_count} 个，跳过已发布 {skipped_published} 个，跳过之前 {skipped_before} 个", "info")
    
    def on_chapter_check_changed(self, item):
        """章节勾选状态变化时更新状态栏"""
        # 延迟更新，避免频繁刷新
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.update_chapter_stats)
    
    def update_chapter_stats(self):
        """更新章节统计状态"""
        total = self.chapters_list.count()
        checked = sum(1 for i in range(total) 
                     if self.chapters_list.item(i).checkState() == Qt.Checked)
        self.chapters_stats.setText(f"共 {total} 个章节，已选 {checked} 个")
    
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
        
        # 获取勾选的章节
        chapters = []
        for i in range(self.chapters_list.count()):
            item = self.chapters_list.item(i)
            if item and item.checkState() == Qt.Checked:
                chapters.append(item.data(Qt.UserRole))
        
        if not chapters:
            QMessageBox.warning(self, "提示", "请先勾选要上传的章节")
            return
        
        # 获取设置
        settings = {
            'delay_min': self.delay_min.value(),
            'delay_max': self.delay_max.value(),
            'stop_on_error': self.stop_on_error.isChecked(),
            'publish_times': self.publish_times_edit.text().strip()
        }
        
        # 获取书名和项目配置
        novel_title = "未知书名"
        novel_config = {}
        project_path = None
        
        proj_idx = self.project_combo.currentIndex()
        if proj_idx >= 0:
            proj_data = self.project_combo.itemData(proj_idx)
            if isinstance(proj_data, dict):
                novel_title = proj_data.get('novel_title') or proj_data.get('proj_name', novel_title)
                novel_config = {k: v for k, v in proj_data.items() if k in [
                    'novel_title', 'synopsis', 'main_character', 'tags_info', 'publish_config', 'project_dir'
                ]}
                project_path = proj_data.get('path')
        
        # 如果章节数据中有书名，优先使用
        if chapters:
            ch_title = chapters[0].get('novel_title') or chapters[0].get('book_title')
            if ch_title:
                novel_title = ch_title
        
        # 若下拉框中没拿到完整配置，尝试现场读取
        if not novel_config.get('novel_title') and project_path:
            extracted_config = self._extract_novel_config(Path(project_path))
            # 合并配置，保留已有的 publish_config 等
            for key, value in extracted_config.items():
                if key not in novel_config or not novel_config[key]:
                    novel_config[key] = value
            novel_config['novel_title'] = novel_config.get('novel_title') or novel_title
        
        # 启动上传线程
        self.upload_worker = UploadWorker(
            novel_title, chapters, settings, acc, novel_config,
            project_path=Path(project_path) if project_path else None
        )
        self.upload_worker.progress_signal.connect(self.on_upload_progress)
        self.upload_worker.log_signal.connect(self.on_upload_log)
        self.upload_worker.finished_signal.connect(self.on_upload_finished)
        self.upload_worker.chapter_uploaded_signal.connect(self.on_chapter_uploaded)
        
        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.pause_btn.setText("⏸️ 暂停")
        self.stop_btn.setEnabled(True)
        self.is_upload_paused = False
        
        self.log(f"🚀 开始上传 '{novel_title}'，使用账户: {acc.name}", "info")
        self.upload_worker.start()
    
    def toggle_pause_upload(self):
        """切换暂停/继续状态"""
        if not self.upload_worker:
            return
        
        if self.is_upload_paused:
            # 继续上传
            self.upload_worker.resume()
            self.pause_btn.setText("⏸️ 暂停")
            self.is_upload_paused = False
        else:
            # 暂停上传
            self.upload_worker.pause()
            self.pause_btn.setText("▶️ 继续")
            self.is_upload_paused = True
    
    def stop_upload(self):
        """停止上传"""
        if self.upload_worker:
            self.upload_worker.stop()
        self.is_upload_paused = False
    
    def on_upload_progress(self, percent: int, message: str):
        """上传进度"""
        self.progress_bar.setValue(percent)
        self.status_label.setText(message)
    
    def on_upload_log(self, message: str, level: str):
        """上传日志"""
        self.log(message, level)
    
    def on_chapter_uploaded(self, chapter: dict):
        """单个章节上传成功，保存记录"""
        try:
            chapter_num = chapter.get('chapter_number', 0)
            
            # 获取当前项目路径
            proj_idx = self.project_combo.currentIndex()
            if proj_idx < 0:
                return
            
            proj_data = self.project_combo.itemData(proj_idx)
            if not isinstance(proj_data, dict):
                return
            
            project_path = proj_data.get('path')
            if not project_path:
                return
            
            # 🔥 获取定时发布时间（从章节数据或配置）
            publish_time = None
            if hasattr(self, 'upload_worker') and self.upload_worker:
                # 从worker获取当前章节的定时时间
                publish_time = getattr(self.upload_worker, 'current_chapter_publish_time', None)
            
            # 如果worker中没有，尝试从章节数据获取
            if not publish_time:
                publish_time = chapter.get('publish_time') or chapter.get('scheduled_time')
            
            # 保存已发布章节记录（带时间）
            self._save_published_chapter(Path(project_path), chapter, publish_time)
            
        except Exception as e:
            self.log(f"⚠️ 保存已发布章节记录失败: {e}", "warning")
    
    def _get_published_chapters_file(self, project_path: Path) -> Path:
        """获取已发布章节记录文件路径"""
        return project_path / ".published_chapters.json"
    
    def _load_published_chapters(self, project_path: Path) -> set:
        """加载已发布章节记录，返回章节号集合（兼容接口）"""
        data = self._load_published_chapters_with_info(project_path)
        return set(int(k) for k in data.get('chapters', {}).keys())
    
    def check_resume_publish(self, project_path: Path) -> dict:
        """
        检测是否需要续发 - 基于 v2.0 发布记录的 publish_time 推算
        """
        try:
            data = self._load_published_chapters_with_info(project_path)
            chapters = data.get('chapters', {})
            
            if not chapters:
                self.log("[Resume] 没有发布记录", "debug")
                return {'need_resume': False}
            
            # 获取配置
            daily_limit = data.get('daily_limit', 8)
            publish_times_str = data.get('publish_times', '06:00')
            publish_times = [t.strip() for t in publish_times_str.split(',') if t.strip()]
            base_time = publish_times[0] if publish_times else '06:00'
            
            # 找出最后发布的章节
            max_chapter = max(int(k) for k in chapters.keys())
            last_ch_info = chapters.get(str(max_chapter), {})
            last_publish_time = last_ch_info.get('publish_time')
            
            self.log(f"[Resume] 最后章节: {max_chapter}, publish_time: {last_publish_time}", "debug")
            
            # 🔥 基于最后章节的 publish_time 推算
            if last_publish_time:
                try:
                    last_dt = datetime.strptime(last_publish_time, '%Y-%m-%d %H:%M')
                    self.log(f"[Resume] 解析成功: {last_dt}", "debug")
                    
                    # 计算最后那天（按 publish_time）已发多少章
                    last_date_str = last_dt.strftime('%Y-%m-%d')
                    last_day_count = sum(
                        1 for ch_info in chapters.values()
                        if isinstance(ch_info, dict) and 
                        ch_info.get('publish_time', '').startswith(last_date_str)
                    )
                    self.log(f"[Resume] {last_date_str} 已发 {last_day_count} 章", "debug")
                    
                    # 推算下一章时间
                    if last_day_count >= daily_limit:
                        # 当天已满，跨到下一天从 base_time 开始
                        next_dt = datetime.combine(
                            last_dt.date() + timedelta(days=1),
                            datetime.strptime(base_time, '%H:%M').time()
                        )
                    else:
                        # 当天还有额度，+30分钟
                        next_dt = last_dt + timedelta(minutes=30)
                    
                    next_date = next_dt.strftime('%Y-%m-%d')
                    next_time = next_dt.strftime('%H:%M')
                    self.log(f"[Resume] 推算下一章: {next_date} {next_time}", "debug")
                    
                except Exception as e:
                    self.log(f"[Resume] 解析 publish_time 失败: {e}, 使用默认值", "warning")
                    next_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                    next_time = base_time
            else:
                self.log("[Resume] 无 publish_time，使用明天", "debug")
                next_date = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
                next_time = base_time
            
            # 计算实际今天的情况
            actual_today = datetime.now().strftime('%Y-%m-%d')
            actual_today_published = sum(
                1 for ch_info in chapters.values()
                if isinstance(ch_info, dict) and 
                ch_info.get('publish_time', '').startswith(actual_today)
            )
            actual_today_remaining = max(0, daily_limit - actual_today_published)
            
            next_chapter = max_chapter + 1
            
            result = {
                'need_resume': True,
                'daily_limit': daily_limit,
                'last_chapter': max_chapter,
                'last_publish_time': last_publish_time,
                'today_published': actual_today_published,
                'today_remaining': actual_today_remaining,
                'next_chapter': next_chapter,
                'next_publish_date': next_date,
                'next_publish_time': next_time,
                'publish_times': publish_times,
                'message': f"最后: 第{max_chapter}章 @ {last_publish_time or 'N/A'} → 下一章: 第{next_chapter}章 @ {next_date} {next_time}"
            }
            self.log(f"[Resume] 结果: {result}", "debug")
            return result
            
        except Exception as e:
            self.log(f"⚠️ 检测续发失败: {e}", "warning")
            import traceback
            traceback.print_exc()
            return {'need_resume': False}
            return {'need_resume': False}
    
    def _save_published_chapter(self, project_path: Path, chapter: dict, publish_time: str = None):
        """
        保存已发布章节记录（v2.0 带发布时间）
        
        Args:
            chapter: 章节信息
            publish_time: 定时发布时间 (ISO格式 2026-04-24T06:00:00)
        """
        try:
            published_file = self._get_published_chapters_file(project_path)
            
            # 读取现有记录（兼容旧格式）
            data = {
                'version': '2.0',
                'daily_limit': 8,  # 每日发布限额
                'publish_times': self.publish_times_edit.text().strip() or '06:00',
                'chapters': {}  # 新格式：章节号 -> 详细信息
            }
            if published_file.exists():
                try:
                    old_data = json.loads(published_file.read_text(encoding='utf-8'))
                    # 兼容旧格式转换
                    if 'published_chapters' in old_data:
                        for ch_num in old_data['published_chapters']:
                            data['chapters'][str(ch_num)] = {
                                'published_at': datetime.now().isoformat(),
                                'publish_time': None,  # 旧数据没有时间
                                'title': f'第{ch_num}章'
                            }
                    else:
                        data = old_data
                except:
                    pass
            
            # 添加新记录
            chapter_num = chapter.get('chapter_number', 0)
            chapter_title = chapter.get('title', f'第{chapter_num}章')
            
            data['chapters'][str(chapter_num)] = {
                'published_at': datetime.now().isoformat(),  # 实际发布时间
                'publish_time': publish_time,  # 定时时间（如果有）
                'title': chapter_title
            }
            
            # 保存到文件
            published_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
            
            # 计算今天发布数量用于提示
            today_count = self._count_today_published(data['chapters'])
            self.log(f"💾 已记录第{chapter_num}章 (今天已发{today_count}章)", "success")
            
        except Exception as e:
            self.log(f"⚠️ 保存发布记录失败: {e}", "warning")
    
    def _count_today_published(self, chapters: dict) -> int:
        """计算今天已发布的章节数"""
        today = datetime.now().strftime('%Y-%m-%d')
        count = 0
        for ch_info in chapters.values():
            if isinstance(ch_info, dict):
                published_at = ch_info.get('published_at', '')
                if published_at.startswith(today):
                    count += 1
        return count
    
    def _load_published_chapters_with_info(self, project_path: Path) -> dict:
        """加载已发布章节记录（返回完整信息）"""
        try:
            published_file = self._get_published_chapters_file(project_path)
            self.log(f"[Resume] 尝试加载发布记录: {published_file}", "debug")
            
            if not published_file.exists():
                self.log(f"[Resume] 发布记录文件不存在", "debug")
                return {'chapters': {}}
            
            content = published_file.read_text(encoding='utf-8')
            data = json.loads(content)
            self.log(f"[Resume] 加载成功，章节数: {len(data.get('chapters', {}))}", "debug")
            
            # 兼容旧格式
            if 'published_chapters' in data:
                self.log(f"[Resume] 检测到旧格式，执行迁移", "debug")
                return self._migrate_old_format(data)
            
            # 检查最后一章的 publish_time
            chapters = data.get('chapters', {})
            if chapters:
                max_ch = max(int(k) for k in chapters.keys())
                last_info = chapters.get(str(max_ch), {})
                self.log(f"[Resume] 最后章节 {max_ch}: {last_info.get('publish_time')}", "debug")
            
            return data
        except Exception as e:
            self.log(f"⚠️ 加载发布记录失败: {e}", "warning")
            import traceback
            traceback.print_exc()
            return {'chapters': {}}
    
    def _migrate_old_format(self, old_data: dict) -> dict:
        """将旧格式迁移到新格式"""
        new_data = {
            'version': '2.0',
            'daily_limit': 8,
            'publish_times': '06:00',
            'chapters': {}
        }
        for ch_num in old_data.get('published_chapters', []):
            new_data['chapters'][str(ch_num)] = {
                'published_at': datetime.now().isoformat(),
                'publish_time': None,
                'title': f'第{ch_num}章'
            }
        return new_data
    
    def on_upload_finished(self, success: bool, message: str):
        """上传完成"""
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.pause_btn.setText("⏸️ 暂停")
        self.stop_btn.setEnabled(False)
        
        if success:
            self.log(f"✅ {message}", "success")
            QMessageBox.information(self, "完成", message)
            # 刷新章节列表，更新选中状态
            proj_idx = self.project_combo.currentIndex()
            if proj_idx >= 0:
                proj_data = self.project_combo.itemData(proj_idx)
                if isinstance(proj_data, dict):
                    project_path = proj_data.get('path')
                    if project_path:
                        self.load_chapters(Path(project_path))
        else:
            self.log(f"❌ {message}", "error")
            QMessageBox.warning(self, "上传停止", message)
    
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
