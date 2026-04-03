#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GUI多账户管理模块
支持多官网账户登录和多浏览器实例管理
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
    QInputDialog, QProgressDialog
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt5.QtGui import QFont

from api_auth import MultiAccountManager, AccountToken


@dataclass
class BrowserInstance:
    """浏览器实例信息"""
    instance_id: str  # 唯一标识
    website_username: str  # 绑定的官网账户
    fanqie_nickname: str  # 番茄账户昵称
    chrome_data_dir: Path  # Chrome数据目录
    debug_port: int  # 调试端口
    status: str = "stopped"  # stopped/starting/running/error
    process: any = None  # Playwright browser实例
    page: any = None  # 当前页面
    started_at: str = ""
    last_error: str = ""


class BrowserManager:
    """浏览器实例管理器"""
    
    # 调试端口范围
    DEBUG_PORT_START = 10000
    DEBUG_PORT_END = 10100
    
    def __init__(self, base_data_dir: str = "browser_data"):
        self.base_dir = Path(__file__).parent / base_data_dir
        self.base_dir.mkdir(exist_ok=True)
        
        self.instances: Dict[str, BrowserInstance] = {}
        self.used_ports: set = set()
        self.playwright = None
        
        # 扫描已存在的实例
        self._scan_existing_instances()
    
    def _scan_existing_instances(self):
        """扫描已有的浏览器数据目录"""
        for item in self.base_dir.iterdir():
            if item.is_dir() and item.name.startswith("instance_"):
                try:
                    parts = item.name.split("_")
                    if len(parts) >= 3:
                        website_user = parts[1]
                        fanqie_name = parts[2]
                        instance_id = f"{website_user}_{fanqie_name}"
                        
                        # 找可用端口
                        port = self._find_available_port()
                        
                        self.instances[instance_id] = BrowserInstance(
                            instance_id=instance_id,
                            website_username=website_user,
                            fanqie_nickname=fanqie_name,
                            chrome_data_dir=item,
                            debug_port=port,
                            status="stopped"
                        )
                        print(f"📂 发现已有实例: {instance_id}")
                except Exception as e:
                    print(f"⚠️ 扫描实例失败: {e}")
    
    def _find_available_port(self) -> int:
        """找一个可用的调试端口"""
        for port in range(self.DEBUG_PORT_START, self.DEBUG_PORT_END):
            if port not in self.used_ports:
                self.used_ports.add(port)
                return port
        raise RuntimeError("没有可用的调试端口")
    
    def create_instance(self, website_username: str, fanqie_nickname: str) -> BrowserInstance:
        """创建新的浏览器实例"""
        instance_id = f"{website_username}_{fanqie_nickname}"
        
        # 检查是否已存在
        if instance_id in self.instances:
            return self.instances[instance_id]
        
        # 创建数据目录
        data_dir = self.base_dir / f"instance_{website_username}_{fanqie_nickname}"
        data_dir.mkdir(exist_ok=True)
        
        # 分配端口
        port = self._find_available_port()
        
        instance = BrowserInstance(
            instance_id=instance_id,
            website_username=website_username,
            fanqie_nickname=fanqie_nickname,
            chrome_data_dir=data_dir,
            debug_port=port,
            status="stopped"
        )
        
        self.instances[instance_id] = instance
        print(f"✅ 创建浏览器实例: {instance_id} (端口: {port})")
        return instance
    
    def get_instance(self, instance_id: str) -> Optional[BrowserInstance]:
        """获取实例"""
        return self.instances.get(instance_id)
    
    def get_instances_by_website_user(self, username: str) -> List[BrowserInstance]:
        """获取某官网账户下的所有实例"""
        return [
            inst for inst in self.instances.values()
            if inst.website_username == username
        ]
    
    def remove_instance(self, instance_id: str) -> bool:
        """删除实例"""
        if instance_id not in self.instances:
            return False
        
        instance = self.instances[instance_id]
        
        # 先停止
        if instance.status == "running":
            self.stop_instance(instance_id)
        
        # 删除数据目录
        try:
            if instance.chrome_data_dir.exists():
                shutil.rmtree(instance.chrome_data_dir)
            
            self.used_ports.discard(instance.debug_port)
            del self.instances[instance_id]
            print(f"🗑️ 删除实例: {instance_id}")
            return True
        except Exception as e:
            print(f"❌ 删除实例失败: {e}")
            return False
    
    def start_instance(self, instance_id: str, headless: bool = False) -> bool:
        """启动浏览器实例"""
        from playwright.sync_api import sync_playwright
        
        instance = self.instances.get(instance_id)
        if not instance:
            print(f"❌ 实例不存在: {instance_id}")
            return False
        
        if instance.status == "running":
            print(f"⚠️ 实例已在运行: {instance_id}")
            return True
        
        try:
            instance.status = "starting"
            instance.last_error = ""
            
            # 初始化playwright（如果还没初始化）
            if not self.playwright:
                self.playwright = sync_playwright().start()
            
            # 启动持久化浏览器
            browser = self.playwright.chromium.launch_persistent_context(
                user_data_dir=str(instance.chrome_data_dir),
                headless=headless,
                args=[
                    f'--remote-debugging-port={instance.debug_port}',
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-blink-features=AutomationControlled'
                ]
            )
            
            # 创建新页面
            page = browser.new_page()
            page.set_viewport_size({"width": 1920, "height": 1080})
            
            # 访问番茄作家后台
            page.goto("https://fanqienovel.com/main/writer/book-manage", timeout=30000)
            
            instance.process = browser
            instance.page = page
            instance.status = "running"
            instance.started_at = datetime.now().isoformat()
            
            print(f"✅ 启动浏览器: {instance_id} (端口: {instance.debug_port})")
            return True
            
        except Exception as e:
            instance.status = "error"
            instance.last_error = str(e)
            print(f"❌ 启动浏览器失败: {instance_id} - {e}")
            return False
    
    def stop_instance(self, instance_id: str) -> bool:
        """停止浏览器实例"""
        instance = self.instances.get(instance_id)
        if not instance:
            return False
        
        if instance.status != "running":
            return True
        
        try:
            if instance.process:
                instance.process.close()
            
            instance.process = None
            instance.page = None
            instance.status = "stopped"
            
            print(f"🛑 停止浏览器: {instance_id}")
            return True
            
        except Exception as e:
            instance.status = "error"
            instance.last_error = str(e)
            print(f"❌ 停止浏览器失败: {e}")
            return False
    
    def stop_all(self):
        """停止所有实例"""
        for instance_id in list(self.instances.keys()):
            self.stop_instance(instance_id)
        
        if self.playwright:
            self.playwright.stop()
            self.playwright = None


class AccountManagerDialog(QDialog):
    """账户管理对话框"""
    
    account_selected = pyqtSignal(str, str)  # website_username, fanqie_nickname
    
    def __init__(self, parent=None, account_manager: MultiAccountManager = None):
        super().__init__(parent)
        self.account_manager = account_manager or MultiAccountManager()
        self.browser_manager = BrowserManager()
        
        self.setWindowTitle("多账户管理")
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.refresh_account_list()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # 左侧：官网账户列表
        left_panel = QVBoxLayout()
        
        left_label = QLabel("官网账户")
        left_label.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
        left_panel.addWidget(left_label)
        
        self.account_list = QListWidget()
        self.account_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.account_list.customContextMenuRequested.connect(self.show_account_menu)
        self.account_list.itemClicked.connect(self.on_account_selected)
        left_panel.addWidget(self.account_list)
        
        # 添加账户按钮
        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("+ 添加账户")
        self.add_btn.clicked.connect(self.add_account)
        btn_layout.addWidget(self.add_btn)
        
        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.clicked.connect(self.refresh_account_list)
        btn_layout.addWidget(self.refresh_btn)
        
        left_panel.addLayout(btn_layout)
        
        layout.addLayout(left_panel, 1)
        
        # 右侧：账户详情和浏览器实例
        right_panel = QVBoxLayout()
        
        # 账户信息组
        info_group = QGroupBox("账户信息")
        info_layout = QGridLayout(info_group)
        
        info_layout.addWidget(QLabel("用户名:"), 0, 0)
        self.info_username = QLabel("未选择")
        self.info_username.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        info_layout.addWidget(self.info_username, 0, 1)
        
        info_layout.addWidget(QLabel("余额:"), 1, 0)
        self.info_points = QLabel("-")
        info_layout.addWidget(self.info_points, 1, 1)
        
        info_layout.addWidget(QLabel("状态:"), 2, 0)
        self.info_status = QLabel("未登录")
        info_layout.addWidget(self.info_status, 2, 1)
        
        right_panel.addWidget(info_group)
        
        # 浏览器实例组
        browser_group = QGroupBox("番茄账户浏览器实例")
        browser_layout = QVBoxLayout(browser_group)
        
        self.browser_list = QListWidget()
        self.browser_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.browser_list.customContextMenuRequested.connect(self.show_browser_menu)
        browser_layout.addWidget(self.browser_list)
        
        browser_btn_layout = QHBoxLayout()
        self.add_browser_btn = QPushButton("+ 添加浏览器")
        self.add_browser_btn.clicked.connect(self.add_browser_instance)
        self.add_browser_btn.setEnabled(False)
        browser_btn_layout.addWidget(self.add_browser_btn)
        
        self.start_all_btn = QPushButton("启动全部")
        self.start_all_btn.clicked.connect(self.start_all_browsers)
        self.start_all_btn.setEnabled(False)
        browser_btn_layout.addWidget(self.start_all_btn)
        
        browser_layout.addLayout(browser_btn_layout)
        
        right_panel.addWidget(browser_group, 2)
        
        # 操作按钮
        action_layout = QHBoxLayout()
        
        self.use_btn = QPushButton("使用此账户")
        self.use_btn.clicked.connect(self.use_selected_account)
        self.use_btn.setEnabled(False)
        action_layout.addWidget(self.use_btn)
        
        self.login_btn = QPushButton("重新登录")
        self.login_btn.clicked.connect(self.relogin_account)
        self.login_btn.setEnabled(False)
        action_layout.addWidget(self.login_btn)
        
        right_panel.addLayout(action_layout)
        
        layout.addLayout(right_panel, 2)
    
    def refresh_account_list(self):
        """刷新账户列表"""
        self.account_list.clear()
        
        accounts = self.account_manager.storage.get_all_accounts()
        for acc in accounts:
            item = QListWidgetItem(f"👤 {acc['username']}")
            item.setData(Qt.UserRole, acc['username'])
            item.setToolTip(f"番茄账户: {acc['fanqie_count']}个\n最后登录: {acc['last_login'][:19] if acc['last_login'] else '-'}")
            self.account_list.addItem(item)
    
    def on_account_selected(self, item):
        """选中账户"""
        username = item.data(Qt.UserRole)
        self.current_username = username
        
        # 更新信息
        self.info_username.setText(username)
        
        # 检查token
        token = self.account_manager.get_token(username)
        if token:
            self.info_status.setText("✅ 已登录")
            self.info_points.setText(f"{token.points_balance} 点")
            self.use_btn.setEnabled(True)
        else:
            self.info_status.setText("❌ 未登录或已过期")
            self.info_points.setText("-")
            self.use_btn.setEnabled(False)
        
        self.add_browser_btn.setEnabled(True)
        self.start_all_btn.setEnabled(True)
        self.login_btn.setEnabled(True)
        
        # 刷新浏览器列表
        self.refresh_browser_list(username)
    
    def refresh_browser_list(self, username: str):
        """刷新浏览器实例列表"""
        self.browser_list.clear()
        
        instances = self.browser_manager.get_instances_by_website_user(username)
        for inst in instances:
            status_icon = {
                "stopped": "⏹️",
                "starting": "🔄",
                "running": "✅",
                "error": "❌"
            }.get(inst.status, "❓")
            
            item_text = f"{status_icon} {inst.fanqie_nickname} (端口:{inst.debug_port})"
            item = QListWidgetItem(item_text)
            item.setData(Qt.UserRole, inst.instance_id)
            item.setToolTip(f"状态: {inst.status}\n目录: {inst.chrome_data_dir}")
            self.browser_list.addItem(item)
    
    def show_account_menu(self, position):
        """显示账户右键菜单"""
        item = self.account_list.itemAt(position)
        if not item:
            return
        
        username = item.data(Qt.UserRole)
        
        menu = QMenu(self)
        
        login_action = menu.addAction("🔄 重新登录")
        delete_action = menu.addAction("🗑️ 删除账户")
        
        action = menu.exec_(self.account_list.mapToGlobal(position))
        
        if action == login_action:
            self.relogin_account_with_username(username)
        elif action == delete_action:
            self.delete_account(username)
    
    def show_browser_menu(self, position):
        """显示浏览器右键菜单"""
        item = self.browser_list.itemAt(position)
        if not item:
            return
        
        instance_id = item.data(Qt.UserRole)
        instance = self.browser_manager.get_instance(instance_id)
        if not instance:
            return
        
        menu = QMenu(self)
        
        if instance.status == "stopped":
            start_action = menu.addAction("▶️ 启动浏览器")
        else:
            start_action = menu.addAction("⏹️ 停止浏览器")
        
        delete_action = menu.addAction("🗑️ 删除实例")
        
        action = menu.exec_(self.browser_list.mapToGlobal(position))
        
        if action == start_action:
            if instance.status == "stopped":
                self.start_browser(instance_id)
            else:
                self.stop_browser(instance_id)
        elif action == delete_action:
            self.delete_browser_instance(instance_id)
    
    def add_account(self):
        """添加新账户"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QLabel
        
        dialog = QDialog(self)
        dialog.setWindowTitle("添加官网账户")
        dialog.setMinimumWidth(350)
        
        layout = QVBoxLayout(dialog)
        
        form = QFormLayout()
        username_input = QLineEdit()
        password_input = QLineEdit()
        password_input.setEchoMode(QLineEdit.Password)
        
        form.addRow("用户名:", username_input)
        form.addRow("密码:", password_input)
        layout.addLayout(form)
        
        save_check = QCheckBox("保存密码（本地加密）")
        save_check.setChecked(True)
        layout.addWidget(save_check)
        
        status_label = QLabel("")
        status_label.setStyleSheet("color: red;")
        layout.addWidget(status_label)
        
        btn_layout = QHBoxLayout()
        
        test_btn = QPushButton("测试登录")
        def test_login():
            status_label.setText("登录中...")
            QTimer.singleShot(100, lambda: self._do_login(
                username_input.text().strip(),
                password_input.text().strip(),
                save_check.isChecked(),
                status_label,
                dialog
            ))
        test_btn.clicked.connect(test_login)
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
            status_label.setStyleSheet("color: green;")
            status_label.setText("✅ 登录成功！")
            self.refresh_account_list()
            QTimer.singleShot(500, dialog.accept)
        else:
            status_label.setText("❌ 登录失败，请检查用户名密码")
    
    def delete_account(self, username: str):
        """删除账户"""
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除账户 {username} 吗？\n相关的浏览器实例也会被删除。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # 删除相关浏览器实例
            instances = self.browser_manager.get_instances_by_website_user(username)
            for inst in instances:
                self.browser_manager.remove_instance(inst.instance_id)
            
            # 删除账户
            self.account_manager.storage.remove_account(username)
            self.refresh_account_list()
    
    def relogin_account(self):
        """重新登录当前选中账户"""
        if hasattr(self, 'current_username'):
            self.relogin_account_with_username(self.current_username)
    
    def relogin_account_with_username(self, username: str):
        """使用保存的密码重新登录"""
        account = self.account_manager.storage.get_account(username)
        if not account:
            QMessageBox.warning(self, "错误", "未找到保存的账户信息")
            return
        
        try:
            password = self.account_manager.storage.decrypt_password(account['password'])
        except:
            QMessageBox.warning(self, "错误", "无法解密密码，请重新添加账户")
            return
        
        # 显示进度
        progress = QProgressDialog("正在登录...", None, 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.show()
        
        def do_login():
            success = self.account_manager.login(username, password, save_account=False)
            progress.close()
            
            if success:
                QMessageBox.information(self, "成功", f"{username} 登录成功！")
                self.refresh_account_list()
                # 更新当前选中项
                for i in range(self.account_list.count()):
                    item = self.account_list.item(i)
                    if item.data(Qt.UserRole) == username:
                        self.account_list.setCurrentItem(item)
                        self.on_account_selected(item)
                        break
            else:
                QMessageBox.warning(self, "失败", "登录失败，请检查密码")
        
        QTimer.singleShot(100, do_login)
    
    def add_browser_instance(self):
        """添加浏览器实例"""
        if not hasattr(self, 'current_username'):
            return
        
        # 输入番茄账户昵称
        nickname, ok = QInputDialog.getText(
            self, "添加番茄账户",
            "为此浏览器实例命名（如：番茄主号、番茄小号1）:"
        )
        
        if not ok or not nickname.strip():
            return
        
        nickname = nickname.strip()
        
        # 创建实例
        instance = self.browser_manager.create_instance(self.current_username, nickname)
        
        # 刷新列表
        self.refresh_browser_list(self.current_username)
        
        QMessageBox.information(
            self, "创建成功",
            f"浏览器实例 '{nickname}' 已创建\n"
            f"调试端口: {instance.debug_port}\n\n"
            f"右键点击实例可以启动浏览器"
        )
    
    def delete_browser_instance(self, instance_id: str):
        """删除浏览器实例"""
        instance = self.browser_manager.get_instance(instance_id)
        if not instance:
            return
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除浏览器实例 '{instance.fanqie_nickname}' 吗？\n"
            f"所有的登录状态和数据将被清除。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.browser_manager.remove_instance(instance_id)
            self.refresh_browser_list(self.current_username)
    
    def start_browser(self, instance_id: str):
        """启动浏览器"""
        instance = self.browser_manager.get_instance(instance_id)
        if not instance:
            return
        
        # 更新状态
        for i in range(self.browser_list.count()):
            item = self.browser_list.item(i)
            if item.data(Qt.UserRole) == instance_id:
                item.setText(f"🔄 {instance.fanqie_nickname} (启动中...)")
                break
        
        def do_start():
            success = self.browser_manager.start_instance(instance_id, headless=False)
            self.refresh_browser_list(self.current_username)
            
            if not success:
                QMessageBox.warning(
                    self, "启动失败",
                    f"浏览器启动失败:\n{instance.last_error}"
                )
        
        QTimer.singleShot(100, do_start)
    
    def stop_browser(self, instance_id: str):
        """停止浏览器"""
        self.browser_manager.stop_instance(instance_id)
        self.refresh_browser_list(self.current_username)
    
    def start_all_browsers(self):
        """启动当前账户的所有浏览器"""
        if not hasattr(self, 'current_username'):
            return
        
        instances = self.browser_manager.get_instances_by_website_user(self.current_username)
        stopped = [inst for inst in instances if inst.status == "stopped"]
        
        if not stopped:
            QMessageBox.information(self, "提示", "没有需要启动的浏览器")
            return
        
        reply = QMessageBox.question(
            self, "确认",
            f"确定要启动 {len(stopped)} 个浏览器实例吗？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            for inst in stopped:
                self.start_browser(inst.instance_id)
    
    def use_selected_account(self):
        """使用选中的账户"""
        if not hasattr(self, 'current_username'):
            return
        
        # 获取选中的浏览器实例
        item = self.browser_list.currentItem()
        if not item:
            QMessageBox.information(self, "提示", "请先选择一个浏览器实例")
            return
        
        instance_id = item.data(Qt.UserRole)
        instance = self.browser_manager.get_instance(instance_id)
        
        if instance and instance.status != "running":
            QMessageBox.information(self, "提示", "请先启动浏览器")
            return
        
        # 发射信号
        self.account_selected.emit(self.current_username, instance.fanqie_nickname)
        self.accept()
    
    def closeEvent(self, event):
        """关闭事件"""
        # 不需要停止浏览器，让它们保持运行
        event.accept()


if __name__ == "__main__":
    import sys
    from PyQt5.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    # 测试
    manager = MultiAccountManager()
    dialog = AccountManagerDialog(account_manager=manager)
    dialog.show()
    
    sys.exit(app.exec_())
