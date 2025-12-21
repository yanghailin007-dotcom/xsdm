# contract_manager.py
import time
import re
from playwright.sync_api import sync_playwright

class ContractManager:
    def __init__(self, config):
        self.config = config
        self.failed_novels = set()  # 新增：记录签约失败的小说
        self.max_retry_count = 2    # 新增：最大重试次数
        self.current_user_id = "user1"  # 当前用户ID

    def check_and_handle_contract_management(self, page):
        """
        检查并处理签约管理 - 优化版本，支持失败跳过和双向翻页
        """
        print("\n=== 开始检查签约管理 ===")
        
        try:
            # 确保在小说管理页面
            novel_selectors = [
                'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
                'text=小说',
                'span:has-text("小说")'
            ]
            
            for selector in novel_selectors:
                if self.safe_click(page.locator(selector).first, "小说标签"):
                    break
            
            time.sleep(1)
            
            # 获取所有小说项
            novel_items = page.locator('//div[contains(@id, "long-article-table-item")]')
            item_count = novel_items.count()
            print(f"找到 {item_count} 个小说项")
            
            handled_count = 0
            skipped_count = 0
            max_pages = 100 # 最大页码，应该从网页获取
            
            # 新增：跟踪翻页方向
            direction = "next"  # 初始方向为下一页
            page_num = 1
            
            # 修改：使用 while 循环替代 for 循环，支持双向翻页
            while page_num <= max_pages:
                print(f"检查第 {page_num} 页的签约状态...")
                
                # 使用列表容器的滚动方法
                self.scroll_list_container(page)
                
                # 快速检查整页状态
                all_contracted_or_failed = True
                unhandled_count = 0
                
                for i in range(novel_items.count()):
                    try:
                        item = novel_items.nth(i)
                        
                        # 获取小说标题用于标识
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
                                    all_contracted_or_failed = False
                                    unhandled_count += 1
                                    
                    except Exception as e:
                        print(f"快速检查第 {i+1} 个小说项时出错: {e}")
                        all_contracted_or_failed = False
                
                # 如果整页都是已签约或已失败，快速翻页
                if all_contracted_or_failed:
                    print(f"第 {page_num} 页全部是已签约或已跳过小说，快速翻页...")
                    
                    # 尝试翻页
                    if direction == "next":
                        next_result = self.navigate_to_next_page(page, "next")
                    else:
                        next_result = self.navigate_to_next_page(page, "prev")
                    
                    if next_result == True:
                        page_num += 1
                        time.sleep(0.5)
                        # 重新获取小说项
                        novel_items = page.locator('//div[contains(@id, "long-article-table-item")]')
                        continue
                    elif next_result == 'no_more_pages':
                        # 如果当前方向没有更多页面，切换方向
                        if direction == "next":
                            print("已到达最后一页，切换到上一页方向...")
                            direction = "prev"
                            # 先翻到前一页
                            prev_result = self.navigate_to_next_page(page, "prev")
                            if prev_result == True:
                                page_num += 1
                                time.sleep(0.5)
                                novel_items = page.locator('//div[contains(@id, "long-article-table-item")]')
                                continue
                            else:
                                print("无法切换到上一页，停止检查")
                                break
                        else:
                            print("已到达第一页，停止检查")
                            break
                    else:
                        print(f"翻页失败，停止检查")
                        break
                
                # 如果页面上有未签约小说，进行详细处理
                print(f"第 {page_num} 页有 {unhandled_count} 个未签约小说，进行详细处理...")
                
                # 在当前页面检查所有小说项
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
                        
                        # 使用您提供的XPath检查签约状态文字
                        status_xpath = './div/div[1]/div[2]/div[2]/div[2]/div[3]'
                        status_elements = item.locator(f'xpath={status_xpath}')
                        
                        if status_elements.count() > 0:
                            status_text = status_elements.first.text_content().strip()
                            
                            # 检查是否包含"连载中"但不包含"已签约"
                            if "连载中" in status_text and "已签约" not in status_text:
                                print(f"小说项 {i+1} 状态: {status_text}")
                                print(f"找到未签约的连载中小说: {novel_title}")
                                
                                # 查找签约管理按钮
                                contract_button_xpath = './div/div[1]/div[2]/div[3]/div/button[2]/span'
                                contract_buttons = item.locator(f'xpath={contract_button_xpath}')
                                
                                if contract_buttons.count() > 0:
                                    button_text = contract_buttons.first.text_content().strip()
                                    if "签约管理" in button_text:
                                        print("找到签约管理按钮，开始处理...")
                                        
                                        # 检查该小说的失败次数
                                        retry_count = getattr(self, f'retry_count_{hash(novel_title)}', 0)
                                        
                                        # 如果已经超过最大重试次数，标记为失败并跳过
                                        if retry_count >= self.max_retry_count:
                                            print(f"小说《{novel_title}》已尝试{retry_count}次签约失败，标记为失败并跳过")
                                            self.failed_novels.add(novel_title)
                                            skipped_count += 1
                                            continue
                                        
                                        # 点击签约管理按钮
                                        if self.safe_click(contract_buttons.first, "签约管理按钮"):
                                            handled_count += 1
                                            
                                            # 等待签约管理页面加载
                                            time.sleep(1)
                                            
                                            # 记录当前URL，用于返回
                                            current_url_before_contract = page.url
                                            
                                            # 处理签约管理流程
                                            success = False
                                            print(f"尝试签约流程 (第{retry_count + 1}次尝试)...")
                                            if self.handle_contract_process(page, retry_count):
                                                print("✓ 签约管理处理成功")
                                                success = True
                                                # 成功时清除重试计数
                                                if hasattr(self, f'retry_count_{hash(novel_title)}'):
                                                    delattr(self, f'retry_count_{hash(novel_title)}')
                                            else:
                                                print("⚠ 签约管理处理失败")
                                                # 增加重试计数
                                                retry_count += 1
                                                setattr(self, f'retry_count_{hash(novel_title)}', retry_count)
                                                
                                                # 如果达到最大重试次数，标记为失败
                                                if retry_count >= self.max_retry_count:
                                                    print(f"小说《{novel_title}》已达到最大重试次数{self.max_retry_count}，标记为失败")
                                                    self.failed_novels.add(novel_title)
                                            
                                            # 使用浏览器后退返回
                                            print("使用浏览器后退返回...")
                                            page.go_back()
                                            time.sleep(0.5)
                                            
                                            # 确保回到小说列表页面
                                            if not self.verify_novel_list_page(page):
                                                print("未正确返回小说列表，重新导航...")
                                                for selector in novel_selectors:
                                                    if self.safe_click(page.locator(selector).first, "小说标签"):
                                                        break
                                                time.sleep(0.5)
                                            
                                            if success:
                                                print("✓ 签约管理处理成功")
                                
                    except Exception as e:
                        print(f"处理第 {i+1} 个小说项时出错: {e}")
                        continue
                
                # 检查是否有下一页/上一页
                if page_num < max_pages:
                    # 根据当前方向翻页
                    if direction == "next":
                        next_result = self.navigate_to_next_page(page, "next")
                    else:
                        next_result = self.navigate_to_next_page(page, "prev")
                    
                    if next_result == True:
                        page_num += 1
                        time.sleep(0.5)
                        # 重新获取小说项
                        novel_items = page.locator('//div[contains(@id, "long-article-table-item")]')
                    elif next_result == 'no_more_pages':
                        # 如果当前方向没有更多页面，切换方向
                        if direction == "next":
                            print("已到达最后一页，切换到上一页方向...")
                            direction = "prev"
                            # 先翻到前一页
                            prev_result = self.navigate_to_next_page(page, "prev")
                            if prev_result == True:
                                page_num += 1
                                time.sleep(0.5)
                                novel_items = page.locator('//div[contains(@id, "long-article-table-item")]')
                            else:
                                print("无法切换到上一页，停止检查")
                                break
                        else:
                            print("已到达第一页，停止检查")
                            break
                    else:
                        print("翻页失败，停止检查")
                        break
                else:
                    print(f"已达到最大页数 {max_pages}，停止检查")
                    break
            
            print(f"=== 签约管理检查完成，共处理 {handled_count} 个小说，跳过 {skipped_count} 个失败小说 ===")
            # page.reload()
            
            # 返回是否处理了任何小说（包括成功和标记为失败的）
            return handled_count > 0 or skipped_count > 0
            
        except Exception as e:
            print(f"检查签约管理时出错: {e}")
            return False

    def verify_novel_list_page(self, page):
        """
        验证当前页面是否为小说列表页面
        """
        try:
            # 检查页面标题或URL
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

    def scroll_list_container(self, page):
        """
        针对列表容器的滚动方法
        使用您提供的列表容器选择器进行精确滚动
        """
        print("使用列表容器进行滚动...")
        
        try:
            # 定位列表容器
            list_container = page.locator('//*[@id="arco-tabs-3-panel-0"]')
            
            if list_container.count() > 0:
                # 获取容器的高度和滚动信息
                container_info = list_container.evaluate('''
                    (element) => {
                        return {
                            scrollHeight: element.scrollHeight,
                            clientHeight: element.clientHeight,
                            scrollTop: element.scrollTop
                        };
                    }
                ''')
                
                scroll_height = container_info['scrollHeight']
                client_height = container_info['clientHeight']
                current_scroll = container_info['scrollTop']
                
                print(f"列表容器 - 总高度: {scroll_height}px, 可视高度: {client_height}px, 当前滚动: {current_scroll}px")
                
                # 如果内容高度大于可视高度，则需要滚动
                if scroll_height > client_height:
                    # 计算滚动步数
                    scroll_steps = 5
                    scroll_step = (scroll_height - client_height) // scroll_steps
                    
                    print(f"将分 {scroll_steps} 步滚动，每步 {scroll_step}px")
                    
                    # 逐步滚动
                    for step in range(1, scroll_steps + 1):
                        target_scroll = scroll_step * step
                        list_container.evaluate(f'(element, position) => {{ element.scrollTop = position; }}', target_scroll)
                        print(f"滚动到: {target_scroll}px")
                        time.sleep(0.2)  # 等待内容加载
                    
                    # 最后滚动回顶部，确保从开始检查
                    list_container.evaluate('(element) => { element.scrollTop = 0; }')
                    print("已滚动回顶部")
                else:
                    print("列表容器内容无需滚动")
            else:
                print("未找到列表容器，使用备选滚动方法")
                self.fallback_scroll_method(page)
                
        except Exception as e:
            print(f"列表容器滚动失败: {e}")
            self.fallback_scroll_method(page)

    def fallback_scroll_method(self, page):
        """
        备选滚动方法 - 当列表容器滚动失败时使用
        """
        print("使用备选滚动方法...")
        
        try:
            # 获取视口高度
            viewport_height = page.evaluate('() => window.innerHeight')
            
            # 小幅滚动：每次滚动视口高度的1/8
            scroll_step = viewport_height // 8
            print(f"备选滚动 - 视口高度: {viewport_height}px, 每步滚动: {scroll_step}px")
            
            # 分8次小幅滚动
            for i in range(1, 9):
                scroll_position = scroll_step * i
                page.evaluate(f'(position) => {{ window.scrollTo(0, position); }}', scroll_position)
                time.sleep(0.1)  # 短暂等待内容加载
            
            # 最后回到顶部
            page.evaluate('() => { window.scrollTo(0, 0); }')
            time.sleep(0.3)
            
        except Exception as e:
            print(f"备选滚动方法失败: {e}")

    def handle_immediate_contract(self, page):
        """
        处理立即签约情况 - 暂时不处理，直接返回
        """
        print("检测到立即签约按钮，根据配置暂时不处理，返回小说列表")
        # 这里可以记录日志或统计信息，但不进行任何操作
        return False

    def handle_contract_process(self, page, attempt=0):
        """
        处理签约管理流程
        包括点击申请签约按钮和填写必要信息
        """
        print(f"处理签约管理流程 (第{attempt+1}次尝试)...")
        
        try:
            # 等待签约管理页面加载
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 检查是否已经在签约管理页面
            page_title = page.title()
            current_url = page.url
            
            print(f"当前页面: {page_title}")
            print(f"当前URL: {current_url}")
            
            # 首先检查是否有"立即签约"按钮
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
                            # 调用处理立即签约的方法
                            return self.handle_immediate_contract(page)
                except Exception as e:
                    print(f"检查立即签约按钮时出错: {e}")
                    continue
            
            # 如果没有立即签约按钮，继续原有的申请签约流程
            # 首先尝试点击申请签约按钮 - 使用您提供的XPath
            apply_contract_xpath = '/html/body/div[3]/div[2]/div/div[2]/div[3]/button[2]'
            apply_contract_buttons = page.locator(f'xpath={apply_contract_xpath}')
            
            if apply_contract_buttons.count() > 0:
                button_text = apply_contract_buttons.first.text_content().strip()
                print(f"找到申请签约按钮: {button_text}")
                
                if self.safe_click(apply_contract_buttons.first, "申请签约按钮"):
                    print("已点击申请签约按钮，等待6秒延迟...")
                    time.sleep(6)  # 等待6秒延迟
                    
                    # 点击后可能需要填写表单，调用表单填写方法
                    if self.fill_contract_details_form(page):
                        print("✓ 签约申请表单填写完成")
                        return True
                    else:
                        print("⚠ 签约申请表单填写未完成")
                        return False
            else:
                print("未找到申请签约按钮，尝试其他选择器...")
                
                # 尝试其他可能的选择器
                alternative_selectors = [
                    'button:has-text("申请签约")',
                    '//button[contains(text(), "申请签约")]',
                    '//span[contains(text(), "申请签约")]'
                    
                    '/html/body/div[3]/div[2]/div/div[2]/div[3]/button[2]/span'
                ]

                for selector in alternative_selectors:
                    try:
                        if selector.startswith('//'):
                            elements = page.locator(f'xpath={selector}')
                        else:
                            elements = page.locator(selector)

                        if elements.count() > 0:
                            button_text = elements.first.text_content().strip()
                            print(f"找到申请签约按钮(备选): {button_text}")

                            if self.safe_click(elements.first, "申请签约按钮(备选)"):
                                print("1 已点击申请签约按钮(备选)，等待3秒延迟...")
                                # time.sleep(3)  # 等待3秒延迟
                                break
                                # # 点击后可能需要填写表单
                                # if self.fill_contract_details_form(page):
                                #     print("✓ 签约申请表单填写完成")
                                #     return True
                                # else:
                                #     print("⚠ 签约申请表单填写未完成")
                                #     return False
                    except Exception as e:
                        print(f"尝试选择器 {selector} 失败: {e}")
                        continue

                time.sleep(6)  # 等待6秒延迟

                # 或者更稳健的写法（推荐）：定位包含 "去修改" 的 button，然后找它后面那个 button
                apply_sign_btn = page.locator("""
                  (//button[.//span[text()="去修改"]]/following-sibling::button)[1]
                """)

                if apply_sign_btn.count() > 0:
                    if self.safe_click(apply_sign_btn.first, "申请签约(按钮)"):
                        print("2 已点击申请签约按钮，等待30秒延迟...")
                        time.sleep(30)  # 等待6秒延迟
                        # 点击后可能需要填写表单
                        if self.fill_contract_details_form(page):
                            print("✓ 2 签约申请表单填写完成")
                            return True
                        else:
                            print("⚠ 2 签约申请表单填写未完成")
                            return False

                # for selector in alternative_selectors:
                #     try:
                #         if selector.startswith('//'):
                #             elements = page.locator(f'xpath={selector}')
                #         else:
                #             elements = page.locator(selector)
                #
                #         if elements.count() > 0:
                #             button_text = elements.first.text_content().strip()
                #             print(f"2 找到申请签约按钮(备选): {button_text}")
                #
                #             if self.safe_click(elements.first, "申请签约按钮(备选)"):
                #                 print("2 已点击申请签约按钮，等待30秒延迟...")
                #                 time.sleep(30)  # 等待6秒延迟
                #
                #                 # 点击后可能需要填写表单
                #                 if self.fill_contract_details_form(page):
                #                     print("✓ 2 签约申请表单填写完成")
                #                     return True
                #                 else:
                #                     print("⚠ 2 签约申请表单填写未完成")
                #                     return False
                #     except Exception as e:
                #         print(f"2 尝试选择器 {selector} 失败: {e}")
                #         continue
                
                # 如果仍然没有找到申请签约按钮，尝试滑动页面寻找填写合同按钮
                print("未找到申请签约按钮，尝试滑动页面寻找填写合同按钮...")
                if self.find_and_click_contract_button(page):
                    # 填写合同表单
                    if self.fill_contract_details_form(page):
                        print("✓ 合同详情表单填写完成")
                        return True
                    else:
                        print("⚠ 合同详情表单填写未完成")
                        return False
                else:
                    print("未找到可用的申请签约按钮或填写合同按钮")
                    return False
            
        except Exception as e:
            print(f"处理签约流程时出错: {e}")
            return False

    def find_and_click_contract_button(self, page):
        """
        滑动页面寻找填写合同按钮并点击
        """
        print("滑动页面寻找填写合同按钮...")
        
        try:
            # 首先尝试直接查找填写合同按钮
            contract_button_xpath = '//*[@id="arco-tabs-4-panel-1"]/div/div/div[3]/div[2]/div[3]/div[2]/button'
            contract_buttons = page.locator(f'xpath={contract_button_xpath}')
            
            if contract_buttons.count() > 0:
                button_text = contract_buttons.first.text_content().strip()
                print(f"找到填写合同按钮: {button_text}")
                
                if self.safe_click(contract_buttons.first, "填写合同按钮"):
                    print("已点击填写合同按钮")
                    time.sleep(3)
                    return True
            
            # 如果直接查找失败，尝试滑动页面查找
            print("直接查找填写合同按钮失败，尝试滑动页面查找...")
            
            # 滑动页面查找填写合同按钮
            max_scroll_attempts = 3
            scroll_step = 300  # 每次滚动300px
            
            for scroll_attempt in range(max_scroll_attempts):
                print(f"滑动页面查找填写合同按钮 (尝试 {scroll_attempt+1}/{max_scroll_attempts})...")
                
                # 尝试滑动页面
                current_scroll = page.evaluate('() => window.pageYOffset')
                target_scroll = current_scroll + scroll_step
                page.evaluate(f'(position) => {{ window.scrollTo(0, position); }}', target_scroll)
                time.sleep(1)  # 等待页面加载
                
                # 再次尝试查找填写合同按钮
                contract_buttons = page.locator(f'xpath={contract_button_xpath}')
                if contract_buttons.count() > 0:
                    button_text = contract_buttons.first.text_content().strip()
                    print(f"滑动后找到填写合同按钮: {button_text}")
                    
                    if self.safe_click(contract_buttons.first, "填写合同按钮"):
                        print("已点击填写合同按钮")
                        time.sleep(3)
                        return True
            
            # 如果滑动后仍然没有找到，尝试其他可能的合同按钮选择器
            print("滑动页面后仍未找到填写合同按钮，尝试其他选择器...")
            
            alternative_contract_selectors = [
                'button:has-text("填写合同")',
                'button:has-text("签署合同")',
                'button:has-text("合同签署")',
                '//button[contains(text(), "填写合同")]',
                '//button[contains(text(), "签署合同")]',
                '//button[contains(text(), "合同签署")]',
                '//span[contains(text(), "填写合同")]',
                '//span[contains(text(), "签署合同")]',
                '//span[contains(text(), "合同签署")]'
            ]
            
            for selector in alternative_contract_selectors:
                try:
                    if selector.startswith('//'):
                        elements = page.locator(f'xpath={selector}')
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0:
                        button_text = elements.first.text_content().strip()
                        print(f"找到填写合同按钮(备选): {button_text}")
                        
                        if self.safe_click(elements.first, "填写合同按钮(备选)"):
                            print("已点击填写合同按钮(备选)")
                            time.sleep(3)
                            return True
                except Exception as e:
                    print(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            print("所有查找填写合同按钮的尝试都失败了")
            return False
            
        except Exception as e:
            print(f"查找填写合同按钮时出错: {e}")
            return False

    def fill_contract_details_form(self, page):
        """
        填写合同详情表单
        包括手机号、邮箱、QQ、地址、详细地址、银行卡信息和银行支行
        """
        print("填写合同详情表单...")
        
        try:
            # 等待合同详情页面加载
            page.wait_for_load_state("networkidle")
            time.sleep(2)
            
            # 首先滑动页面确保所有元素可见
            print("滑动页面确保所有表单元素可见...")
            self.scroll_contract_form(page)
            
            # 获取当前用户的联系信息
            contact_info = self.get_user_contact_info()
            current_user = self.get_current_user_info()
            print(f"使用签约用户配置: {current_user['user_id']}")
            
            # 填写手机号
            phone_input_xpath = '//*[@id="phone_input"]'
            phone_input = page.locator(f'xpath={phone_input_xpath}')
            if phone_input.count() > 0:
                phone = contact_info.get("phone", "13760125919")
                if self.safe_fill(phone_input.first, phone, "手机号"):
                    print(f"✓ 已填写手机号: {phone}")
                else:
                    print("✗ 填写手机号失败")
            else:
                print("未找到手机号输入框")
            
            time.sleep(1)
            
            # 填写邮箱
            email_input_xpath = '//*[@id="email_input"]'
            email_input = page.locator(f'xpath={email_input_xpath}')
            if email_input.count() > 0:
                email = contact_info.get("email", "405625365@qq.com")
                if self.safe_fill(email_input.first, email, "邮箱"):
                    print(f"✓ 已填写邮箱: {email}")
                else:
                    print("✗ 填写邮箱失败")
            else:
                print("未找到邮箱输入框")
            
            time.sleep(1)
            
            # 填写QQ
            qq_input_xpath = '//*[@id="qq_input"]'
            qq_input = page.locator(f'xpath={qq_input_xpath}')
            if qq_input.count() > 0:
                qq = contact_info.get("qq", "405625365")
                if self.safe_fill(qq_input.first, qq, "QQ"):
                    print(f"✓ 已填写QQ: {qq}")
                else:
                    print("✗ 填写QQ失败")
            else:
                print("未找到QQ输入框")
            
            time.sleep(1)
            
            # 填写地址 - 使用级联选择器
            print("填写地址级联选择器...")
            if self.fill_address_cascader(page, contact_info):
                print("✓ 地址填写成功")
            else:
                print("✗ 地址填写失败")
            
            time.sleep(1)
            
            # 填写详细地址
            address_detail_input_xpath = '//*[@id="addressDetail_input"]'
            address_detail_input = page.locator(f'xpath={address_detail_input_xpath}')
            if address_detail_input.count() > 0:
                # 滑动一下页面
                print("滑动页面以显示详细地址输入框...")
                page.evaluate('() => { window.scrollBy(0, 200); }')
                time.sleep(1)
                
                address_info = contact_info.get("address", {})
                detail_address = address_info.get("detail", "宝安区")
                if self.safe_fill(address_detail_input.first, detail_address, "详细地址"):
                    print(f"✓ 已填写详细地址: {detail_address}")
                else:
                    print("✗ 填写详细地址失败")
            else:
                print("未找到详细地址输入框")
            
            time.sleep(1)
            
            # 填写银行卡号
            bank_account_input_xpath = '//*[@id="bankAccount_input"]'
            bank_account_input = page.locator(f'xpath={bank_account_input_xpath}')
            if bank_account_input.count() > 0:
                bank_account = contact_info.get("bank_account", "6214857812704759")
                if self.safe_fill(bank_account_input.first, bank_account, "银行卡号"):
                    print(f"✓ 已填写银行卡号: {bank_account}")
                else:
                    print("✗ 填写银行卡号失败")
            else:
                print("未找到银行卡号输入框")
            
            time.sleep(1)
            
            # 填写银行支行
            if self.fill_bank_branch(page, contact_info):
                print("✓ 银行支行填写成功")
            else:
                print("✗ 银行支行填写失败")
            
            time.sleep(1)
            
            # 提交合同表单
            if self.submit_contract_form(page):
                print("✓ 合同表单提交成功")
                return True
            else:
                print("⚠ 合同表单提交失败")
                return False
            
        except Exception as e:
            print(f"填写合同详情表单时出错: {e}")
            return False

    def fill_address_cascader(self, page, contact_info=None):
        """
        填写地址级联选择器
        
        Args:
            page: 页面对象
            contact_info: 联系信息字典，如果为None则使用默认配置
        """
        print("处理地址级联选择器...")
        
        try:
            # 获取地址信息
            if contact_info:
                address_info = contact_info.get("address", {})
                province = address_info.get("province", "广东省")
                city = address_info.get("city", "深圳市")
            else:
                province = "广东省"
                city = "深圳市"
            
            print(f"将要选择的地址: {province} {city}")
            
            # 使用正确的地址级联选择器XPath
            address_cascader_xpath = '//*[@id="address_input"]/div/span/input'
            address_cascader = page.locator(f'xpath={address_cascader_xpath}')
            
            if address_cascader.count() == 0:
                print("未找到地址级联选择器输入框")
                return False
            
            print("找到地址级联选择器输入框")
            
            # 先点击地址选择器
            if not self.safe_click(address_cascader.first, "地址选择器"):
                print("点击地址选择器失败")
                return False
            
            time.sleep(1)
            
            # 等待弹出框出现
            popup_selectors = [
                '//div[contains(@class, "arco-cascader-popup")]',
                '//div[contains(@id, "arco-cascader-popup")]',
                '//div[@class="arco-cascader-popup"]'
            ]
            
            popup = None
            for selector in popup_selectors:
                popup = page.locator(f'xpath={selector}')
                if popup.count() > 0:
                    print("找到地址选择器弹出框")
                    break
            
            if popup is None or popup.count() == 0:
                print("地址选择器弹出框未出现")
                return False
            
            # 尝试直接选择省份
            print(f"尝试直接选择{province}...")
            province_selectors = [
                f'//span[text()="{province}"]',
                f'//div[text()="{province}"]',
                f'//*[text()="{province}"]'
            ]
            
            province_selected = False
            for selector in province_selectors:
                try:
                    elements = page.locator(f'xpath={selector}')
                    if elements.count() > 0:
                        # 找到父级元素并点击
                        parent_element = elements.first.locator('xpath=./ancestor::div[contains(@class, "arco-cascader-list-item")]')
                        if parent_element.count() > 0:
                            if self.safe_click(parent_element.first, province):
                                province_selected = True
                                print(f"✓ 已选择{province}")
                                time.sleep(1)
                                break
                        else:
                            # 如果没有找到父级元素，直接点击找到的元素
                            if self.safe_click(elements.first, f"{province}(直接点击)"):
                                province_selected = True
                                print(f"✓ 已选择{province}(直接点击)")
                                time.sleep(1)
                                break
                except Exception as e:
                    print(f"尝试选择{province}失败: {e}")
                    continue
            
            if province_selected:
                # 等待第二级列表加载
                time.sleep(1)
                
                # 然后选择城市
                print(f"选择{city}...")
                city_selectors = [
                    f'//span[text()="{city}"]',
                    f'//div[text()="{city}"]',
                    f'//*[text()="{city}"]'
                ]
                
                for city_selector in city_selectors:
                    try:
                        city_elements = page.locator(f'xpath={city_selector}')
                        if city_elements.count() > 0:
                            # 找到父级元素并点击
                            city_parent = city_elements.first.locator('xpath=./ancestor::div[contains(@class, "arco-cascader-list-item")]')
                            if city_parent.count() > 0:
                                if self.safe_click(city_parent.first, city):
                                    print(f"✓ 已选择{city}")
                                    return True
                            else:
                                # 如果没有找到父级元素，直接点击找到的元素
                                if self.safe_click(city_elements.first, f"{city}(直接点击)"):
                                    print(f"✓ 已选择{city}(直接点击)")
                                    return True
                    except Exception as e:
                        print(f"尝试选择{city}失败: {e}")
                        continue
            
            print("所有地址选择方法都失败了")
            return False
            
        except Exception as e:
            print(f"填写地址级联选择器时出错: {e}")
            return False

    def fill_bank_branch(self, page, contact_info=None):
        """
        填写银行支行信息
        
        Args:
            page: 页面对象
            contact_info: 联系信息字典，如果为None则使用默认配置
        """
        print("填写银行支行信息...")
        
        try:
            # 获取银行支行信息
            if contact_info:
                bank_branch = contact_info.get("bank_branch", "招商银行深圳愉康支行")
            else:
                bank_branch = "招商银行深圳愉康支行"
            
            # 查找银行支行输入框
            bank_code_input_xpath = '//*[@id="bankCode_input"]/div/span/input'
            bank_code_input = page.locator(f'xpath={bank_code_input_xpath}')
            
            if bank_code_input.count() == 0:
                print("未找到银行支行输入框")
                return False
            
            # 先点击输入框
            if not self.safe_click(bank_code_input.first, "银行支行输入框"):
                print("点击银行支行输入框失败")
                return False
            
            time.sleep(1)
            
            # 输入银行支行名称
            if not self.safe_fill(bank_code_input.first, bank_branch, "银行支行"):
                print("填写银行支行失败")
                return False
            
            time.sleep(2)  # 等待下拉选项加载
            
            # 尝试点击您提供的下拉选项XPath
            dropdown_option_xpath = '//*[@id="arco-select-popup-2"]/div/div/li/span[2]'
            dropdown_option = page.locator(f'xpath={dropdown_option_xpath}')
            
            if dropdown_option.count() > 0:
                option_text = dropdown_option.first.text_content().strip()
                print(f"找到银行支行下拉选项: {option_text}")
                
                if bank_branch in option_text:
                    if self.safe_click(dropdown_option.first, "银行支行下拉选项"):
                        print("✓ 已选择银行支行下拉选项")
                        return True
                else:
                    print(f"下拉选项文本不符合预期: {option_text}")
            else:
                print("未找到指定的银行支行下拉选项XPath")
            
            # 如果特定XPath找不到，尝试使用类名和文本匹配
            print("尝试使用类名和文本匹配查找银行支行选项...")
            
            # 使用您提供的类名和文本匹配
            bank_option_selectors = [
                f'//span[@class="arco-select-highlight" and contains(text(), "{bank_branch}")]',
                f'//span[contains(@class, "arco-select-highlight") and contains(text(), "{bank_branch}")]',
                f'//li//span[contains(text(), "{bank_branch}")]',
                f'//div[contains(@class, "arco-select-option")]//span[contains(text(), "{bank_branch}")]'
            ]
            
            for selector in bank_option_selectors:
                try:
                    elements = page.locator(f'xpath={selector}')
                    if elements.count() > 0:
                        option_text = elements.first.text_content().strip()
                        print(f"找到银行支行选项(文本匹配): {option_text}")
                        
                        if self.safe_click(elements.first, "银行支行选项(文本匹配)"):
                            print("✓ 已选择银行支行选项(文本匹配)")
                            return True
                except Exception as e:
                    print(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            # 如果以上方法都失败，尝试查找包含银行支行名称的任何元素
            print("尝试通用文本匹配查找银行支行选项...")
            
            generic_selectors = [
                f'//*[contains(text(), "{bank_branch}")]',
                f'//span[contains(text(), "{bank_branch}")]',
                f'//div[contains(text(), "{bank_branch}")]',
                f'//li[contains(text(), "{bank_branch}")]'
            ]
            
            for selector in generic_selectors:
                try:
                    elements = page.locator(f'xpath={selector}')
                    if elements.count() > 0:
                        option_text = elements.first.text_content().strip()
                        print(f"找到银行支行选项(通用匹配): {option_text}")
                        
                        # 找到可点击的父级元素
                        clickable_parent = elements.first.locator('xpath=./ancestor::li | ./ancestor::div[contains(@class, "option")] | ./ancestor::div[contains(@class, "select")]')
                        if clickable_parent.count() > 0:
                            if self.safe_click(clickable_parent.first, "银行支行选项(通用匹配)"):
                                print("✓ 已选择银行支行选项(通用匹配)")
                                return True
                        else:
                            # 如果没有找到父级元素，直接点击找到的元素
                            if self.safe_click(elements.first, "银行支行选项(直接点击)"):
                                print("✓ 已选择银行支行选项(直接点击)")
                                return True
                except Exception as e:
                    print(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            print("所有银行支行选择方法都失败了")
            return False
            
        except Exception as e:
            print(f"填写银行支行信息时出错: {e}")
            return False

    def scroll_contract_form(self, page):
        """
        滑动合同表单页面以确保所有元素可见
        """
        print("滑动合同表单页面...")
        
        try:
            # 获取页面高度
            page_height = page.evaluate('() => document.body.scrollHeight')
            viewport_height = page.evaluate('() => window.innerHeight')
            
            print(f"页面高度: {page_height}px, 视口高度: {viewport_height}px")
            
            # 如果页面高度大于视口高度，则需要滚动
            if page_height > viewport_height:
                # 计算滚动步数
                scroll_steps = 3
                scroll_step = (page_height - viewport_height) // scroll_steps
                
                print(f"将分 {scroll_steps} 步滚动合同表单，每步 {scroll_step}px")
                
                # 逐步滚动
                for step in range(1, scroll_steps + 1):
                    target_scroll = scroll_step * step
                    page.evaluate(f'(position) => {{ window.scrollTo(0, position); }}', target_scroll)
                    print(f"滚动到: {target_scroll}px")
                    time.sleep(0.5)  # 等待内容加载
                
                # 滚动回顶部
                page.evaluate('() => { window.scrollTo(0, 0); }')
                time.sleep(0.5)
            else:
                print("合同表单页面无需滚动")
                
        except Exception as e:
            print(f"滑动合同表单页面时出错: {e}")

    def navigate_to_next_page(self, page, direction="next"):
        """
        导航到下一页或上一页 - 增强版本，支持双向翻页
        """
        try:
            if direction == "next":
                # 下一页选择器
                next_selectors = [
                    '//*[@id="arco-tabs-6-panel-0"]/div/div/div/div[2]/ul/li[7]/svg',
                    'button:has-text("下一页")',
                    '.arco-pagination-next',
                    '[class*="next"]',
                    'button[aria-label="下一页"]',
                    '//button[contains(text(), "下一页")]',
                    '//span[contains(text(), "下一页")]'
                ]
                button_desc = "下一页按钮"
                disabled_desc = "下一页按钮不可点击，已到达最后一页"
            else:
                # 上一页选择器
                next_selectors = [
                    '//*[@id="arco-tabs-6-panel-0"]/div/div/div/div[2]/ul/li[1]/svg',
                    'button:has-text("上一页")',
                    '.arco-pagination-prev',
                    '[class*="prev"]',
                    'button[aria-label="上一页"]',
                    '//button[contains(text(), "上一页")]',
                    '//span[contains(text(), "上一页")]'
                ]
                button_desc = "上一页按钮"
                disabled_desc = "上一页按钮不可点击，已到达第一页"
            
            for selector in next_selectors:
                try:
                    # 如果是XPath选择器
                    if selector.startswith('//'):
                        next_btn = page.locator(f'xpath={selector}')
                    else:
                        next_btn = page.locator(selector).first
                    
                    if next_btn.count() > 0:
                        # 检查按钮是否被禁用
                        is_disabled = next_btn.get_attribute('disabled') is not None or \
                                    'disabled' in next_btn.get_attribute('class') or \
                                    not next_btn.is_enabled()
                        
                        if is_disabled:
                            print(disabled_desc)
                            return 'no_more_pages'
                        
                        # 检查按钮是否可见
                        if next_btn.is_visible():
                            self.safe_click(next_btn, button_desc)
                            time.sleep(1)
                            return True
                        else:
                            # 如果下一页按钮不可见，先滑动页面到底部
                            print(f"{button_desc}不可见，滑动页面...")
                            page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                            time.sleep(0.5)
                            
                            # 再次尝试点击
                            if next_btn.is_visible() and next_btn.is_enabled():
                                self.safe_click(next_btn, f"{button_desc}(滑动后)")
                                time.sleep(1)
                                return True
                            else:
                                # 如果滑动后仍然不可见或不可用，尝试使用JavaScript点击
                                print(f"尝试通过JavaScript点击{button_desc}...")
                                next_btn.evaluate('(element) => element.click()')
                                time.sleep(1)
                                return True
                except Exception as e:
                    print(f"尝试选择器 {selector} 失败: {e}")
                    continue
            
            print(f"未找到可用的{button_desc}")
            return False
            
        except Exception as e:
            print(f"翻页时出错: {e}")
            return False

    def safe_click(self, element, desc="元素", timeout=None, retries=3):
        """
        安全的点击操作
        """
        timeout = timeout or self.config["timeouts"]["click"]
        
        for attempt in range(retries):
            try:
                element.scroll_into_view_if_needed()
                element.wait_for(state="visible", timeout=5000)
                
                try:
                    # element.click(timeout=timeout)
                    element.click(force=True, timeout=timeout)
                    print(f"✓ 成功点击: {desc}")
                    time.sleep(0.3)
                    return True
                except Exception as e:
                    if "intercepts pointer events" in str(e) and attempt < retries - 1:
                        print(f"第{attempt+1}次点击被遮挡，尝试强制点击...")
                        element.click(force=True, timeout=timeout)
                        print(f"✓ 强制点击成功: {desc}")
                        time.sleep(0.3)
                        return True
                    else:
                        raise e
                        
            except Exception as e:
                print(f"✗ 点击失败 {desc} (尝试 {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    wait_time = 2 * (attempt + 1)
                    print(f"等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                else:
                    return False
        return False

    def safe_fill(self, element, text, desc="元素", timeout=None):
        """
        安全的填充文本操作
        """
        timeout = timeout or self.config["timeouts"]["fill"]
        try:
            element.scroll_into_view_if_needed()
            element.click()
            time.sleep(0.3)
            element.fill(text, timeout=timeout)
            print(f"✓ 成功填充: {desc}")
            time.sleep(0.3)
            return True
        except Exception as e:
            print(f"✗ 填充失败 {desc}: {e}")
            return False

    def submit_contract_form(self, page):
        """
        提交合同表单并处理确认弹窗
        """
        print("提交合同表单...")
        
        try:
            # 首先尝试使用您提供的确认提交按钮XPath
            confirm_submit_xpath = '//*[@id="app"]/div/div[2]/div/div[2]/div/div/button'
            confirm_submit_buttons = page.locator(f'xpath={confirm_submit_xpath}')
            
            if confirm_submit_buttons.count() > 0:
                button_text = confirm_submit_buttons.first.text_content().strip()
                print(f"找到确认提交按钮: {button_text}")
                
                if "确认无误，提交" in button_text:
                    if self.safe_click(confirm_submit_buttons.first, "确认无误提交按钮"):
                        print("已点击确认无误提交按钮")
                        time.sleep(3)
                        
                        # 处理合同确认弹窗中的生成合同按钮
                        if self.handle_contract_confirmation_popup(page):
                            return True
                        else:
                            # 如果没有弹窗，可能是直接成功了
                            return self.handle_success_popup(page)
            
            # 如果特定按钮找不到，尝试通用提交按钮
            submit_buttons = [
                'button:has-text("确认无误，提交")',
                'button:has-text("提交")',
                'button:has-text("确认")',
                'button:has-text("确定")',
                'button:has-text("完成")',
                '//button[contains(text(), "确认无误，提交")]',
                '//button[contains(text(), "提交")]',
                '//button[contains(text(), "确认")]',
                '//button[contains(text(), "确定")]',
                '//button[contains(text(), "完成")]'
            ]
            
            for selector in submit_buttons:
                try:
                    if selector.startswith('//'):
                        elements = page.locator(f'xpath={selector}')
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0 and elements.first.is_visible():
                        button_text = elements.first.text_content().strip()
                        print(f"找到提交按钮: {button_text}")
                        
                        if self.safe_click(elements.first, "提交按钮"):
                            print("已提交合同表单")
                            time.sleep(3)
                            
                            # 处理合同确认弹窗中的生成合同按钮
                            if self.handle_contract_confirmation_popup(page):
                                return True
                            else:
                                # 如果没有弹窗，可能是直接成功了
                                return self.handle_success_popup(page)
                except Exception as e:
                    print(f"尝试提交按钮 {selector} 失败: {e}")
                    continue
            
            print("未找到提交按钮，可能表单已自动提交")
            return True
            
        except Exception as e:
            print(f"提交合同表单时出错: {e}")
            return False

    def handle_contract_confirmation_popup(self, page):
        """
        处理合同确认弹窗中的生成合同按钮
        """
        print("处理合同确认弹窗...")
        
        try:
            # 等待合同确认弹窗出现
            time.sleep(2)
            
            # 使用您提供的生成合同按钮XPath
            generate_contract_xpath = '/html/body/div[3]/div[2]/div/div[2]/div[2]/div[2]'
            generate_contract_buttons = page.locator(f'xpath={generate_contract_xpath}')
            
            if generate_contract_buttons.count() > 0:
                button_text = generate_contract_buttons.first.text_content().strip()
                print(f"找到生成合同按钮: {button_text}")
                
                if "生成合同" in button_text:
                    if self.safe_click(generate_contract_buttons.first, "生成合同按钮"):
                        print("✓ 已点击生成合同按钮，完成合同签署")
                        time.sleep(3)
                        
                        # 处理可能的成功提示或弹窗
                        return self.handle_success_popup(page)
            
            # 如果特定XPath找不到，尝试其他选择器
            print("尝试其他生成合同按钮选择器...")
            
            generate_contract_selectors = [
                'button:has-text("生成合同")',
                '//button[contains(text(), "生成合同")]',
                '//span[contains(text(), "生成合同")]',
                '//div[contains(text(), "生成合同")]'
            ]
            
            for selector in generate_contract_selectors:
                try:
                    if selector.startswith('//'):
                        elements = page.locator(f'xpath={selector}')
                    else:
                        elements = page.locator(selector)
                    
                    if elements.count() > 0 and elements.first.is_visible():
                        button_text = elements.first.text_content().strip()
                        print(f"找到生成合同按钮(备选): {button_text}")
                        
                        if self.safe_click(elements.first, "生成合同按钮(备选)"):
                            print("✓ 已点击生成合同按钮(备选)，完成合同签署")
                            time.sleep(3)
                            
                            # 处理可能的成功提示或弹窗
                            return self.handle_success_popup(page)
                except Exception as e:
                    print(f"尝试生成合同按钮选择器 {selector} 失败: {e}")
                    continue
            
            print("未找到生成合同按钮，可能已经自动生成或流程不同")
            return True
            
        except Exception as e:
            print(f"处理合同确认弹窗时出错: {e}")
            return False

    def handle_success_popup(self, page):
        """
        处理成功提交后的弹窗
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
                            self.safe_click(button.first, f"弹窗按钮: {button_name}")
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
                'text=合同生成成功',
                'text=生成合同成功'
            ]
            
            for selector in success_selectors:
                if page.locator(selector).count() > 0:
                    print("✓ 合同/签约申请已成功提交")
                    return True
            
            print("未检测到明确的成功提示，但流程已完成")
            return True
            
        except Exception as e:
            print(f"处理成功弹窗时出错: {e}")
            return 
        
    def check_and_handle_recommendations(self, page):
        """
        在小说列表页检查并处理所有作品的“作品推荐”流程。
        (最终版：增加状态记忆，防止对无法处理的作品进行重复扫描)
        """
        print("\n=== 开始检查作品推荐 ===")
        
        # --- 核心修改：增加状态记忆 ---
        # 创建一个集合，用于存储在本轮运行中已经尝试处理过的小说ID。
        # 无论处理成功还是失败，只要尝试过，就加入这里，避免重复进入。
        processed_book_ids = set()
        
        try:
            max_pages = 100
            for page_num in range(1, max_pages + 1):
                print(f"\n--- 正在检查第 {page_num} 页的作品推荐 ---")
                
                items_to_process_on_this_page = True
                while items_to_process_on_this_page:
                    self.scroll_list_container(page)
                    time.sleep(1)

                    novel_items = page.locator('div.long-article-table-item')
                    item_count = novel_items.count()
                    if item_count == 0:
                        print("当前页未找到小说项。")
                        break
                    
                    found_and_processed_this_cycle = False
                    for i in range(item_count):
                        item = novel_items.nth(i)
                        
                        # --- 核心修改：检查并跳过已处理的小说 ---
                        book_id = item.get_attribute('id')
                        if not book_id:
                            continue # 如果没有ID，无法追踪，跳过

                        if book_id in processed_book_ids:
                            continue # 如果这个ID已经处理过，直接跳到下一个小说

                        # 只有未处理过的小说才继续往下走
                        recommend_button = item.locator('button.arco-btn-primary:has-text("作品推荐")')

                        if recommend_button.count() > 0:
                            title_locator = item.locator('.info-content-title .hoverup')
                            novel_title = (title_locator.first.text_content() or "未知小说").strip()

                            # --- 核心修改：标记为已处理 ---
                            # 无论接下来成功与否，都将此ID加入集合，防止下次再扫描它。
                            print(f"为小说《{novel_title}》找到 '作品推荐' 按钮。")
                            print(f"  -> 标记 ID '{book_id}' 为本轮已尝试，将不再重复检查。")
                            processed_book_ids.add(book_id)
                            
                            if self.safe_click(recommend_button, f"作品推荐按钮 - 《{novel_title}》"):
                                page.wait_for_load_state("domcontentloaded")
                                time.sleep(2)
                                
                                success = self._process_recommendation_details(page)
                                if success:
                                    print(f"✓ 小说《{novel_title}》的作品推荐流程处理成功。")
                                else:
                                    # 即使处理失败（例如因为硬性条件），也因为ID已记录，不会再循环
                                    print(f"  -> 小说《{novel_title}》的推荐流程中止或有未满足的硬性条件。")

                                print("正在返回小说列表页...")
                                page.go_back()
                                page.wait_for_load_state("domcontentloaded")
                                time.sleep(2)
                                
                                found_and_processed_this_cycle = True
                                break # 跳出 for 循环，让 while 重新扫描页面
                    
                    if not found_and_processed_this_cycle:
                        items_to_process_on_this_page = False

                # 翻页逻辑
                if not items_to_process_on_this_page:
                    print("本页检查完毕，尝试翻至下一页...")
                    next_result = self.navigate_to_next_page(page, "next")
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
        
    def _handle_start_recommendation_confirm_popup(self, page):
        """
        处理点击“开始推荐”后弹出的“推荐确定”确认框。
        """
        print("    -> 正在处理 '推荐确定' 弹窗...")
        try:
            # 根据您提供的HTML，精准定位弹窗中的“确定”按钮
            confirm_button_selector = 'div.byte-modal-footer button.byte-btn-primary:has-text("确定")'
            
            # 明确等待该按钮出现，最多等待5秒
            page.wait_for_selector(confirm_button_selector, state='visible', timeout=5000)
            
            confirm_button = page.locator(confirm_button_selector)
            
            if self.safe_click(confirm_button, "'推荐确定'弹窗的确定按钮"):
                print("    -> ✓ 已点击 '确定'。")
                return True
            else:
                print("    -> ✗ 点击 '确定' 失败。")
                return False
                
        except Exception as e:
            # 如果超时（TimeoutError），说明弹窗没有出现
            if "Timeout" in str(e):
                print("    -> ⚠ 未在5秒内检测到 '推荐确定' 弹窗，可能流程已变更或本次无需确认。")
                # 在这种情况下，我们假设操作已经成功或可以继续，返回True
                return True
            else:
                print(f"    -> ✗ 处理 '推荐确定' 弹窗时发生意外错误: {e}")
                return False

    def _process_recommendation_details(self, page):
        """
        【内部函数】处理作品推荐详情页的具体逻辑。
        循环检查并完成所有准备任务，直到全部完成后点击“开始推荐”。
        """
        print(" -> 进入作品推荐详情页，开始处理推荐任务...")
        try:
            page.wait_for_selector('div.recommend-area.prepare-recommend', timeout=10000)

            max_attempts = 5  # 最大尝试次数，防止无限循环
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
                            if self.safe_click(confirm_button, f"任务'{task_title}'的确认按钮"):
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
                        if self.safe_click(start_button, "开始推荐按钮"):
                            print("  -> ✓ 已成功点击 '开始推荐'。")
                            # --- 新增逻辑：调用函数处理确认弹窗 ---
                            if self._handle_start_recommendation_confirm_popup(page):
                                print("  -> ✓ 推荐流程已最终确认。")
                                # 等待最终的“操作成功”之类的全局提示
                                time.sleep(1)
                                self.handle_success_popup(page)
                                return True
                            else:
                                print("  -> ✗ 推荐确认步骤失败，流程中止。")
                                return False
                            # --- 逻辑新增结束 ---
                            return True
                        else:
                            print("  -> ✗ 点击 '开始推荐' 按钮失败。")
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
    
    def get_user_contact_info(self, user_id=None):
        """
        获取指定用户的联系信息
        如果不指定用户ID，则返回当前用户的信息
        """
        if user_id is None:
            user_id = self.current_user_id
        
        # 多用户配置映射
        users_config = {
            "user1": {
                "phone": "13760125919",
                "email": "405625365@qq.com",
                "qq": "405625365",
                "bank_account": "6214857812704759",
                "bank_branch": "招商银行深圳愉康支行",
                "address": {
                    "province": "广东省",
                    "city": "深圳市",
                    "detail": "宝安区"
                }
            },
            "user2": {
                "phone": "13800138000",
                "email": "user2@example.com",
                "qq": "123456789",
                "bank_account": "6222021234567890123",
                "bank_branch": "工商银行北京分行",
                "address": {
                    "province": "北京市",
                    "city": "北京市",
                    "detail": "朝阳区"
                }
            },
            "user3": {
                "phone": "13900139000",
                "email": "user3@example.com",
                "qq": "987654321",
                "bank_account": "6228481234567890123",
                "bank_branch": "农业银行上海分行",
                "address": {
                    "province": "上海市",
                    "city": "上海市",
                    "detail": "浦东新区"
                }
            }
        }
        
        return users_config.get(user_id, users_config["user1"])
    
    def set_current_user(self, user_id):
        """设置当前签约用户"""
        if user_id in ["user1", "user2", "user3"]:
            self.current_user_id = user_id
            print(f"[成功] 已切换到签约用户: {user_id}")
            return True
        else:
            print(f"[错误] 用户 {user_id} 不存在")
            return False
    
    def get_current_user_info(self):
        """获取当前用户信息"""
        contact_info = self.get_user_contact_info()
        return {
            'user_id': self.current_user_id,
            'contact_info': contact_info
        }
    
    def list_users(self):
        """列出所有可用用户"""
        users = ["user1", "user2", "user3"]
        print("\n=== 可用签约用户 ===")
        for user in users:
            status = " (当前)" if user == self.current_user_id else ""
            print(f"{user}{status}")
        print("==================")
