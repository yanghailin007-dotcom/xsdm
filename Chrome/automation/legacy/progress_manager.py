"""
番茄小说自动发布系统 - 进度管理模块
处理发布进度的保存、加载和管理
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from .config import CONFIG
from .utils import ensure_directory_exists


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


def clean_novel_progress(novel_title):
    """
    清理指定小说的进度记录
    """
    progress_file = CONFIG["progress_file"]
    progress2_file = CONFIG["progress2_file"]
    
    # 清理基本进度文件
    if os.path.exists(progress_file):
        try:
            with open(progress_file, 'r', encoding='utf-8') as f:
                all_progress = json.load(f)

            if novel_title in all_progress:
                del all_progress[novel_title]

            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(all_progress, f, ensure_ascii=False, indent=2)
                
            print(f"✓ 已清理《{novel_title}》的基本进度记录")
        except Exception as e:
            print(f"清理基本进度记录时出错: {e}")

    # 清理详细进度文件
    if os.path.exists(progress2_file):
        try:
            with open(progress2_file, 'r', encoding='utf-8') as f:
                all_progress = json.load(f)

            if novel_title in all_progress:
                del all_progress[novel_title]

            with open(progress2_file, 'w', encoding='utf-8') as f:
                json.dump(all_progress, f, ensure_ascii=False, indent=2)
                
            print(f"✓ 已清理《{novel_title}》的详细进度记录")
        except Exception as e:
            print(f"清理详细进度记录时出错: {e}")


def get_all_novels_progress():
    """
    获取所有小说的进度信息
    """
    progress_file = CONFIG["progress2_file"]
    
    if not os.path.exists(progress_file):
        return {}
    
    try:
        with open(progress_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"获取所有进度信息时出错: {e}")
        return {}


def is_novel_completed(novel_title, json_file_path):
    """
    检查小说是否已完成所有章节的发布
    """
    try:
        progress_data = load_publish_progress2(novel_title)
        published_chapters = progress_data.get("published_chapters", [])
        
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否有进度信息
        if "progress" in data:
            progress = data["progress"]
            total_chapters = progress.get("total_chapters", 0)

            if total_chapters > 0 and len(published_chapters) >= total_chapters:
                return True

        return False

    except Exception as e:
        print(f"检查小说完成状态时出错: {e}")
        return False