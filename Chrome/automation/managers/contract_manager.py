"""
签约管理模块
处理番茄小说平台的签约申请和作品推荐功能
"""

import time
import re
from typing import Set, Dict, Any, Optional
from playwright.sync_api import Page
from ..utils.ui_helper import UIHelper
from ..utils.config_loader import ConfigLoader


class ContractManager:
    """签约管理器类"""
    
    def __init__(self, config_loader: Optional[ConfigLoader] = None):
        """
        初始化签约管理器
        
        Args:
            config_loader: 配置加载器实例
        """
        self.config_loader = config_loader
        self.ui_helper = UIHelper(config_loader)
        self.failed_novels: Set[str] = set()  # 记录签约失败的小说
        self.processed_book_ids: Set[str] = set()  # 记录已处理的小说ID
        self.max_retry_count = 2  # 最大重试次数
        
        # 从配置加载器获取重试次数
        if self.config_loader:
            self.max_retry_count = self.config_loader.get('contract.max_retry_count', 2)
    
    def check_and_handle_contract_management(self, page: Page) -> bool:
        """
        检查并处理签约管理
        
        Args:
            page: 页面对象
            
        Returns:
            是否处理了任何小说
        """
        print("\n=== 开始检查签约管理 ===")
        
        try:
            # 确保在小说管理页面
            self._ensure_novel_management_page(page)
            
            max_pages = 100
            direction = "next"
            page_num = 1
            handled_count = 0
            skipped_count = 0
            
            while page_num <= max_pages:
                print(f"检查第 {page_num} 页的签约状态...")
                
                # 使用列表容器的滚动方法
                self.ui_helper.scroll_list_container(page)
                
                # 快速检查整页状态
                all_contracted_or_failed = self._quick_check_page_status(page)
                
                if all_contracted_or_failed:
                    print(f"第 {page_num} 页全部是已签约或已跳过小说，快速翻页...")
                    
                    next_result = self.ui_helper.navigate_to_next_page(page, direction)
                    if next_result:
                        page_num += 1
                        time.sleep(0.5)
                        continue
                    elif direction == "next":
                        print("已到达最后一页，切换到上一页方向...")
                        direction = "prev"
                        prev_result = self.ui_helper.navigate_to_next_page(page, "prev")
                        if prev_result:
                            page_num += 1
                            time.sleep(0.5)
                            continue
                        else:
                            print("无法切换到上一页，停止检查")
                            break
                    else:
                        print("已到达第一页，停止检查")
                        break
                
                # 详细处理页面
                print(f"第 {page_num} 页有未签约小说，进行详细处理...")
                page_handled, page_skipped = self._process_page_contracts(page)
                handled_count += page_handled
                skipped_count += page_skipped
                
                # 翻页逻辑
                if page_num < max_pages:
                    next_result = self.ui_helper.navigate_to_next_page(page, direction)
                    if next_result:
                        page_num += 1
                        time.sleep(0.5)
                    elif direction == "next":
                        print("已到达最后一页，切换到上一页方向...")
                        direction = "prev"
                        prev_result = self.ui_helper.navigate_to_next_page(page, "prev")
                        if prev_result:
                            page_num += 1
                            time.sleep(0.5)
                        else:
                            print("无法切换到上一页，停止检查")
                            break
                    else:
                        print("已到达第一页，停止检查")
                        break
                else:
                    print(f"已达到最大页数 {max_pages}，停止检查")
                    break
            
            print(f"=== 签约管理检查完成，共处理 {handled_count} 个小说，跳过 {skipped_count} 个失败小说 ===")
            return handled_count > 0 or skipped_count > 0
            
        except Exception as e:
            print(f"检查签约管理时出错: {e}")
            return False
    
    def check_and_handle_recommendations(self, page: Page) -> bool:
        """
        检查并处理作品推荐
        
        Args:
            page: 页面对象
            
        Returns:
            是否处理成功
        """
        print("\n=== 开始检查作品推荐 ===")
        
        try:
            max_pages = 100
            for page_num in range(1, max_pages + 1):
                print(f"\n--- 正在检查第 {page_num} 页的作品推荐 ---")
                
                items_to_process_on_this_page = True
                while items_to_process_on_this_page:
                    self.ui_helper.scroll_list_container(page)
                    time.sleep(1)
                    
                    novel_items = page.locator('div.long-article-table-item')
                    item_count = novel_items.count()
                    if item_count == 0:
                        print("当前页未找到小说项。")
                        break
                    
                    found_and_processed_this_cycle = False
                    for i in range(item_count):
                        item = novel_items.nth(i)
                        
                        # 检查并跳过已处理的小说
                        book_id = item.get_attribute('id')
                        if not book_id or book_id in self.processed_book_ids:
                            continue
                        
                        # 查找作品推荐按钮
                        recommend_button = item.locator('button.arco-btn-primary:has-text("作品推荐")')
                        
                        if recommend_button.count() > 0:
                            title_locator = item.locator('.info-content-title .hoverup')
                            novel_title = (title_locator.first.text_content() or "未知小说").strip()
                            
                            # 标记为已处理
                            print(f"为小说《{novel_title}》找到 '作品推荐' 按钮。")
                            print(f"  -> 标记 ID '{book_id}' 为本轮已尝试，将不再重复检查。")
                            self.processed_book_ids.add(book_id)
                            
                            if self.ui_helper.safe_click(recommend_button, f"作品推荐按钮 - 《{novel_title}》"):
                                page.wait_for_load_state("domcontentloaded")
                                time.sleep(2)
                                
                                success = self._process_recommendation_details(page)
                                if success:
                                    print(f"✓ 小说《{novel_title}》的作品推荐流程处理成功。")
                                else:
                                    print(f"  -> 小说《{novel_title}》的推荐流程中止或有未满足的硬性条件。")
                                
                                print("正在返回小说列表页...")
                                page.go_back()
                                page.wait_for_load_state("domcontentloaded")
                                time.sleep(2)
                                
                                found_and_processed_this_cycle = True
                                break
                    
                    if not found_and_processed_this_cycle:
                        items_to_process_on_this_page = False
                
                # 翻页逻辑
                if not items_to_process_on_this_page:
                    print("本页检查完毕，尝试翻至下一页...")
                    next_result = self.ui_helper.navigate_to_next_page(page, "next")
                    if next_result is not True:
                        print("无法翻至下一页或已到达末页，作品推荐检查完成。")
                        break
                    time.sleep(1)
            
            print("\n=== 作品推荐检查全部完成 ===")
            return True
            
        except Exception as e:
            print(f"检查作品推荐时发生意外错误: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _ensure_novel_management_page(self, page: Page) -> None:
        """确保在小说管理页面"""
        novel_selectors = [
            'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
            'text=小说',
            'span:has-text("小说")'
        ]
        
        for selector in novel_selectors:
            if self.ui_helper.safe_click(page.locator(selector).first, "小说标签"):
                break
        
        time.sleep(1)
    
    def _quick_check_page_status(self, page: Page) -> bool:
        """
        快速检查整页状态
        
        Args:
            page: 页面对象
            
        Returns:
            是否整页都是已签约或已失败
        """
        try:
            novel_items = page.locator('//div[contains(@id, "long-article-table-item")]')
            
            for i in range(novel_items.count()):
                try:
                    item = novel_items.nth(i)
                    
                    # 获取小说标题
                    title_xpath = './div/div[1]/div[2]/div[1]/div'
                    title_elements = item.locator(f'xpath={title_xpath}')
                    
                    if title_elements.count() > 0:
                        novel_title = title_elements.first.text_content().strip()
                        
                        # 检查是否在失败列表中
                        if novel_title in self.failed_novels:
                            continue
                    
                    # 检查签约状态
                    status_xpath = './div/div[1]/div[2]/div[2]/div[2]/div[3]'
                    status_elements = item.locator(f'xpath={status_xpath}')
                    
                    if status_elements.count() > 0:
                        status_text = status_elements.first.text_content().strip()
                        
                        # 检查是否包含"连载中"但不包含"已签约"
                        if "连载中" in status_text and "已签约" not in status_text:
                            return False
                            
                except Exception:
                    return False
            
            return True
            
        except Exception:
            return False
    
    def _process_page_contracts(self, page: Page) -> tuple:
        """
        处理页面的签约检查
        
        Args:
            page: 页面对象
            
        Returns:
            (处理数量, 跳过数量)
        """
        handled_count = 0
        skipped_count = 0
        
        novel_items = page.locator('//div[contains(@id, "long-article-table-item")]')
        
        for i in range(novel_items.count()):
            try:
                item = novel_items.nth(i)
                
                # 获取小说标题
                title_xpath = './div/div[1]/div[2]/div[1]/div'
                title_elements = item.locator(f'xpath={title_xpath}')
                
                if title_elements.count() > 0:
                    novel_title = title_elements.first.text_content().strip()
                    
                    # 检查是否在失败列表中
                    if novel_title in self.failed_novels:
                        print(f"小说《{novel_title}》已标记为失败，跳过")
                        skipped_count += 1
                        continue
                
                # 检查签约状态
                status_xpath = './div/div[1]/div[2]/div[2]/div[2]/div[3]'
                status_elements = item.locator(f'xpath={status_xpath}')
                
                if status_elements.count() > 0:
                    status_text = status_elements.first.text_content().strip()
                    
                    # 检查是否包含"连载中"但不包含"已签约"
                    if "连载中" in status_text and "已签约" not in status_text:
                        print(f"小说项 {i+1} 状态: {status_text}")
                        
                        # 获取小说标题用于日志
                        if title_elements.count() > 0:
                            novel_title = title_elements.first.text_content().strip()
                            print(f"找到未签约的连载中小说: {novel_title}")
                        
                        # 使用键盘导航激活条目，避免点击跳转
                        print("使用键盘导航激活条目...")
                        
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
                                        print("✓ 已点击第一个条目获取焦点")
                                except:
                                    pass
                            
                            # 使用键盘向下箭头导航到目标行
                            if i > 0:
                                for _ in range(i):
                                    page.keyboard.press('ArrowDown')
                                    time.sleep(0.1)
                                print(f"✓ 使用键盘导航到第 {i+1} 行")
                            else:
                                print("✓ 已在第一行")
                            
                            time.sleep(0.5)
                            
                        except Exception as e:
                            print(f"键盘导航失败，尝试备用方案: {e}")
                            # 备用方案：尝试悬停
                            try:
                                item.hover(timeout=2000)
                                print("✓ 使用悬停激活")
                            except:
                                print("⚠ 激活失败，继续尝试")
                        
                        # 重新查找签约管理按钮（激活后应该会出现）
                        contract_button_xpath = './div/div[1]/div[2]/div[3]/div/button[2]/span'
                        contract_buttons = item.locator(f'xpath={contract_button_xpath}')
                        
                        if contract_buttons.count() > 0:
                            button_text = contract_buttons.first.text_content().strip()
                            print(f"找到按钮: {button_text}")
                            if "签约管理" in button_text:
                                print("找到签约管理按钮，开始处理...")
                                
                                # 检查重试次数
                                retry_count = getattr(self, f'retry_count_{hash(novel_title)}', 0)
                                
                                if retry_count >= self.max_retry_count:
                                    print(f"小说《{novel_title}》已尝试{retry_count}次签约失败，标记为失败并跳过")
                                    self.failed_novels.add(novel_title)
                                    skipped_count += 1
                                    continue
                                
                                # 点击签约管理按钮
                                if self.ui_helper.safe_click(contract_buttons.first, "签约管理按钮"):
                                    handled_count += 1
                                    
                                    # 等待签约管理页面加载
                                    time.sleep(1)
                                    
                                    # 记录当前URL
                                    current_url_before_contract = page.url
                                    
                                    # 处理签约管理流程
                                    success = False
                                    print(f"尝试签约流程 (第{retry_count + 1}次尝试)...")
                                    if self._handle_contract_process(page, retry_count):
                                        print("✓ 签约管理处理成功")
                                        success = True
                                        # 成功时清除重试计数
                                        if hasattr(self, f'retry_count_{hash(novel_title)}'):
                                            delattr(self, f'retry_count_{hash(novel_title)}')
                                    else:
                                        print("⚠ 签约管理处理失败")
                                        retry_count += 1
                                        setattr(self, f'retry_count_{hash(novel_title)}', retry_count)
                                        
                                        if retry_count >= self.max_retry_count:
                                            print(f"小说《{novel_title}》已达到最大重试次数{self.max_retry_count}，标记为失败")
                                            self.failed_novels.add(novel_title)
                                    
                                    # 使用浏览器后退返回
                                    print("使用浏览器后退返回...")
                                    page.go_back()
                                    time.sleep(0.5)
                                    
                                    # 确保回到小说列表页面
                                    if not self._verify_novel_list_page(page):
                                        print("未正确返回小说列表，重新导航...")
                                        self._ensure_novel_management_page(page)
                                        time.sleep(0.5)
                                    
                                    if success:
                                        print("✓ 签约管理处理成功")
                        
            except Exception as e:
                print(f"处理第 {i+1} 个小说项时出错: {e}")
                continue
        
        return handled_count, skipped_count
    
    def _handle_contract_process(self, page: Page, attempt: int = 0) -> bool:
        """
        处理签约管理流程
        
        Args:
            page: 页面对象
            attempt: 尝试次数
            
        Returns:
            是否处理成功
        """
        print(f"处理签约管理流程 (第{attempt+1}次尝试)...")
        
        try:
            # 等待签约管理页面加载
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 检查页面上的所有按钮
            print("检查当前页面上的按钮...")
            all_buttons = page.locator('button')
            button_count = all_buttons.count()
            print(f"页面上共有 {button_count} 个按钮")
            
            found_buttons = []
            for i in range(min(button_count, 20)):
                try:
                    btn_text = all_buttons.nth(i).text_content().strip()
                    if btn_text:
                        found_buttons.append(btn_text)
                except:
                    pass
            
            print(f"找到的按钮文本: {found_buttons}")
            
            # 情况1: 检查是否有"申请签约"按钮
            if any("申请签约" in btn for btn in found_buttons):
                print("✓ 检测到'申请签约'按钮，这是申请签约流程")
                return self._handle_apply_contract_process(page)
            
            # 情况2: 检查是否有"填写合同"按钮
            if any("填写合同" in btn for btn in found_buttons):
                print("✓ 检测到'填写合同'按钮，这是填写合同流程")
                return self._handle_fill_contract_process(page)
            
            # 情况3: 检查是否有"立即签约"按钮
            if any("立即签约" in btn for btn in found_buttons):
                print("✓ 检测到'立即签约'按钮，暂时不处理")
                return False
            
            # 情况4: 检查是否有成功提示（已经提交过）
            print("未找到签约相关按钮，检查是否已经有成功提示...")
            return self._check_success_indicators(page)
            
        except Exception as e:
            print(f"处理签约流程时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_apply_contract_process(self, page: Page) -> bool:
        """
        处理申请签约流程（独立流程）
        1. 点击"申请签约"按钮
        2. 处理确认弹窗
        3. 验证提交成功
        """
        print("处理申请签约流程...")
        
        try:
            # 步骤1: 查找并点击第一个"申请签约"按钮
            if not self._click_first_apply_button(page):
                return False
            
            # 步骤2: 处理确认弹窗
            time.sleep(2)
            if not self._handle_apply_confirm_modal(page):
                return False
            
            # 步骤3: 验证申请提交成功
            return self._verify_apply_contract_success(page)
            
        except Exception as e:
            print(f"处理申请签约流程时出错: {e}")
            return False
    
    def _click_first_apply_button(self, page: Page) -> bool:
        """
        点击第一个"申请签约"按钮
        """
        print("【步骤1】查找并点击申请签约按钮...")
        
        apply_contract_selectors = [
            '//div[contains(@class, "flow-card-actions")]//button[.//span[text()="申请签约"]]',
            'button:has-text("申请签约")',
            '//button[contains(text(), "申请签约")]',
            '//span[contains(text(), "申请签约")]'
        ]
        
        for selector in apply_contract_selectors:
            try:
                if selector.startswith('//'):
                    elements = page.locator(f'xpath={selector}')
                else:
                    elements = page.locator(selector)
                
                if elements.count() > 0:
                    button_text = elements.first.text_content().strip()
                    if "申请签约" in button_text:
                        print(f"找到申请签约按钮: {button_text}")
                        
                        # 滚动到按钮位置
                        try:
                            elements.first.scroll_into_view_if_needed()
                            time.sleep(0.5)
                        except:
                            pass
                        
                        # 点击按钮
                        for click_attempt in range(3):
                            try:
                                print(f"尝试点击 (第{click_attempt+1}次)...")
                                elements.first.click(timeout=5000)
                                print("✓ 已成功点击申请签约按钮")
                                time.sleep(2)
                                return True
                            except Exception as click_err:
                                print(f"点击失败: {click_err}")
                                if click_attempt < 2:
                                    time.sleep(1)
                        
                        break
            except Exception as e:
                print(f"选择器失败: {e}")
                continue
        
        print("✗ 所有尝试点击申请签约按钮的操作都失败了")
        return False
    
    def _handle_apply_confirm_modal(self, page: Page) -> bool:
        """
        处理申请签约确认弹窗
        点击弹窗中的"申请签约"按钮
        """
        print("【步骤2】处理确认弹窗...")
        
        try:
            # 等待弹窗出现
            time.sleep(2)
            page.wait_for_load_state("networkidle")
            
            # 查找确认弹窗
            modal_selectors = [
                'div.sign-confirm-modal',
                'div.arco-modal.sign-confirm-modal',
                '//div[contains(@class, "sign-confirm-modal")]'
            ]
            
            modal_found = False
            for selector in modal_selectors:
                try:
                    if selector.startswith('//'):
                        modal = page.locator(f'xpath={selector}')
                    else:
                        modal = page.locator(selector)
                    
                    if modal.count() > 0 and modal.first.is_visible():
                        print("✓ 找到确认弹窗")
                        modal_found = True
                        break
                except:
                    continue
            
            if not modal_found:
                print("未找到确认弹窗，可能不需要确认")
                return True
            
            # 查找弹窗中的"申请签约"按钮（primary按钮）
            confirm_button_selectors = [
                'div.arco-modal-footer button.arco-btn-primary:has-text("申请签约")',
                '//div[contains(@class, "arco-modal-footer")]//button[contains(@class, "arco-btn-primary") and contains(text(), "申请签约")]',
                'div.arco-modal-footer button:has-text("申请签约")',
            ]
            
            for selector in confirm_button_selectors:
                try:
                    if selector.startswith('//'):
                        elements = page.locator(f'xpath={selector}')
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0 and elements.first.is_visible():
                        button_text = elements.first.text_content().strip()
                        print(f"找到弹窗中的确认按钮: {button_text}")
                        
                        # 点击确认按钮
                        for click_attempt in range(3):
                            try:
                                print(f"尝试点击确认按钮 (第{click_attempt+1}次)...")
                                elements.first.click(timeout=5000)
                                print("✓ 已成功点击弹窗中的申请签约按钮")
                                time.sleep(3)
                                return True
                            except Exception as click_err:
                                print(f"点击失败: {click_err}")
                                if click_attempt < 2:
                                    time.sleep(1)
                        
                        break
                except Exception as e:
                    print(f"选择器失败: {e}")
                    continue
            
            print("✗ 所有尝试点击确认按钮的操作都失败了")
            return False
            
        except Exception as e:
            print(f"处理确认弹窗时出错: {e}")
            return False
    
    def _verify_apply_contract_success(self, page: Page) -> bool:
        """
        验证申请签约是否成功提交
        """
        print("验证申请签约提交结果...")
        
        try:
            time.sleep(2)
            page.wait_for_load_state("networkidle")
            
            # 检查成功提示
            success_indicators = [
                'text=申请成功',
                'text=提交成功',
                'text=等待审核',
                'text=签约申请已提交',
                'text=申请已提交'
            ]
            
            for indicator in success_indicators:
                if page.locator(indicator).count() > 0:
                    print(f"✓ 检测到成功提示: {indicator}")
                    time.sleep(1)
                    self._handle_success_popup(page)
                    return True
            
            # 检查流程进度变化
            progress_indicators = [
                '//div[contains(@class, "flow-card status-active")]//div[contains(text(), "安全审核")]',
                '//div[contains(@class, "flow-card")]//div[contains(text(), "签约评估")]',
                '//div[contains(@class, "flow-card")]//div[contains(text(), "合同审核")]'
            ]
            
            for indicator in progress_indicators:
                try:
                    if page.locator(f'xpath={indicator}').count() > 0:
                        print(f"✓ 检测到签约流程已进入下一阶段")
                        return True
                except:
                    continue
            
            # 检查按钮状态
            apply_button = page.locator('button:has-text("申请签约")')
            if apply_button.count() > 0:
                button = apply_button.first
                is_disabled = button.get_attribute('disabled') is not None or \
                            'disabled' in button.get_attribute('class', '') or \
                            not button.is_enabled()
                
                if is_disabled:
                    print(f"✓ 申请签约按钮已被禁用，说明申请已提交")
                    return True
            else:
                print(f"✓ 申请签约按钮已消失，说明申请已提交")
                return True
            
            print("未检测到明确的失败标志，假设申请签约已完成")
            return True
            
        except Exception as e:
            print(f"验证申请签约结果时出错: {e}")
            return False
    
    def _handle_fill_contract_process(self, page: Page) -> bool:
        """
        处理填写合同流程（独立流程）
        负责查找并点击"填写合同"按钮，然后填写表单
        """
        print("处理填写合同流程...")
        
        try:
            # 查找"填写合同"按钮
            fill_contract_selectors = [
                'button:has-text("填写合同")',
                '//button[contains(text(), "填写合同")]',
                '//span[contains(text(), "填写合同")]',
                '//div[contains(@class, "flow-card-actions")]//button'
            ]
            
            for selector in fill_contract_selectors:
                try:
                    if selector.startswith('//'):
                        elements = page.locator(f'xpath={selector}')
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0:
                        for i in range(elements.count()):
                            button_text = elements.nth(i).text_content().strip()
                            print(f"找到按钮: {button_text}")
                            
                            if "填写合同" in button_text:
                                print(f"✓ 找到填写合同按钮")
                                
                                if self.ui_helper.safe_click(elements.nth(i), "填写合同按钮"):
                                    print("已点击填写合同按钮")
                                    time.sleep(3)
                                    return self._fill_contract_details_form(page)
                except Exception as e:
                    print(f"选择器失败: {e}")
                    continue
            
            print("未找到填写合同按钮")
            return False
            
        except Exception as e:
            print(f"处理填写合同流程时出错: {e}")
            return False
    
    def _check_success_indicators(self, page: Page) -> bool:
        """
        检查页面是否已经有成功提示
        """
        try:
            success_indicators = [
                'text=申请成功',
                'text=提交成功',
                'text=等待审核',
                'text=签约申请已提交',
                'text=申请已提交',
                'text=合同已签署',
                'text=签署成功'
            ]
            
            for indicator in success_indicators:
                if page.locator(indicator).count() > 0:
                    print(f"✓ 检测到成功提示: {indicator}")
                    return True
            
            print("⚠ 未找到签约相关操作，也没有成功提示")
            return False
            
        except Exception as e:
            print(f"检查成功提示时出错: {e}")
            return False
                
        except Exception as e:
            print(f"处理签约流程时出错: {e}")
            return False
    
    def _find_and_click_contract_button(self, page: Page) -> bool:
        """
        已废弃 - 使用 _handle_fill_contract_process 替代
        此方法保留用于向后兼容
        """
        print("警告: _find_and_click_contract_button 已废弃，使用 _handle_fill_contract_process")
        return self._handle_fill_contract_process(page)
    
    def _fill_contract_details_form(self, page: Page) -> bool:
        """
        填写合同详情表单
        
        Args:
            page: 页面对象
            
        Returns:
            是否填写成功
        """
        print("填写合同详情表单...")
        
        try:
            # 获取当前用户的联系信息
            contact_info = {}
            if self.config_loader:
                contact_info = self.config_loader.get_contract_contact_info()
                if not contact_info:
                    print("✗ 当前用户配置无效或未启用，无法填写签约信息")
                    return False
                else:
                    current_user = self.config_loader.get_current_contract_user()
                    print(f"使用签约用户配置: {current_user}")
            
            # 等待合同详情页面加载
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 滑动页面确保所有元素可见
            self._scroll_contract_form(page)
            
            # 填写各种信息
            self._fill_contact_fields(page, contact_info)
            
            # 提交表单
            return self._submit_contract_form(page)
            
        except Exception as e:
            print(f"填写合同详情表单时出错: {e}")
            return False
    
    def _fill_contact_fields(self, page: Page, contact_info: Dict[str, str]) -> None:
        """
        填写联系信息字段
        
        Args:
            page: 页面对象
            contact_info: 联系信息字典
        """
        # 填写手机号
        phone = contact_info.get('phone', '13760125919')
        phone_input = page.locator('//*[@id="phone_input"]')
        if phone_input.count() > 0:
            if self.ui_helper.safe_fill(phone_input.first, phone, "手机号"):
                print(f"✓ 已填写手机号: {phone}")
        
        time.sleep(1)
        
        # 填写邮箱
        email = contact_info.get('email', '405625365@qq.com')
        email_input = page.locator('//*[@id="email_input"]')
        if email_input.count() > 0:
            if self.ui_helper.safe_fill(email_input.first, email, "邮箱"):
                print(f"✓ 已填写邮箱: {email}")
        
        time.sleep(1)
        
        # 填写QQ
        qq = contact_info.get('qq', '405625365')
        qq_input = page.locator('//*[@id="qq_input"]')
        if qq_input.count() > 0:
            if self.ui_helper.safe_fill(qq_input.first, qq, "QQ"):
                print(f"✓ 已填写QQ: {qq}")
        
        time.sleep(1)
        
        # 填写联系地址（级联选择器）
        self._fill_address_cascader(page, contact_info)
        
        # 填写银行卡号
        bank_account = contact_info.get('bank_account', '6214857812704759')
        bank_account_input = page.locator('//*[@id="bankAccount_input"]')
        if bank_account_input.count() > 0:
            if self.ui_helper.safe_fill(bank_account_input.first, bank_account, "银行卡号"):
                print(f"✓ 已填写银行卡号: {bank_account}")
        
        time.sleep(1)
        
        # 填写所属支行（搜索选择器）
        self._fill_bank_branch(page, contact_info)
    
    def _fill_address_cascader(self, page: Page, contact_info: Dict[str, Any]) -> None:
        """
        填写联系地址级联选择器
        
        Args:
            page: 页面对象
            contact_info: 联系信息字典
        """
        print("填写联系地址...")
        
        try:
            # 获取地址信息
            address = contact_info.get('address', {})
            
            # 确保address是字典类型
            if isinstance(address, str):
                # 如果address是字符串，尝试解析或使用默认值
                print(f"  ⚠ 地址配置为字符串格式，使用默认值")
                province = '贵州省'
                city = '凯里市'
                detail = address
            elif isinstance(address, dict):
                province = address.get('province', '贵州省')
                city = address.get('city', '凯里市')
                detail = address.get('detail', '北京路')
            else:
                # 其他情况使用默认值
                province = '贵州省'
                city = '凯里市'
                detail = '北京路'
            
            # 点击级联选择器
            address_cascader = page.locator('//*[@id="address_input"]')
            if address_cascader.count() > 0:
                self.ui_helper.safe_click(address_cascader.first, "联系地址选择器")
                time.sleep(1)
                
                # 选择省份
                self._select_cascader_option(page, province, "省份")
                time.sleep(0.5)
                
                # 选择城市
                self._select_cascader_option(page, city, "城市")
                time.sleep(0.5)
                
                # 填写详细地址
                address_detail_input = page.locator('//*[@id="addressDetail_input"]')
                if address_detail_input.count() > 0:
                    page.evaluate('() => { window.scrollBy(0, 200); }')
                    time.sleep(0.5)
                    
                    if self.ui_helper.safe_fill(address_detail_input.first, detail, "详细地址"):
                        print(f"✓ 已填写地址: {province} {city} {detail}")
                
                # 点击页面其他地方关闭选择器
                page.evaluate('() => { document.body.click(); }')
                time.sleep(0.5)
                
        except Exception as e:
            print(f"填写联系地址时出错: {e}")
    
    def _select_cascader_option(self, page: Page, text: str, level: str) -> bool:
        """
        选择级联选择器选项
        
        Args:
            page: 页面对象
            text: 选项文本（如"贵州"、"贵州省"）
            level: 级别名称（用于日志）
            
        Returns:
            是否成功
        """
        try:
            # 等待级联菜单加载
            time.sleep(0.8)
            
            # 标准化文本（去除"省"、"市"、"自治区"等后缀）
            normalized_text = text.replace('省', '').replace('市', '').replace('自治区', '').replace('特别行政区', '')
            
            # 查找包含指定文本的选项 - 使用实际的选择器类名
            option_selectors = [
                f'li.arco-cascader-list-item[title="{text}"]',
                f'li.arco-cascader-list-item[title="{normalized_text}"]',
                f'xpath=//li[contains(@class, "arco-cascader-list-item") and @title="{text}"]',
                f'xpath=//li[contains(@class, "arco-cascader-list-item") and @title="{normalized_text}"]',
                f'xpath=//li[contains(@class, "arco-cascader-list-item") and contains(@title, "{normalized_text}")]',
            ]
            
            for selector in option_selectors:
                try:
                    if selector.startswith('xpath='):
                        elements = page.locator(selector)
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0:
                        # 尝试点击第一个匹配的选项
                        element = elements.first
                        if self.ui_helper.safe_click(element, f"{level}选项-{text}"):
                            print(f"  ✓ 已选择{level}: {text}")
                            time.sleep(0.5)
                            return True
                except Exception:
                    continue
            
            print(f"  ⚠ 未找到{level}选项: {text}")
            
            # 如果没有找到精确匹配，尝试模糊匹配
            try:
                all_options = page.locator('li.arco-cascader-list-item')
                if all_options.count() > 0:
                    print(f"  尝试模糊匹配，找到 {all_options.count()} 个选项")
                    for i in range(all_options.count()):
                        option = all_options.nth(i)
                        option_text = (option.get_attribute('title') or "").strip()
                        if normalized_text in option_text or option_text in normalized_text:
                            if self.ui_helper.safe_click(option, f"{level}模糊匹配选项-{option_text}"):
                                print(f"  ✓ 已选择{level}（模糊匹配）: {option_text}")
                                time.sleep(0.5)
                                return True
            except Exception as e:
                print(f"  模糊匹配失败: {e}")
            
            return False
            
        except Exception as e:
            print(f"选择{level}选项时出错: {e}")
            return False
    
    def _fill_bank_branch(self, page: Page, contact_info: Dict[str, Any]) -> None:
        """
        填写银行支行选择器
        
        Args:
            page: 页面对象
            contact_info: 联系信息字典
        """
        print("填写所属支行...")
        
        try:
            # 获取银行支行信息
            bank_branch = contact_info.get('bank_branch', '中国建设银行股份有限公司凯里北京路支行')
            print(f"  目标支行: {bank_branch}")
            
            # 点击支行选择器
            bank_code_input = page.locator('//*[@id="bankCode_input"]')
            if bank_code_input.count() == 0:
                print(f"  ⚠ 未找到支行选择器")
                return
            
            # 先点击输入框打开下拉列表
            self.ui_helper.safe_click(bank_code_input.first, "所属支行选择器")
            time.sleep(1.5)
            
            # 滚动到支行选择器可见
            page.evaluate('() => { window.scrollBy(0, 100); }')
            time.sleep(0.5)
            
            # 直接使用完整支行名称进行精准匹配
            search_keywords = bank_branch  # 使用完整的支行名称
            print(f"  搜索关键词: {search_keywords}")
            
            # 查找实际的输入框元素
            search_input_selectors = [
                '//*[@id="bankCode_input"]//input[@class="arco-select-view-input"]',
                '//*[@id="bankCode_input"]//input[@type="text"]',
                '#bankCode_input input.arco-select-view-input',
            ]
            
            search_input = None
            for selector in search_input_selectors:
                try:
                    elements = page.locator(selector)
                    if elements.count() > 0:
                        search_input = elements.first
                        break
                except Exception:
                    continue
            
            if not search_input:
                print(f"  ⚠ 未找到支行搜索输入框")
                return
            
            # 直接输入完整支行名称进行精准匹配
            try:
                print(f"  输入完整支行名称进行精准匹配")
                
                # 清空输入框并输入完整的支行名称
                search_input.fill('')
                time.sleep(0.5)
                search_input.fill(search_keywords)
                time.sleep(5)  # 增加等待时间到5秒，让搜索结果完全刷新
                
                # 检查是否有结果 - 使用正确的li选择器
                options = page.locator('li.arco-select-option')
                option_count = options.count()
                
                print(f"  检查到 {option_count} 个支行选项")
                
                if option_count == 0:
                    print(f"  ⚠ 搜索 '{search_keywords}' 无结果，请检查支行名称是否正确")
                    # 尝试等待更长时间再检查一次
                    time.sleep(3)
                    option_count = options.count()
                    print(f"  再次检查到 {option_count} 个支行选项")
                
                if option_count == 0:
                    return
                
                print(f"  找到 {option_count} 个支行选项")
                
                # 查找完全匹配的选项
                for i in range(option_count):
                    option = options.nth(i)
                    try:
                        # 获取选项文本 - 可能需要从内部span获取
                        option_text = (option.text_content() or "").strip()
                        # 如果text_content为空，尝试获取内部span的文本
                        if not option_text:
                            highlight_span = option.locator('span.arco-select-highlight')
                            if highlight_span.count() > 0:
                                option_text = (highlight_span.first.text_content() or "").strip()
                        
                        print(f"    选项 {i+1}: {option_text}")
                        
                        # 精准匹配：选项文本必须完全等于目标支行名称
                        if option_text == bank_branch:
                            print(f"  ✓ 找到精准匹配的支行: {option_text}")
                            
                            # 点击选项
                            if self.ui_helper.safe_click(option, f"支行选项-{option_text}"):
                                print(f"  ✓ 已点击支行选项: {option_text}")
                                time.sleep(0.8)
                                
                                # 按回车键确认选择
                                try:
                                    page.keyboard.press('Enter')
                                    time.sleep(0.8)
                                    print(f"  ✓ 已按回车键确认选择")
                                except Exception as e:
                                    print(f"  ⚠ 按回车键失败: {e}")
                                    # 如果回车失败，尝试点击页面其他地方关闭下拉列表
                                    try:
                                        page.evaluate('() => { document.body.click(); }')
                                        time.sleep(0.5)
                                    except Exception:
                                        pass
                                
                                print(f"  ✓ 已选择支行: {option_text}")
                                return
                    except Exception as e:
                        print(f"    检查选项 {i+1} 时出错: {e}")
                        continue
                
                # 如果没有找到完全匹配的，尝试包含匹配
                print(f"  ⚠ 未找到完全匹配的选项，尝试部分匹配")
                for i in range(option_count):
                    option = options.nth(i)
                    try:
                        option_text = (option.text_content() or "").strip()
                        
                        # 检查是否包含关键部分
                        if bank_branch in option_text or option_text in bank_branch:
                            print(f"  ✓ 找到部分匹配的支行: {option_text}")
                            
                            if self.ui_helper.safe_click(option, f"支行选项-{option_text}"):
                                print(f"  ✓ 已点击支行选项: {option_text}")
                                time.sleep(0.8)
                                
                                try:
                                    page.keyboard.press('Enter')
                                    time.sleep(0.8)
                                    print(f"  ✓ 已按回车键确认选择")
                                except Exception as e:
                                    print(f"  ⚠ 按回车键失败: {e}")
                                    try:
                                        page.evaluate('() => { document.body.click(); }')
                                        time.sleep(0.5)
                                    except Exception:
                                        pass
                                
                                print(f"  ✓ 已选择支行: {option_text}")
                                return
                    except Exception:
                        continue
                
                print(f"  ⚠ 未找到匹配的支行选项")
                
            except Exception as e:
                print(f"  ✗ 搜索支行时出错: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"填写银行支行时出错: {e}")
            import traceback
            traceback.print_exc()
    
    def _scroll_contract_form(self, page: Page) -> None:
        """
        滑动合同表单页面
        
        Args:
            page: 页面对象
        """
        print("滑动合同表单页面...")
        
        try:
            page_height = page.evaluate('() => document.body.scrollHeight')
            viewport_height = page.evaluate('() => window.innerHeight')
            
            print(f"页面高度: {page_height}px, 视口高度: {viewport_height}px")
            
            if page_height > viewport_height:
                scroll_steps = 3
                scroll_step = (page_height - viewport_height) // scroll_steps
                
                print(f"将分 {scroll_steps} 步滚动合同表单，每步 {scroll_step}px")
                
                for step in range(1, scroll_steps + 1):
                    target_scroll = scroll_step * step
                    page.evaluate(f'(position) => {{ window.scrollTo(0, position); }}', target_scroll)
                    print(f"滚动到: {target_scroll}px")
                    time.sleep(0.5)
                
                page.evaluate('() => { window.scrollTo(0, 0); }')
                time.sleep(0.5)
            else:
                print("合同表单页面无需滚动")
                
        except Exception as e:
            print(f"滑动合同表单页面时出错: {e}")
    
    def _submit_contract_form(self, page: Page) -> bool:
        """
        提交合同表单
        
        Args:
            page: 页面对象
            
        Returns:
            是否提交成功
        """
        print("提交合同表单...")
        
        try:
            # 查找确认提交按钮
            confirm_submit_xpath = '//*[@id="app"]/div/div[2]/div/div[2]/div/div/button'
            confirm_submit_buttons = page.locator(f'xpath={confirm_submit_xpath}')
            
            if confirm_submit_buttons.count() > 0:
                button_text = confirm_submit_buttons.first.text_content().strip()
                print(f"找到确认提交按钮: {button_text}")
                
                if "确认无误，提交" in button_text:
                    if self.ui_helper.safe_click(confirm_submit_buttons.first, "确认无误提交按钮"):
                        print("已点击确认无误提交按钮")
                        time.sleep(3)
                        return self._handle_contract_confirmation_popup(page)
            
            print("未找到提交按钮，可能表单已自动提交")
            return True
            
        except Exception as e:
            print(f"提交合同表单时出错: {e}")
            return False
    
    def _handle_contract_confirmation_popup(self, page: Page) -> bool:
        """
        处理合同确认弹窗
        
        Args:
            page: 页面对象
            
        Returns:
            是否处理成功
        """
        print("处理合同确认弹窗...")
        
        try:
            # 等待弹窗出现和加载
            time.sleep(3)
            
            # 查找生成合同按钮 - 使用多种选择器
            generate_contract_selectors = [
                'button.arco-btn-primary:has-text("生成合同")',
                'xpath=//button[contains(@class, "arco-btn-primary") and contains(text(), "生成合同")]',
                'xpath=//button//span[contains(text(), "生成合同")]',
                '/html/body/div[3]/div[2]/div/div[2]/div[2]/div[2]',
            ]
            
            for selector in generate_contract_selectors:
                try:
                    if selector.startswith('xpath=') or selector.startswith('/html'):
                        elements = page.locator(selector)
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0:
                        button_text = (elements.first.text_content() or "").strip()
                        print(f"找到生成合同按钮: {button_text}")
                        
                        if "生成合同" in button_text:
                            if self.ui_helper.safe_click(elements.first, "生成合同按钮"):
                                print("✓ 已点击生成合同按钮，完成合同签署")
                                time.sleep(3)
                                return self._handle_success_popup(page)
                            break
                except Exception as e:
                    print(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            print("未找到生成合同按钮，可能已经自动生成或流程不同")
            return True
            
        except Exception as e:
            print(f"处理合同确认弹窗时出错: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _handle_success_popup(self, page: Page) -> bool:
        """
        处理成功提交后的弹窗
        
        Args:
            page: 页面对象
            
        Returns:
            是否处理成功
        """
        print("处理成功提交后的弹窗...")
        
        try:
            # 处理可能的弹窗
            for _ in range(5):
                time.sleep(1)
                for button_name in ["确定", "确认", "知道了", "关闭", "完成"]:
                    try:
                        button = page.get_by_role("button", name=button_name, exact=False)
                        if button.count() > 0 and button.first.is_visible():
                            self.ui_helper.safe_click(button.first, f"弹窗按钮: {button_name}")
                            print(f"已点击弹窗按钮: {button_name}")
                            time.sleep(0.5)
                            return True
                    except:
                        pass
            
            # 检查是否有成功提示
            success_selectors = [
                'text=申请成功',
                'text=提交成功',
                'text=操作成功',
                'text=签约申请已提交',
                'text=合同提交成功',
                'text=合同签署成功',
                'text=合同生成成功'
            ]
            
            for selector in success_selectors:
                if page.locator(selector).count() > 0:
                    print("✓ 合同/签约申请已成功提交")
                    return True
            
            print("未检测到明确的成功提示，但流程已完成")
            return True
            
        except Exception as e:
            print(f"处理成功弹窗时出错: {e}")
            return True
    
    def _process_recommendation_details(self, page: Page) -> bool:
        """
        处理作品推荐详情页
        
        Args:
            page: 页面对象
            
        Returns:
            是否处理成功
        """
        print(" -> 进入作品推荐详情页，开始处理推荐任务...")
        try:
            page.wait_for_selector('div.recommend-area.prepare-recommend', timeout=10000)
            
            max_attempts = 5
            for attempt in range(max_attempts):
                print(f"  -> 第 {attempt + 1}/{max_attempts} 次检查推荐任务...")
                
                tasks = page.locator('div.recommend-task')
                all_completed = True
                action_taken = False
                
                for i in range(tasks.count()):
                    task = tasks.nth(i)
                    task_title = (task.locator('.recommend-task-title').text_content() or "未知任务").strip()
                    status_tag = task.locator('.recommend-task-tag:has-text("已完成")')
                    
                    if status_tag.count() == 0:
                        all_completed = False
                        print(f"    - 任务 '{task_title}' 未完成。")
                        confirm_button = task.locator('span:has-text("点击确定")')
                        if confirm_button.count() > 0 and confirm_button.is_visible():
                            if self.ui_helper.safe_click(confirm_button, f"任务'{task_title}'的确认按钮"):
                                action_taken = True
                                time.sleep(2)
                                break
                            else:
                                print("      -> 点击失败，终止当前作品的推荐流程。")
                                return False
                
                if action_taken:
                    continue
                
                if all_completed:
                    print("  -> ✓ 所有准备任务均已完成！")
                    start_button = page.locator('button:has-text("开始推荐")')
                    if start_button.count() > 0 and start_button.is_enabled():
                        if self.ui_helper.safe_click(start_button, "开始推荐按钮"):
                            print("  -> ✓ 已成功点击 '开始推荐'。")
                            if self._handle_start_recommendation_confirm_popup(page):
                                print("  -> ✓ 推荐流程已最终确认。")
                                time.sleep(1)
                                self._handle_success_popup(page)
                                return True
                            else:
                                print("  -> ✗ 推荐确认步骤失败，流程中止。")
                                return False
                    else:
                        print("  -> ✗ 未找到或 '开始推荐' 按钮不可用。")
                        return False
                
                time.sleep(3)
            
            print(f"  -> ✗ 在达到最大尝试次数({max_attempts})后，仍有任务未完成。")
            return False
            
        except Exception as e:
            print(f"  -> ✗ 处理作品推荐详情页时出错: {e}")
            return False
    
    def _handle_start_recommendation_confirm_popup(self, page: Page) -> bool:
        """
        处理开始推荐确认弹窗
        
        Args:
            page: 页面对象
            
        Returns:
            是否处理成功
        """
        print("    -> 正在处理 '推荐确定' 弹窗...")
        try:
            confirm_button_selector = 'div.byte-modal-footer button.byte-btn-primary:has-text("确定")'
            
            page.wait_for_selector(confirm_button_selector, state='visible', timeout=5000)
            
            confirm_button = page.locator(confirm_button_selector)
            
            if self.ui_helper.safe_click(confirm_button, "'推荐确定'弹窗的确定按钮"):
                print("    -> ✓ 已点击 '确定'。")
                return True
            else:
                print("    -> ✗ 点击 '确定' 失败。")
                return False
                
        except Exception as e:
            if "Timeout" in str(e):
                print("    -> ⚠ 未在5秒内检测到 '推荐确定' 弹窗，可能流程已变更或本次无需确认。")
                return True
            else:
                print(f"    -> ✗ 处理 '推荐确定' 弹窗时发生意外错误: {e}")
                return False
        
    def get_current_user_info(self) -> Dict[str, Any]:
        """
        获取当前签约用户信息
        
        Returns:
            当前用户信息字典
        """
        if not self.config_loader:
            return {}
        
        current_user_id = self.config_loader.get_current_contract_user()
        user_config = self.config_loader.get(f'contract.users.{current_user_id}', {})
        
        return {
            'user_id': current_user_id,
            'name': user_config.get('name', current_user_id),
            'enabled': user_config.get('enabled', False),
            'contact_info': user_config.get('contact_info', {})
        }
    
    def switch_user(self, user_id: Optional[str] = None) -> bool:
        """
        切换签约用户
        
        Args:
            user_id: 目标用户ID，如果为None则切换到下一个启用的用户
            
        Returns:
            是否切换成功
        """
        if not self.config_loader:
            print("✗ 配置加载器未初始化，无法切换用户")
            return False
        
        success = self.config_loader.switch_contract_user(user_id)
        if success:
            current_user = self.get_current_user_info()
            print(f"✓ 已切换到用户: {current_user['name']} ({current_user['user_id']})")
        return success
    
    def list_users(self) -> None:
        """列出所有签约用户"""
        if not self.config_loader:
            print("✗ 配置加载器未初始化")
            return
        
        self.config_loader.list_contract_users()
    
    def validate_current_user(self) -> bool:
        """
        验证当前用户配置是否有效
        
        Returns:
            当前用户是否有效
        """
        if not self.config_loader:
            print("✗ 配置加载器未初始化")
            return False
        
        current_user_info = self.get_current_user_info()
        if not current_user_info:
            print("✗ 无法获取当前用户信息")
            return False
        
        if not current_user_info.get('enabled', False):
            print(f"✗ 用户 {current_user_info['name']} 已禁用")
            return False
        
        contact_info = current_user_info.get('contact_info', {})
        required_fields = ['phone', 'email', 'bank_account']
        
        for field in required_fields:
            if not contact_info.get(field):
                print(f"✗ 用户 {current_user_info['name']} 缺少必需字段: {field}")
                return False
        
        print(f"✓ 用户 {current_user_info['name']} 配置有效")
        return True
    
    def _verify_novel_list_page(self, page: Page) -> bool:
        """
        验证当前页面是否为小说列表页面
        
        Args:
            page: 页面对象
            
        Returns:
            是否为小说列表页面
        """
        try:
            current_url = page.url
            page_title = page.title()
            
            # 检查是否有小说列表特有的元素
            novel_list_indicators = [
                '//div[contains(@id, "long-article-table-item")]',
                'text=创建书本',
                'button:has-text("创建书本")'
            ]
            
            for indicator in novel_list_indicators:
                if indicator.startswith('//'):
                    elements = page.locator(f'xpath={indicator}')
                else:
                    elements = page.locator(indicator)
                
                if elements.count() > 0:
                    return True
            
            return False
            
        except Exception as e:
            print(f"验证小说列表页面时出错: {e}")
            return False