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
                        
                        # 查找签约管理按钮
                        contract_button_xpath = './div/div[1]/div[2]/div[3]/div/button[2]/span'
                        contract_buttons = item.locator(f'xpath={contract_button_xpath}')
                        
                        if contract_buttons.count() > 0:
                            button_text = contract_buttons.first.text_content().strip()
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
            
            # 检查是否有"立即签约"按钮
            immediate_contract_selectors = [
                'button:has-text("立即签约")',
                '//button[contains(text(), "立即签约")]',
                '//span[contains(text(), "立即签约")]'
            ]
            
            for selector in immediate_contract_selectors:
                try:
                    if selector.startswith('//'):
                        elements = page.locator(f'xpath={selector}')
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0:
                        button_text = elements.first.text_content().strip()
                        if "立即签约" in button_text:
                            print("检测到立即签约按钮，暂时不处理")
                            return False
                except Exception:
                    continue
            
            # 尝试点击申请签约按钮
            apply_contract_xpath = '/html/body/div[3]/div[2]/div/div[2]/div[3]/button[2]'
            apply_contract_buttons = page.locator(f'xpath={apply_contract_xpath}')
            
            if apply_contract_buttons.count() > 0:
                button_text = apply_contract_buttons.first.text_content().strip()
                print(f"找到申请签约按钮: {button_text}")
                
                if self.ui_helper.safe_click(apply_contract_buttons.first, "申请签约按钮"):
                    print("已点击申请签约按钮，等待6秒延迟...")
                    time.sleep(6)
                    
                    # 填写表单
                    if self._fill_contract_details_form(page):
                        print("✓ 签约申请表单填写完成")
                        return True
                    else:
                        print("⚠ 签约申请表单填写未完成")
                        return False
            else:
                print("未找到申请签约按钮，尝试其他方法...")
                return self._find_and_click_contract_button(page)
                
        except Exception as e:
            print(f"处理签约流程时出错: {e}")
            return False
    
    def _find_and_click_contract_button(self, page: Page) -> bool:
        """
        查找并点击合同按钮
        
        Args:
            page: 页面对象
            
        Returns:
            是否成功
        """
        print("滑动页面寻找填写合同按钮...")
        
        try:
            # 直接查找填写合同按钮
            contract_button_xpath = '//*[@id="arco-tabs-4-panel-1"]/div/div/div[3]/div[2]/div[3]/div[2]/button'
            contract_buttons = page.locator(f'xpath={contract_button_xpath}')
            
            if contract_buttons.count() > 0:
                button_text = contract_buttons.first.text_content().strip()
                print(f"找到填写合同按钮: {button_text}")
                
                if self.ui_helper.safe_click(contract_buttons.first, "填写合同按钮"):
                    print("已点击填写合同按钮")
                    time.sleep(3)
                    return self._fill_contract_details_form(page)
            
            print("未找到可用的申请签约按钮或填写合同按钮")
            return False
            
        except Exception as e:
            print(f"查找填写合同按钮时出错: {e}")
            return False
    
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
            # 获取联系信息
            contact_info = {}
            if self.config_loader:
                contact_info = self.config_loader.get_contract_contact_info()
            
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
        
        # 填写详细地址
        detail_address = contact_info.get('detail', '宝安区')
        address_detail_input = page.locator('//*[@id="addressDetail_input"]')
        if address_detail_input.count() > 0:
            page.evaluate('() => { window.scrollBy(0, 200); }')
            time.sleep(1)
            
            if self.ui_helper.safe_fill(address_detail_input.first, detail_address, "详细地址"):
                print(f"✓ 已填写详细地址: {detail_address}")
        
        time.sleep(1)
        
        # 填写银行卡号
        bank_account = contact_info.get('bank_account', '6214857812704759')
        bank_account_input = page.locator('//*[@id="bankAccount_input"]')
        if bank_account_input.count() > 0:
            if self.ui_helper.safe_fill(bank_account_input.first, bank_account, "银行卡号"):
                print(f"✓ 已填写银行卡号: {bank_account}")
    
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
            time.sleep(2)
            
            # 查找生成合同按钮
            generate_contract_xpath = '/html/body/div[3]/div[2]/div/div[2]/div[2]/div[2]'
            generate_contract_buttons = page.locator(f'xpath={generate_contract_xpath}')
            
            if generate_contract_buttons.count() > 0:
                button_text = generate_contract_buttons.first.text_content().strip()
                print(f"找到生成合同按钮: {button_text}")
                
                if "生成合同" in button_text:
                    if self.ui_helper.safe_click(generate_contract_buttons.first, "生成合同按钮"):
                        print("✓ 已点击生成合同按钮，完成合同签署")
                        time.sleep(3)
                        return self._handle_success_popup(page)
            
            print("未找到生成合同按钮，可能已经自动生成或流程不同")
            return True
            
        except Exception as e:
            print(f"处理合同确认弹窗时出错: {e}")
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