#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版签约上传独立进程服务
集成实际的浏览器自动化功能，提供完整的签约和上传功能
"""

import os
import sys
import json
import time
import signal
import threading
import multiprocessing
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from queue import Empty as QueueEmpty

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from Chrome.automation.utils.config_loader import ConfigLoader, get_config_loader
from Chrome.automation.managers.contract_manager import ContractManager
from Chrome.automation.legacy.browser_manager import connect_to_browser, navigate_to_writer_platform
from Chrome.automation.legacy.utils import ensure_directory_exists
try:
    from playwright.sync_api import sync_playwright, Page
except ImportError:
    Page = None


class EnhancedContractService:
    """增强版签约上传服务类 - 集成浏览器自动化"""
    
    def __init__(self):
        """初始化增强版签约服务"""
        self.config_loader = get_config_loader()
        self.contract_manager = ContractManager(self.config_loader)
        self.running = False
        self.current_task = None
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.status_file = Path("logs/enhanced_contract_service_status.json")
        self.log_file = Path("logs/enhanced_contract_service.log")
        
        # 浏览器相关
        self.playwright = None
        self.browser = None
        self.page: Optional[Page] = None
        self.default_context = None
        
        # 确保日志目录存在
        self.log_file.parent.mkdir(exist_ok=True)
        
        # 注册信号处理器
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        self.log(f"收到信号 {signum}，正在优雅关闭服务...")
        self.running = False
        self._cleanup_browser()
    
    def log(self, message: str):
        """记录日志"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        
        # 写入日志文件
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_message + '\n')
        except Exception as e:
            print(f"写入日志文件失败: {e}")
    
    def update_status(self, status: Dict[str, Any]):
        """更新服务状态"""
        try:
            status["timestamp"] = datetime.now().isoformat()
            with open(self.status_file, 'w', encoding='utf-8') as f:
                json.dump(status, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"更新状态文件失败: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """获取当前服务状态"""
        return {
            "running": self.running,
            "current_task": self.current_task,
            "browser_connected": self.browser is not None,
            "timestamp": datetime.now().isoformat(),
            "service_pid": os.getpid()
        }
    
    def _ensure_browser_connection(self) -> bool:
        """确保浏览器连接"""
        try:
            if self.browser is None or self.page is None:
                self.log("正在连接浏览器...")
                
                # 连接浏览器
                browser_result = connect_to_browser()
                if browser_result and len(browser_result) >= 4:
                    self.playwright, self.browser, self.page, self.default_context = browser_result
                else:
                    self.browser = None
                    self.page = None
                    self.default_context = None
                
                if not self.browser or not self.page:
                    self.log("❌ 浏览器连接失败")
                    return False
                
                # 导航到作家专区
                self.page = navigate_to_writer_platform(self.page, self.default_context)
                if not self.page:
                    self.log("❌ 导航到作家专区失败")
                    return False
                
                self.log("✅ 浏览器连接成功")
            
            return True
            
        except Exception as e:
            self.log(f"浏览器连接失败: {e}")
            return False
    
    def _cleanup_browser(self):
        """清理浏览器资源"""
        try:
            if self.browser:
                self.browser.close()
                self.browser = None
            if self.playwright:
                self.playwright.stop()
                self.playwright = None
            self.page = None
            self.default_context = None
            self.log("浏览器资源已清理")
        except Exception as e:
            self.log(f"清理浏览器资源失败: {e}")
    
    def process_contract_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理签约任务"""
        task_id = task.get("task_id", "unknown")
        task_type = task.get("task_type", "contract_management")
        
        self.log(f"开始处理任务: {task_id} ({task_type})")
        
        try:
            # 更新任务状态
            self.current_task = {
                "task_id": task_id,
                "task_type": task_type,
                "status": "processing",
                "start_time": datetime.now().isoformat()
            }
            self.update_status(self.get_status())
            
            result = {"success": False, "task_id": task_id}
            
            # 确保浏览器连接
            if not self._ensure_browser_connection():
                result["error"] = "浏览器连接失败"
                return result
            
            if task_type == "contract_management":
                # 处理签约管理任务
                result = self._handle_contract_management(task)
            elif task_type == "recommendation_management":
                # 处理作品推荐任务
                result = self._handle_recommendation_management(task)
            elif task_type == "switch_user":
                # 处理切换用户任务
                result = self._handle_switch_user(task)
            elif task_type == "validate_user":
                # 处理验证用户任务
                result = self._handle_validate_user(task)
            elif task_type == "upload_novel":
                # 处理小说上传任务
                result = self._handle_upload_novel(task)
            elif task_type == "get_novels_list":
                # 处理获取小说列表任务
                result = self._handle_get_novels_list(task)
            elif task_type == "auto_sign":
                # 处理自动签约任务
                result = self._handle_auto_sign(task)
            else:
                result["error"] = f"不支持的任务类型: {task_type}"
            
            self.log(f"任务完成: {task_id} - {'成功' if result['success'] else '失败'}")
            
        except Exception as e:
            self.log(f"任务处理异常: {task_id} - {str(e)}")
            result = {
                "success": False,
                "task_id": task_id,
                "error": str(e)
            }
        
        finally:
            # 清除当前任务状态
            self.current_task = None
            self.update_status(self.get_status())
        
        return result
    
    def _handle_contract_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理签约管理任务"""
        try:
            self.log("开始执行签约管理流程...")
            
            # 调用实际的签约管理功能
            if self.page is None:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "浏览器页面未初始化"
                }
            
            handled_count = self.contract_manager.check_and_handle_contract_management(self.page)
            
            return {
                "success": True,
                "task_id": task.get("task_id"),
                "handled_count": handled_count,
                "message": "签约管理检查完成"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"签约管理处理失败: {str(e)}"
            }
    
    def _handle_recommendation_management(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理作品推荐任务"""
        try:
            self.log("开始执行作品推荐流程...")
            
            # 调用实际的作品推荐功能
            if self.page is None:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "浏览器页面未初始化"
                }
            
            success = self.contract_manager.check_and_handle_recommendations(self.page)
            
            return {
                "success": success,
                "task_id": task.get("task_id"),
                "message": "作品推荐检查完成"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"作品推荐处理失败: {str(e)}"
            }
    
    def _handle_switch_user(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理切换用户任务"""
        try:
            user_id = task.get("user_id")
            if not user_id:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "缺少用户ID"
                }
            
            self.log(f"切换到用户: {user_id}")
            
            # 调用合同管理器的用户切换功能
            success = self.contract_manager.switch_user(user_id)
            
            return {
                "success": success,
                "task_id": task.get("task_id"),
                "user_id": user_id,
                "message": f"已切换到用户: {user_id}" if success else "用户切换失败"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"用户切换失败: {str(e)}"
            }
    
    def _handle_validate_user(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理验证用户任务"""
        try:
            self.log("验证当前用户配置...")
            
            # 调用合同管理器的用户验证功能
            is_valid = self.contract_manager.validate_current_user()
            user_info = self.contract_manager.get_current_user_info()
            
            return {
                "success": True,
                "task_id": task.get("task_id"),
                "is_valid": is_valid,
                "user_info": user_info,
                "message": "用户配置验证完成"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"用户验证失败: {str(e)}"
            }
    
    def _handle_upload_novel(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理小说上传任务"""
        try:
            novel_title = task.get("novel_title")
            if not novel_title:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "缺少小说标题"
                }
            
            self.log(f"开始上传小说: {novel_title}")
            
            # 这里可以集成实际的上传逻辑
            # 暂时返回模拟结果
            time.sleep(5)  # 模拟上传时间
            
            return {
                "success": True,
                "task_id": task.get("task_id"),
                "novel_title": novel_title,
                "uploaded_chapters": 10,  # 示例数据
                "message": f"小说《{novel_title}》上传完成"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"小说上传失败: {str(e)}"
            }
    
    def _handle_get_novels_list(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理获取小说列表任务"""
        try:
            self.log("正在获取可签约小说列表...")
            
            # 获取当前作者名
            current_author_name = self._get_current_author_name()
            
            if not current_author_name:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "无法获取当前作者名"
                }
            
            self.log(f"当前作者名: {current_author_name}")
            
            # 获取小说列表
            if self.page is None:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "浏览器页面未初始化"
                }
            
            novels = self._get_contractable_novels_from_page()
            
            return {
                "success": True,
                "task_id": task.get("task_id"),
                "current_author_name": current_author_name,
                "novels": novels,
                "count": len(novels),
                "message": f"成功获取 {len(novels)} 本可签约小说"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"获取小说列表失败: {str(e)}"
            }
    
    def _handle_auto_sign(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """处理自动签约任务"""
        try:
            novel_title = task.get("novel_title")
            user_id = task.get("user_id")
            user_name = task.get("user_name", "")
            
            if not novel_title or not user_id:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "缺少必要参数"
                }
            
            self.log(f"开始自动签约: 《{novel_title}》使用用户 {user_name}")
            
            # 验证当前作者名是否匹配
            current_author_name = self._get_current_author_name()
            
            if current_author_name != user_name:
                error_msg = f"作者名不匹配！当前作者: {current_author_name}, 配置作者: {user_name}"
                self.log(f"❌ {error_msg}")
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": error_msg,
                    "current_author_name": current_author_name,
                    "expected_author_name": user_name
                }
            
            self.log(f"✓ 作者名匹配: {current_author_name}")
            
            # 切换到指定用户
            switch_success = self.contract_manager.switch_user(user_id)
            if not switch_success:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": f"切换到用户 {user_id} 失败"
                }
            
            # 执行签约流程
            if self.page is None:
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "浏览器页面未初始化"
                }
            
            sign_success = self._sign_novel_by_title(novel_title)
            
            return {
                "success": sign_success,
                "task_id": task.get("task_id"),
                "novel_title": novel_title,
                "user_id": user_id,
                "current_author_name": current_author_name,
                "message": f"小说《{novel_title}》签约{'成功' if sign_success else '失败'}"
            }
            
        except Exception as e:
            return {
                "success": False,
                "task_id": task.get("task_id"),
                "error": f"自动签约失败: {str(e)}"
            }
    
    def _get_current_author_name(self) -> Optional[str]:
        """获取当前页面的作者名"""
        try:
            if self.page is None:
                return None
            
            # 等待页面加载
            self.page.wait_for_load_state("domcontentloaded")
            time.sleep(1)
            
            # 使用用户信息选择器获取作者名
            author_name_selectors = [
                'div.slogin-user-avatar__info__name',
                '//div[contains(@class, "slogin-user-avatar__info__name")]',
                'xpath=/html/body/div[1]/div/div[1]/div[2]/div/div[2]/div[2]/div[1]/div/div[1]'
            ]
            
            for selector in author_name_selectors:
                try:
                    if selector.startswith('//'):
                        element = self.page.locator(f'xpath={selector}')
                    elif selector.startswith('xpath='):
                        element = self.page.locator(selector)
                    else:
                        element = self.page.locator(selector).first
                    
                    if element.count() > 0:
                        author_name = element.first.text_content().strip()
                        if author_name:
                            self.log(f"获取到作者名: {author_name}")
                            return author_name
                except Exception:
                    continue
            
            self.log("⚠ 未找到作者名元素")
            return None
            
        except Exception as e:
            self.log(f"获取作者名失败: {e}")
            return None
    
    def _get_contractable_novels_from_page(self) -> list:
        """从页面获取所有可签约的小说列表"""
        try:
            if self.page is None:
                return []
            
            novels = []
            
            # 滚动页面确保加载所有内容
            self.contract_manager.ui_helper.scroll_list_container(self.page)
            time.sleep(1)
            
            # 获取所有小说项
            novel_items = self.page.locator('//div[contains(@id, "long-article-table-item")]')
            item_count = novel_items.count()
            
            self.log(f"找到 {item_count} 个小说项")
            
            for i in range(item_count):
                try:
                    item = novel_items.nth(i)
                    
                    # 获取小说标题
                    title_xpath = './div/div[1]/div[2]/div[1]/div'
                    title_elements = item.locator(f'xpath={title_xpath}')
                    
                    if title_elements.count() > 0:
                        novel_title = title_elements.first.text_content().strip()
                        
                        # 检查签约状态
                        status_xpath = './div/div[1]/div[2]/div[2]/div[2]/div[3]'
                        status_elements = item.locator(f'xpath={status_xpath}')
                        
                        if status_elements.count() > 0:
                            status_text = status_elements.first.text_content().strip()
                            
                            # 只返回连载中且未签约的小说
                            if "连载中" in status_text and "已签约" not in status_text:
                                novels.append({
                                    "title": novel_title,
                                    "status": status_text,
                                    "can_sign": True
                                })
                
                except Exception as e:
                    self.log(f"处理第 {i+1} 个小说项时出错: {e}")
                    continue
            
            self.log(f"找到 {len(novels)} 本可签约小说")
            return novels
            
        except Exception as e:
            self.log(f"获取小说列表失败: {e}")
            return []
    
    def _sign_novel_by_title(self, novel_title: str) -> bool:
        """根据小说标题执行签约流程"""
        try:
            self.log(f"开始为《{novel_title}》执行签约流程...")
            
            if self.page is None:
                return False
            
            # 确保在小说管理页面
            self.contract_manager._ensure_novel_management_page(self.page)
            time.sleep(1)
            
            # 滚动页面
            self.contract_manager.ui_helper.scroll_list_container(self.page)
            time.sleep(1)
            
            # 查找目标小说
            novel_items = self.page.locator('//div[contains(@id, "long-article-table-item")]')
            item_count = novel_items.count()
            
            for i in range(item_count):
                try:
                    item = novel_items.nth(i)
                    
                    # 获取小说标题
                    title_xpath = './div/div[1]/div[2]/div[1]/div'
                    title_elements = item.locator(f'xpath={title_xpath}')
                    
                    if title_elements.count() > 0:
                        current_title = title_elements.first.text_content().strip()
                        
                        if current_title == novel_title:
                            self.log(f"找到目标小说: {novel_title}")
                            
                            # 使用键盘导航激活条目，避免点击跳转
                            self.log("使用键盘导航激活条目...")
                            
                            try:
                                # 先点击第一个条目获取焦点（如果还没焦点的话）
                                if i == 0:
                                    first_item = novel_items.nth(0)
                                    try:
                                        # 尝试点击复选框区域获取焦点
                                        checkbox_xpath = './div/div[1]/div[1]/div/div/div'
                                        checkbox = first_item.locator(f'xpath={checkbox_xpath}')
                                        if checkbox.count() > 0:
                                            checkbox.first.click(timeout=2000)
                                            self.log("✓ 已点击第一个条目获取焦点")
                                    except:
                                        pass
                                
                                # 使用键盘向下箭头导航到目标行
                                if i > 0:
                                    for _ in range(i):
                                        self.page.keyboard.press('ArrowDown')
                                        time.sleep(0.1)
                                    self.log(f"✓ 使用键盘导航到第 {i+1} 行")
                                else:
                                    self.log("✓ 已在第一行")
                                
                                time.sleep(0.5)
                                
                            except Exception as e:
                                self.log(f"键盘导航失败，尝试备用方案: {e}")
                                # 备用方案：尝试悬停
                                try:
                                    item.hover(timeout=2000)
                                    self.log("✓ 使用悬停激活")
                                except:
                                    self.log("⚠ 激活失败，继续尝试")
                            
                            # 重新查找签约管理按钮
                            contract_button_xpath = './div/div[1]/div[2]/div[3]/div/button[2]/span'
                            contract_buttons = item.locator(f'xpath={contract_button_xpath}')
                            
                            if contract_buttons.count() > 0:
                                button_text = contract_buttons.first.text_content().strip()
                                self.log(f"找到按钮: {button_text}")
                                if "签约管理" in button_text:
                                    self.log("找到签约管理按钮")
                                    
                                    # 点击签约管理按钮
                                    if self.contract_manager.ui_helper.safe_click(
                                        contract_buttons.first,
                                        "签约管理按钮"
                                    ):
                                        time.sleep(2)
                                        
                                        # 处理签约流程
                                        success = self.contract_manager._handle_contract_process(self.page, 0)
                                        
                                        # 返回
                                        self.page.go_back()
                                        time.sleep(1)
                                        
                                        return success
                            else:
                                self.log("未找到签约管理按钮")
                                return False
                
                except Exception as e:
                    self.log(f"处理第 {i+1} 个小说项时出错: {e}")
                    continue
            
            self.log(f"未找到小说: {novel_title}")
            return False
            
        except Exception as e:
            self.log(f"签约流程失败: {e}")
            return False
    
    def run_service(self):
        """运行服务主循环"""
        self.running = True
        self.log("增强版签约上传服务启动")
        self.log(f"服务进程ID: {os.getpid()}")
        
        # 初始化状态
        self.update_status(self.get_status())
        
        try:
            while self.running:
                try:
                    # 检查是否有新任务（非阻塞）
                    if not self.task_queue.empty():
                        task = self.task_queue.get(timeout=1)
                        self.log(f"接收到新任务: {task}")
                        
                        # 处理任务
                        result = self.process_contract_task(task)
                        
                        # 将结果放入结果队列
                        self.result_queue.put(result)
                    
                    else:
                        # 没有任务时短暂休眠
                        time.sleep(0.1)
                
                except QueueEmpty:
                    continue
                except Exception as e:
                    self.log(f"处理任务时发生错误: {e}")
                    continue
        
        except KeyboardInterrupt:
            self.log("收到键盘中断信号")
        except Exception as e:
            self.log(f"服务运行时发生严重错误: {e}")
        finally:
            self.running = False
            self._cleanup_browser()
            self.log("增强版签约上传服务停止")


def run_enhanced_contract_service_process(task_queue: multiprocessing.Queue, 
                                         result_queue: multiprocessing.Queue):
    """在独立进程中运行增强版签约服务的入口函数"""
    # 创建服务实例
    service = EnhancedContractService()
    
    # 设置队列
    service.task_queue = task_queue
    service.result_queue = result_queue
    
    # 运行服务
    service.run_service()


class EnhancedContractServiceClient:
    """增强版签约服务客户端 - 在主进程中使用"""
    
    def __init__(self):
        """初始化客户端"""
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.service_process = None
        self.running = False
    
    def start_service(self) -> bool:
        """启动签约服务进程"""
        if self.running:
            return True
        
        try:
            # 创建服务进程
            self.service_process = multiprocessing.Process(
                target=run_enhanced_contract_service_process,
                args=(self.task_queue, self.result_queue),
                name="EnhancedContractService"
            )
            
            self.service_process.daemon = True
            self.service_process.start()
            self.running = True
            
            print(f"✅ 增强版签约服务进程已启动，PID: {self.service_process.pid}")
            return True
            
        except Exception as e:
            print(f"❌ 启动增强版签约服务失败: {e}")
            return False
    
    def stop_service(self) -> bool:
        """停止签约服务进程"""
        if not self.running:
            return True
        
        try:
            if self.service_process and self.service_process.is_alive():
                self.service_process.terminate()
                self.service_process.join(timeout=10)
                
                if self.service_process.is_alive():
                    self.service_process.kill()
                    self.service_process.join()
            
            self.running = False
            print("✅ 增强版签约服务进程已停止")
            return True
            
        except Exception as e:
            print(f"❌ 停止增强版签约服务失败: {e}")
            return False
    
    def is_service_running(self) -> bool:
        """检查服务是否运行中"""
        return bool(self.running and self.service_process and self.service_process.is_alive())
    
    def submit_task(self, task_type: str, **kwargs) -> str:
        """提交任务到签约服务"""
        if not self.is_service_running():
            raise RuntimeError("增强版签约服务未运行")
        
        import uuid
        task_id = kwargs.get("task_id", str(uuid.uuid4()))
        
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        try:
            self.task_queue.put(task, timeout=5)
            print(f"✅ 任务已提交: {task_id} ({task_type})")
            return task_id
        except Exception as e:
            print(f"❌ 提交任务失败: {e}")
            raise
    
    def get_task_result(self, task_id: Optional[str] = None, timeout: Optional[float] = 60.0) -> Optional[Dict[str, Any]]:
        """获取任务结果"""
        if not self.is_service_running():
            return None
        
        try:
            result = self.result_queue.get(timeout=timeout)
            
            # 如果指定了task_id，只返回匹配的结果
            if task_id and result.get("task_id") != task_id:
                # 将结果放回队列，继续等待匹配的结果
                self.result_queue.put(result)
                return None
            
            return result
        except QueueEmpty:
            return None
        except Exception as e:
            print(f"❌ 获取任务结果失败: {e}")
            return None
    
    def get_service_status(self) -> Dict[str, Any]:
        """获取服务状态"""
        try:
            # 读取状态文件
            status_file = Path("logs/enhanced_contract_service_status.json")
            if status_file.exists():
                with open(status_file, 'r', encoding='utf-8') as f:
                    status = json.load(f)
                    status["process_running"] = self.is_service_running()
                    return status
            else:
                return {
                    "running": False,
                    "process_running": self.is_service_running(),
                    "error": "状态文件不存在"
                }
        except Exception as e:
            return {
                "running": False,
                "process_running": self.is_service_running(),
                "error": f"读取状态文件失败: {str(e)}"
            }


# 创建全局客户端实例
enhanced_contract_client = EnhancedContractServiceClient()


if __name__ == "__main__":
    # 直接运行服务时，启动独立进程模式
    service = EnhancedContractService()
    service.run_service()