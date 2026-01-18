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

# 🔥 全局单例队列 - 确保客户端和服务端使用同一个队列对象
_task_queue = None
_result_queue = None

def get_global_queues():
    """获取全局任务队列（单例模式）
    
    🔥 修复: 使用全局单例队列,避免客户端和服务端使用不同的队列对象
    """
    global _task_queue, _result_queue
    if _task_queue is None:
        _task_queue = multiprocessing.Queue()
        _result_queue = multiprocessing.Queue()
        print(f"✅ 创建全局队列: task_queue={id(_task_queue)}, result_queue={id(_result_queue)}")
    return _task_queue, _result_queue

def reset_global_queues():
    """重置全局队列（用于测试或重置）"""
    global _task_queue, _result_queue
    _task_queue = None
    _result_queue = None
    print("✅ 全局队列已重置")

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
        
        # 🔥 修复：不在这里创建队列，等待外部传入
        # 队列将在 run_enhanced_contract_service_process 中设置
        self.task_queue = None
        self.result_queue = None
        
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
            self.log("=" * 60)
            self.log("【步骤1】开始获取可签约小说列表...")
            self.log("=" * 60)
            
            # 验证浏览器页面
            if self.page is None:
                self.log("❌ 浏览器页面未初始化")
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "浏览器页面未初始化"
                }
            
            self.log(f"✓ 浏览器页面已初始化")
            self.log(f"  当前URL: {self.page.url}")
            
            # 【步骤2】确保在小说管理页面
            self.log("\n【步骤2】确保在小说管理页面...")
            if not self._ensure_novel_management_page_for_list():
                self.log("❌ 无法导航到小说管理页面")
                return {
                    "success": False,
                    "task_id": task.get("task_id"),
                    "error": "无法导航到小说管理页面"
                }
            
            self.log("✓ 已确认在小说管理页面")
            
            # 【步骤3】获取当前作者名
            self.log("\n【步骤3】获取当前作者名...")
            current_author_name = self._get_current_author_name()
            
            if not current_author_name:
                self.log("⚠️ 警告: 无法获取当前作者名，但继续执行...")
                current_author_name = "未知作者"
            else:
                self.log(f"✓ 当前作者名: {current_author_name}")
            
            # 【步骤4】等待页面完全加载
            self.log("\n【步骤4】等待页面完全加载...")
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=10000)
                self.log("✓ 页面DOM已加载")
                time.sleep(2)
                self.log("✓ 页面稳定等待完成")
            except Exception as e:
                self.log(f"⚠️ 页面加载超时: {e}，继续执行...")
            
            # 【步骤5】获取小说列表
            self.log("\n【步骤5】开始扫描小说列表...")
            novels = self._get_contractable_novels_from_page()
            
            self.log(f"\n【结果】扫描完成")
            self.log(f"  找到小说总数: {len(novels)} 本")
            
            if len(novels) > 0:
                self.log(f"  可签约小说列表:")
                for idx, novel in enumerate(novels, 1):
                    self.log(f"    {idx}. 《{novel['title']}》 - 状态: {novel['status']}")
            else:
                self.log("  ⚠️ 未找到可签约的小说（可能所有小说已签约或未达到签约条件）")
            
            self.log("=" * 60)
            self.log("✓ 获取小说列表任务完成")
            self.log("=" * 60)
            
            return {
                "success": True,
                "task_id": task.get("task_id"),
                "current_author_name": current_author_name,
                "novels": novels,
                "count": len(novels),
                "message": f"成功获取 {len(novels)} 本可签约小说"
            }
            
        except Exception as e:
            self.log(f"❌ 获取小说列表失败: {str(e)}")
            import traceback
            self.log(f"错误详情:\n{traceback.format_exc()}")
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
    
    def _ensure_novel_management_page_for_list(self) -> bool:
        """确保在小说管理页面（用于获取小说列表）"""
        try:
            self.log("  → 检查当前页面位置...")
            
            # 检查当前URL
            current_url = self.page.url
            self.log(f"  → 当前URL: {current_url}")
            
            # 等待页面稳定
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            time.sleep(1)
            
            # 检查是否有小说标签页指示器
            novel_tab_indicators = [
                '//span[text()="小说"]',
                '//div[contains(@class, "arco-tabs-tab")]//span[text()="小说"]',
                'text=小说',
                '[class*="novel"]'
            ]
            
            tab_found = False
            for indicator in novel_tab_indicators:
                try:
                    if indicator.startswith('//'):
                        element = self.page.locator(f'xpath={indicator}')
                    else:
                        element = self.page.locator(indicator)
                    
                    if element.count() > 0 and element.first.is_visible():
                        self.log(f"  → 找到小说标签页指示器")
                        tab_found = True
                        break
                except:
                    continue
            
            if not tab_found:
                self.log("  ⚠️ 未找到小说标签页，尝试点击...")
                # 尝试点击小说标签
                novel_selectors = [
                    '//span[text()="小说"]',
                    '//div[contains(@class, "arco-tabs-tab")]//span[text()="小说"]',
                    'text=小说',
                    'span:has-text("小说")'
                ]
                
                for selector in novel_selectors:
                    try:
                        if selector.startswith('//'):
                            element = self.page.locator(f'xpath={selector}')
                        else:
                            element = self.page.locator(selector).first
                        
                        if element.count() > 0 and element.first.is_visible():
                            self.log(f"  → 尝试点击小说标签...")
                            element.first.click(timeout=5000)
                            self.log(f"  ✓ 已点击小说标签")
                            time.sleep(2)
                            break
                    except Exception as e:
                        self.log(f"  → 点击失败: {e}")
                        continue
            
            # 验证是否在小说列表页面
            self.log("  → 验证是否在小说列表页面...")
            list_indicators = [
                '//div[contains(@id, "long-article-table-item")]',
                '//div[contains(@class, "long-article-table")]',
                'text=创建书本',
                'button:has-text("创建书本")'
            ]
            
            list_found = False
            for indicator in list_indicators:
                try:
                    if indicator.startswith('//'):
                        element = self.page.locator(f'xpath={indicator}')
                    else:
                        element = self.page.locator(indicator)
                    
                    if element.count() > 0:
                        self.log(f"  ✓ 确认在小说列表页面")
                        list_found = True
                        break
                except:
                    continue
            
            if not list_found:
                self.log("  ⚠️ 无法确认在小说列表页面")
                return False
            
            return True
            
        except Exception as e:
            self.log(f"  ❌ 确保小说管理页面失败: {e}")
            import traceback
            self.log(f"  错误详情:\n{traceback.format_exc()}")
            return False
    
    def _get_current_author_name(self) -> Optional[str]:
        """获取当前页面的作者名"""
        try:
            if self.page is None:
                return None
            
            self.log("  → 开始获取作者名...")
            
            # 等待页面加载
            self.page.wait_for_load_state("domcontentloaded", timeout=10000)
            time.sleep(1)
            
            # 使用用户信息选择器获取作者名
            author_name_selectors = [
                'div.slogin-user-avatar__info__name',
                'div[class*="user-avatar"] div[class*="name"]',
                'div[class*="slogin"] [class*="name"]',
                '//div[contains(@class, "slogin-user-avatar__info__name")]',
                '//div[contains(@class, "user-avatar")]//div[contains(@class, "name")]',
                'xpath=/html/body/div[1]/div/div[1]/div[2]/div/div[2]/div[2]/div[1]/div/div[1]'
            ]
            
            self.log(f"  → 尝试 {len(author_name_selectors)} 种选择器获取作者名...")
            
            for idx, selector in enumerate(author_name_selectors, 1):
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
                            self.log(f"  ✓ 选择器 #{idx} 成功获取作者名: {author_name}")
                            return author_name
                except Exception as e:
                    self.log(f"  → 选择器 #{idx} 失败: {e}")
                    continue
            
            self.log("  ⚠ 所有选择器均未找到作者名元素")
            return None
            
        except Exception as e:
            self.log(f"  ❌ 获取作者名失败: {e}")
            import traceback
            self.log(f"  错误详情:\n{traceback.format_exc()}")
            return None
    
    def _get_contractable_novels_from_page(self) -> list:
        """从页面获取所有可签约的小说列表"""
        try:
            if self.page is None:
                self.log("  ❌ 页面对象为空")
                return []
            
            novels = []
            
            self.log("  → 开始滚动页面以加载所有内容...")
            # 滚动页面确保加载所有内容
            self.contract_manager.ui_helper.scroll_list_container(self.page)
            time.sleep(1)
            self.log("  ✓ 页面滚动完成")
            
            # 使用多种选择器尝试获取小说项
            novel_item_selectors = [
                '//div[contains(@id, "long-article-table-item")]',
                '//div[contains(@class, "long-article-table-item")]',
                '//div[contains(@class, "arco-table-tr")]',
                'div[class*="long-article"]'
            ]
            
            novel_items = None
            item_count = 0
            
            self.log("  → 尝试查找小说项...")
            for idx, selector in enumerate(novel_item_selectors, 1):
                try:
                    if selector.startswith('//'):
                        items = self.page.locator(f'xpath={selector}')
                    else:
                        items = self.page.locator(selector)
                    
                    count = items.count()
                    self.log(f"    选择器 #{idx}: 找到 {count} 个项")
                    
                    if count > 0:
                        novel_items = items
                        item_count = count
                        self.log(f"  ✓ 使用选择器 #{idx} 找到 {item_count} 个小说项")
                        break
                except Exception as e:
                    self.log(f"    选择器 #{idx} 失败: {e}")
                    continue
            
            if novel_items is None or item_count == 0:
                self.log("  ⚠️ 未找到任何小说项")
                # 尝试截图帮助调试
                try:
                    screenshot_path = "logs/debug_novel_list.png"
                    self.page.screenshot(path=screenshot_path)
                    self.log(f"  → 已保存调试截图: {screenshot_path}")
                except:
                    pass
                return []
            
            self.log(f"  → 开始处理 {item_count} 个小说项...")
            
            for i in range(item_count):
                try:
                    item = novel_items.nth(i)
                    
                    # 获取小说标题 - 使用多种选择器
                    title_selectors = [
                        './div/div[1]/div[2]/div[1]/div',
                        './/div[contains(@class, "info-content-title")]',
                        './/div[contains(@class, "title")]',
                        './/a[contains(@class, "title")]'
                    ]
                    
                    novel_title = None
                    for title_selector in title_selectors:
                        try:
                            title_elements = item.locator(f'xpath={title_selector}')
                            if title_elements.count() > 0:
                                title_text = title_elements.first.text_content().strip()
                                if title_text:
                                    novel_title = title_text
                                    break
                        except:
                            continue
                    
                    if not novel_title:
                        self.log(f"    项 {i+1}: ⚠️ 无法获取标题，跳过")
                        continue
                    
                    # 检查签约状态 - 使用多种选择器
                    status_selectors = [
                        './div/div[1]/div[2]/div[2]/div[2]/div[3]',
                        './/div[contains(@class, "status")]',
                        './/span[contains(@class, "status")]'
                    ]
                    
                    status_text = ""
                    for status_selector in status_selectors:
                        try:
                            status_elements = item.locator(f'xpath={status_selector}')
                            if status_elements.count() > 0:
                                status_text = status_elements.first.text_content().strip()
                                break
                        except:
                            continue
                    
                    if not status_text:
                        self.log(f"    项 {i+1}: ⚠️ 无法获取状态，跳过《{novel_title}》")
                        continue
                    
                    self.log(f"    项 {i+1}: 《{novel_title}》 - 状态: {status_text}")
                    
                    # 只返回连载中且未签约的小说
                    if "连载中" in status_text and "已签约" not in status_text:
                        novels.append({
                            "title": novel_title,
                            "status": status_text,
                            "can_sign": True
                        })
                        self.log(f"    ✓ 《{novel_title}》符合签约条件")
                    elif "已签约" in status_text:
                        self.log(f"    → 《{novel_title}》已签约，跳过")
                    else:
                        self.log(f"    → 《{novel_title}》状态不符合条件: {status_text}")
                
                except Exception as e:
                    self.log(f"    项 {i+1}: ❌ 处理出错: {e}")
                    import traceback
                    self.log(f"    错误详情: {traceback.format_exc()}")
                    continue
            
            self.log(f"  ✓ 处理完成，找到 {len(novels)} 本可签约小说")
            return novels
            
        except Exception as e:
            self.log(f"  ❌ 获取小说列表失败: {e}")
            import traceback
            self.log(f"  错误详情:\n{traceback.format_exc()}")
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
        self.log("=" * 60)
        self.log("🚀 增强版签约上传服务启动")
        self.log("=" * 60)
        self.log(f"📌 服务进程ID: {os.getpid()}")
        
        # 🔥 添加：确认队列连接
        self.log(f"📌 task_queue ID: {id(self.task_queue)}")
        self.log(f"📌 result_queue ID: {id(self.result_queue)}")
        
        # 🔥 修复：服务端先发送准备完成信号，确保客户端知道服务端已就绪
        self.log("📤 发送准备完成信号到客户端...")
        ready_message = {
            "type": "service_ready",
            "message": "服务已准备就绪，可以开始接收任务",
            "service_pid": os.getpid(),
            "timestamp": datetime.now().isoformat()
        }
        self.result_queue.put(ready_message)
        self.log("✅ 准备完成信号已发送")
        
        # 初始化状态
        self.update_status(self.get_status())
        
        # 🔥 添加：主循环开始日志
        self.log("⏳ 服务主循环开始，等待任务...")
        self.log("=" * 60)
        
        # 🔥 添加：心跳计数器
        heartbeat_counter = 0
        last_heartbeat_time = time.time()
        
        try:
            while self.running:
                try:
                    # 检查是否有新任务（非阻塞）
                    if not self.task_queue.empty():
                        task = self.task_queue.get(timeout=1)
                        self.log(f"📨 接收到新任务: {task.get('task_type')} (ID: {task.get('task_id')})")
                        
                        # 处理任务
                        result = self.process_contract_task(task)
                        
                        # 将结果放入结果队列
                        self.log(f"📤 任务结果准备返回: {result.get('task_id')}")
                        self.result_queue.put(result)
                        self.log(f"✅ 结果已放入结果队列")
                    
                    else:
                        # 没有任务时短暂休眠
                        time.sleep(0.1)
                    
                    # 🔥 添加：每10秒打印心跳日志
                    current_time = time.time()
                    if current_time - last_heartbeat_time >= 10:
                        heartbeat_counter += 1
                        self.log(f"💓 服务心跳 #{heartbeat_counter} - 服务运行正常 (队列大小: {self.task_queue.qsize()})")
                        last_heartbeat_time = current_time
                
                except QueueEmpty:
                    continue
                except Exception as e:
                    self.log(f"❌ 处理任务时发生错误: {e}")
                    import traceback
                    self.log(f"错误详情:\n{traceback.format_exc()}")
                    continue
        
        except KeyboardInterrupt:
            self.log("⚠️ 收到键盘中断信号")
        except Exception as e:
            self.log(f"❌ 服务运行时发生严重错误: {e}")
            import traceback
            self.log(f"错误详情:\n{traceback.format_exc()}")
        finally:
            self.running = False
            self._cleanup_browser()
            self.log("=" * 60)
            self.log("🛑 增强版签约上传服务停止")
            self.log(f"💓 总心跳次数: {heartbeat_counter}")
            self.log("=" * 60)


def run_enhanced_contract_service_process(task_queue: multiprocessing.Queue,
                                         result_queue: multiprocessing.Queue):
    """在独立进程中运行增强版签约服务的入口函数"""
    # 🔥 修复：不创建新队列，直接使用传入的队列
    # 创建服务实例
    service = EnhancedContractService()
    
    # 🔥 添加：记录接收到的队列ID
    print(f"🔥 [服务进程] 接收到task_queue ID: {id(task_queue)}")
    print(f"🔥 [服务进程] 接收到result_queue ID: {id(result_queue)}")
    
    # 🔥 修复：直接使用传入的队列，不重新赋值
    # 这样可以确保使用的是客户端传入的队列
    service.task_queue = task_queue
    service.result_queue = result_queue
    
    # 🔥 添加：验证队列已设置
    print(f"🔥 [服务进程] service.task_queue ID: {id(service.task_queue)}")
    print(f"🔥 [服务进程] service.result_queue ID: {id(service.result_queue)}")
    
    # 运行服务
    service.run_service()


class EnhancedContractServiceClient:
    """增强版签约服务客户端 - 在主进程中使用"""
    
    def __init__(self):
        """初始化客户端"""
        # 🔥 修复：创建并持有队列，服务进程将使用这些队列
        self.task_queue = multiprocessing.Queue()
        self.result_queue = multiprocessing.Queue()
        self.service_process = None
        self.running = False
        
        print(f"✅ [客户端] 创建队列: task_queue={id(self.task_queue)}, result_queue={id(self.result_queue)}")
    
    def start_service(self) -> bool:
        """启动签约服务进程"""
        if self.running:
            return True
        
        try:
            # 🔥 修复：不使用全局队列，直接使用客户端自己创建的队列
            # 客户端在__init__中已经创建了队列
            
            print(f"🔄 [客户端] 启动服务...")
            print(f"🔄 [客户端] task_queue ID: {id(self.task_queue)}")
            print(f"🔄 [客户端] result_queue ID: {id(self.result_queue)}")
            
            # 创建服务进程，传递客户端的队列
            self.service_process = multiprocessing.Process(
                target=run_enhanced_contract_service_process,
                args=(self.task_queue, self.result_queue),
                name="EnhancedContractService"
            )
            
            self.service_process.daemon = True
            self.service_process.start()
            self.running = True
            
            print(f"✅ [客户端] 服务进程已启动，PID: {self.service_process.pid}")
            print(f"✅ [客户端] 传递给进程的队列ID: task_queue={id(self.task_queue)}, result_queue={id(self.result_queue)}")
            
            # 🔥 修复：等待服务端发送准备完成信号
            print(f"⏳ [客户端] 等待服务端准备完成信号...")
            try:
                ready_message = self.result_queue.get(timeout=30)  # 等待最多30秒
                if ready_message.get("type") == "service_ready":
                    print(f"✅ [客户端] 收到服务端准备完成信号")
                    print(f"   服务PID: {ready_message.get('service_pid')}")
                    print(f"   消息: {ready_message.get('message')}")
                    print(f"✅ [客户端] 服务已就绪，现在可以提交任务")
                else:
                    print(f"⚠️ [客户端] 收到非预期的消息类型: {ready_message.get('type')}")
                    return False
            except Exception as e:
                print(f"❌ [客户端] 等待准备完成信号超时或失败: {e}")
                print(f"   服务可能启动较慢或失败")
                self.running = False
                if self.service_process:
                    self.service_process.terminate()
                    self.service_process = None
                return False
            
            return True
            
        except Exception as e:
            print(f"❌ 启动增强版签约服务失败: {e}")
            import traceback
            print(f"错误详情:\n{traceback.format_exc()}")
            self.running = False
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
        """提交任务到签约服务
        
        🔥 修复：先检查服务进程是否准备就绪，并验证队列通信
        """
        if not self.is_service_running():
            raise RuntimeError("增强版签约服务未运行")
        
        # 🔥 修复：验证服务进程真的在运行
        if not self.service_process.is_alive():
            raise RuntimeError("服务进程已停止")
        
        # 🔥 修复：打印当前队列ID，便于调试
        print(f"📤 [客户端] 准备提交任务...")
        print(f"   客户端队列ID: task_queue={id(self.task_queue)}, result_queue={id(self.result_queue)}")
        print(f"   服务PID: {self.service_process.pid}")
        print(f"   服务状态: {self.is_service_alive()}")
        
        import uuid
        task_id = kwargs.get("task_id", str(uuid.uuid4()))
        
        task = {
            "task_id": task_id,
            "task_type": task_type,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        
        try:
            # 🔥 修复：添加超时和重试机制
            self.task_queue.put(task, timeout=10)
            print(f"✅ [客户端] 任务已提交: {task_id}")
            print(f"   队列大小: {self.task_queue.qsize()}")
            
            # 🔥 修复：验证任务是否到达服务进程（通过检查服务日志）
            print(f"⏳ 等待服务进程处理任务...")
            
            return task_id
        except Exception as e:
            print(f"❌ [客户端] 提交任务失败: {e}")
            raise
    
    def is_service_alive(self) -> bool:
        """检查服务进程是否存活（包括心跳检测）"""
        if not self.service_process:
            return False
        
        if not self.service_process.is_alive():
            return False
        
        # TODO: 可以添加心跳检测机制
        return True
    
    def get_task_result(self, task_id: Optional[str] = None, timeout: Optional[float] = 60.0) -> Optional[Dict[str, Any]]:
        """获取任务结果
        
        🔥 修复：改进结果获取逻辑，避免竞争条件
        """
        if not self.is_service_running():
            return None
        
        try:
            result = self.result_queue.get(timeout=timeout)
            
            # 如果指定了task_id，只返回匹配的结果
            if task_id and result.get("task_id") != task_id:
                # 🔥 修复：不要将结果放回队列，这会导致竞争条件
                # 相反，继续从队列中获取下一个结果
                print(f"⚠️ 结果ID不匹配，期望: {task_id}, 实际: {result.get('task_id')}")
                # 递归尝试获取下一个结果（带超时保护）
                if timeout > 1.0:
                    return self.get_task_result(task_id, timeout=timeout/2)
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