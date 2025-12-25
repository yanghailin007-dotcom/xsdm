"""
番茄小说自动发布系统 - 小说操作模块
处理小说的创建、导航、查找等操作
"""

import os
import time
import json
import shutil
from datetime import datetime
from typing import Optional, List

from .config import CONFIG
from .utils import safe_click, safe_fill, format_synopsis_for_fanqie
from .tag_selector import select_novel_tags_interactive


def navigate_to_correct_book(page, expected_book_title):
    """
    导航到正确的书籍详情页
    """
    try:
        print(f"尝试导航到书籍《{expected_book_title}》...")

        # 首先确保在小说管理页面
        novel_selectors = [
            'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
            'text=小说',
            'span:has-text("小说")'
        ]

        for selector in novel_selectors:
            if safe_click(page.locator(selector).first, "小说标签"):
                break

        time.sleep(3)  # 等待书籍列表加载

        # 在书籍列表中查找目标书籍 - 使用您提供的书名元素XPath
        book_found = False

        # 首先尝试使用您提供的书名元素XPath模式
        # 注意：这个XPath包含特定ID，我们需要使用部分匹配
        book_title_selectors = [
            f'//div[contains(@id, "long-article-table-item")]/div/div[1]/div[2]/div[1]/div[contains(text(), "{expected_book_title}")]',
            f'//div[contains(@id, "long-article-table-item")]//div[contains(text(), "{expected_book_title}")]',
            f'//div[contains(text(), "{expected_book_title}")]'
        ]

        for selector in book_title_selectors:
            try:
                title_elements = page.locator(f'xpath={selector}')
                if title_elements.count() > 0:
                    # 找到匹配的标题，点击其父级元素或相关容器
                    for i in range(title_elements.count()):
                        title_element = title_elements.nth(i)
                        actual_title = title_element.text_content().strip()
                        if expected_book_title in actual_title:
                            # 点击包含这个标题的书籍项
                            book_item = title_element.locator(
                                'xpath=./ancestor::div[contains(@id, "long-article-table-item")]')
                            if book_item.count() > 0:
                                safe_click(book_item.first, f"书籍《{expected_book_title}》")
                                book_found = True
                                time.sleep(3)  # 等待书籍详情页加载
                                break
                    if book_found:
                        break
            except Exception as e:
                continue

        if not book_found:
            # 如果通过标题找不到，尝试其他方法
            book_items = page.locator('[class*="book"], [class*="item"], [class*="card"]')

            for i in range(book_items.count()):
                try:
                    item = book_items.nth(i)
                    item_text = item.text_content()
                    if expected_book_title in item_text:
                        safe_click(item, f"书籍《{expected_book_title}》")
                        book_found = True
                        time.sleep(3)  # 等待书籍详情页加载
                        break
                except:
                    continue

        if book_found:
            # 再次验证是否成功导航到目标书籍
            if verify_current_book_by_header(page, expected_book_title) or verify_current_book(page, expected_book_title):
                print(f"✓ 成功导航到书籍《{expected_book_title}》")
                return True
            else:
                print(f"⚠ 导航后仍然无法验证书籍《{expected_book_title}》")
                return False
        else:
            print(f"✗ 在书籍列表中未找到《{expected_book_title}》")
            return False

    except Exception as e:
        print(f"导航到正确书籍时出错: {e}")
        return False


def verify_current_book_by_header(page, expected_book_title):
    """
    通过发布页面的头部元素验证当前书籍
    """
    try:
        # 等待页面加载
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # 查找发布页面的书籍名称元素
        book_name_elements = page.locator('.publish-header-book-name')
        if book_name_elements.count() > 0:
            actual_title = book_name_elements.first.text_content().strip()
            if expected_book_title in actual_title:
                print(f"✓ 通过头部元素验证成功: 当前在书籍《{actual_title}》页面")
                return True
            else:
                print(f"✗ 书籍不匹配! 期望: {expected_book_title}, 实际: {actual_title}")
                return False
        else:
            print("⚠ 未找到发布页面头部书籍名称元素")
            return False

    except Exception as e:
        print(f"通过头部元素验证当前书籍时出错: {e}")
        return False


def verify_current_book(page, expected_book_title):
    """
    验证当前页面是否在正确的书籍详情页 - 使用多种方法
    """

    # 如果头部元素验证失败，尝试其他方法
    try:
        # 等待页面加载
        page.wait_for_load_state("networkidle")
        time.sleep(2)

        # 尝试多种选择器查找书籍标题
        title_selectors = [
            'h1',  # 通常书籍标题使用h1标签
            '.book-title',
            '.title',
            '[class*="title"]',
            '[class*="book"] h1',
            '[class*="book"] [class*="title"]'
        ]

        for selector in title_selectors:
            try:
                title_elements = page.locator(selector)
                if title_elements.count() > 0:
                    for i in range(title_elements.count()):
                        actual_title = title_elements.nth(i).text_content().strip()
                        if actual_title and expected_book_title in actual_title:
                            print(f"✓ 验证成功: 当前在书籍《{actual_title}》详情页")
                            return True
            except:
                continue

        # 如果通过选择器找不到，尝试通过页面URL或其它元素判断
        print(f"⚠ 无法验证当前书籍，期望: {expected_book_title}")
        return False

    except Exception as e:
        print(f"验证当前书籍时出错: {e}")
        return False


def create_new_book(page, novel_title, formatted_synopsis, main_character, novel_data):
    """创建新书 - 适配新的JSON结构"""
    print("创建新书...")

    # 尝试多种选择器来找到"创建新书"按钮
    create_new_book_selectors = [
        # 基于用户提供的HTML结构，使用class选择器
        'div.font-4.hoverup:has-text("创建新书")',
        # 备用XPath选择器
        '//div[contains(@class, "font-4") and contains(@class, "hoverup") and contains(text(), "创建新书")]',
        '//div[contains(text(), "创建新书")]',
        # 原有的XPath作为备用
        'xpath=//*[@id="app"]/div/div[2]/div[2]/div/div/div[1]/div/div[2]/div/span/div',
    ]
    
    create_new_book_clicked = False
    for selector in create_new_book_selectors:
        try:
            if selector.startswith('xpath='):
                element = page.locator(selector)
            else:
                element = page.locator(selector)
            
            if element.count() > 0 and element.first.is_visible():
                if safe_click(element.first, "创建新书"):
                    create_new_book_clicked = True
                    print("✓ 成功点击创建新书按钮")
                    break
        except Exception as e:
            print(f"尝试选择器 {selector} 失败: {e}")
            continue
    
    if not create_new_book_clicked:
        print("✗ 无法点击创建新书按钮，尝试继续...")
    
    time.sleep(1)  # 增加等待时间，确保下拉菜单完全展开
    
    # 尝试多种选择器来找到"创建书本"选项
    create_book_selectors = [
        # 直接文本匹配
        'text=创建书本',
        # 包含文本匹配
        ':has-text("创建书本")',
        # XPath文本匹配
        'xpath=//*[text()="创建书本"]',
        'xpath=//*[contains(text(), "创建书本")]',
        # 可能是li或div元素
        'li:has-text("创建书本")',
        'div:has-text("创建书本")',
    ]
    
    create_book_clicked = False
    for selector in create_book_selectors:
        try:
            element = page.locator(selector)
            if element.count() > 0:
                # 尝试点击第一个可见的元素
                for i in range(element.count()):
                    try:
                        if element.nth(i).is_visible():
                            if safe_click(element.nth(i), "创建书本"):
                                create_book_clicked = True
                                print("✓ 成功点击创建书本选项")
                                break
                    except:
                        continue
                if create_book_clicked:
                    break
        except Exception as e:
            print(f"尝试选择器 {selector} 失败: {e}")
            continue
    
    if not create_book_clicked:
        print("✗ 无法点击创建书本选项，尝试继续...")
    
    time.sleep(0.5)

    # 填写书名
    title_short = novel_title[-15:] if len(novel_title) >= 15 else novel_title
    safe_fill(page.locator('xpath=//*[@id="name_input"]/div/span/span/input'), title_short, "书名")

    # 选择男女频 - 从selected_plan.tags.target_audience获取
    tags_info = novel_data.get("project_info", {}).get("selected_plan", {}).get("tags", {})
    gender = tags_info.get("target_audience", "男频")
    if gender == "女频":
        safe_click(page.locator('xpath=//*[@id="radio"]/div/div/label[2]/span[1]'), "女频")
        print("✓ 选择女频")
    else:
        safe_click(page.locator('xpath=//*[@id="radio"]/div/div/label[1]/span[1]'), "男频")
        print("✓ 选择男频")

    # 选择作品标签
    print("选择作品标签...")
    safe_click(page.locator('xpath=//*[@id="selectRow"]/div/div/span/div/span[1]'), "选择作品标签")
    time.sleep(3)  # 等待标签弹窗完全加载

    # 使用新的标签选择函数
    if select_novel_tags_interactive(page, novel_data):
        print("✓ 标签选择完成")
    else:
        print("⚠ 标签选择可能有问题，但继续流程")

    # 上传封面
    upload_book_cover(page, novel_title)

    # 填写主角名
    character_short = main_character[:5] if len(main_character) >= 5 else main_character
    safe_fill(page.locator('xpath=//*[@id="roleList"]/div/div/div[1]/span/span/input'), character_short, "主角名")

    # 填写作品简介
    synopsis_short = formatted_synopsis[:500] if len(formatted_synopsis) >= 500 else formatted_synopsis
    safe_fill(page.locator('xpath=//*[@id="descRow_input"]/div/div/textarea'), synopsis_short, "作品简介")

    # 立即创建
    safe_click(page.locator('xpath=//*[@id="app"]/div/div[2]/div[2]/div[2]/div[2]/button[2]/span'), "立即创建")
    print("✓ 提交创建书籍")

    # 等待创建完成并返回小说列表
    print("等待书籍创建完成...")
    for _ in range(10):
        # 尝试返回小说列表
        safe_click(
            page.locator('xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]'),
            "小说标签")
        time.sleep(1)
        try:
            page.get_by_text(title_short, exact=True).wait_for(state="visible", timeout=1000)
            return True
        except:
            pass

    return False


def upload_book_cover(page, novel_title):
    """上传书籍封面"""
    print("选择封面...")
    cover_selectors = [
        '//*[@id="app"]/div/div[2]/div[2]/div[2]/div[1]/div/button',
        '//button[contains(text(), "封面")]',
        '//span[contains(text(), "封面")]',
    ]

    for selector in cover_selectors:
        if safe_click(page.locator(f'xpath={selector}'), "选择封面"):
            time.sleep(1)  # 等待封面选择界面加载
            break
    else:
        print("⚠ 无法找到封面选择按钮")
        return False

    # 等待上传区域出现
    print("等待上传区域出现...")
    try:
        # 等待上传区域出现（包含"点击或拖拽文件到此处上传"文本）
        page.wait_for_selector(f'text=点击或拖拽文件到此处上传', timeout=10000)
        print("✓ 上传区域已出现")

        # 修复：改进封面文件查找逻辑，处理中文字符问题
        novel_project_dir = os.path.abspath(CONFIG["novel_path"])
        print(f"搜索目录: {novel_project_dir}")

        # 检查目录是否存在
        if not os.path.exists(novel_project_dir):
            print(f"✗ 目录不存在: {novel_project_dir}")
            return False

        # 方法1：尝试直接使用您提供的路径
        expected_path = os.path.join(novel_project_dir, f"{novel_title}_封面.jpg")
        print(f"尝试路径1: {expected_path}")
        cover_found = False
        cover_path = None
        
        if os.path.exists(expected_path):
            cover_path = expected_path
            cover_found = True
            print(f"✓ 找到封面文件 (路径1): {cover_path}")
        else:
            # 尝试其他可能的封面文件名
            alternative_names = [
                f"{novel_title}_封面.png",
                f"{novel_title}_cover.jpg",
                f"{novel_title}_cover.png",
                "cover.jpg",
                "cover.png"
            ]
            
            for alt_name in alternative_names:
                alt_path = os.path.join(novel_project_dir, alt_name)
                if os.path.exists(alt_path):
                    cover_path = alt_path
                    cover_found = True
                    print(f"✓ 找到封面文件 (备用路径): {alt_path}")
                    break
        
        if cover_found and cover_path:
            # 使用Playwright的文件上传功能
            file_input_selectors = [
                'input[type="file"]',
                '//input[@type="file"]',
            ]

            file_uploaded = False
            for selector in file_input_selectors:
                file_inputs = page.locator(selector)
                if file_inputs.count() > 0:
                    try:
                        # 直接设置文件路径，不通过系统对话框
                        file_inputs.first.set_input_files(cover_path)
                        print(f"✓ 已直接上传封面图片: {os.path.basename(cover_path)}")
                        file_uploaded = True
                        break
                    except Exception as e:
                        print(f"直接文件上传失败: {e}")

            if not file_uploaded:
                print("⚠ 封面上传失败")
        else:
            print(f"⚠ 未找到封面文件，将使用默认封面")

        # 等待封面上传和处理完成
        time.sleep(3)

        # 点击确认按钮以完成封面选择
        print("点击封面确认按钮...")
        cover_confirm_selectors = [
            '/html/body/div[2]/div[2]/div/div[2]/div/div/button[2]/span',  # 您提供的XPath
            '//button[text()="确定"]',
            '//button[text()="确认"]',
            '//span[text()="确定"]',
            '//span[text()="确认"]',
            '//*[contains(@class, "arco-btn") and text()="确定"]',
            '//*[contains(@class, "arco-btn") and text()="确认"]',
        ]

        confirm_clicked = False
        for selector in cover_confirm_selectors:
            if safe_click(page.locator(f'xpath={selector}'), "封面确认按钮"):
                print("✓ 已确认封面选择")
                confirm_clicked = True
                break

        if not confirm_clicked:
            print("⚠ 未找到封面确认按钮")

    except Exception as e:
        print(f"⚠ 封面上传过程中出错: {e}")

    # 等待封面选择完成
    time.sleep(2)
    return True


def find_existing_book_in_list(page, expected_book_title, max_pages=10):
    """
    在小说列表中寻找已存在的小说（仅检测，不执行操作）
    """
    try:
        print(f"检测书籍《{expected_book_title}》是否存在...")

        # 确保在小说管理页面
        if not ensure_novel_management_page(page):
            return False

        # 尝试多页查找
        for page_num in range(1, max_pages + 1):
            print(f"搜索第 {page_num} 页...")

            # 使用精细滚动加载书籍
            if not scroll_to_load_books(page):
                continue

            # 在滚动过程中实时检查
            book_found, novel_id = check_for_book_existence_during_scroll(page, expected_book_title)
            if book_found:
                print(f"[OK] 找到书籍《{expected_book_title}》")
                return True

            # 如果当前页没找到，尝试翻到下一页
            if page_num < max_pages:
                next_result = navigate_to_next_page(page)
                if next_result == 'no_more_pages':
                    break
                elif not next_result:
                    continue
                time.sleep(2)

        print(f"[INFO] 在 {max_pages} 页内未找到书籍《{expected_book_title}》")
        return False

    except Exception as e:
        print(f"[ERROR] 检测书籍时出错: {e}")
        return False


def ensure_novel_management_page(page):
    """确保在小说管理页面"""
    try:
        # 检查是否已经在小说管理页面
        novel_tab_indicators = [
            '//span[text()="小说"]',
            'text=小说',
            '[class*="novel"]',
        ]

        for indicator in novel_tab_indicators:
            if page.locator(indicator).count() > 0:
                return True

        # 如果不在，点击小说标签
        novel_selectors = [
            'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
            'text=小说',
            'span:has-text("小说")'
        ]

        for selector in novel_selectors:
            if safe_click(page.locator(selector).first, "小说标签"):
                time.sleep(3)
                return True

        return False
    except Exception as e:
        print(f"确保小说管理页面时出错: {e}")
        return False


def scroll_to_load_books(page):
    """滚动加载书籍"""
    try:
        scroll_element = page.locator('xpath=//*[@id="app"]/div')
        if scroll_element.count() > 0:
            viewport_height = page.evaluate('() => window.innerHeight')

            # 分次小幅滚动
            for i in range(1, 9):
                scroll_position = (viewport_height * i) // 8
                scroll_element.evaluate(f'(element) => {{ element.scrollTop = {scroll_position}; }}')
                time.sleep(0.3)

            # 回到顶部附近
            scroll_element.evaluate('(element) => { element.scrollTop = 100; }')
            time.sleep(0.3)
            return True
        return False
    except Exception as e:
        print(f"滚动加载书籍时出错: {e}")
        return False


def check_for_book_existence_during_scroll(page, expected_book_title):
    """
    在滚动过程中实时检查是否找到目标书籍（仅检测存在性）
    """
    try:
        book_title_selectors = [
            f'//div[contains(@id, "long-article-table-item")]/div/div[1]/div[2]/div[1]/div[contains(text(), "{expected_book_title}")]',
            f'//div[contains(@id, "long-article-table-item")]//div[contains(text(), "{expected_book_title}")]',
        ]

        for selector in book_title_selectors:
            elements = page.locator(f'xpath={selector}')
            if elements.count() > 0:
                for i in range(elements.count()):
                    element = elements.nth(i)
                    actual_title = element.text_content().strip()
                    if expected_book_title == actual_title:  # 严格匹配，而不是包含匹配
                        print(f"[OK] 精确匹配到书籍: {actual_title}")
                        return True, None
        return False, None
    except Exception as e:
        print(f"[ERROR] 检查书籍存在性时出错: {e}")
        return False, None


def find_and_click_create_chapter_button(page, expected_book_title, max_pages=10):
    """
    在小说列表中寻找已存在的小说并点击创建章节按钮
    """
    try:
        print(f"寻找书籍《{expected_book_title}》并点击创建章节按钮...")

        # 确保在小说管理页面
        if not ensure_novel_management_page(page):
            return False

        # 尝试多页查找
        for page_num in range(1, max_pages + 1):
            print(f"搜索第 {page_num} 页...")

            # 使用精细滚动加载书籍
            if not scroll_to_load_books(page):
                continue

            # 在滚动过程中实时检查
            book_found, novel_id = check_for_book_and_status_during_scroll(page, expected_book_title)
            if book_found:
                print(f"✓ 找到书籍《{expected_book_title}》，状态为连载中")

                # 直接点击创建章节按钮
                if click_create_chapter_button_directly(page, expected_book_title, novel_id or ""):
                    return True
                else:
                    print("✗ 无法点击创建章节按钮，继续查找")

            # 如果当前页没找到，尝试翻到下一页
            if page_num < max_pages:
                next_result = navigate_to_next_page(page)
                if next_result == 'no_more_pages':
                    break
                elif not next_result:
                    continue
                time.sleep(2)

        print(f"✗ 在 {max_pages} 页内未找到可用的书籍《{expected_book_title}》")
        return False

    except Exception as e:
        print(f"寻找书籍时出错: {e}")
        return False


def check_for_book_and_status_during_scroll(page, expected_book_title):
    """
    在滚动过程中实时检查是否找到目标书籍和状态
    """
    try:
        book_title_selectors = [
            f'//div[contains(@id, "long-article-table-item")]/div/div[1]/div[2]/div[1]/div[contains(text(), "{expected_book_title}")]',
            f'//div[contains(@id, "long-article-table-item")]//div[contains(text(), "{expected_book_title}")]',
        ]

        for selector in book_title_selectors:
            elements = page.locator(f'xpath={selector}')
            if elements.count() > 0:
                for i in range(elements.count()):
                    element = elements.nth(i)
                    actual_title = element.text_content().strip()
                    if expected_book_title in actual_title:
                        # 获取小说项的ID
                        book_item = element.locator('xpath=./ancestor::div[contains(@id, "long-article-table-item")]')
                        if book_item.count() > 0:
                            # 提取小说ID
                            novel_id = extract_novel_id_from_element(book_item.first)

                            if novel_id:
                                # 检查状态是否为"连载中"
                                if check_novel_status(page, novel_id, "连载中"):
                                    return True, novel_id
        return False, None
    except:
        return False, None


def extract_novel_id_from_element(element):
    """
    从小说元素中提取ID
    """
    try:
        # 获取元素的ID属性
        element_id = element.get_attribute('id')
        if element_id and 'long-article-table-item-' in element_id:
            # 提取ID的数字部分
            novel_id = element_id.replace('long-article-table-item-', '')
            print(f"提取到小说ID: {novel_id}")
            return novel_id
        return None
    except Exception as e:
        print(f"提取小说ID时出错: {e}")
        return None


def check_novel_status(page, novel_id, expected_status="连载中"):
    """
    检查小说的状态
    """
    try:
        # 构建状态元素的XPath
        status_xpath = f'//*[@id="long-article-table-item-{novel_id}"]/div/div[1]/div[2]/div[2]/div[2]/div[3]'
        status_elements = page.locator(f'xpath={status_xpath}')

        if status_elements.count() > 0:
            status_text = status_elements.first.text_content().strip()
            print(f"小说状态: {status_text}")

            # 检查是否包含预期的状态
            if expected_status in status_text:
                return True
            else:
                print(f"小说状态不是'{expected_status}'，而是'{status_text}'")
                return False
        else:
            print("未找到状态元素")
            return False
    except Exception as e:
        print(f"检查小说状态时出错: {e}")
        return False


def click_create_chapter_button_directly(page, novel_title: str, novel_id: str = None) -> bool:
    """
    直接在书籍列表中找到并点击与指定小说标题相关联的"创建章节"按钮。
    修正了查找逻辑，确保只点击目标小说的按钮，如果未找到则忽略。
    """
    print(f"尝试精确定位《{novel_title}》的'创建章节'按钮...")

    try:
        # 找到页面上所有的书籍条目容器
        book_items = page.locator('//div[contains(@id, "long-article-table-item")]')
        if book_items.count() == 0:
            print("✗ 页面上未找到任何书籍条目。")
            return False

        print(f"在页面上找到 {book_items.count()} 个书籍条目，开始匹配标题...")

        # 遍历所有书籍条目，查找标题匹配的那一个
        for i in range(book_items.count()):
            item = book_items.nth(i)

            # 在当前条目内查找小说标题元素。根据HTML结构，标题在 .info-content-title > .hoverup
            title_element = item.locator('.info-content-title .hoverup')

            if title_element.count() > 0:
                item_title = title_element.first.text_content().strip()

                # 严格匹配小说标题，确保找到正确的书
                if novel_title == item_title:
                    print(f"✓ 已找到小说《{item_title}》的条目。")

                    # 在这个正确的书籍条目内查找"创建章节"按钮
                    # 使用 :has-text() 伪类可以精准匹配包含特定文本的按钮
                    create_button = item.locator('button:has-text("创建章节")').first

                    if create_button and create_button.is_visible():
                        print("✓ 在条目内找到'创建章节'按钮。")

                        # 高亮显示找到的按钮，便于调试
                        create_button.evaluate('''(element) => {
                            element.style.border = '3px solid #00ff00';
                            element.style.backgroundColor = '#00ff0020';
                            element.scrollIntoView({ block: 'center', inline: 'center' });
                        }''')
                        time.sleep(1)

                        # 使用safe_click函数进行点击
                        if safe_click(create_button, f"《{novel_title}》的创建章节按钮"):
                            print("✓ 成功点击创建章节按钮。")
                            time.sleep(2)  # 等待页面跳转或响应
                            return True
                        else:
                            print(f"✗ 点击《{novel_title}》的创建章节按钮失败。")
                            # 找到了但点击失败，这是一个明确的失败，应停止
                            return False
                    else:
                        # 找到了书，但没有创建章节的按钮，可能是因为状态不对
                        print(f"✓ 找到小说《{novel_title}》，但该小说没有可点击的'创建章节'按钮，已忽略。")
                        return False

        # 如果遍历完所有条目都没有找到匹配的小说
        print(f"✗ 在当前页面所有书籍中未找到小说《{novel_title}》。")
        return False

    except Exception as e:
        print(f"定位'创建章节'按钮时发生严重错误: {e}")
        return False


def navigate_to_next_page(page, direction="next"):
    """
    导航到下一页或上一页 - 增强版本，支持双向翻页
    参数:
        direction: "next" - 下一页, "prev" - 上一页
    返回:
        True - 成功翻页
        False - 翻页失败
        'no_more_pages' - 没有更多页面
    """
    try:
        if direction == "next":
            # 下一页选择器
            selectors = [
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
            selectors = [
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

        for selector in selectors:
            try:
                # 如果是XPath选择器
                if selector.startswith('//'):
                    button = page.locator(f'xpath={selector}')
                else:
                    button = page.locator(selector).first

                if button.count() > 0:
                    # 检查按钮是否被禁用
                    is_disabled = button.get_attribute('disabled') is not None or \
                                  'disabled' in button.get_attribute('class') or \
                                  not button.is_enabled()

                    if is_disabled:
                        print(disabled_desc)
                        return 'no_more_pages'

                    # 检查按钮是否可见
                    if button.is_visible():
                        safe_click(button, button_desc)
                        time.sleep(1)
                        return True
                    else:
                        # 如果按钮不可见，先滑动页面到底部
                        print(f"{button_desc}不可见，滑动页面...")
                        page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                        time.sleep(0.5)

                        # 再次尝试点击
                        if button.is_visible() and button.is_enabled():
                            safe_click(button, f"{button_desc}(滑动后)")
                            time.sleep(1)
                            return True
                        else:
                            # 如果滑动后仍然不可见或不可用，尝试使用JavaScript点击
                            print(f"尝试通过JavaScript点击{button_desc}...")
                            button.evaluate('(element) => element.click()')
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


def click_create_chapter_button_by_novel_title(page, novel_title: str, novel_id: str = None):
    """
    在书籍列表中找到并点击与指定小说标题相关联的"创建章节"按钮，支持自动翻页。
    如果成功，此函数会返回新打开页面的 Page 对象。
    如果失败（未找到书籍、未找到按钮、点击失败等），则返回 None。

    参数:
    - page: 当前的浏览器页面对象 (书籍列表页)。
    - novel_title (str): 要查找的小说标题。
    - novel_id (str, optional): 小说的ID，用于更精确的定位。

    返回:
    - 新打开的章节编辑页面的 Page 对象，如果失败则为 None。
    """
    print(f"开始查找小说《{novel_title}》，支持自动翻页...")
    page_number = 1

    # 核心修改点: 引入 while True 循环来处理翻页
    while True:
        print(f"\n--- 正在搜索第 {page_number} 页 ---")
        page.wait_for_load_state("networkidle")  # 等待当前页数据加载完毕

        # 找到页面上所有的书籍条目容器
        book_items = page.locator('//div[contains(@id, "long-article-table-item")]')
        if book_items.count() == 0:
            print(f"✗ 第 {page_number} 页上未找到任何书籍条目。")
        else:
            print(f"在第 {page_number} 页上找到 {book_items.count()} 个书籍条目，开始匹配标题...")

            # 遍历当前页面的所有书籍条目
            for i in range(book_items.count()):
                item = book_items.nth(i)
                title_element = item.locator('.info-content-title .hoverup')

                if title_element.count() > 0:
                    item_title = title_element.first.text_content().strip()

                    if novel_title == item_title:
                        print(f"✓ 已在第 {page_number} 页找到小说《{item_title}》！")
                        create_button = item.locator('button:has-text("创建章节")').first

                        if create_button and create_button.is_visible():
                            print("✓ 在条目内找到'创建章节'按钮。准备点击并捕获新页面...")
                            try:
                                with page.context.expect_page() as new_page_info:
                                    # 使用 force=True 强制点击，以绕过元素遮挡问题
                                    create_button.click(timeout=5000, force=True)
                                new_page = new_page_info.value
                                print(f"✓ 成功点击并捕获到新页面: {new_page.url}")
                                new_page.wait_for_load_state("domcontentloaded")
                                return new_page  # 成功找到并点击，返回新页面
                            except Exception as e:
                                print(f"✗ 点击或捕获新页面时出错: {e}")
                                return None  # 明确的失败，终止整个过程
                        else:
                            print(f"✓ 找到小说《{novel_title}》，但该小说没有'创建章节'按钮，操作终止。")
                            return None  # 找到了书但没有按钮，是明确结果，终止

        # --- 如果在当前页没找到，则处理翻页 ---
        next_button = page.locator('.arco-pagination-item-next')

        # 检查"下一页"按钮是否存在且可点击
        if not next_button.count() or 'arco-pagination-item-disabled' in (next_button.get_attribute('class') or ''):
            print(f"\n✗ 已搜索完所有页面，未找到小说《{novel_title}》。")
            return None  # 到达最后一页或没有翻页按钮，结束查找

        # 如果可以翻页，则点击进入下一页
        print(f"在第 {page_number} 页未找到，准备翻页...")
        try:
            next_button.click()
            page_number += 1
            # 循环将继续，并在顶部等待新页面加载
        except Exception as e:
            print(f"✗ 点击'下一页'按钮时出错: {e}")
            return None