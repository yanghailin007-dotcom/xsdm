"""
番茄小说自动发布系统 - 通用工具函数模块
包含各种通用的辅助函数
"""

import os
import re
import time
import json
import shutil
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from .config import CONFIG


def ensure_directory_exists(directory):
    """确保目录存在，如果不存在则创建"""
    if not os.path.exists(directory):
        print(f"创建目录: {directory}")
        os.makedirs(directory)
    return directory


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
    """列出指定目录下的项目信息JSON文件（支持递归查找子目录）"""
    try:
        # 确保目录存在
        directory = ensure_directory_exists(directory)

        matched_files = []
        
        # 首先在根目录查找
        for filename in os.listdir(directory):
            if filename.endswith(CONFIG["required_json_suffix"]):
                filepath = os.path.join(directory, filename)
                if os.path.isfile(filepath):
                    matched_files.append(filepath)
        
        # 然后递归查找子目录
        for item_name in os.listdir(directory):
            item_path = os.path.join(directory, item_name)
            if os.path.isdir(item_path):
                # 在子目录中查找项目文件
                for filename in os.listdir(item_path):
                    if filename.endswith(CONFIG["required_json_suffix"]):
                        filepath = os.path.join(item_path, filename)
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


def calculate_similarity(str1, str2):
    """计算两个字符串的相似度"""
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


def move_completed_novel_to_published(novel_title, json_file_path):
    """将已完成发布的小说移动到已发布目录 (已修复，可动态移动所有相关文件)"""
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


def check_if_novel_completed(json_file_path, published_chapters_count):
    """检查小说是否已完成所有章节的发布"""
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