import os
import re
import time
import json
import shutil  # 新增导入
import threading
from pathlib import Path
from datetime import datetime, timedelta
from playwright.sync_api import sync_playwright
from playwright.sync_api import Locator, Page, expect
from typing import Optional

from typing import List, Dict, Any
# ContractManager 导入已禁用 - 签约管理功能暂时不需要
# try:
#     # 优先尝试相对导入
#     from .contract_manager_legacy import ContractManager
# except ImportError:
#     try:
#         # 如果相对导入失败，尝试绝对导入
#         import sys
#         import os
#         # 添加项目根目录到路径
#         current_dir = os.path.dirname(os.path.abspath(__file__))
#         project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
#         if project_root not in sys.path:
#             sys.path.insert(0, project_root)
#
#         from Chrome.automation.legacy.contract_manager_legacy import ContractManager
#     except ImportError:
#         # 如果还是失败，尝试直接导入
#         import importlib.util
#         import os
#
#         contract_manager_path = os.path.join(os.path.dirname(__file__), 'contract_manager_legacy.py')
#         spec = importlib.util.spec_from_file_location("contract_manager_legacy", contract_manager_path)
#         contract_manager_module = importlib.util.module_from_spec(spec)
#         spec.loader.exec_module(contract_manager_module)
#         ContractManager = contract_manager_module.ContractManager

# 配置参数
CONFIG = {
    "debug_port": 9988,
    "novel_path": "小说项目",  # 这是默认路径，如果不存在会创建
    "published_path": "已经发布",  # 新增：已发布小说目录
    "required_json_suffix": "项目信息.json",
    "timeouts": {
        "click": 15000,
        "fill": 12000,
        "wait_element": 5000
    },
    "auto_continue_delay": 10,
    "max_retries": 3,
    "min_words_for_scheduled_publish": 60000,
    "progress_file": "发布进度.json",
    "progress2_file": "发布进度细节.json",
    "date_format": "%Y-%m-%d",
    "time_format": "%H:%M",
    "scan_interval": 1800  # 每小时扫描一次（秒）
}

# ========== 可配置参数 ==========
# 累计字数阈值，达到此值后才开始设置定时发布
WORD_COUNT_THRESHOLD = 20000

# 发布时间点列表，可修改此列表来调整发布时间
novel_publish_times = ["05:25", "11:25", "17:25", "23:25"]  # 可修改此列表

# 每个时间点最多发布的章节数
CHAPTERS_PER_TIME_SLOT = 2  # 可修改此值

# 发布时间缓冲，单位为分钟，当前为 35 分钟
PUBLISH_BUFFER_MINUTES = 35


# ========== 可配置参数 ==========

def move_completed_novel_to_published(novel_title, json_file_path):
    """
    将已完成发布的小说移动到已发布目录 (已修复，可动态移动所有相关文件)
    """
    try:
        # 确保已发布目录存在
        published_dir = ensure_directory_exists(CONFIG["published_path"])

        # 创建目标子目录（使用小说标题和时间戳）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        target_subdir = os.path.join(published_dir, f"{novel_title}_{timestamp}")
        ensure_directory_exists(target_subdir)

        # --- 主要修改部分：从硬编码列表改为动态查找 ---
        moved_items = []
        source_dir = CONFIG["novel_path"]
        
        print(f"正在从 '{source_dir}' 目录查找所有与《{novel_title}》相关的文件和目录...")

        # 遍历源目录中的所有条目
        for item_name in os.listdir(source_dir):
            # 检查条目是否以小说标题和下划线开头
            if item_name.startswith(f"{novel_title}_"):
                source_path = os.path.join(source_dir, item_name)
                target_path = os.path.join(target_subdir, item_name)
                
                try:
                    # 移动文件或目录
                    shutil.move(source_path, target_path)
                    moved_items.append(item_name)
                except Exception as e:
                    print(f"✗ 移动 '{item_name}' 失败: {e}")
        # --- 修改结束 ---

        # 从发布进度中移除该小说的记录
        progress_file = CONFIG["progress_file"]
        if os.path.exists(progress_file):
            try:
                with open(progress_file, 'r', encoding='utf-8') as f:
                    all_progress = json.load(f)

                if novel_title in all_progress:
                    del all_progress[novel_title]

                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(all_progress, f, ensure_ascii=False, indent=2)

                moved_items.append("发布进度记录")
            except Exception as e:
                print(f"清理发布进度记录时出错: {e}")
        
        if not moved_items:
             print(f"⚠ 未找到任何与《{novel_title}》相关的文件进行移动。请检查文件命名是否正确。")
             # 即使没移动文件，也可能需要清理进度，所以不直接返回False
        
        print(f"✓ 小说《{novel_title}》发布完成，已移动到: {target_subdir}")
        print(f"  移动的项目: {', '.join(moved_items)}")

        return True

    except Exception as e:
        print(f"✗ 移动已发布小说时出错: {e}")
        return False

    except Exception as e:
        print(f"✗ 移动已发布小说时出错: {e}")
        return False


def check_if_novel_completed(json_file_path, published_chapters_count):
    """
    检查小说是否已完成所有章节的发布
    """
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否有进度信息
        if "progress" in data:
            progress = data["progress"]
            total_chapters = progress.get("total_chapters", 0)

            if total_chapters > 0 and published_chapters_count >= total_chapters:
                return True

        return False

    except Exception as e:
        print(f"检查小说完成状态时出错: {e}")
        return False


def ensure_directory_exists(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        print(f"创建目录: {directory}")
        os.makedirs(directory)
    return directory


def format_synopsis_for_fanqie(text, novel_data=None, max_length=500):
    """针对番茄小说优化简介排版 - 按指定格式：标签+核心卖点+原简介"""
    if not text or len(text.strip()) == 0:
        return ""

    # 清理文本，去除多余空格和换行
    text = re.sub(r'\s+', ' ', text.strip())

    # 如果有完整的novel_data，尝试提取标签和核心卖点
    if novel_data and isinstance(novel_data, dict):
        # 尝试从不同位置提取标签
        tag_line = ""

        # 方法1: 从简介开头提取标签
        tag_match = re.search(r'^(\[[^\]]+\])', text)
        if tag_match:
            tag_line = tag_match.group(1)
            # 移除标签从原文本中
            text = text.replace(tag_line, "").strip()

        # 方法2: 如果没有找到标签，尝试从creative_seed或core_settings中提取
        if not tag_line:
            if "creative_seed" in novel_data:
                creative_seed = novel_data["creative_seed"]
                # 尝试从创意种子中提取标签
                tag_match = re.search(r'(\[[^\]]+\])', creative_seed)
                if tag_match:
                    tag_line = tag_match.group(1)

            # 方法3: 如果还是没有，使用默认标签
            if not tag_line:
                tag_line = "[系统+爽文]"

        # 对原简介部分进行换行处理
        original_synopsis = text

        # 按句子分割原简介（中文句号、问号、感叹号）
        sentences = re.split(r'([。！？])', original_synopsis)

        # 重新组合句子，保留标点
        processed_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                if sentence.strip():
                    processed_sentences.append(sentence.strip())

        # 如果分割失败，使用简单分割
        if not processed_sentences:
            processed_sentences = [s.strip() for s in original_synopsis.split('。') if s.strip()]
            processed_sentences = [s + '。' for s in processed_sentences]

        # 构建新格式的简介 - 修复：标签行后面只跟一个空行，然后直接接内容
        formatted_lines = [tag_line, ""]  # 标签行 + 空行

        # 添加处理后的原简介（每句换行）
        formatted_lines.extend(processed_sentences)

        formatted_text = '\n'.join(formatted_lines)
    else:
        # 对于没有完整novel_data的情况，使用原有的处理逻辑
        if len(text) <= 100:
            return text

        # 按句子分割（中文句号、问号、感叹号）
        sentences = re.split(r'([。！？])', text)

        # 重新组合句子，保留标点
        processed_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            if i + 1 < len(sentences):
                sentence = sentences[i] + sentences[i + 1]
                if sentence.strip():
                    processed_sentences.append(sentence.strip())

        # 如果分割失败，使用简单分割
        if not processed_sentences:
            processed_sentences = [s.strip() for s in text.split('。') if s.strip()]
            processed_sentences = [s + '。' for s in processed_sentences]

        # 每句都换行
        formatted_text = '\n'.join(processed_sentences)

    # 确保不超过最大长度
    if len(formatted_text) > max_length:
        formatted_text = formatted_text[:max_length - 3] + '...'

    return formatted_text


def wait_for_enter(prompt="按回车键继续...", timeout=None):
    """等待用户按回车继续，超时后自动继续"""
    if timeout is None:
        timeout = CONFIG["auto_continue_delay"]

    print(f"\n>>> {prompt} ({timeout}秒后自动继续)")

    # 创建事件标志来跟踪是否收到输入
    input_received = threading.Event()

    def wait_for_input():
        input()
        input_received.set()

    # 在后台线程中等待输入
    input_thread = threading.Thread(target=wait_for_input)
    input_thread.daemon = True
    input_thread.start()

    # 等待超时或输入
    input_received.wait(timeout=timeout)

    if input_received.is_set():
        print(">>> 用户按回车，继续执行...")
    else:
        print(f">>> 等待超时，自动继续执行...")


def safe_click(element, desc="元素", timeout=None, retries=3):
    """安全的点击操作，带有重试和遮挡处理"""
    timeout = timeout or CONFIG["timeouts"]["click"]

    for attempt in range(retries):
        try:
            # 滚动元素到视图中
            element.scroll_into_view_if_needed(timeout=5000)

            # 等待元素可交互
            element.wait_for(state="visible", timeout=5000)

            # 尝试点击，如果被遮挡则强制点击
            try:
                element.click(timeout=timeout)
                print(f"✓ 成功点击: {desc}")
                time.sleep(0.3)
                return True
            except Exception as e:
                if "intercepts pointer events" in str(e) and attempt < retries - 1:
                    print(f"第{attempt + 1}次点击被遮挡，尝试强制点击...")
                    # 强制点击，忽略遮挡
                    element.click(force=True, timeout=timeout)
                    print(f"✓ 强制点击成功: {desc}")
                    time.sleep(0.3)
                    return True
                else:
                    raise e

        except Exception as e:
            print(f"✗ 点击失败 {desc} (尝试 {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                # 等待一段时间后重试
                wait_time = 2 * (attempt + 1)
                print(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                return False
    return False


def safe_fill(element, text, desc="元素", timeout=None):
    """安全的填充文本操作"""
    timeout = timeout or CONFIG["timeouts"]["fill"]
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


def count_content_chars(text: str) -> int:
    """统计字符串中字母、数字和汉字的总数量"""
    pattern = r'[a-zA-Z0-9\u4e00-\u9fa5]'
    content_chars = re.findall(pattern, text)
    return len(content_chars)


def normalize_all_line_breaks(text):
    """处理各种换行符组合"""
    text = re.sub(r'\r\n|\r', '\n', text)
    text = re.sub(r'\n[ \t]*\n', '\n\n', text)
    return re.sub(r'\n{3,}', '\n\n', text)


def list_json_files(directory):
    """列出指定目录下的项目信息JSON文件"""
    try:
        # 确保目录存在
        directory = ensure_directory_exists(directory)

        matched_files = []
        for filename in os.listdir(directory):
            if filename.endswith(CONFIG["required_json_suffix"]):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    matched_files.append(filepath)
        return matched_files
    except FileNotFoundError:
        print(f"错误：目录 '{directory}' 不存在，已自动创建")
        return []
    except Exception as e:
        print(f"列出JSON文件时出错: {e}")
        return []


def sort_files_by_chapter(file_paths):
    """按章节号对文件路径进行排序"""

    def extract_chapter_number(filepath):
        match = re.search(r"_第(\d+)章_", os.path.basename(filepath))
        return int(match.group(1)) if match else 0

    return sorted(file_paths, key=extract_chapter_number)


def load_publish_progress(novel_title):
    """加载发布进度"""
    progress_file = CONFIG["progress_file"]
    if not os.path.exists(progress_file):
        return {
            "published_chapters": [],
            "total_content_len": 0,
            "base_chapter_num": 0,  # 新增：基准章节号
            "book_created": False  # 新增：书籍是否已创建
        }

    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            all_progress = json.load(f)
            progress = all_progress.get(novel_title, {
                "published_chapters": [],
                "total_content_len": 0,
                "base_chapter_num": 0,
                "book_created": False
            })
            # 确保有必要的字段
            if "base_chapter_num" not in progress:
                progress["base_chapter_num"] = 0
            if "book_created" not in progress:
                progress["book_created"] = False
            return progress
    except:
        return {
            "published_chapters": [],
            "total_content_len": 0,
            "base_chapter_num": 0,
            "book_created": False
        }


def save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num, book_created):
    """保存发布进度"""
    progress_file = CONFIG["progress_file"]

    # 确保目录存在
    ensure_directory_exists(os.path.dirname(progress_file) if os.path.dirname(progress_file) else ".")

    # 加载现有进度
    all_progress = {}
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                all_progress = json.load(f)
        except:
            all_progress = {}

    # 更新当前小说的进度
    all_progress[novel_title] = {
        "published_chapters": published_chapters,
        "total_content_len": total_content_len,
        "base_chapter_num": base_chapter_num,  # 保存基准章节号
        "book_created": book_created,  # 保存书籍创建状态
        "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 保存进度
    with open(progress_file, 'w', encoding='utf-8') as f:
        json.dump(all_progress, f, ensure_ascii=False, indent=2)


def is_chapter_published(progress, chapter_file):
    """检查章节是否已发布"""
    return os.path.basename(chapter_file) in progress["published_chapters"]


def mark_chapter_published(progress, chapter_file, word_count, current_chapter_num):
    """标记章节为已发布，并检查是否需要设置基准章节号"""
    chapter_name = os.path.basename(chapter_file)
    if chapter_name not in progress["published_chapters"]:
        progress["published_chapters"].append(chapter_name)
    progress["total_content_len"] += word_count

    # 如果达到定时发布字数且基准章节号还未设置，设置当前章节为基准章节号
    if (progress["total_content_len"] > CONFIG["min_words_for_scheduled_publish"] and
            progress["base_chapter_num"] == 0):
        progress["base_chapter_num"] = current_chapter_num
        print(f"✓ 设置基准章节号为第 {current_chapter_num} 章 (达到定时发布字数)")

    return progress


def refresh_book_list(page):
    """刷新书籍列表"""
    print("刷新书籍列表...")
    try:
        # 点击小说标签页
        novel_selectors = [
            'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
            'text=小说',
            'span:has-text("小说")'
        ]

        for selector in novel_selectors:
            if safe_click(page.locator(selector).first, "小说标签"):
                break

        # 等待页面刷新
        time.sleep(3)
        return True
    except Exception as e:
        print(f"刷新书籍列表失败: {e}")
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
            if verify_current_book_by_header(page, expected_book_title) or verify_current_book(page,
                                                                                               expected_book_title):
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


def find_existing_book_in_list(page, expected_book_title, max_pages=10):
    """
    在小说列表中寻找已存在的小说并直接点击创建章节按钮
    """
    try:
        print(f"寻找书籍《{expected_book_title}》并直接点击创建章节按钮...")

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
                if click_create_chapter_button_directly(page, expected_book_title, novel_id):
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


def click_create_chapter_by_id(page, novel_id):
    """
    使用小说ID精准定位并点击创建章节按钮
    """
    try:
        # 构建创建章节按钮的XPath
        create_chapter_xpath = f'//*[@id="long-article-table-item-{novel_id}"]/div/div[1]/div[2]/div[3]/div/a[2]/button/span'
        create_chapter_buttons = page.locator(f'xpath={create_chapter_xpath}')

        if create_chapter_buttons.count() > 0:
            button_text = create_chapter_buttons.first.text_content().strip()
            print(f"找到创建章节按钮: {button_text}")

            if safe_click(create_chapter_buttons.first, "创建章节按钮(精准定位)"):
                print("✓ 成功点击创建章节按钮")
                time.sleep(2)  # 等待页面跳转
                return True
            else:
                print("✗ 点击创建章节按钮失败")
                return False
        else:
            print("未找到创建章节按钮")

            # 尝试其他可能的选择器
            alternative_selectors = [
                f'//*[@id="long-article-table-item-{novel_id}"]//button[contains(text(), "创建章节")]',
                f'//*[@id="long-article-table-item-{novel_id}"]//span[contains(text(), "创建章节")]',
                f'//*[@id="long-article-table-item-{novel_id}"]//a[contains(text(), "创建章节")]'
            ]

            for selector in alternative_selectors:
                elements = page.locator(f'xpath={selector}')
                if elements.count() > 0:
                    button_text = elements.first.text_content().strip()
                    print(f"找到创建章节按钮(备选): {button_text}")

                    if safe_click(elements.first, "创建章节按钮(备选)"):
                        print("✓ 成功点击创建章节按钮(备选)")
                        time.sleep(2)
                        return True

            return False
    except Exception as e:
        print(f"点击创建章节按钮时出错: {e}")
        return False

def click_create_chapter_button_directly(page: Page, novel_title: str, novel_id: str = None) -> bool:
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

                        # 使用假定的safe_click函数进行点击
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


def click_create_chapter_by_index(page, item_index):
    """
    直接通过小说项的索引定位并点击创建章节按钮
    item_index: 小说项在列表中的位置（从1开始）
    """
    try:
        print(f"尝试通过索引定位第 {item_index} 个小说项的创建章节按钮...")

        # 构建小说项的选择器
        novel_item_selectors = [
            f'(//div[contains(@id, "long-article-table-item")])[{item_index}]',
            f'//div[contains(@id, "long-article-table-item")][{item_index}]',
        ]

        for item_selector in novel_item_selectors:
            try:
                novel_item = page.locator(f'xpath={item_selector}')
                if novel_item.count() > 0:
                    print(f"✓ 找到第 {item_index} 个小说项")

                    # 高亮显示找到的小说项
                    page.evaluate('''(element) => {
                        element.style.border = '3px solid #ff00ff';
                        element.style.backgroundColor = '#ff00ff20';
                        element.style.boxShadow = '0 0 15px #ff00ff';
                    }''', novel_item.first)

                    time.sleep(1)

                    # 在小说项内部查找创建章节按钮
                    button_selectors = [
                        './/button[contains(text(), "创建章节")]',
                        './/a[contains(text(), "创建章节")]',
                        './/span[contains(text(), "创建章节")]',
                        './/*[contains(text(), "创建章节")]',
                        './/button[contains(., "创建章节")]',
                        './/a[contains(., "创建章节")]',
                        './/span[contains(., "创建章节")]',
                    ]

                    for btn_selector in button_selectors:
                        try:
                            buttons = novel_item.locator(f'xpath={btn_selector}')
                            if buttons.count() > 0:
                                for i in range(buttons.count()):
                                    button = buttons.nth(i)
                                    if button.is_visible():
                                        button_text = button.text_content().strip()
                                        print(f"✓ 在小说项内找到按钮: {button_text}")

                                        # 高亮显示按钮
                                        page.evaluate('''(element) => {
                                            element.style.border = '3px solid #00ff00';
                                            element.style.backgroundColor = '#00ff0040';
                                        }''', button)

                                        time.sleep(1)

                                        if safe_click(button, f"创建章节按钮(索引{item_index})"):
                                            print("✓ 成功点击创建章节按钮")
                                            time.sleep(2)
                                            return True
                        except Exception as e:
                            continue

                    # 如果上面没找到，查找小说项内的所有按钮
                    print("搜索小说项内的所有按钮...")
                    all_buttons = novel_item.locator('button, a')
                    if all_buttons.count() > 0:
                        print(f"小说项内找到 {all_buttons.count()} 个按钮/链接")

                        for i in range(all_buttons.count()):
                            button = all_buttons.nth(i)
                            if button.is_visible():
                                try:
                                    button_text = button.text_content().strip()
                                    print(f"  按钮 {i + 1}: '{button_text}'")

                                    if "创建章节" in button_text:
                                        print(f"✓ 通过文本筛选找到创建章节按钮")

                                        if safe_click(button, f"创建章节按钮(文本筛选)"):
                                            print("✓ 成功点击创建章节按钮")
                                            time.sleep(2)
                                            return True
                                except Exception as e:
                                    print(f"  按钮 {i + 1}: [无法获取文本]")
                                    continue

                    break  # 如果找到了小说项但没找到按钮，跳出选择器循环

            except Exception as e:
                print(f"尝试选择器 {item_selector} 失败: {e}")
                continue

        print(f"✗ 无法在第 {item_index} 个小说项中找到创建章节按钮")
        return False

    except Exception as e:
        print(f"通过索引定位时出错: {e}")
        return False


def process_specific_novel_item(page, item_index, novel_title):
    """
    处理特定索引的小说项
    """
    print(f"处理第 {item_index} 个小说项: 《{novel_title}》")

    # 首先确保在小说管理页面
    if not ensure_novel_management_page(page):
        print("不在小说管理页面，无法处理")
        return False

    # 直接通过索引定位并点击创建章节按钮
    if click_create_chapter_by_index(page, item_index):
        print(f"✓ 成功进入《{novel_title}》的创建章节流程")
        return True
    else:
        print(f"✗ 无法通过索引定位《{novel_title}》的创建章节按钮")

        # 备用方案：通过标题定位
        print("尝试通过标题定位...")
        if click_create_chapter_button_directly(page, novel_title):
            return True
        else:
            print("所有自动定位方法都失败")
            return False


def check_for_book_during_scroll(page, expected_book_title):
    """
    在滚动过程中实时检查是否找到目标书籍
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
                        return True
        return False
    except:
        return False


def check_and_rename_duplicate_chapters(chapter_files, novel_title):
    """
    检查并重命名重复的章节文件名，同时更新文件内的章节标题
    返回处理后的章节文件列表
    """
    print("检查章节文件名重复...")

    # 用于记录每个章节标题出现的次数
    chapter_title_count = {}
    renamed_files = []
    renamed_count = 0

    for chapter_file in chapter_files:
        # 读取章节文件内容
        try:
            with open(chapter_file, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)

            original_chapter_title = chapter_data.get('chapter_title', '')

            # 检查这个章节标题是否已经出现过
            if original_chapter_title in chapter_title_count:
                chapter_title_count[original_chapter_title] += 1
                count = chapter_title_count[original_chapter_title]

                # 创建新的章节标题（在原标题后添加序号）
                new_chapter_title = f"{original_chapter_title}（{count}）"

                # 更新文件内的章节标题
                chapter_data['chapter_title'] = new_chapter_title

                # 保存更新后的内容
                with open(chapter_file, 'w', encoding='utf-8') as f:
                    json.dump(chapter_data, f, ensure_ascii=False, indent=2)

                # 构建新的文件名
                dir_path = os.path.dirname(chapter_file)
                filename = os.path.basename(chapter_file)

                # 解析原文件名并构建新文件名
                # 假设格式为: 第XXX章_原章节标题.txt
                parts = filename.split('_')
                if len(parts) >= 2:
                    # 保留章节号部分，更新标题部分
                    chapter_num_part = parts[0]
                    extension = '.txt' if filename.endswith('.txt') else ''

                    # 创建新文件名：章节号_新章节标题.txt
                    new_filename = f"{chapter_num_part}_{new_chapter_title}{extension}"
                    new_filepath = os.path.join(dir_path, new_filename)

                    # 如果新文件路径已经存在，继续递增数字
                    while os.path.exists(new_filepath):
                        count += 1
                        new_chapter_title = f"{original_chapter_title}（{count}）"
                        new_filename = f"{chapter_num_part}_{new_chapter_title}{extension}"
                        new_filepath = os.path.join(dir_path, new_filename)

                    # 重命名文件
                    try:
                        os.rename(chapter_file, new_filepath)
                        renamed_files.append(new_filepath)
                        renamed_count += 1
                        print(f"重命名: {filename} -> {new_filename}")
                        print(f"  更新章节标题: {original_chapter_title} -> {new_chapter_title}")
                    except Exception as e:
                        print(f"重命名失败 {filename}: {e}")
                        renamed_files.append(chapter_file)  # 如果重命名失败，使用原文件
                else:
                    # 如果文件名格式不符合预期，只更新文件内容
                    print(f"更新章节标题: {original_chapter_title} -> {new_chapter_title}")
                    renamed_files.append(chapter_file)
                    renamed_count += 1

            else:
                # 第一次出现这个标题
                chapter_title_count[original_chapter_title] = 1
                renamed_files.append(chapter_file)

        except Exception as e:
            print(f"处理章节文件失败 {chapter_file}: {e}")
            renamed_files.append(chapter_file)

    if renamed_count > 0:
        print(f"✓ 已完成 {renamed_count} 个文件的重命名和内容更新")
    else:
        print("✓ 没有发现重复的章节文件名")

    return renamed_files


def validate_and_fix_chapter_files(chapter_files, novel_title):
    """
    验证章节文件的完整性和唯一性，并修复重复问题
    """
    print("验证和修复章节文件...")

    # 首先检查并修复重复的章节
    fixed_files = check_and_rename_duplicate_chapters(chapter_files, novel_title)

    # 然后验证文件完整性
    valid_files = []
    error_count = 0

    for chapter_file in fixed_files:
        # 检查文件是否存在
        if not os.path.exists(chapter_file):
            print(f"✗ 文件不存在: {chapter_file}")
            error_count += 1
            continue

        # 检查文件是否可读
        try:
            with open(chapter_file, 'r', encoding='utf-8') as f:
                content = f.read()
                # 修复中文引号问题 - 更全面的处理
                # 先将JSON字符串中的中文引号转义，然后统一处理
                content = content.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
                chapter_data = json.loads(content)

            # 检查必需字段
            required_fields = ['chapter_number', 'chapter_title', 'content']
            missing_fields = []
            for field in required_fields:
                if field not in chapter_data:
                    missing_fields.append(field)

            if missing_fields:
                print(f"✗ 文件缺少必需字段 {missing_fields}: {chapter_file}")
                error_count += 1
            else:
                # 所有字段都存在
                valid_files.append(chapter_file)

        except json.JSONDecodeError:
            print(f"✗ JSON 格式错误: {chapter_file}")
            error_count += 1
        except Exception as e:
            print(f"✗ 读取文件失败 {chapter_file}: {e}")
            error_count += 1

    if error_count > 0:
        print(f"⚠ 发现 {error_count} 个文件问题")
    else:
        print("✓ 所有章节文件验证通过")

    return valid_files


def click_create_chapter_button_by_novel_title(page: Page, novel_title: str, novel_id: str = None) -> Optional[Page]:
    """
    在书籍列表中找到并点击与指定小说标题相关联的"创建章节"按钮，支持自动翻页。
    如果成功，此函数会返回新打开页面的 Page 对象。
    如果失败（未找到书籍、未找到按钮、点击失败等），则返回 None。

    参数:
    - page (Page): 当前的浏览器页面对象 (书籍列表页)。
    - novel_title (str): 要查找的小说标题。
    - novel_id (str, optional): 小说的ID，用于更精确的定位。

    返回:
    - Optional[Page]: 新打开的章节编辑页面的 Page 对象，如果失败则为 None。
    """
    print(f"开始查找小说《{novel_title}》，支持自动翻页...")
    page_number = 1

    # ==========================================================
    # 核心修改点: 引入 while True 循环来处理翻页
    # ==========================================================
    while True:
        print(f"\n--- 正在搜索第 {page_number} 页 ---")
        page.wait_for_load_state("networkidle")  # 等待当前页数据加载完毕

        # 找到页面上所有的书籍条目容器
        book_items = page.locator('//div[contains(@id, "long-article-table-item")]')
        if book_items.count() == 0:
            print(f"✗ 第 {page_number} 页上未找到任何书籍条目。")
            # This might happen on an empty last page, so we check pagination next.
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

        # 检查“下一页”按钮是否存在且可点击
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
    # ==========================================================
    # 循环结束
    # ==========================================================


def verify_and_create_chapter(target_page, expected_book_title, chap_number, chap_title, chap_content, target_date,
                              target_time):
    """
    验证当前页面并创建章节，如果不匹配则退出并重新开始
    """

    current_page = click_create_chapter_button_by_novel_title(target_page,expected_book_title)

    try:
        # 等待页面加载
        current_page.wait_for_load_state("networkidle")
        time.sleep(2)

        # 在创建章节页面中验证书名
        header_book_name = current_page.locator('.publish-header-book-name')
        if header_book_name.count() > 0:
            actual_title = header_book_name.first.text_content().strip()
            if expected_book_title not in actual_title:
                print(f"✗ 创建章节页面书籍不匹配! 期望: {expected_book_title}, 实际: {actual_title}")
                current_page.close()
                return 2  # 返回2表示需要重新导航

        # 填写章节信息
        input_elements = current_page.locator('input.serial-input.byte-input.byte-input-size-default')
        if input_elements.count() < 2:
            print("未找到章节输入框")
            current_page.close()
            return 1

        # 填写章节序号和标题
        if not safe_fill(input_elements.nth(0), chap_number, "章节序号"):
            current_page.close()
            return 1
        if not safe_fill(input_elements.nth(1), chap_title, "章节标题"):
            current_page.close()
            return 1

        # 处理并填写内容
        content_cleaned = re.sub(r'^【.*?】\s*?\n', '', chap_content, flags=re.MULTILINE)
        processed_text = normalize_all_line_breaks(content_cleaned)

        content_input = current_page.locator('div[class*="ProseMirror"][contenteditable]').first
        if not safe_fill(content_input, processed_text, "章节内容"):
            current_page.close()
            return 1

        # 点击下一步
        if not safe_click(current_page.get_by_role("button", name="下一步"), "下一步按钮", retries=2):
            current_page.close()
            return 1

        time.sleep(0.5)

        # 处理可能的弹窗
        retry_times = 5
        while retry_times >= 0:
            time.sleep(0.3)
            retry_times = retry_times - 1
            for button_name in ["提交", "继续编辑本地", "确定", "确认"]:
                try:
                    button = current_page.get_by_role("button", name=button_name, exact=False)
                    button_text = button.text_content(timeout=100)
                    if "发布" not in button_text:
                        button.click(timeout=100)

                    time.sleep(0.3)
                except:
                    pass

        # 选择AI选项
        try:
            current_page.locator(".arco-radio-text >> text=是").click(timeout=5000)
            time.sleep(0.3)
        except:
            pass

        # 设置定时发布 - 使用您提供的方法
        if target_date or target_time:
            try:
                switch_button = current_page.get_by_role("switch")
                current_state = switch_button.get_attribute("aria-checked")
                if current_state == "false":
                    switch_button.click()  # 点击切换状态
                    time.sleep(0.3)

                # 获取所有匹配元素（使用更严格的等待）
                all_pickers = current_page.locator('.arco-picker-start-time').all()
                current_page.wait_for_selector('.arco-picker-start-time', state='attached', timeout=12000)

                if len(all_pickers) < 2:
                    raise Exception("未找到第二个时间选择器")
                else:
                    # 禁用页面的重置脚本
                    current_page.evaluate('''() => {
                        const originalBlur = HTMLInputElement.prototype.blur;
                        HTMLInputElement.prototype.blur = function() {
                            if (this.type === 'time' && this.value) {
                                this.value = this.value.slice(0, 5);  // 强制保留HH:MM格式
                            }
                            originalBlur.call(this);
                        };
                    }''')

                if target_date is not None:
                    date_picker = all_pickers[0]
                    date_picker.evaluate('''(el, date) => {
                        // 绕过框架的拦截
                        const prototype = HTMLInputElement.prototype;
                        const nativeSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                        nativeSetter.call(el, date);

                        // 触发框架监听的所有事件
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur'));
                    }''', target_date)

                    date_picker.click(timeout=2000)
                    time.sleep(1)

                    # 先尝试向前翻页最多12次
                    timeout_cnt = 0
                    date_found = False

                    # 向前翻页寻找日期
                    while timeout_cnt <= 12:
                        try:
                            # 点击设置的日期
                            selected_cell = current_page.locator('''
                                div.arco-picker-body 
                                >> div.arco-picker-row 
                                >> div.arco-picker-cell-selected
                            ''')
                            selected_cell.click(timeout=500)
                            date_found = True
                            break
                        except Exception as e:
                            next_selector = "div.arco-picker-header-icon:has(svg.arco-icon-right)"
                            next_div = current_page.locator(next_selector)
                            next_div.click(timeout=5000)
                            timeout_cnt = timeout_cnt + 1
                            time.sleep(1)

                    # 如果向前翻页没找到，改为向后翻页
                    if not date_found:
                        print("向前翻页12次未找到日期，改为向后翻页")
                        back_count = 0
                        max_back_count = 24  # 最多向后翻24个月（两年）

                        while back_count < max_back_count and not date_found:
                            try:
                                # 点击设置的日期
                                selected_cell = current_page.locator('''
                                    div.arco-picker-body 
                                    >> div.arco-picker-row 
                                    >> div.arco-picker-cell-selected
                                ''')
                                selected_cell.click(timeout=500)
                                date_found = True
                                break
                            except Exception as e:
                                prev_selector = "div.arco-picker-header-icon:has(svg.arco-icon-left)"
                                prev_div = current_page.locator(prev_selector)
                                prev_div.click(timeout=5000)
                                back_count += 1
                                time.sleep(1)

                    # 如果最终都没找到日期，发布失败，继续下一章
                    if not date_found:
                        print(f"✗ 无法找到目标日期 {target_date}，发布失败，继续下一章")
                        current_page.close()
                        return 1

                if target_time is not None:
                    time_picker = all_pickers[1]
                    time_picker.evaluate('''(el, time) => {
                        // 绕过框架的拦截
                        const prototype = HTMLInputElement.prototype;
                        const nativeSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                        nativeSetter.call(el, time);

                        // 触发框架监听的所有事件
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                        el.dispatchEvent(new Event('blur'));
                    }''', target_time)

                    time_picker.click(timeout=2000)
                    time.sleep(1)
                    # 点击确定
                    current_page.get_by_role("button", name="确定").click(timeout=12000)
                    time.sleep(1)

            except Exception as e:
                print(f"设置定时发布失败: {e}")
        # 处理可能的弹窗
        retry_times = 3
        while retry_times >= 0:
            time.sleep(0.5)
            retry_times = retry_times - 1
            for button_name in ["提交", "提交"]:
                try:
                    button = current_page.get_by_role("button", name=button_name, exact=False)
                    button_text = button.text_content(timeout=100)
                    if "发布" not in button_text:
                        button.click(timeout=100)

                    time.sleep(0.5)
                except:
                    pass
        # 确认发布
        if safe_click(current_page.get_by_role("button", name="确认发布"), "确认发布按钮", retries=2):
            time.sleep(1)
            # 处理可能的弹窗
            retry_times = 3
            while retry_times >= 0:
                time.sleep(0.5)
                retry_times = retry_times - 1
                for button_name in ["确定", "确认"]:
                    try:
                        button = current_page.get_by_role("button", name=button_name, exact=False)
                        button_text = button.text_content(timeout=100)
                        if "发布" not in button_text:
                            button.click(timeout=100)

                        time.sleep(0.5)
                    except:
                        pass

            # 发布完后，会自动进入章节列表，且最新的排在前面。所以只要检查上面发布的章节标题，是否在其中即可确认发布成功没有。
            divs = current_page.locator('div[class*="table-title"][class*="table-title-narrow"]')
            # 获取所有匹配的元素
            all_div_elements = divs.all()

            # 遍历并使用 enumerate 打印索引和文本内容
            for index, element in enumerate(all_div_elements):
                element_inner_text = element.inner_text()
                chap_no = f"""第{chap_number}章"""
                if chap_title in element_inner_text and chap_no in element_inner_text:
                    print(f"✓ 本章节 [{chap_no} {chap_title}] 发布成功,已确认! ")
                    current_page.close()
                    return 0

            current_page.close()
            return 1

    except Exception as e:
        print(f"发布章节时发生错误: {e}")
        try:
            current_page.close()
        except:
            pass
        current_page.close()
        return 1

    current_page.close()
    return 1


def publish_chapter_with_retry(target_page, chap_number, chap_title, chap_content, target_date, target_time,
                               expected_book_title, max_retries=9):
    """
    带有重试机制的章节发布函数
    """
    retry_count = 0

    while retry_count < max_retries:
        result = verify_and_create_chapter(target_page, expected_book_title, chap_number, chap_title, chap_content,
                                           target_date, target_time)

        if result == 0:  # 成功
            return 0
        elif result == 2:  # 需要重新导航
            print("需要重新导航到正确书籍...")
            if not navigate_to_correct_book(target_page, expected_book_title):
                print("重新导航失败")
                return 1
            retry_count += 1
            print(f"重新导航后重试发布 (第{retry_count}次重试)")
        else:  # 其他错误
            retry_count += 1
            continue
            # return result

    print(f"达到最大重试次数({max_retries})，发布失败")
    return 1


def check_and_recover_page(page):
    """检查页面状态并尝试恢复"""
    try:
        # 检查页面是否仍然可用
        page.title()
        return True
    except:
        print("页面可能已关闭或失效，尝试重新连接...")
        return False


def connect_to_browser():
    """连接浏览器 - 全自动集成版本"""
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'utils'))
    
    print(f"🔗 尝试连接浏览器 (调试端口: {CONFIG['debug_port']})...")
    
    try:
        from auto_browser_manager import auto_connect_to_browser
        
        debug_port = CONFIG['debug_port']
        print(f"🤖 启动自动化浏览器管理器 (端口: {debug_port})...")
        
        # 使用自动化连接管理器，增加重试次数
        for attempt in range(3):
            try:
                print(f"  尝试自动连接 (第 {attempt + 1} 次)...")
                playwright, browser, page, context = auto_connect_to_browser(
                    debug_port=debug_port,
                    auto_start_chrome=True  # 自动启动Chrome
                )
                
                if browser:
                    print("✅ 浏览器连接已建立!")
                    return playwright, browser, page, context
                else:
                    print(f"  第 {attempt + 1} 次自动连接失败")
                    if attempt < 2:
                        print("  等待 5 秒后重试...")
                        time.sleep(5)
                        
            except Exception as auto_error:
                print(f"  第 {attempt + 1} 次自动连接异常: {auto_error}")
                if attempt < 2:
                    print("  等待 5 秒后重试...")
                    time.sleep(5)
        
        print("❌ 所有自动连接尝试都失败")
        return None, None, None, None
            
    except ImportError as e:
        print(f"❌ 导入自动化管理器失败: {e}")
        print("尝试使用简化连接方案...")
        
        # 回退到简化连接方案
        try:
            from simple_connection_fix import connect_to_existing_browser, test_debug_connection
            
            debug_port = CONFIG['debug_port']
            print(f"尝试连接到端口 {debug_port} 的浏览器...")
            
            # 首先测试调试端口，增加重试
            for attempt in range(3):
                try:
                    print(f"  测试调试端口连接 (第 {attempt + 1} 次)...")
                    if test_debug_connection(debug_port):
                        print("✓ 调试端口连接成功")
                        break
                    else:
                        print(f"  第 {attempt + 1} 次端口测试失败")
                        if attempt < 2:
                            time.sleep(3)
                except Exception as port_error:
                    print(f"  第 {attempt + 1} 次端口测试异常: {port_error}")
                    if attempt < 2:
                        time.sleep(3)
            else:
                print(f"❌ 端口 {debug_port} 无法访问")
                print("请确保:")
                print("1. Chrome已启动")
                print(f"2. 使用了 --remote-debugging-port={debug_port} 参数")
                print("3. 防火墙没有阻止连接")
                print("\n💡 或者运行自动启动脚本:")
                print("   python fanqie_browser_launcher.py")
                return None, None, None, None
            
            # 尝试连接
            for attempt in range(3):
                try:
                    print(f"  尝试建立浏览器连接 (第 {attempt + 1} 次)...")
                    playwright, browser, context, page = connect_to_existing_browser(debug_port, max_retries=2)
                    
                    if browser:
                        print("✓ 成功连接到浏览器!")
                        return playwright, browser, page, context
                    else:
                        print(f"  第 {attempt + 1} 次连接失败")
                        if attempt < 2:
                            time.sleep(3)
                except Exception as conn_error:
                    print(f"  第 {attempt + 1} 次连接异常: {conn_error}")
                    if attempt < 2:
                        time.sleep(3)
            
            print("❌ 所有连接尝试都失败")
            return None, None, None, None
                
        except ImportError as e2:
            print(f"❌ 导入简化连接模块失败: {e2}")
            print("使用原有连接方式...")
            
            # 最后回退到原有方式
            playwright = sync_playwright().start()
            try:
                for attempt in range(3):
                    try:
                        print(f"  使用原有方式连接 (第 {attempt + 1} 次)...")
                        browser = playwright.chromium.connect_over_cdp(f"http://127.0.0.1:{CONFIG['debug_port']}")
                        default_context = browser.contexts[0]
                        page1 = default_context.pages[0]
                        print("✓ 原有方式连接成功")
                        return playwright, browser, page1, default_context
                    except Exception as e3:
                        print(f"  第 {attempt + 1} 次原有方式连接失败: {e3}")
                        if attempt < 2:
                            time.sleep(3)
            except Exception as e3:
                print(f"❌ 原有连接方式也失败: {e3}")
                return None, None, None, None
        except Exception as e2:
            print(f"❌ 简化连接失败: {e2}")
            return None, None, None, None
    except Exception as e:
        print(f"❌ 自动连接失败: {e}")
        return None, None, None, None


def navigate_to_writer_platform(page1, default_context):
    """导航到作家专区 - 全自动版本"""
    print("=" * 60)
    print("🍅 自动导航到番茄小说作家专区")
    print("=" * 60)
    print("🚀 正在自动导航，无需手动操作...")
    print()
    
    # 自动导航到作家专区
    print("📍 步骤1: 导航到番茄小说首页...")
    try:
        # 增加超时时间并添加重试机制
        for attempt in range(3):
            try:
                print(f"  尝试导航到番茄网站 (第 {attempt + 1} 次)...")
                page1.goto("https://fanqienovel.com/", timeout=60000)  # 60秒超时
                page1.wait_for_load_state("domcontentloaded", timeout=30000)  # 30秒等待
                print("✅ 已打开番茄小说首页")
                break
            except Exception as nav_error:
                print(f"  第 {attempt + 1} 次导航失败: {nav_error}")
                if attempt == 2:  # 最后一次尝试
                    raise nav_error
                print("  等待 5 秒后重试...")
                time.sleep(5)
    except Exception as e:
        print(f"❌ 打开番茄小说首页失败: {e}")
        print("💡 可能的解决方案:")
        print("   1. 检查网络连接")
        print("   2. 确认防火墙设置")
        print("   3. 验证 Chrome 是否正确启动")
        print("   4. 尝试手动打开 https://fanqienovel.com")
        return None
    
    # 等待页面加载
    time.sleep(3)
    
    print("📍 步骤2: 查找并点击作家专区链接...")
    try:
        # 尝试多种选择器定位作家专区链接
        writer_zone_selectors = [
            'xpath=//*[@id="app"]/div/div[1]/div/div[2]/div[5]/a',
            'a:has-text("作家专区")',
            'text=作家专区',
            '[href*="writer"]',
            'a[href*="author"]',
            'a[href*="creator"]'
        ]
        
        link_found = False
        for selector in writer_zone_selectors:
            try:
                print(f"  尝试选择器: {selector}")
                element = page1.locator(selector).first
                if element.count() > 0 and element.is_visible():
                    print("  ✓ 找到作家专区链接")
                    
                    # 使用expect_popup处理新窗口
                    with page1.expect_popup(timeout=10000) as page2_info:
                        element.click()
                    
                    page2 = page2_info.value
                    link_found = True
                    break
            except Exception as e:
                print(f"  选择器失败: {e}")
                continue
        
        if not link_found:
            print("❌ 未找到作家专区链接，尝试备用方案...")
            # 备用方案：直接导航到作家专区URL
            try:
                with page1.expect_popup(timeout=10000) as page2_info:
                    page1.goto("https://fanqienovel.com/writer", timeout=15000)
                page2 = page2_info.value
                print("✅ 通过直接导航打开作家专区")
            except Exception as e:
                print(f"❌ 备用方案也失败: {e}")
                return None
                
    except Exception as e:
        print(f"❌ 打开作家专区失败: {e}")
        return None
    
    print("📍 步骤3: 等待作家专区页面加载...")
    try:
        page2.wait_for_load_state("domcontentloaded")
        time.sleep(3)
        print("✅ 作家专区页面已加载")
    except Exception as e:
        print(f"⚠️ 页面加载检查失败: {e}")
    
    print("📍 步骤4: 导航到工作台...")
    try:
        # 尝试点击工作台
        workbench_selectors = [
            'xpath=//*[@id="root"]/div[2]/div/div[3]/div[1]/div[1]/div[2]/button[1]',
            'button:has-text("工作台")',
            'text=工作台',
            '[class*="workbench"]',
            '[class*="dashboard"]'
        ]
        
        workbench_found = False
        for selector in workbench_selectors:
            try:
                print(f"  尝试工作台选择器: {selector}")
                element = page2.locator(selector).first
                if element.count() > 0 and element.is_visible():
                    if safe_click(element, "工作台"):
                        workbench_found = True
                        break
            except Exception as e:
                print(f"  工作台选择器失败: {e}")
                continue
        
        if workbench_found:
            print("✅ 已进入工作台")
            time.sleep(2)
        else:
            print("⚠️ 未找到工作台按钮，可能已在正确页面")
            
    except Exception as e:
        print(f"⚠️ 导航工作台失败: {e}")
    
    print("📍 步骤5: 导航到小说管理页面...")
    try:
        # 尝试点击小说
        novel_selectors = [
            'xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]',
            'text=小说',
            'span:has-text("小说")',
            '[class*="novel"]',
            'a[href*="novel"]'
        ]
        
        novel_found = False
        for selector in novel_selectors:
            try:
                print(f"  尝试小说选择器: {selector}")
                element = page2.locator(selector).first
                if element.count() > 0 and element.is_visible():
                    if safe_click(element, "小说"):
                        novel_found = True
                        break
            except Exception as e:
                print(f"  小说选择器失败: {e}")
                continue
        
        if novel_found:
            print("✅ 已进入小说管理页面")
            time.sleep(2)
        else:
            print("⚠️ 未找到小说按钮，可能已在正确页面")
            
    except Exception as e:
        print(f"⚠️ 导航小说页面失败: {e}")
    
    print("=" * 60)
    print("✅ 自动导航完成！")
    print("📝 当前应该位于作家专区的小说管理页面")
    print("📍 如未登录，请在浏览器中手动登录番茄小说账号")
    print("=" * 60)
    
    return page2


def create_new_book(page2, novel_title, formatted_synopsis, main_character, novel_data):
    """创建新书 - 适配新的JSON结构"""
    print("创建新书...")

    safe_click(page2.locator('xpath=//*[@id="app"]/div/div[2]/div[2]/div/div/div[1]/div/div[2]/div/span/div'),
               "创建新书")
    time.sleep(0.3)
    safe_click(page2.get_by_text("创建书本", exact=False), "创建书本")
    time.sleep(0.3)

    # 3. 填写书名
    title_short = novel_title[-15:] if len(novel_title) >= 15 else novel_title
    safe_fill(page2.locator('xpath=//*[@id="name_input"]/div/span/span/input'), title_short, "书名")

    # 4. 选择男女频 - 从selected_plan.tags.target_audience获取
    tags_info = novel_data.get("novel_info", {}).get("selected_plan", {}).get("tags", {})
    gender = tags_info.get("target_audience", "男频")
    if gender == "女频":
        safe_click(page2.locator('xpath=//*[@id="radio"]/div/div/label[2]/span[1]'), "女频")
        print("✓ 选择女频")
    else:
        safe_click(page2.locator('xpath=//*[@id="radio"]/div/div/label[1]/span[1]'), "男频")
        print("✓ 选择男频")

    # 5. 选择作品标签
    print("选择作品标签...")

    safe_click(page2.locator('xpath=//*[@id="selectRow"]/div/div/span/div/span[1]'), "选择作品标签")
    time.sleep(3)  # 等待标签弹窗完全加载

    # 使用新的标签选择函数
    if select_novel_tags_interactive(page2, novel_data):
        print("✓ 标签选择完成")
    else:
        print("⚠ 标签选择可能有问题，但继续流程")


def validate_tags_with_platform(tags_info):
    """
    验证标签是否在番茄平台的实际分类中，如果不匹配则使用最接近的有效标签
    """
    # 番茄平台分类映射（按性别分类）
    platform_categories = {
        "男频": {
            "main_category": [
                "西方奇幻", "东方仙侠", "科幻末世", "男频衍生", "都市高武", "悬疑灵异", "悬疑脑洞",
                "抗战谍战", "历史古代", "历史脑洞", "都市种田", "都市脑洞", "都市日常", "玄幻脑洞",
                "战神赘婿", "动漫衍生", "游戏体育", "传统玄幻", "都市修真"
            ],
            "themes": [
                "衍生", "仕途", "综影视", "天灾", "第一人称", "赛博朋克", "第四天灾", "规则怪谈", "古代", "悬疑",
                "克苏鲁", "都市异能", "末日求生", "灵气复苏", "高武世界", "异世大陆", "东方玄幻", "谍战",
                "清朝", "宋朝", "断层", "武将", "国运", "综漫", "开局", "架空", "奇幻仙侠",
                "都市", "玄幻", "历史", "体育", "武侠"
            ],
            "roles": [
                "多女主", "赘婿", "全能", "大佬", "大小姐", "特工", "游戏主播", "神探", "宫廷侯爵", "皇帝", "单女主", "校花",
                "无女主", "女帝", "特种兵", "反派", "神医", "奶爸", "学霸", "天才", "腹黑", "扮猪吃虎"
            ],
            "plots": [
                "斩神衍生", "十日衍生", "西游衍生", "公版衍生", "红楼衍生", "甄嬛衍生", "如懿衍生",
                "惊悚游戏", "卡牌", "山海经", "捉鬼", "剑修", "废土", "副本", "黑科技", "无脑爽",
                "魂穿", "高手下山", "黑化", "迪化", "发家致富", "无后宫", "争霸", "1v1", "升级流",
                "灵魂互换", "封神", "四合院", "电竞", "双重生", "乡村", "同人", "打脸", "破案", "囤物资", "钓鱼",
                "网游", "奥特同人", "求生", "无敌", "九叔", "穿书", "聊天群", "大秦", "龙珠", "漫威", "神奇宝贝", "海贼", "火影",
                "职场", "明朝", "家庭", "三国", "末世", "直播", "无限流", "诸天万界", "大唐", "宠物", "外卖",
                "星际", "美食", "剑道", "盗墓", "灵异", "鉴宝", "系统", "神豪", "重生", "穿越", "二次元",
                "海岛", "娱乐圈", "空间", "推理", "洪荒"
            ]
        },
        "女频": {
            "main_category": [
                "古代言情", "现代言情", "玄幻言情", "科幻言情", "青春校园", "悬疑推理", "游戏竞技",
                "同人衍生", "次元幻想", "现实题材", "港台言情", "影视原著", "经典名著"
            ],
            "themes": [
                "甜宠", "虐恋", "穿书", "重生", "快穿", "系统", "空间", "爽文", "甜文", "虐文",
                "宫斗", "宅斗", "权谋", "江湖", "仙侠", "玄幻", "校园", "都市", "职场",
                "娱乐圈", "电竞", "直播", "美食", "萌宝", "种田", "经商", "军婚", "警匪",
                "悬疑", "推理", "惊悚", "灵异", "历史", "科幻", "奇幻", "神话", "武侠"
            ],
            "roles": [
                "总裁", "王爷", "皇帝", "影帝", "明星", "医生", "律师", "教授", "军人", "警察",
                "总裁夫人", "王妃", "皇后", "影后", "学霸", "校花", "才女", "美女", "主播", "网红",
                "霸道总裁", "温柔男主", "腹黑男主", "忠犬男主", "傲娇男主", "病娇男主", "清冷男主", "妖孽男主"
            ],
            "plots": [
                "先婚后爱", "一见钟情", "日久生情", "暗恋成真", "破镜重圆", "久别重逢", "青梅竹马",
                "欢喜冤家", "冤家路窄", "近水楼台", "朝夕相处", "共事", "邻居", "同事", "同学",
                "穿越", "重生", "系统", "空间", "快穿", "穿书", "玄幻", "修仙", "魔法", "异能",
                "宫斗", "宅斗", "权谋", "江湖", "武侠", "仙侠", "校园", "都市", "职场", "娱乐圈",
                "电竞", "直播", "美食", "萌宝", "种田", "经商", "军婚", "警匪", "悬疑", "推理",
                "惊悚", "灵异", "历史", "科幻", "奇幻", "神话", "同人", "衍生", "影视", "游戏"
            ]
        }
    }
    
    validated_tags = {}
    
    # 验证目标受众
    target_audience = tags_info.get("target_audience", "男频")
    validated_tags["target_audience"] = target_audience if target_audience in ["男频", "女频"] else "男频"
    
    # 验证主分类
    main_category = tags_info.get("main_category", "传统玄幻")
    available_categories = platform_categories.get(target_audience, {}).get("main_category", [])
    
    if main_category in available_categories:
        validated_tags["main_category"] = main_category
    else:
        # 查找最接近的匹配
        best_match = None
        best_match_score = 0
        for category in available_categories:
            # 计算相似度
            similarity = calculate_similarity(main_category, category)
            if similarity > best_match_score:
                best_match_score = similarity
                best_match = category
        
        if best_match and best_match_score > 0.3:  # 设置最低相似度阈值
            validated_tags["main_category"] = best_match
            print(f"主分类 '{main_category}' 不在平台分类中，使用最接近的匹配: {best_match} (相似度: {best_match_score:.2f})")
        else:
            print(f"无法找到合适的主分类匹配: {main_category}，使用默认分类")
            validated_tags["main_category"] = "东方玄幻" if target_audience == "男频" else "古代言情"
    
    # 验证主题标签（最多选择2个）
    original_themes = tags_info.get("themes", [])
    validated_themes = []
    available_themes = platform_categories.get(target_audience, {}).get("themes", [])
    
    for theme in original_themes[:2]:  # 最多选择2个主题
        validated_theme = validate_single_tag(theme, available_themes, f"主题标签")
        if validated_theme:
            validated_themes.append(validated_theme)
    
    # 如果没有有效的主题，添加默认主题
    if not validated_themes:
        default_themes = ["玄幻", "都市"] if target_audience == "男频" else ["甜宠", "言情"]
        for default_theme in default_themes[:1]:  # 至少添加一个默认主题
            if default_theme in available_themes:
                validated_themes.append(default_theme)
                print(f"添加默认主题标签: {default_theme}")
                break
    
    validated_tags["themes"] = validated_themes
    
    # 验证角色标签（最多选择2个）
    original_roles = tags_info.get("roles", [])
    validated_roles = []
    available_roles = platform_categories.get(target_audience, {}).get("roles", [])
    
    for role in original_roles[:2]:  # 最多选择2个角色
        validated_role = validate_single_tag(role, available_roles, f"角色标签")
        if validated_role:
            validated_roles.append(validated_role)
    
    # 如果没有有效的角色，添加默认角色
    if not validated_roles:
        default_roles = ["天才", "大佬"] if target_audience == "男频" else ["总裁", "学霸"]
        for default_role in default_roles[:1]:  # 至少添加一个默认角色
            if default_role in available_roles:
                validated_roles.append(default_role)
                print(f"添加默认角色标签: {default_role}")
                break
    
    validated_tags["roles"] = validated_roles
    
    # 验证情节标签（最多选择2个）
    original_plots = tags_info.get("plots", [])
    validated_plots = []
    available_plots = platform_categories.get(target_audience, {}).get("plots", [])
    
    for plot in original_plots[:2]:  # 最多选择2个情节
        validated_plot = validate_single_tag(plot, available_plots, f"情节标签")
        if validated_plot:
            validated_plots.append(validated_plot)
    
    # 如果没有有效的情节，添加默认情节
    if not validated_plots:
        default_plots = ["系统", "重生"] if target_audience == "男频" else ["穿越", "重生"]
        for default_plot in default_plots[:1]:  # 至少添加一个默认情节
            if default_plot in available_plots:
                validated_plots.append(default_plot)
                print(f"添加默认情节标签: {default_plot}")
                break
    
    validated_tags["plots"] = validated_plots
    
    return validated_tags

def validate_single_tag(tag, available_tags, tag_type):
    """
    验证单个标签是否在可用标签列表中，如果不匹配则返回最接近的匹配
    """
    if tag in available_tags:
        return tag
    
    # 如果直接匹配失败，查找最接近的匹配
    best_match = None
    best_match_score = 0
    
    for available_tag in available_tags:
        # 计算相似度
        similarity = calculate_similarity(tag, available_tag)
        if similarity > best_match_score and similarity > 0.6:  # 相似度阈值
            best_match_score = similarity
            best_match = available_tag
    
    if best_match:
        print(f"⚠ {tag_type}标签 '{tag}' 不在平台分类中，使用最接近的匹配: {best_match}")
        return best_match
    else:
        print(f"无法找到合适的{tag_type}标签匹配: {tag}")
        return None  # 返回None表示无法找到匹配

def calculate_similarity(str1, str2):
    """
    计算两个字符串的相似度
    """
    if not str1 or not str2:
        return 0
    
    if str1 == str2:
        return 1.0
    
    # 简单的相似度计算
    common_chars = set(str1) & set(str2)
    total_chars = set(str1) | set(str2)
    
    if total_chars:
        return len(common_chars) / len(total_chars)
    else:
        return 0

def select_novel_tags_interactive(page, novel_data):
    """
    交互式选择小说标签 - 基于当前弹窗结构，支持动态JSON结构，并匹配番茄平台实际分类
    """
    try:
        print("开始选择小说标签...")
        
        # 等待弹窗完全加载
        page.wait_for_timeout(2000)
        
        # 动态获取标签信息 - 支持多种JSON结构
        tags_info = {}
        
        # 方法1: 尝试从 project_info.tags 获取（当前结构）
        if "project_info" in novel_data and "tags" in novel_data["project_info"]:
            tags_info = novel_data["project_info"]["tags"]
            print("✓ 从 project_info.tags 获取标签信息")
        
        # 方法2: 尝试从 novel_info.tags 获取（兼容结构）
        elif "novel_info" in novel_data and "tags" in novel_data["novel_info"]:
            tags_info = novel_data["novel_info"]["tags"]
            print("✓ 从 novel_info.tags 获取标签信息")
        
        # 方法3: 尝试从 novel_info.selected_plan.tags 获取（旧结构）
        elif "novel_info" in novel_data and "selected_plan" in novel_data["novel_info"] and "tags" in novel_data["novel_info"]["selected_plan"]:
            tags_info = novel_data["novel_info"]["selected_plan"]["tags"]
            print("✓ 从 novel_info.selected_plan.tags 获取标签信息")
        
        else:
            print("⚠ 未找到标准标签信息，使用默认标签")
            # 使用默认标签作为备选
            tags_info = {
                "target_audience": "男频",
                "main_category": "东方玄幻",
                "themes": ["种田流", "凡人流"],
                "roles": ["谨慎型主角", "稳健发育"],
                "plots": ["凡人流", "种田"]
            }
        
        print(f"原始标签信息: {tags_info}")
        
        # 验证标签是否在番茄平台的实际分类中
        valid_tags_info = validate_tags_with_platform(tags_info)
        
        print(f"验证后的标签信息:")
        print(f"- 目标受众: {valid_tags_info['target_audience']}")
        print(f"- 主分类: {valid_tags_info['main_category']}")
        print(f"- 主题: {valid_tags_info['themes']}")
        print(f"- 角色: {valid_tags_info['roles']}")
        print(f"- 情节: {valid_tags_info['plots']}")
        
        # 1. 选择主分类
        print("\n=== 选择主分类 ===")
        if select_category_tag(page, "主分类", valid_tags_info["main_category"]):
            print(f"✓ 主分类选择成功: {valid_tags_info['main_category']}")
        else:
            print(f"⚠ 主分类选择失败: {valid_tags_info['main_category']}")
        
        # 2. 选择主题（最多2个）
        print("\n=== 选择主题 ===")
        theme_selected = 0
        for theme in valid_tags_info["themes"][:2]:  # 最多选择2个主题
            if select_category_tag(page, "主题", theme):
                theme_selected += 1
                print(f"✓ 主题选择成功: {theme}")
                time.sleep(0.5)
            else:
                print(f"⚠ 主题选择失败: {theme}")
        
        print(f"主题选择完成: {theme_selected}/2 个主题")
        
        # 3. 选择角色（最多2个）
        print("\n=== 选择角色 ===")
        role_selected = 0
        for role in valid_tags_info["roles"][:2]:  # 最多选择2个角色
            if select_category_tag(page, "角色", role):
                role_selected += 1
                print(f"✓ 角色选择成功: {role}")
                time.sleep(0.5)
            else:
                print(f"⚠ 角色选择失败: {role}")
        
        print(f"角色选择完成: {role_selected}/2 个角色")
        
        # 4. 选择情节（最多2个）
        print("\n=== 选择情节 ===")
        plot_selected = 0
        for plot in valid_tags_info["plots"][:2]:  # 最多选择2个情节
            if select_category_tag(page, "情节", plot):
                plot_selected += 1
                print(f"✓ 情节选择成功: {plot}")
                time.sleep(0.5)
            else:
                print(f"⚠ 情节选择失败: {plot}")
        
        print(f"情节选择完成: {plot_selected}/2 个情节")
        
        # 5. 确认选择
        print("\n=== 确认标签选择 ===")
        return confirm_tag_selection(page)
        
    except Exception as e:
        print(f"标签选择过程中出错: {e}")
        return False


def select_category_tag(page, tab_name, target_text):
    """
    在指定标签页中选择目标分类
    """
    try:
        # 1. 点击标签页
        tab_selectors = [
            f'//span[text()="{tab_name}"]',
            f'//div[contains(@class, "arco-tabs-tab")]//span[text()="{tab_name}"]',
        ]
        
        tab_clicked = False
        for selector in tab_selectors:
            try:
                tab_element = page.locator(f'xpath={selector}')
                if tab_element.count() > 0:
                    tab_element.first.click()
                    page.wait_for_timeout(1000)  # 等待标签页切换
                    tab_clicked = True
                    print(f"✓ 成功点击标签页: {tab_name}")
                    break
            except Exception as e:
                continue
        
        if not tab_clicked:
            print(f"❌ 无法点击标签页: {tab_name}")
            return False
        
        # 2. 查找并点击目标标签
        target_selectors = [
            f'//div[contains(@class, "category-choose-item")]//div[contains(text(), "{target_text}")]',
            f'//div[contains(@class, "category-choose-item-title") and text()="{target_text}"]',
            f'//*[contains(text(), "{target_text}")]',
        ]
        
        # 首先尝试不滚动查找
        for selector in target_selectors:
            try:
                target_elements = page.locator(f'xpath={selector}')
                if target_elements.count() > 0:
                    for i in range(target_elements.count()):
                        element = target_elements.nth(i)
                        if element.is_visible():
                            element_text = element.text_content().strip()
                            if target_text in element_text:
                                print(f"找到目标标签: {element_text}")
                                element.click()
                                page.wait_for_timeout(500)
                                return True
            except Exception as e:
                continue
        
        # 3. 如果没找到，尝试滚动查找
        print(f"未找到目标标签 '{target_text}'，开始滚动查找...")
        
        # 定位滚动容器
        scroll_container = page.locator('.category-choose-scroll-parent').first
        if scroll_container.count() == 0:
            scroll_container = page.locator('.arco-tabs-content-item-active').first
        
        # 滚动查找
        for scroll_attempt in range(20):  # 最多滚动20次
            try:
                # 再次尝试查找
                for selector in target_selectors:
                    try:
                        target_elements = page.locator(f'xpath={selector}')
                        if target_elements.count() > 0:
                            for i in range(target_elements.count()):
                                element = target_elements.nth(i)
                                if element.is_visible():
                                    element_text = element.text_content().strip()
                                    if target_text in element_text:
                                        print(f"滚动找到目标标签: {element_text}")
                                        element.click()
                                        page.wait_for_timeout(500)
                                        return True
                    except:
                        continue
                
                # 滚动一小段距离
                page.evaluate('window.scrollBy(0, 200)')
                page.wait_for_timeout(300)
                
            except Exception as e:
                break
        
        print(f"❌ 未找到目标标签: {target_text}")
        return False
        
    except Exception as e:
        print(f"选择标签时出错: {e}")
        return False


def confirm_tag_selection(page):
    """
    确认标签选择 - 修复版本
    """
    try:
        print("尝试确认标签选择...")
        
        # 等待一下确保选择完成
        time.sleep(1)
        
        # 使用更精确的确认按钮选择器，基于你提供的HTML结构
        confirm_selectors = [
            # 基于你提供的HTML结构的精确选择器
            'div.arco-modal-footer button.arco-btn-primary:has-text("确认")',
            'div.arco-modal-footer button.arco-btn-primary span:has-text("确认")',
            '//div[@class="arco-modal-footer"]//button[@class="arco-btn arco-btn-primary"]//span[text()="确认"]',
            '//div[@class="arco-modal-footer"]//button[@class="arco-btn arco-btn-primary" and contains(text(), "确认")]',
            '//div[@class="arco-modal-footer"]//button[contains(@class, "arco-btn-primary") and .//span[text()="确认"]]',
            # 备用选择器
            '//button[contains(@class, "arco-btn-primary")]//span[text()="确认"]',
            '//button[contains(@class, "arco-btn-primary") and text()="确认"]',
            'button:has-text("确认")',
            'button:has(span:text("确认"))',
        ]
        
        for attempt in range(8):  # 增加重试次数
            print(f"尝试点击确认按钮 (第 {attempt + 1} 次)...")
            
            # 每次重试前等待一下，让页面有时间响应
            if attempt > 0:
                time.sleep(1.5)
            
            for selector_idx, selector in enumerate(confirm_selectors):
                try:
                    if selector.startswith('//'):
                        button_element = page.locator(f'xpath={selector}')
                    else:
                        button_element = page.locator(selector)
                    
                    if button_element.count() > 0:
                        button = button_element.first
                        
                        # 检查按钮是否可见和可点击
                        if button.is_visible() and button.is_enabled():
                            print(f"找到确认按钮 (选择器 {selector_idx + 1}), 尝试点击...")
                            
                            # 滚动到按钮位置
                            button.scroll_into_view_if_needed()
                            time.sleep(0.5)
                            
                            # 尝试多种点击方式
                            click_success = False
                            
                            # 方法1: 普通点击
                            try:
                                button.click(timeout=5000)
                                print("✓ 普通点击成功")
                                click_success = True
                            except Exception as click_error:
                                print(f"普通点击失败: {click_error}")
                                
                                # 方法2: 强制点击
                                try:
                                    button.click(force=True, timeout=3000)
                                    print("✓ 强制点击成功")
                                    click_success = True
                                except Exception as force_error:
                                    print(f"强制点击失败: {force_error}")
                                    
                                    # 方法3: JavaScript点击
                                    try:
                                        button.evaluate('(element) => element.click()')
                                        print("✓ JavaScript点击成功")
                                        click_success = True
                                    except Exception as js_error:
                                        print(f"JavaScript点击失败: {js_error}")
                            
                            if click_success:
                                print("✓ 确认按钮点击成功")
                                time.sleep(2)  # 等待弹窗关闭
                                return True
                            else:
                                print(f"所有点击方式都失败")
                                continue
                        else:
                            print(f"按钮不可见或不可用 (选择器 {selector_idx + 1})")
                            continue
                    else:
                        print(f"未找到按钮元素 (选择器 {selector_idx + 1})")
                        continue
                
                except Exception as e:
                    print(f"选择器 {selector_idx + 1} 失败: {e}")
                    continue
            
            # 如果所有选择器都失败，尝试滚动页面后重试
            if attempt < 7:
                print(f"第 {attempt + 1} 次尝试失败，尝试滚动页面后重试...")
                try:
                    # 滚动到页面底部
                    page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                    time.sleep(1)
                    
                    # 再滚动回顶部
                    page.evaluate('window.scrollTo(0, 0)')
                    time.sleep(0.5)
                except:
                    pass
        
        print("❌ 所有尝试都无法点击确认按钮")
        
        # 最后的备用方案：尝试按ESC键关闭弹窗
        try:
            page.keyboard.press('Escape')
            print("尝试按ESC键关闭弹窗")
            time.sleep(1)
            return True
        except:
            pass
        
        return False
        
    except Exception as e:
        print(f"确认标签选择时出错: {e}")
        import traceback
        traceback.print_exc()
        return False

    # 10. 确认标签选择 - 修复确认按钮点击逻辑
    print("尝试确认标签选择...")
    confirm_clicked = False
    
    # 等待一下确保标签选择完成
    time.sleep(1)
    
    # 使用多种方法定位确认按钮
    confirm_selectors = [
        'div.arco-modal-footer button.arco-btn-primary',  # 最精准的选择器
        '//div[@class="arco-modal-footer"]//button[@class="arco-btn arco-btn-primary"]',
        '//div[@class="arco-modal-footer"]//button[contains(@class, "arco-btn-primary")]',
        '//button[contains(@class, "arco-btn-primary") and span[text()="确认"]]',
        '//button[span[text()="确认"]]',
        '//button[text()="确认"]',
    ]
    
    for attempt in range(8):  # 增加重试次数
        print(f"尝试点击确认按钮 (第 {attempt + 1} 次)...")
        
        for selector_idx, selector in enumerate(confirm_selectors):
            try:
                if selector.startswith('//'):
                    button_element = page2.locator(f'xpath={selector}')
                else:
                    button_element = page2.locator(selector)
                
                if button_element.count() > 0:
                    button = button_element.first
                    
                    # 检查按钮是否可见和可点击
                    if button.is_visible() and button.is_enabled():
                        print(f"找到确认按钮，使用选择器: {selector}")
                        
                        # 尝试普通点击
                        try:
                            button.click(timeout=3000)
                            print("✓ 普通点击成功")
                            confirm_clicked = True
                            break
                        except Exception as click_error:
                            if "intercepts pointer events" in str(click_error):
                                print("按钮被遮挡，尝试强制点击...")
                                button.click(force=True, timeout=3000)
                                print("✓ 强制点击成功")
                                confirm_clicked = True
                                break
                            else:
                                print(f"点击失败: {click_error}")
                                continue
                    else:
                        print(f"按钮不可见或不可用")
                        continue
                else:
                    print(f"未找到按钮元素")
                    continue
                    
            except Exception as e:
                print(f"选择器 {selector} 失败: {e}")
                continue
        
        if confirm_clicked:
            break
        
        # 如果所有选择器都失败，等待后重试
        print(f"第 {attempt + 1} 次尝试失败，等待2秒后重试...")
        time.sleep(2)
        
        # 尝试滚动页面，确保按钮在视图中
        try:
            page2.evaluate('window.scrollTo(0, document.body.scrollHeight)')
            time.sleep(0.5)
        except:
            pass

    if confirm_clicked:
        print("✓ 标签选择确认完成")
        time.sleep(1)  # 等待弹窗关闭
    else:
        print("⚠ 无法点击确认按钮，可能标签选择有问题")
        # 尝试按ESC键关闭弹窗
        try:
            page2.keyboard.press('Escape')
            print("尝试按ESC键关闭弹窗")
            time.sleep(1)
        except:
            pass

    time.sleep(1)

    # 11. 选择封面
    print("选择封面...")
    cover_selectors = [
        '//*[@id="app"]/div/div[2]/div[2]/div[2]/div[1]/div/button',
        '//button[contains(text(), "封面")]',
        '//span[contains(text(), "封面")]',
    ]

    for selector in cover_selectors:
        if safe_click(page2.locator(f'xpath={selector}'), "选择封面"):
            time.sleep(1)  # 等待封面选择界面加载
            break
    else:
        print("⚠ 无法找到封面选择按钮")

    # 等待上传区域出现
    print("等待上传区域出现...")
    try:
        # 等待上传区域出现（包含"点击或拖拽文件到此处上传"文本）
        page2.wait_for_selector(f'text=点击或拖拽文件到此处上传', timeout=10000)
        print("✓ 上传区域已出现")

        # 修复：改进封面文件查找逻辑，处理中文字符问题
        novel_project_dir = os.path.abspath(CONFIG["novel_path"])
        print(f"搜索目录: {novel_project_dir}")

        # 检查目录是否存在
        if not os.path.exists(novel_project_dir):
            print(f"✗ 目录不存在: {novel_project_dir}")
            return False

        # 列出目录中的所有文件，用于调试
        print("目录中的所有文件:")
        all_files = os.listdir(novel_project_dir)
        for f in all_files:
            print(f"  - {f}")

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

            if cover_found:
                # 方法1: 直接使用Playwright的文件上传功能
                file_input_selectors = [
                    'input[type="file"]',
                    '//input[@type="file"]',
                ]

                file_uploaded = False
                for selector in file_input_selectors:
                    file_inputs = page2.locator(selector)
                    if file_inputs.count() > 0:
                        try:
                            # 直接设置文件路径，不通过系统对话框
                            file_inputs.first.set_input_files(cover_path)
                            print(f"✓ 已直接上传封面图片: {os.path.basename(cover_path)}")
                            file_uploaded = True
                            break
                        except Exception as e:
                            print(f"直接文件上传失败: {e}")

                # 方法2: 如果直接上传失败，使用拖放方式
                if not file_uploaded:
                    print("尝试使用拖放方式上传封面...")
                    try:
                        # 找到上传区域
                        upload_area = page2.locator('//*[@id="arco-tabs-3-panel-0"]/div/div/div[1]/div/div')
                        if upload_area.count() > 0:
                            # 使用拖放API上传文件
                            with open(cover_path, 'rb') as f:
                                file_data = f.read()

                            # 将文件数据作为DataTransfer对象传递
                            page2.evaluate('''([fileData, fileName]) => {
                                const dataTransfer = new DataTransfer();
                                const file = new File([new Uint8Array(fileData)], fileName, { type: 'image/jpeg' });
                                dataTransfer.items.add(file);

                                // 触发上传区域的拖放事件
                                const uploadArea = document.querySelector('#arco-tabs-3-panel-0 div div div div div');
                                if (uploadArea) {
                                    const dropEvent = new DragEvent('drop', {
                                        dataTransfer: dataTransfer,
                                        bubbles: true
                                    });
                                    uploadArea.dispatchEvent(dropEvent);

                                    // 同时触发change事件
                                    const input = document.querySelector('input[type="file"]');
                                    if (input) {
                                        input.files = dataTransfer.files;
                                        const changeEvent = new Event('change', { bubbles: true });
                                        input.dispatchEvent(changeEvent);
                                    }
                                }
                            }''', [list(file_data), os.path.basename(cover_path)])

                            print(f"✓ 已通过拖放方式上传封面图片: {os.path.basename(cover_path)}")
                            file_uploaded = True
                    except Exception as e:
                        print(f"拖放上传失败: {e}")

                if not file_uploaded:
                    print("⚠ 所有上传方法都失败了")
        else:
            print(f"⚠ 未找到封面文件，将使用默认封面")

        # 等待封面上传和处理完成
        time.sleep(3)

        # 点击确认按钮以完成封面选择
        print("点击封面确认按钮...")

        # 使用您提供的确认按钮XPath
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
            if safe_click(page2.locator(f'xpath={selector}'), "封面确认按钮"):
                print("✓ 已确认封面选择")
                confirm_clicked = True
                break

        if not confirm_clicked:
            print("⚠ 未找到封面确认按钮")

    except Exception as e:
        print(f"⚠ 封面上传过程中出错: {e}")

    # 等待封面选择完成
    time.sleep(2)

    # 11. 填写主角名
    character_short = main_character[:5] if len(main_character) >= 5 else main_character
    safe_fill(page2.locator('xpath=//*[@id="roleList"]/div/div/div[1]/span/span/input'), character_short, "主角名")

    # 12. 填写作品简介
    synopsis_short = formatted_synopsis[:500] if len(formatted_synopsis) >= 500 else formatted_synopsis
    safe_fill(page2.locator('xpath=//*[@id="descRow_input"]/div/div/textarea'), synopsis_short, "作品简介")

    # 13. 立即创建
    safe_click(page2.locator('xpath=//*[@id="app"]/div/div[2]/div[2]/div[2]/div[2]/button[2]/span'), "立即创建")
    print("✓ 提交创建书籍")

    # 等待创建完成并返回小说列表
    print("等待书籍创建完成...")
    for _ in range(10):
        # 尝试返回小说列表
        safe_click(
            page2.locator('xpath=//*[@id="app"]/div/div[2]/div[1]/div/div/div/div/div[2]/div[2]/div[1]/div/span[2]'),
            "小说标签")
        time.sleep(1)
        try:
            page2.get_by_text(title_short, exact=True).wait_for(state="visible", timeout=1000)
            return True
        except:
            pass

    return False

def scroll_and_click_enhanced(page, tab_name, target_text, max_scrolls=30, scroll_step=300):
    """
    增强版：在分类选择模态框中查找目标文本并点击
    使用更通用的选择器来适应网页结构变化
    """
    try:
        print(f"🔍 开始在'{tab_name}'标签页中查找: '{target_text}'")
        
        # 1. 首先点击对应的标签页 - 使用多种选择器
        tab_selectors = [
            f".arco-tabs-header-title:has-text('{tab_name}')",
            f"//span[contains(text(), '{tab_name}')]",
            f"[class*='tabs'] span:has-text('{tab_name}')",
            f"div[class*='tab'] span:has-text('{tab_name}')"
        ]
        
        tab_clicked = False
        for selector in tab_selectors:
            try:
                if selector.startswith('//'):
                    tab_element = page.locator(f'xpath={selector}')
                else:
                    tab_element = page.locator(selector)
                
                if tab_element.count() > 0:
                    tab_element.first.click()
                    page.wait_for_timeout(800)  # 等待标签页切换动画
                    tab_clicked = True
                    print(f"✅ 成功点击标签页: {tab_name}")
                    break
            except Exception as e:
                continue
        
        if not tab_clicked:
            print(f"❌ 无法点击标签页: {tab_name}")
            return False
        
        # 2. 定位滚动容器 - 使用多种选择器
        scroll_selectors = [
            ".arco-tabs-content-item-active .category-choose-scroll-parent",
            ".arco-tabs-content-item-active [class*='scroll']",
            ".arco-tabs-content-item-active div[class*='content']",
            "[class*='tabs-content'] [class*='scroll']",
            "[class*='category'] [class*='scroll']",
            ".arco-modal-body [class*='scroll']"
        ]
        
        scrollable = None
        for selector in scroll_selectors:
            try:
                element = page.locator(selector)
                if element.count() > 0:
                    scrollable = element.first
                    print(f"✅ 找到滚动容器: {selector}")
                    break
            except Exception as e:
                continue
        
        if scrollable is None:
            print(f"❌ 未找到滚动容器，尝试全局搜索")
            # 如果找不到特定的滚动容器，尝试在整个模态框中搜索
            scrollable = page.locator(".arco-modal-body").first
            if scrollable.count() == 0:
                scrollable = page.locator("body").first
        
        # 3. 将鼠标悬停在滚动区域上
        try:
            scrollable.hover(timeout=3000)
        except:
            print(f"⚠️ 无法悬停在滚动区域，继续尝试")
        
        # 4. 循环查找和滚动 - 使用多种目标选择器
        target_selectors = [
            f".category-choose-item:has-text('{target_text}')",
            f"[class*='category-item']:has-text('{target_text}')",
            f"[class*='choose-item']:has-text('{target_text}')",
            f"div:has-text('{target_text}')",
            f"span:has-text('{target_text}')",
            f"//*[contains(text(), '{target_text}')]"
        ]
        
        for i in range(max_scrolls):
            # 尝试多种目标选择器
            for target_selector in target_selectors:
                try:
                    if target_selector.startswith('//'):
                        target = scrollable.locator(f'xpath={target_selector}')
                    else:
                        target = scrollable.locator(target_selector)
                    
                    if target.count() > 0:
                        # 检查元素是否可见和可点击
                        for j in range(target.count()):
                            element = target.nth(j)
                            if element.is_visible() and element.is_enabled():
                                element_text = element.text_content().strip()
                                if target_text in element_text:
                                    print(f"✅ 在'{tab_name}'标签页找到目标: {element_text}")
                                    # 滚动到元素并点击
                                    element.scroll_into_view_if_needed()
                                    page.wait_for_timeout(300)
                                    element.click()
                                    page.wait_for_timeout(500)  # 等待点击响应
                                    return True
                except Exception as e:
                    continue
            
            # 使用鼠标滚轮滚动
            try:
                page.mouse.wheel(0, scroll_step)
                page.wait_for_timeout(400)
            except Exception as e:
                # 如果鼠标滚轮失败，尝试JavaScript滚动
                try:
                    page.evaluate("() => window.scrollBy(0, 300)")
                    page.wait_for_timeout(400)
                except:
                    pass
            
            # 检查是否到达底部
            if i % 5 == 0:
                try:
                    scroll_height = page.evaluate("() => document.body.scrollHeight")
                    current_scroll = page.evaluate("() => window.pageYOffset")
                    viewport_height = page.evaluate("() => window.innerHeight")
                    
                    if current_scroll + viewport_height >= scroll_height - 100:
                        print(f"🟡 已滚动到底部，停止滚动")
                        break
                except:
                    pass

        print(f"🟡 在'{tab_name}'标签页滚动{max_scrolls}次后未找到: '{target_text}'")
        return False

    except Exception as e:
        print(f"✗ 在'{tab_name}'标签页操作'{target_text}'时发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

# 使用示例
def select_categories(page):
    """选择分类的完整流程"""
    
    # 选择主题
    scroll_and_click_enhanced(page, "主题", "系统")
    
    # 选择角色  
    scroll_and_click_enhanced(page, "角色", "天才")
    
    # 选择情节
    scroll_and_click_enhanced(page, "情节", "重生")

import time

def scroll_and_click(page, idx, scroll_selector, target_text, max_scrolls=30, scroll_step=300):
    """
    自动在滚动容器中查找目标文本并点击。
    使用更健壮的选择器和错误处理。
    找不到或发生任何错误时，会安全退出并返回 False。
    """
    try:
        print(f"🔍 在滚动容器 {idx} 中查找目标: '{target_text}'")
        
        # 尝试找到滚动容器
        scrollable = None
        try:
            scrollable = page.locator(scroll_selector).nth(idx)
            if scrollable.count() == 0:
                print(f"⚠️ 指定索引 {idx} 的滚动容器不存在，尝试第一个")
                scrollable = page.locator(scroll_selector).first
                if scrollable.count() == 0:
                    print(f"❌ 未找到任何滚动容器: {scroll_selector}")
                    return False
        except Exception as e:
            print(f"⚠️ 定位滚动容器失败，尝试全局搜索: {e}")
            # 回退到全局搜索
            global_selectors = [
                ".arco-modal-body",
                "[class*='scroll']",
                "[class*='content']",
                "body"
            ]
            for selector in global_selectors:
                try:
                    scrollable = page.locator(selector).first
                    if scrollable.count() > 0:
                        print(f"✅ 找到备用滚动容器: {selector}")
                        break
                except:
                    continue
            
            if scrollable is None or scrollable.count() == 0:
                print(f"❌ 无法找到任何可用的滚动容器")
                return False
        
        # 尝试悬停以激活滚动区域
        try:
            scrollable.hover(timeout=3000)
            print("✅ 成功悬停在滚动区域")
        except Exception as e:
            print(f"⚠️ 无法悬停在滚动区域，继续尝试: {e}")

        # 循环查找和滚动 - 使用多种目标选择器
        target_selectors = [
            f".category-choose-item:has-text('{target_text}')",
            f"[class*='category-item']:has-text('{target_text}')",
            f"[class*='choose-item']:has-text('{target_text}')",
            f"div:has-text('{target_text}')",
            f"span:has-text('{target_text}')",
            f"//*[contains(text(), '{target_text}')]"
        ]
        
        for i in range(max_scrolls):
            # 尝试多种目标选择器
            for target_selector in target_selectors:
                try:
                    if target_selector.startswith('//'):
                        target = scrollable.locator(f'xpath={target_selector}')
                    else:
                        target = scrollable.locator(target_selector)
                    
                    if target.count() > 0:
                        # 检查元素是否可见和可点击
                        for j in range(target.count()):
                            element = target.nth(j)
                            if element.is_visible() and element.is_enabled():
                                element_text = element.text_content().strip()
                                if target_text in element_text:
                                    print(f"✅ 找到目标: {element_text}")
                                    # 滚动到元素并点击
                                    element.scroll_into_view_if_needed()
                                    page.wait_for_timeout(300)
                                    element.click()
                                    page.wait_for_timeout(500)  # 等待点击响应
                                    return True
                except Exception as e:
                    continue
            
            # 改进滚动方式 - 尝试多种滚动方法
            scroll_success = False
            try:
                # 方法1: 鼠标滚轮
                page.mouse.wheel(0, scroll_step)
                scroll_success = True
            except:
                try:
                    # 方法2: JavaScript滚动
                    page.evaluate(f"() => window.scrollBy(0, {scroll_step})")
                    scroll_success = True
                except:
                    try:
                        # 方法3: 滚动容器的scrollTop
                        scrollable.evaluate(f"(element) => {{ element.scrollTop += {scroll_step}; }}")
                        scroll_success = True
                    except:
                        pass
            
            if scroll_success:
                page.wait_for_timeout(400)  # 等待滚动动画和可能的懒加载
            else:
                print(f"⚠️ 所有滚动方法都失败，停止滚动")
                break

            # 检查是否到达底部
            if i % 5 == 0:
                try:
                    scroll_height = page.evaluate("() => document.body.scrollHeight")
                    current_scroll = page.evaluate("() => window.pageYOffset")
                    viewport_height = page.evaluate("() => window.innerHeight")
                    
                    if current_scroll + viewport_height >= scroll_height - 100:
                        print(f"🟡 已滚动到底部，停止滚动")
                        break
                except:
                    pass

        # 如果循环完成仍未找到
        print(f"🟡 在滚动 {max_scrolls} 次后，未找到目标: '{target_text}'")
        return False

    except Exception as e:
        print(f"✗ 在操作 '{target_text}' 时发生错误，已跳过。错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def save_publish_progress2(novel_title: str, published_chapters: list, total_content_len: int, base_chapter_num: int,
                           book_created: bool):
    """
    保存发布进度，包括每章的详细定时信息（target_date, target_time, time_slot_index）
    支持多本小说，进度保存在同一个进度文件中，以小说标题为键区分。

    参数:
    - novel_title (str): 小说标题
    - published_chapters (list): 已发布章节的详细信息列表，每个元素是一个字典，包含：
        - 'file': 章节文件路径
        - 'chap_num': 章节编号
        - 'chap_title': 章节标题
        - 'chap_content': 章节内容
        - 'chap_len': 章节字数
        - 'target_date': 发布日期（'YYYY-MM-DD'）
        - 'target_time': 发布时间（'HH:MM'），来自 novel_publish_times
        - 'time_slot_index': 当天该 target_time 是第几次被使用（例如，1 或 2）
    - total_content_len (int): 总发布字数
    - base_chapter_num (int): 基准章节号
    - book_created (bool): 书籍是否已创建
    """
    progress_file = CONFIG["progress2_file"]

    # 确保目录存在
    ensure_directory_exists(os.path.dirname(progress_file) if os.path.dirname(progress_file) else ".")

    # 加载现有进度
    all_progress = {}
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                all_progress = json.load(f)
        except Exception as e:
            print(f"加载进度文件时出错: {e}")
            all_progress = {}

    # 更新当前小说的进度
    all_progress[novel_title] = {
        "published_chapters": published_chapters,  # 每个元素是一个包含详细定时信息的字典
        "total_content_len": total_content_len,
        "base_chapter_num": base_chapter_num,  # 保存基准章节号
        "book_created": book_created,  # 保存书籍创建状态
        "last_update": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }

    # 保存进度
    try:
        with open(progress_file, 'w', encoding='utf-8') as f:
            json.dump(all_progress, f, ensure_ascii=False, indent=2)
        print(f"✓ 发布进度（详细）已保存: {progress_file}")
    except Exception as e:
        print(f"✗ 保存发布进度（详细）时出错: {e}")


def load_publish_progress2(novel_title: str) -> dict:
    """
    加载发布进度，包括每章的详细定时信息（target_date, target_time, time_slot_index）
    支持多本小说，从同一个进度文件中根据小说标题加载对应的进度信息。

    参数:
    - novel_title (str): 小说标题

    返回:
    - dict: 包含以下键的进度数据：
        - 'novel_title': 小说标题
        - 'published_chapters': 已发布章节的详细信息列表，每个元素是一个字典，包含：
            - 'file': 章节文件路径
            - 'chap_num': 章节编号
            - 'chap_title': 章节标题
            - 'chap_content': 章节内容
            - 'chap_len': 章节字数
            - 'target_date': 发布日期（'YYYY-MM-DD'）
            - 'target_time': 发布时间（'HH:MM'），来自 novel_publish_times
            - 'time_slot_index': 当天该 target_time 是第几次被使用（例如，1 或 2）
        - 'total_content_len': 总发布字数
        - 'base_chapter_num': 基准章节号
        - 'book_created': 书籍是否已创建
        - 'last_update': 最后更新时间
    """
    progress_file = CONFIG["progress2_file"]

    # 确保目录存在
    ensure_directory_exists(os.path.dirname(progress_file) if os.path.dirname(progress_file) else ".")

    # 默认进度数据
    progress_data = {
        "novel_title": novel_title,
        "published_chapters": [],  # 每个元素是一个包含详细定时信息的字典
        "total_content_len": 0,
        "base_chapter_num": 0,  # 保存基准章节号
        "book_created": False,  # 保存书籍创建状态
        "last_update": None
    }

    # 如果进度文件存在，尝试加载
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                all_progress = json.load(f)
                if novel_title in all_progress:
                    progress_data = all_progress[novel_title]
                else:
                    print(f"未找到小说《{novel_title}》的进度信息，将使用默认进度。")
        except Exception as e:
            print(f"加载进度文件时出错: {e}")

    # 确保 published_chapters 是一个列表
    if "published_chapters" not in progress_data:
        progress_data["published_chapters"] = []

    return progress_data


def publish_novel(page2, json_file):
    """发布单个小说"""
    print(f"\n处理小说项目: {os.path.basename(json_file)}")

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # 适配不同的JSON结构
    if 'novel_info' in data:
        novel_info = data['novel_info']
    elif 'project_info' in data:
        novel_info = data['project_info']
    else:
        print("❌ 未找到小说信息字段")
        return False
    
    novel_title = novel_info['title']
    novel_synopsis = novel_info.get('synopsis', '')
    
    # 处理角色信息
    main_character = "未知主角"
    if 'character_design' in data and 'main_character' in data['character_design']:
        main_character = data['character_design']['main_character'].get('name', '未知主角')
    elif 'characters' in data and 'protagonist' in data['characters']:
        main_character = data['characters']['protagonist'].get('name', '未知主角')

    print(f"小说名称: {novel_title}")
    print(f"主角: {main_character}")

    # 优化简介排版 - 传入完整的data以便提取标签和核心卖点
    formatted_synopsis = format_synopsis_for_fanqie(novel_synopsis, data)
    print("优化后的简介:")
    print(formatted_synopsis)
    print("-" * 50)

    # 加载发布进度，使用 load_publish_progress2
    progress = load_publish_progress2(novel_title)

    # 确保 published_chapters 是一个列表，且每个元素是一个字典
    published_chapters = progress.get("published_chapters", [])

    total_content_len = progress.get("total_content_len", 0)
    base_chapter_num = progress.get("base_chapter_num", 0)
    book_created = progress.get("book_created", False)

    # 修复逻辑：如果书籍未创建，直接创建新书，不尝试寻找已存在的书籍
    if not book_created:
        print("书籍未创建，开始创建新书...")
        if create_new_book(page2, novel_title, formatted_synopsis, main_character, data):
            # 标记书籍已创建
            book_created = True
            progress["book_created"] = book_created
            progress["total_content_len"] = total_content_len
            progress["base_chapter_num"] = base_chapter_num
            save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num, book_created)
            print(f"✓ 书籍《{novel_title}》创建成功")

            # 导航到新创建的书籍
            if not navigate_to_correct_book(page2, novel_title):
                print(f"✗ 无法导航到新创建的书籍《{novel_title}》")
                return False
        else:
            print(f"✗ 书籍《{novel_title}》创建失败")
            return False
    else:
        # 书籍已创建，直接导航到正确的书籍
        print("书籍已创建，导航到书籍详情页...")
        if not navigate_to_correct_book(page2, novel_title):
            # 如果导航失败，尝试重新寻找
            print("导航失败，尝试重新寻找书籍...")
            book_found = find_existing_book_in_list(page2, novel_title)

            if book_found:
                print(f"✓ 重新找到书籍《{novel_title}》")
                # 再次尝试导航
                if not navigate_to_correct_book(page2, novel_title):
                    print(f"✗ 仍然无法导航到书籍《{novel_title}》")
                    return False
            else:
                # 如果没有找到现有书籍，创建新书
                print(f"未找到现有书籍《{novel_title}》，将创建新书...")
                if create_new_book(page2, novel_title, formatted_synopsis, main_character, data):
                    book_created = True
                    progress["book_created"] = book_created
                    progress["total_content_len"] = total_content_len
                    progress["base_chapter_num"] = base_chapter_num
                    save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num,
                                          book_created)
                    print(f"✓ 书籍《{novel_title}》创建成功")

                    if not navigate_to_correct_book(page2, novel_title):
                        print(f"✗ 无法导航到新创建的书籍《{novel_title}》")
                        return False
                else:
                    print(f"✗ 书籍《{novel_title}》创建失败")
                    return False

    # 等待页面完全加载
    print("等待书籍详情页完全加载...")
    try:
        page2.wait_for_load_state("networkidle")
        time.sleep(2)
    except Exception as e:
        print(f"等待页面加载时出错: {e}")

    # 查找章节文件 - 适配现有目录结构
    # 首先尝试标准的"小说名_章节"目录
    chapter_path = os.path.join(CONFIG["novel_path"], f"{novel_title}_章节")
    if not os.path.exists(chapter_path):
        # 如果不存在，尝试"小说名/chapters"目录结构
        chapter_path = os.path.join(CONFIG["novel_path"], novel_title, "chapters")
        if not os.path.exists(chapter_path):
            print(f"章节目录不存在: {chapter_path}")
            print("请确保章节文件位于正确的目录中")
            return False
    print(f"✓ 找到章节目录: {chapter_path}")

    # 获取章节文件
    chapter_files = []
    for filename in os.listdir(chapter_path):
        if filename.endswith('.txt'):
            chapter_files.append(os.path.join(chapter_path, filename))

    # 验证并修复章节文件（包括重复问题）
    valid_chapter_files = validate_and_fix_chapter_files(chapter_files, novel_title)
    chapter_files_sorted = sort_files_by_chapter(valid_chapter_files)

    if not chapter_files_sorted:
        print("未找到章节文件")
        return False

    print(f"找到 {len(chapter_files_sorted)} 个章节")

    # 发布章节
    total_content_len = progress.get("total_content_len", 0)
    base_chapter_num = progress.get("base_chapter_num", 0)
    today = datetime.now().date()

    published_count = len(published_chapters)
    print(f"检测到已发布 {published_count} 章，将从第 {published_count + 1} 章继续...")

    if base_chapter_num > 0:
        print(f"基准章节号: 第 {base_chapter_num} 章 (从这一章开始定时发布)")

    # 章节发布信息，用于跟踪分配情况
    chapter_publish_info = []
    for chap_index, chapter_file in enumerate(chapter_files_sorted):
        # 检查章节是否已经发布
        is_published = False
        for pub_chap in published_chapters:
            if pub_chap['file'] == chapter_file:
                is_published = True
                break
        if is_published:
            chapter_publish_info.append({
                'file': chapter_file,
                'chap_num': str(pub_chap.get('chap_num', '0')),
                'chap_title': pub_chap.get('chap_title', ''),
                'chap_content': pub_chap.get('chap_content', ''),
                'chap_len': pub_chap.get('chap_len', 0),
                'index': chap_index,
                'published': True,
                'target_date': pub_chap.get('target_date', ''),
                'target_time': pub_chap.get('target_time', ''),
                'time_slot_index': pub_chap.get('time_slot_index', 0)
            })
            continue

        with open(chapter_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 修复中文引号问题 - 更全面的处理
            # 先将JSON字符串中的中文引号转义，然后统一处理
            content = content.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
            chapter_data = json.loads(content)

        chap_num = str(chapter_data['chapter_number'])
        chap_title = chapter_data['chapter_title']
        chap_content = chapter_data['content']
        chap_len = count_content_chars(chap_content)

        chapter_publish_info.append({
            'file': chapter_file,
            'chap_num': chap_num,
            'chap_title': chap_title,
            'chap_content': chap_content,
            'chap_len': chap_len,
            'index': chap_index,
            'published': False,
            'target_date': '',
            'target_time': '',
            'time_slot_index': 0
        })

    # 按原始顺序处理章节
    current_chapter_index = 0
    total_chapters = len(chapter_publish_info)

    # ===============================
    # 关键修改点 1：获取当前日期和时间，仅一次，在进入定时发布逻辑之前
    # ===============================
    now = datetime.now()  # 仅获取一次，后续不再修改
    current_date = now.date()
    current_time = now.time()
    # ===============================
    # 关键修改点 1 结束
    # ===============================

    # ===============================
    # 关键修改点 2：重新设计状态恢复逻辑，严格遵循 time_slot_index
    # ===============================
    # 检查是否需要恢复定时发布状态
    if published_chapters and total_content_len >= WORD_COUNT_THRESHOLD:
        # 找到最后一个设置了定时的章节
        timed_chapters = [chap for chap in published_chapters
                          if chap.get('target_date') and chap.get('target_time')]

        if timed_chapters:
            last_timed_chapter = timed_chapters[-1]
            last_date_str = last_timed_chapter.get('target_date', '')
            last_time_str = last_timed_chapter.get('target_time', '')
            last_slot_index = last_timed_chapter.get('time_slot_index', 0)

            if last_date_str and last_time_str:
                try:
                    # 解析最后发布日期和时间
                    last_datetime = datetime.strptime(f"{last_date_str} {last_time_str}", "%Y-%m-%d %H:%M")
                    last_date = last_datetime.date()

                    # 根据 time_slot_index 决定下一步操作
                    if last_slot_index < CHAPTERS_PER_TIME_SLOT:
                        # 当前时间点还有空位，继续使用相同的日期和时间
                        current_date = last_date
                        current_time = datetime.strptime(last_time_str, "%H:%M").time()
                        print(
                            f"✓ 恢复状态: 继续使用 {current_date} {current_time.strftime('%H:%M')} 的第 {last_slot_index + 1} 个位置")
                    else:
                        # 当前时间点已满，需要移动到下一个时间点
                        time_index = novel_publish_times.index(last_time_str)
                        if time_index + 1 < len(novel_publish_times):
                            # 同一天的下一个时间点
                            next_time_str = novel_publish_times[time_index + 1]
                            current_date = last_date
                            current_time = datetime.strptime(next_time_str, "%H:%M").time()
                            print(
                                f"✓ 恢复状态: 时间点已满，移动到同一天的下一个时间点 {current_date} {current_time.strftime('%H:%M')}")
                        else:
                            # 需要到下一天的第一个时间点
                            current_date = last_date + timedelta(days=1)
                            current_time = datetime.strptime(novel_publish_times[0], "%H:%M").time()
                            print(
                                f"✓ 恢复状态: 当天时间点已满，移动到下一天 {current_date} {current_time.strftime('%H:%M')}")

                    # 验证恢复的时间是否有效（不能早于当前时间）
                    restored_datetime = datetime.combine(current_date, current_time)
                    if restored_datetime <= now:
                        print(f"⚠️  恢复的时间 {current_date} {current_time.strftime('%H:%M')} 已过期，使用当前时间")
                        current_date = now.date()
                        current_time = now.time()

                except Exception as e:
                    print(f"恢复定时发布状态时出错: {e}, 将使用当前时间")
                    current_date = now.date()
                    current_time = now.time()
    # ===============================
    # 关键修改点 2 结束
    # ===============================

    while current_chapter_index < total_chapters:
        current_chapter = chapter_publish_info[current_chapter_index]

        # 跳过已发布的章节
        if current_chapter['published']:
            print(f"跳过已发布章节: {os.path.basename(current_chapter['file'])}")
            current_chapter_index += 1
            continue

        # 检查累计字数是否达到阈值
        if total_content_len < WORD_COUNT_THRESHOLD:
            print(
                f"当前累计字数 {total_content_len} 小于 {WORD_COUNT_THRESHOLD}，跳过章节 {current_chapter['chap_num']} 的定时发布设置")
            # 直接发布章节但不设置定时
            # 检查页面状态，如果页面失效则重新连接
            if not check_and_recover_page(page2):
                print("页面已失效，无法继续发布")
                break

            print(
                f"\n发布第 {current_chapter['chap_num']} 章: {current_chapter['chap_title']} (字数: {current_chapter['chap_len']}) - 不设置定时")

            # 发布章节（不设置定时）
            result = publish_chapter_with_retry(page2, current_chapter['chap_num'], current_chapter['chap_title'],
                                                current_chapter['chap_content'], None, None, novel_title)
            if result == 0:
                total_content_len += current_chapter['chap_len']
                # 标记章节为已发布，并更新基准章节号（如果需要）
                progress["total_content_len"] = total_content_len
                # 保存进度（暂时不保存章节详细信息）
                save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num,
                                      book_created)
                print(f"✓ 发布成功 (累计字数: {total_content_len})")

                # 标记为已发布
                current_chapter['published'] = True
                # 保存章节详细信息（无定时信息）
                current_chapter.update({
                    'target_date': '',
                    'target_time': '',
                    'time_slot_index': 0
                })
                published_chapters.append(current_chapter.copy())
                save_publish_progress(novel_title, published_chapters, total_content_len, base_chapter_num,
                                      book_created)

                # 检查是否已完成所有章节发布
                current_published_count = len(published_chapters)
                if check_if_novel_completed(json_file, current_published_count):
                    print(f"🎉 小说《{novel_title}》已完成所有章节发布!")
                    if move_completed_novel_to_published(novel_title, json_file):
                        return True
            else:
                print("✗ 发布失败")
                wait_for_enter("发布失败，按回车继续下一章...", timeout=10)

            current_chapter_index += 1
            continue

        # 累计字数达到阈值后，开始设置定时发布
        print(f"累计字数已达 {total_content_len}，超过阈值 {WORD_COUNT_THRESHOLD}，开始设置定时发布")

        # ===============================
        # 定时发布逻辑开始
        # ===============================
        # 初始化当前日期的变量（已在外部获取，不再更改）
        # current_date 和 current_time 已经被获取且不会被修改

        # ===============================
        # 关键修改点 3：重新设计定时发布循环，严格遵循 time_slot_index 逻辑
        # ===============================
        # 初始化时间点使用情况跟踪
        date_time_slot_usage = {}  # 格式: {date: {time: count}}

        # 首先，从已发布的章节中恢复时间点使用情况
        for chap in published_chapters:
            if chap.get('target_date') and chap.get('target_time'):
                date = chap['target_date']
                time_slot = chap['target_time']
                if date not in date_time_slot_usage:
                    date_time_slot_usage[date] = {}
                if time_slot not in date_time_slot_usage[date]:
                    date_time_slot_usage[date][time_slot] = 0
                date_time_slot_usage[date][time_slot] += 1

        # 主发布循环
        while current_chapter_index < total_chapters:
            current_chapter = chapter_publish_info[current_chapter_index]
            if current_chapter['published']:
                current_chapter_index += 1
                continue

            # 检查累计字数是否仍然超过阈值
            if total_content_len < WORD_COUNT_THRESHOLD:
                print(f"当前累计字数 {total_content_len} 小于 {WORD_COUNT_THRESHOLD}，退出定时发布逻辑")
                break

            # 查找可用的时间点
            found_available_slot = False
            temp_date = current_date
            temp_time = current_time

            # 在多个日期中查找可用时间点
            for day_offset in range(30):  # 最多查找30天
                search_date = current_date + timedelta(days=day_offset)
                date_str = search_date.strftime('%Y-%m-%d')

                # 初始化该日期的时间点使用情况
                if date_str not in date_time_slot_usage:
                    date_time_slot_usage[date_str] = {}

                # 检查该日期的每个时间点
                for time_slot in novel_publish_times:
                    # 获取该时间点的当前使用计数
                    current_count = date_time_slot_usage[date_str].get(time_slot, 0)

                    # 检查是否还有空位
                    if current_count < CHAPTERS_PER_TIME_SLOT:
                        # 验证时间是否有效
                        slot_datetime = datetime.strptime(f"{date_str} {time_slot}", "%Y-%m-%d %H:%M")
                        if slot_datetime > now + timedelta(minutes=PUBLISH_BUFFER_MINUTES):
                            # 找到可用时间点
                            current_date = search_date
                            current_time = datetime.strptime(time_slot, "%H:%M").time()
                            found_available_slot = True
                            break

                if found_available_slot:
                    break

            if not found_available_slot:
                print("✗ 在30天内未找到可用的发布时间点")
                break

            # 发布当前章节到找到的时间点
            chap_file = current_chapter['file']
            chap_num = current_chapter['chap_num']
            chap_title = current_chapter['chap_title']
            chap_content = current_chapter['chap_content']
            chap_len = current_chapter['chap_len']

            # 检查页面状态
            if not check_and_recover_page(page2):
                print("页面已失效，无法继续发布")
                return False

            target_date = current_date.strftime('%Y-%m-%d')
            target_time = current_time.strftime('%H:%M')

            # 获取当前时间点的使用计数
            current_count = date_time_slot_usage.get(target_date, {}).get(target_time, 0)
            time_slot_index = current_count + 1

            print(f"\n发布第 {chap_num} 章: {chap_title} (字数: {chap_len})")
            print(f"定时发布: {target_date} {target_time} (第 {time_slot_index} 个位置)")

            # 发布章节
            result = publish_chapter_with_retry(page2, chap_num, chap_title, chap_content,
                                                target_date, target_time, novel_title)
            if result == 0:
                total_content_len += chap_len
                # 更新进度
                current_chapter.update({
                    'published': True,
                    'target_date': target_date,
                    'target_time': target_time,
                    'time_slot_index': time_slot_index
                })
                published_chapters.append(current_chapter.copy())
                save_publish_progress2(novel_title, published_chapters, total_content_len, base_chapter_num,
                                       book_created)
                print(f"✓ 发布成功 (累计字数: {total_content_len})")

                # 更新时间点使用计数
                if target_date not in date_time_slot_usage:
                    date_time_slot_usage[target_date] = {}
                date_time_slot_usage[target_date][target_time] = time_slot_index

                # 检查是否已完成所有章节发布
                current_published_count = len(published_chapters)
                if check_if_novel_completed(json_file, current_published_count):
                    print(f"🎉 小说《{novel_title}》已完成所有章节发布!")
                    if move_completed_novel_to_published(novel_title, json_file):
                        return True
            else:
                print("✗ 发布失败")
                wait_for_enter("发布失败，按回车继续下一章...", timeout=10)

            current_chapter_index += 1
        # ===============================
        # 关键修改点 3 结束
        # ===============================

    print(f"\n✓ 小说《{novel_title}》发布完成，共 {len(chapter_files_sorted)} 章，总字数 {total_content_len}")
    return True


def main_scan_cycle():
    """主扫描循环 - 修改：在发布小说前先检查签约管理"""
    print("=== 番茄小说自动发布程序 - 扫描模式 ===")
    print(f"扫描间隔: {CONFIG['scan_interval']} 秒")

    # 确保小说项目目录存在
    ensure_directory_exists(CONFIG["novel_path"])
    print(f"小说项目目录: {os.path.abspath(CONFIG['novel_path'])}")

    # 连接浏览器
    playwright, browser, page1, default_context = connect_to_browser()
    if not browser or not page1 or not default_context:
        print("❌ 浏览器连接失败，等待下次扫描")
        print("💡 请确保:")
        print("   1. Chrome浏览器已安装")
        print("   2. 运行: python fanqie_browser_launcher.py")
        print("   3. 检查防火墙设置")
        return False

    print("✅ 浏览器连接成功，开始页面管理...")
    
    # 获取当前 context 下所有页面
    try:
        pages = default_context.pages
        pages_count = len(pages)
        print(f"📄 发现 {pages_count} 个浏览器页面")
        
        for idx, page in enumerate(pages):
            try:
                url = page.url
                print(f"  页面 {idx + 1}: {url}")
                if url != 'https://fanqienovel.com/':
                    if pages_count != 1:
                        print(f"  🔒 关闭非番茄页面: {url}")
                        page.close()
                else:
                    print(f"  ✅ 保留番茄页面: {url}")
                    page1 = page
            except Exception as e:
                print(f"  ❌ 关闭页面 {idx + 1} 时出错: {e}")
    except Exception as e:
        print(f"❌ 页面管理失败: {e}")
        # 如果页面管理失败，但浏览器连接正常，继续使用现有页面
        print("⚠️ 使用现有页面继续...")

    # 确保在番茄小说页面
    try:
        current_url = page1.url
        print(f"📍 当前页面: {current_url}")
        
        if current_url != 'https://fanqienovel.com/':
            print("🔄 导航到番茄小说首页...")
            page1.goto("https://fanqienovel.com/", timeout=60000)
            page1.wait_for_load_state("domcontentloaded", timeout=30000)
        
        # 检查页面标题
        page_title = page1.title()
        print(f"📄 页面标题: {page_title}")
        
        if '番茄小说' not in page_title:
            print("⚠️ 当前页面可能不是番茄小说，但继续尝试...")
            print("🔄 强制导航到番茄小说...")
            page1.goto("https://fanqienovel.com/", timeout=60000)
            page1.wait_for_load_state("domcontentloaded", timeout=30000)
            
    except Exception as e:
        print(f"❌ 页面导航失败: {e}")
        print("💡 尝试刷新页面...")
        try:
            page1.reload()
            page1.wait_for_load_state("domcontentloaded", timeout=30000)
        except Exception as reload_error:
            print(f"❌ 页面刷新也失败: {reload_error}")
            print("🚨 无法继续，关闭浏览器连接")
            try:
                browser.close()
                if playwright:
                    playwright.stop()
            except:
                pass
            return False

    # 导航到作家专区
    print("🎯 开始导航到作家专区...")
    page2 = navigate_to_writer_platform(page1, default_context)
    if not page2:
        print("❌ 导航到作家专区失败")
        print("🔄 尝试返回番茄小说首页...")
        try:
            if page1:
                page1.goto("https://fanqienovel.com/", timeout=30000)
        except:
            pass
        
        print("🧹 清理浏览器连接...")
        try:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
        except:
            pass
        return False

    # 检查小说项目
    print("=" * 50)
    print("📚 小说项目检查")
    print("=" * 50)
    
    json_files = list_json_files(CONFIG["novel_path"])
    if not json_files:
        print(f"❌ 在目录 '{CONFIG['novel_path']}' 中未找到小说项目文件")
        print(f"💡 请确保您的JSON文件命名以 '{CONFIG['required_json_suffix']}' 结尾")
        print("📁 示例文件名: '我的小说_项目信息.json'")
        
        # 询问是否继续
        continue_scan = input("是否继续完成环境检查然后退出? (y/n): ").strip().lower()
        if continue_scan not in ['y', 'yes']:
            browser.close()
            playwright.stop()
            return False
    else:
        print(f"✅ 找到 {len(json_files)} 个小说项目:")
        for file_index, json_file in enumerate(json_files):
            file_name = os.path.basename(json_file)
            print(f"   {file_index + 1}. {file_name}")

    # 环境就绪确认
    print("=" * 50)
    print("🎯 环境就绪确认")
    print("=" * 50)
    print("✅ 浏览器连接: 成功")
    print("✅ 番茄小说页面: 已进入")
    print("✅ 登录状态: 用户确认")
    print(f"✅ 作家专区: 已进入" if page2 else "❌ 作家专区: 未进入")
    
    if json_files:
        print(f"✅ 小说项目: {len(json_files)} 个")
        print()
        
        # 自动执行发布流程，无需用户选择
        print("🚀 自动开始执行发布流程...")
        
        # 初始化 success_count 变量，确保在任何情况下都有定义
        success_count = 0
        
        # 处理每个小说项目
        for file_index, json_file in enumerate(json_files):
            print(f"\n{'=' * 50}")
            print(f"📖 处理第 {file_index + 1} 个小说项目")

            try:
                if publish_novel(page2, json_file):
                    success_count += 1
                    print(f"✅ 小说项目 {file_index + 1} 处理成功")
                else:
                    print(f"❌ 小说项目 {file_index + 1} 处理失败")
            except Exception as e:
                print(f"❌ 处理小说项目时出错: {e}")
                continue

        print(f"\n{'=' * 50})
        print(f"📊 发布完成！成功处理 {success_count}/{len(json_files)} 个小说项目")

        # 签约管理功能已禁用
        print("=" * 50)
        print("📋 签约管理检查 [已禁用]")
        print("=" * 50)
        print("ℹ️ 签约管理功能已被禁用，跳过签约检查流程")
        # try:
        #     contract_manager = ContractManager(CONFIG)
        #     contract_manager.check_and_handle_recommendations(page2)
        #     contract_manager.check_and_handle_contract_management(page2)
        #     print("✅ 签约管理检查完成")
        # except Exception as e:
        #     print(f"⚠️ 签约管理检查出错: {e}")

    # 清理和退出
    print("=" * 50)
    print("🧹 清理和退出")
    print("=" * 50)
    
    try:
        if page2:
            page2.close()
            print("✅ 作家专区页面已关闭")
    except Exception as e:
        print(f"⚠️ 关闭作家专区页面时出错: {e}")
        pass
    
    # 显示当前页面状态
    try:
        if default_context:
            remaining_pages = default_context.pages
            print(f"📄 剩余浏览器页面: {len(remaining_pages)} 个")
        else:
            print("📄 无法获取页面状态")
    except Exception as e:
        print(f"⚠️ 获取页面状态时出错: {e}")
    
    # 自动关闭浏览器连接
    try:
        print("🔄 自动关闭浏览器连接...")
        try:
            if browser:
                browser.close()
            if playwright:
                playwright.stop()
            print("✅ 浏览器连接已自动关闭")
        except Exception as e:
            print(f"⚠️ 关闭浏览器连接时出错: {e}")
    except Exception as e:
        print(f"⚠️ 关闭浏览器连接时发生异常: {e}")

    return success_count > 0 if json_files else True


def main():
    """主函数 - 定时扫描模式"""
    print("=== 番茄小说自动发布程序 - 定时扫描模式 ===")
    print("程序将每小时自动扫描一次新书并发布")
    print("按 Ctrl+C 退出程序")

    scan_count = 0

    try:
        while True:
            scan_count += 1
            print(f"\n{'=' * 60}")
            print(f"开始第 {scan_count} 次扫描 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print('=' * 60)

            try:
                main_scan_cycle()
            except Exception as e:
                print(f"扫描过程中发生错误: {e}")

            # 等待下一次扫描
            print(f"\n[{datetime.now()}]#等待下一次扫描... ({CONFIG['scan_interval']} 秒后)")
            time.sleep(CONFIG["scan_interval"])

    except KeyboardInterrupt:
        print("\n\n程序被用户中断，退出...")
    except Exception as e:
        print(f"\n程序发生未知错误: {e}")


if __name__ == "__main__":
    main()
