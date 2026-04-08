#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI多账户管理模块 V2
每个浏览器实例对应一个官网账户（不是番茄账户）
想开N个浏览器同时上传 = 需要N个官网账户
"""

import json
import time
import shutil
from pathlib import Path
from typing import Optional, Dict, List, Callable
from dataclasses import dataclass, field, asdict
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QListWidget, QListWidgetItem, QMessageBox,
    QComboBox, QGroupBox, QGridLayout, QCheckBox, QMenu,
    QInputDialog, QProgressDialog, QWidget, QScrollArea, QFrame,
    QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt5.QtGui import QFont, QColor

from api_auth import MultiAccountManager, AccountToken


@dataclass
class BrowserInstance:
    """浏览器实例信息 - 绑定一个官网账户"""
    instance_id: str  # 唯一标识 = website_username
    website_username: str  # 官网账户名
    chrome_data_dir: Path  # Chrome数据目录
    debug_port: int  # 调试端口
    status: str = "stopped"  # stopped/starting/running/error
    process: any = None  # Playwright browser实例
    page: any = None  # 当前页面
    started_at: str = ""
    last_error: str = ""


class BrowserManager:
    """浏览器实例管理器 - 每个实例对应一个官网账户"""
    
    DEBUG_PORT_START = 10000
    DEBUG_PORT_END = 10100
    
    def __init__(self, base_data_dir: str = "browser_data"):
        self.base_dir = Path(__file__).parent / base_data_dir
        self.base_dir.mkdir(exist_ok=True)
        
        self.instances: Dict[str, BrowserInstance] = {}
        self.used_ports: set = set()
        self.playwright = None
        
        self._scan_existing_instances()
    
    def _scan_existing_instances(self):
        """扫描已有的浏览器数据目录"""
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.startswith("account_"):
                try:
                    # 目录名格式: account_{username}
                    username = item.name.replace("account_", "")
                    instance_id = username
                    
                    # 找可用端口
                    port = self._find_available_port()
                    
                    self.instances[instance_id] = BrowserInstance(
                        instance_id=instance_id,
                        website_username=username,
                        chrome_data_dir=item,
                        debug_port=port,
                        status="stopped"
                    )
                    print(f"📂 发现已有实例: {username}")
                except Exception as e:
                    print(f"⚠️ 扫描实例失败: {e}")
    
    def _find_available_port(self) -> int:
        """找一个可用的调试端口"""
        for port in range(self.DEBUG_PORT_START, self.DEBUG_PORT_END):
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
        raise RuntimeError("没有可用的调试端口")
    
    def create_instance(self, website_username: str) -> Optional[BrowserInstance]:
        """创建新的浏览器实例（绑定官网账户）"""
        instance_id = website_username
        
        # 检查是否已存在
        if instance_id in self.instances:
            return self.instances[instance_id]
        
        # 创建数据目录
        data_dir = self.base_dir / f"account_{website_username}"
        data_dir.mkdir(exist_ok=True)
        
        # 分配端口
        port = self._find_available_port()
        
        instance = BrowserInstance(
            instance_id=instance_id,
            website_username=website_username,
            chrome_data_dir=data_dir,
            debug_port=port,
            status="stopped"
        )
        
        self.instances[instance_id] = instance
        print(f"✅ 创建浏览器实例: {website_username} (端口: {port})")
        return instance
    
    def get_instance(self, username: str) -> Optional[BrowserInstance]:
        """获取实例"""
        return self.instances.get(username)
    
    def remove_instance(self, username: str) -> bool:
        """删除实例"""
        if username not in self.instances:
            return False
        
        instance = self.instances[username]
        
        # 先停止
        if instance.status == "running":
            self.stop_instance(username)
        
        # 删除数据目录
        try:
            if instance.chrome_data_dir.exists():
                shutil.rmtree(instance.chrome_data_dir)
            
            self.used_ports.discard(instance.debug_port)
            del self.instances[username]
            print(f"🗑️ 删除实例: {username}")
            return True
        except Exception as e:
            print(f"❌ 删除实例失败: {e}")
            return False
    
    def _find_chrome_executable(self) -> str:
        """查找 Chrome - 只检查固定下载目录，避免遍历卡死"""
        from pathlib import Path
        
        # 只检查固定下载目录（ChromeManager 下载的位置）
        work_dir = Path(__file__).parent
        chrome_exe = work_dir / "chrome" / "chrome-win64" / "chrome.exe"
        
        if chrome_exe.exists():
            print(f"✅ 找到 Chrome: {chrome_exe}")
            return str(chrome_exe)
        
        print("❌ Chrome 不存在")
        return None
    
    def download_chrome_if_needed(self, progress_callback=None) -> str:
        """如果 Chrome 不存在，自动下载"""
        chrome_path = self._find_chrome_executable()
        if chrome_path:
            return chrome_path
        
        print("🚀 Chrome 不存在，开始自动下载...")
        print(f"   下载目录: {self.get_chrome_download_path()}")
        
        try:
            from chrome_manager import ChromeManager
            chrome_manager = ChromeManager()
            
            # 下载 Chrome
            success = chrome_manager.download_chrome(
                progress_callback=progress_callback,
                confirm_callback=lambda msg: True  # 自动确认下载
            )
            
            if success:
                # 再次查找
                exists, chrome_path = chrome_manager.get_chrome_executable()
                if exists:
                    print(f"✅ Chrome 下载完成: {chrome_path}")
                    return str(chrome_path)
            
            print("❌ Chrome 下载失败")
            print("💡 请手动下载 Chrome 并安装到默认路径")
            return None
            
        except Exception as e:
            import traceback
            print(f"❌ 下载 Chrome 异常: {e}")
            print(f"   堆栈: {traceback.format_exc()}")
            return None
    
    def start_instance(self, username: str, headless: bool = False) -> bool:
        """启动浏览器实例 - 使用 subprocess 避免 Playwright 事件循环冲突"""
        import subprocess
        import os
        
        instance = self.instances.get(username)
        if not instance:
            print(f"❌ 实例不存在: {username}")
            return False
        
        if instance.status == "running":
            print(f"⚠️ 实例已在运行: {username}")
            return True
        
        try:
            instance.status = "starting"
            instance.last_error = ""
            
            # 查找 Chrome
            chrome_path = self._find_chrome_executable()
            
            # 如果没找到，自动下载
            if not chrome_path:
                print("⚠️ 未找到 Chrome，尝试自动下载...")
                chrome_path = self.download_chrome_if_needed(
                    progress_callback=lambda p, m: print(f"  [{p}%] {m}")
                )
            
            if not chrome_path:
                instance.status = "error"
                instance.last_error = "未找到 Chrome 且下载失败"
                print("❌ 启动失败: 未找到 Chrome")
                return False
            
            # 使用 subprocess 直接启动 Chrome（避免 Playwright 事件循环问题）
            cmd = [
                chrome_path,
                f"--remote-debugging-port={instance.debug_port}",
                f"--user-data-dir={instance.chrome_data_dir}",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
                "https://fanqienovel.com/main/writer/book-manage"
            ]
            
            print(f"🚀 启动 Chrome: {chrome_path}")
            print(f"   调试端口: {instance.debug_port}")
            print(f"   数据目录: {instance.chrome_data_dir}")
            
            # 启动进程
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
            )
            
            # 等待 Chrome 启动
            import time
            time.sleep(3)
            
            # 检查进程是否还在运行
            if process.poll() is not None:
                instance.status = "error"
                instance.last_error = "Chrome 进程启动后立即退出"
                print("❌ Chrome 进程启动失败（可能已退出）")
                return False
            
            instance.process = process
            instance.status = "running"
            instance.started_at = datetime.now().isoformat()
            
            print(f"✅ 浏览器启动成功: {username} (端口: {instance.debug_port})")
            return True
            
        except Exception as e:
            import traceback
            instance.status = "error"
            instance.last_error = str(e)
            print(f"❌ 启动浏览器失败: {username}")
            print(f"   错误: {e}")
            print(f"   堆栈: {traceback.format_exc()}")
            return False
    
    def stop_instance(self, username: str) -> bool:
        """停止浏览器实例"""
        import subprocess
        
        instance = self.instances.get(username)
        if not instance:
            return False
        
        if instance.status != "running":
            return True
        
        try:
            if instance.process:
                # 终止进程
                instance.process.terminate()
                try:
                    instance.process.wait(timeout=3)
                except:
                    instance.process.kill()
            
            instance.process = None
            instance.page = None
            instance.status = "stopped"
            
            print(f"🛑 停止浏览器: {username}")
            return True
            
        except Exception as e:
            import traceback
            instance.status = "error"
            instance.last_error = str(e)
            print(f"❌ 停止浏览器失败: {e}")
            print(f"   堆栈: {traceback.format_exc()}")
            return False
    
    def get_chrome_download_path(self) -> str:
        """获取 Chrome 下载路径"""
        work_dir = Path(__file__).parent
        return str(work_dir / "chrome" / "chrome-win64" / "chrome.exe")
    
    def stop_all(self):
        """停止所有实例"""
        for username in list(self.instances.keys()):
            self.stop_instance(username)
        
        if self.playwright:
            self.playwright.stop()
            self.playwright = None
    
    def get_running_count(self) -> int:
        """获取正在运行的实例数"""
        return sum(1 for inst in self.instances.values() if inst.status == "running")


class AccountManagerDialogV2(QDialog):
    """账户管理对话框 V2 - 简化版，每个账户就是一个浏览器实例"""
    
    account_selected = pyqtSignal(str)  # website_username
    
    def __init__(self, parent=None, account_manager: MultiAccountManager = None):
        super().__init__(parent)
        self.account_manager = account_manager or MultiAccountManager()
        self.browser_manager = BrowserManager()
        
        self.setWindowTitle("多账户管理 - 每个账户一个浏览器实例")
        self.setMinimumSize(850, 600)
        self.setup_ui()
        self.refresh_account_list()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # 说明区域
        info_card = QWidget()
        info_card.setStyleSheet("""
            QWidget {
                background-color: #E3F2FD;
                border-radius: 8px;
                padding: 12px;
            }
        """)
        info_layout = QVBoxLayout(info_card)
        
        info_title = QLabel("💡 使用说明")
        info_title.setStyleSheet("font-weight: bold; color: #1565C0;")
        info_layout.addWidget(info_title)
        
        info_text = QLabel(
            "• 每个官网账户对应一个独立的浏览器实例\n"
            "• 想同时上传N个书籍 = 需要登录N个官网账户\n"
            "• 每个浏览器可以登录不同的番茄账号\n"
            "• 余额和权限根据官网账户独立计算"
        )
        info_text.setStyleSheet("color: #424242;")
        info_layout.addWidget(info_text)
        
        layout.addWidget(info_card)
        
        # 账户列表 - 网格卡片布局
        list_label = QLabel("官网账户列表 (点击卡片选中)")
        list_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        layout.addWidget(list_label)
        
        # 创建滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                background-color: #f5f5f5;
            }
        """)
        
        # 创建网格容器
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setContentsMargins(10, 10, 10, 10)
        
        scroll_area.setWidget(self.grid_container)
        layout.addWidget(scroll_area)
        
        # 存储卡片字典 {username: card_widget}
        self.account_cards = {}
        
        # 按钮区域
        btn_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("+ 添加官网账户")
        self.add_btn.clicked.connect(self.add_account)
        btn_layout.addWidget(self.add_btn)
        
        self.start_btn = QPushButton("▶️ 启动浏览器")
        self.start_btn.clicked.connect(self.start_selected_browser)
        self.start_btn.setEnabled(False)
        btn_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ 停止浏览器")
        self.stop_btn.clicked.connect(self.stop_selected_browser)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)
        
        btn_layout.addStretch()
        
        self.refresh_btn = QPushButton("🔄 刷新")
        self.refresh_btn.clicked.connect(self.refresh_account_list)
        btn_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(btn_layout)
        
        # 底部按钮
        bottom_layout = QHBoxLayout()
        
        self.use_btn = QPushButton("✅ 使用此账户上传")
        self.use_btn.clicked.connect(self.use_selected_account)
        self.use_btn.setEnabled(False)
        self.use_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
        """)
        bottom_layout.addWidget(self.use_btn)
        
        bottom_layout.addStretch()
        
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.reject)
        bottom_layout.addWidget(close_btn)
        
        layout.addLayout(bottom_layout)
    
    def create_account_card(self, acc: dict, row: int, col: int):
        """创建账户卡片"""
        username = acc['username']
        
        # 创建卡片框架
        card = QFrame()
        card.setFrameShape(QFrame.StyledPanel)
        card.setCursor(Qt.PointingHandCursor)
        card.setMinimumSize(180, 120)
        card.setMaximumSize(200, 140)
        
        # 检查浏览器状态
        instance = self.browser_manager.get_instance(username)
        if instance:
            status_text = {
                "stopped": "已停止",
                "starting": "启动中",
                "running": "运行中",
                "error": "错误"
            }.get(instance.status, "未知")
            status_color = {
                "stopped": "#9e9e9e",
                "starting": "#ff9800",
                "running": "#4caf50",
                "error": "#f44336"
            }.get(instance.status, "#9e9e9e")
            port_info = f"端口:{instance.debug_port}"
        else:
            status_text = "未创建"
            status_color = "#9e9e9e"
            port_info = "点击创建"
        
        # 检查登录状态
        token = self.account_manager.get_token(username)
        login_status = "已登录" if token else "未登录"
        login_color = "#4caf50" if token else "#f44336"
        
        # 卡片样式
        is_selected = getattr(self, 'current_username', None) == username
        border_color = "#2196F3" if is_selected else "#e0e0e0"
        bg_color = "#e3f2fd" if is_selected else "#ffffff"
        
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 10px;
                padding: 8px;
            }}
            QFrame:hover {{
                border: 2px solid #2196F3;
                background-color: #f5f5f5;
            }}
        """)
        
        # 卡片布局
        card_layout = QVBoxLayout(card)
        card_layout.setSpacing(4)
        card_layout.setContentsMargins(8, 8, 8, 8)
        
        # 用户名
        name_label = QLabel(f"👤 {username[:12]}{'...' if len(username) > 12 else ''}")
        name_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        name_label.setStyleSheet("color: #333;")
        card_layout.addWidget(name_label)
        
        # 状态行
        status_layout = QHBoxLayout()
        status_layout.setSpacing(4)
        
        status_label = QLabel(f"● {status_text}")
        status_label.setStyleSheet(f"color: {status_color}; font-size: 11px;")
        status_layout.addWidget(status_label)
        
        status_layout.addStretch()
        
        login_label = QLabel(f"{login_status}")
        login_label.setStyleSheet(f"color: {login_color}; font-size: 11px;")
        status_layout.addWidget(login_label)
        
        card_layout.addLayout(status_layout)
        
        # 端口信息
        port_label = QLabel(f"🌐 {port_info}")
        port_label.setStyleSheet("color: #666; font-size: 10px;")
        card_layout.addWidget(port_label)
        
        # 余额信息
        balance = acc.get('points_balance', 0)
        balance_label = QLabel(f"💎 {balance}点")
        balance_label.setStyleSheet("color: #ff9800; font-size: 11px; font-weight: bold;")
        card_layout.addWidget(balance_label)
        
        card_layout.addStretch()
        
        # 点击事件
        card.mousePressEvent = lambda event, u=username: self.on_card_clicked(u)
        
        # 右键菜单
        card.setContextMenuPolicy(Qt.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, u=username: self.show_context_menu(u, card.mapToGlobal(pos))
        )
        
        # 存储卡片引用
        self.account_cards[username] = card
        self.grid_layout.addWidget(card, row, col)
    
    def on_card_clicked(self, username: str):
        """点击卡片选中账户"""
        self.current_username = username
        
        # 更新所有卡片样式
        for uname, card in self.account_cards.items():
            is_selected = uname == username
            border_color = "#2196F3" if is_selected else "#e0e0e0"
            bg_color = "#e3f2fd" if is_selected else "#ffffff"
            card.setStyleSheet(f"""
                QFrame {{
                    background-color: {bg_color};
                    border: 2px solid {border_color};
                    border-radius: 10px;
                    padding: 8px;
                }}
                QFrame:hover {{
                    border: 2px solid #2196F3;
                    background-color: #f5f5f5;
                }}
            """)
        
        # 检查是否创建了浏览器实例
        instance = self.browser_manager.get_instance(username)
        if not instance:
            instance = self.browser_manager.create_instance(username)
        
        # 更新按钮状态
        if instance.status == "running":
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            self.use_btn.setEnabled(True)
            self.use_btn.setText("✅ 使用此账户上传")
        else:
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.use_btn.setEnabled(True)
            self.use_btn.setText("✅ 选择此账户（需启动浏览器）")
    
    def refresh_account_list(self):
        """刷新账户列表 - 网格卡片布局"""
        # 清除现有卡片
        for card in self.account_cards.values():
            card.deleteLater()
        self.account_cards.clear()
        
        # 清除布局中的所有项目
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        accounts = self.account_manager.storage.get_all_accounts()
        
        # 每行显示4个卡片
        cards_per_row = 4
        
        for idx, acc in enumerate(accounts):
            row = idx // cards_per_row
            col = idx % cards_per_row
            self.create_account_card(acc, row, col)
        
        # 添加弹性空间
        self.grid_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Expanding), 
                                  row + 1, cards_per_row)
    
    def show_context_menu(self, username: str, pos):
        """显示右键菜单"""
        if not username:
            return
        
        self.current_username = username
        self.on_card_clicked(username)
        
        # 创建菜单
        menu = QMenu(self)
        
        # 启动/停止浏览器
        instance = self.browser_manager.get_instance(username)
        if instance and instance.status == "running":
            stop_action = menu.addAction("⏹️ 停止浏览器")
            stop_action.triggered.connect(lambda: self.stop_selected_browser())
        else:
            start_action = menu.addAction("▶️ 启动浏览器")
            start_action.triggered.connect(lambda: self.start_selected_browser())
        
        menu.addSeparator()
        
        # 删除账户
        delete_action = menu.addAction("🗑️ 删除此账户")
        delete_action.triggered.connect(lambda: self.delete_account(username))
        
        menu.exec_(pos)
    
    def delete_account(self, username: str):
        """删除账户"""
        reply = QMessageBox.question(
            self, '确认删除',
            f'确定要删除账户 "{username}" 吗？\n\n这将删除：\n• 该账户的登录信息\n• 浏览器数据目录\n• 相关配置文件\n\n此操作不可恢复！',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # 先停止浏览器
                instance = self.browser_manager.get_instance(username)
                if instance and instance.status == "running":
                    self.browser_manager.stop_browser(username)
                
                # 删除账户数据
                self.account_manager.storage.delete_account(username)
                
                # 删除浏览器数据目录
                data_dir = self.browser_manager.base_dir / f"account_{username}"
                if data_dir.exists():
                    import shutil
                    shutil.rmtree(data_dir)
                
                # 从管理器中移除
                if username in self.browser_manager.instances:
                    del self.browser_manager.instances[username]
                
                self.refresh_account_list()
                QMessageBox.information(self, "删除成功", f"账户 '{username}' 已删除")
                
            except Exception as e:
                QMessageBox.warning(self, "删除失败", f"删除账户时出错：{e}")
    
    # 保留旧方法兼容性
    def show_account_menu(self, position):
        """兼容旧版本 - 不再使用"""
        pass
            return
        
        username = item.data(Qt.UserRole)
        instance = self.browser_manager.get_instance(username)
        
        menu = QMenu(self)
        
        # 登录/重新登录
        login_action = menu.addAction("🔄 重新登录")
        
        menu.addSeparator()
        
        # 浏览器操作
        if instance and instance.status == "running":
            browser_action = menu.addAction("⏹️ 停止浏览器")
        else:
            browser_action = menu.addAction("▶️ 启动浏览器")
        
        menu.addSeparator()
        
        delete_action = menu.addAction("🗑️ 删除账户")
        
        action = menu.exec_(self.account_list.mapToGlobal(position))
        
        if action == login_action:
            self.relogin_account(username)
        elif action == browser_action:
            if instance and instance.status == "running":
                self.stop_browser(username)
            else:
                self.start_browser(username)
        elif action == delete_action:
            self.delete_account(username)
    
    def add_account(self):
        """添加新账户"""
        dialog = QDialog(self)
        dialog.setWindowTitle("添加官网账户")
        dialog.setMinimumWidth(350)
        
        layout = QVBoxLayout(dialog)
        
        form = QGridLayout()
        form.setSpacing(10)
        
        form.addWidget(QLabel("用户名:"), 0, 0)
        username_input = QLineEdit()
        username_input.setPlaceholderText("官网注册的用户名")
        form.addWidget(username_input, 0, 1)
        
        form.addWidget(QLabel("密码:"), 1, 0)
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        password_input.setPlaceholderText("官网账户密码")
        form.addWidget(password_input, 1, 1)
        
        layout.addLayout(form)
        
        save_check = QCheckBox("保存密码（本地加密存储）")
        save_check.setChecked(True)
        layout.addWidget(save_check)
        
        status_label = QLabel("")
        status_label.setStyleSheet("color: red;")
        layout.addWidget(status_label)
        
        btn_layout = QHBoxLayout()
        
        test_btn = QPushButton("测试并保存")
        def do_test():
            status_label.setText("登录中...")
            QTimer.singleShot(100, lambda: self._do_login(
                username_input.text().strip(),
                password_input.text().strip(),
                save_check.isChecked(),
                status_label,
                dialog
            ))
        test_btn.clicked.connect(do_test)
        btn_layout.addWidget(test_btn)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        layout.addLayout(btn_layout)
        
        dialog.exec_()
    
    def _do_login(self, username: str, password: str, save: bool, 
                  status_label: QLabel, dialog: QDialog):
        """执行登录"""
        if not username or not password:
            status_label.setText("请输入用户名和密码")
            return
        
        success = self.account_manager.login(username, password, save_account=save)
        
        if success:
            # 创建浏览器实例
            self.browser_manager.create_instance(username)
            
            status_label.setStyleSheet("color: green;")
            status_label.setText("✅ 登录成功！")
            self.refresh_account_list()
            QTimer.singleShot(500, dialog.accept)
        else:
            status_label.setText("❌ 登录失败，请检查用户名密码")
    
    def relogin_account(self, username: str):
        """重新登录"""
        account = self.account_manager.storage.get_account(username)
        if not account:
            QMessageBox.warning(self, "错误", "未找到账户信息")
            return
        
        try:
            password = self.account_manager.storage.decrypt_password(account['password'])
        except:
            QMessageBox.warning(self, "错误", "无法解密密码，请删除后重新添加")
            return
        
        progress = QProgressDialog("正在登录...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        def do_login():
            success = self.account_manager.login(username, password, save_account=False)
            progress.close()
            
            if success:
                QMessageBox.information(self, "成功", f"{username} 登录成功！")
                self.refresh_account_list()
            else:
                QMessageBox.warning(self, "失败", "登录失败，请检查密码")
        
        QTimer.singleShot(100, do_login)
    
    def delete_account(self, username: str):
        """删除账户"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除账户 {username} 吗？\n相关的浏览器数据也会被删除。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.browser_manager.remove_instance(username)
            self.account_manager.storage.remove_account(username)
            self.refresh_account_list()
    
    def start_selected_browser(self):
        """启动选中的浏览器"""
        if not hasattr(self, 'current_username'):
            return
        self.start_browser(self.current_username)
    
    def stop_selected_browser(self):
        """停止选中的浏览器"""
        if not hasattr(self, 'current_username'):
            return
        self.stop_browser(self.current_username)
    
    def start_browser(self, username: str):
        """启动浏览器"""
        instance = self.browser_manager.get_instance(username)
        if not instance:
            QMessageBox.warning(self, "错误", "浏览器实例不存在")
            return
        
        progress = QProgressDialog("正在启动浏览器...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        def do_start():
            success = self.browser_manager.start_instance(username, headless=False)
            progress.close()
            self.refresh_account_list()
            
            if success:
                QMessageBox.information(
                    self, "启动成功",
                    f"浏览器已启动！\n\n"
                    f"请在浏览器中：\n"
                    f"1. 登录番茄小说作者账号\n"
                    f"2. 创建或打开要上传的书籍\n"
                    f"3. 回到本工具点击'使用此账户上传'"
                )
            else:
                instance = self.browser_manager.get_instance(username)
                QMessageBox.warning(self, "启动失败", instance.last_error if instance else "未知错误")
        
        QTimer.singleShot(100, do_start)
    
    def stop_browser(self, username: str):
        """停止浏览器"""
        self.browser_manager.stop_instance(username)
        self.refresh_account_list()
    
    def use_selected_account(self):
        """使用选中的账户"""
        if not hasattr(self, 'current_username'):
            QMessageBox.warning(self, "错误", "请先选择一个账户")
            return
        
        instance = self.browser_manager.get_instance(self.current_username)
        if not instance:
            QMessageBox.warning(self, "错误", "浏览器实例不存在")
            return
        
        # 如果浏览器未启动，提示用户
        if instance.status != "running":
            reply = QMessageBox.question(
                self, "浏览器未启动",
                f"账户 '{self.current_username}' 的浏览器未启动。\n\n"
                "选择此账户后，需要在主界面点击上传时启动浏览器。\n"
                "是否继续选择此账户？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
        
        # 发射信号，通知主界面已选择账户
        self.account_selected.emit(self.current_username)
        self.accept()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    manager = MultiAccountManager()
    dialog = AccountManagerDialogV2(account_manager=manager)
    dialog.show()
    
    sys.exit(app.exec_())
