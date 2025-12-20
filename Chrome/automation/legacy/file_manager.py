"""
番茄小说自动发布系统 - 文件管理模块
处理章节文件的验证、修复和管理
"""

import os
import json
import re
from typing import List, Dict, Any

from .config import CONFIG
from .utils import ensure_directory_exists, sort_files_by_chapter


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


def find_chapter_files(novel_title):
    """
    查找指定小说的章节文件
    """
    # 查找章节文件 - 适配现有目录结构
    # 首先尝试标准的"小说名_章节"目录
    chapter_path = os.path.join(CONFIG["novel_path"], f"{novel_title}_章节")
    if not os.path.exists(chapter_path):
        # 如果不存在，尝试"小说名/chapters"目录结构
        chapter_path = os.path.join(CONFIG["novel_path"], novel_title, "chapters")
        if not os.path.exists(chapter_path):
            print(f"章节目录不存在: {chapter_path}")
            print("请确保章节文件位于正确的目录中")
            return []
    
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
        return []

    print(f"找到 {len(chapter_files_sorted)} 个章节")
    return chapter_files_sorted


def load_chapter_data(chapter_file):
    """
    加载章节数据
    """
    try:
        with open(chapter_file, 'r', encoding='utf-8') as f:
            content = f.read()
            # 修复中文引号问题 - 更全面的处理
            # 先将JSON字符串中的中文引号转义，然后统一处理
            content = content.replace('"', '"').replace('"', '"').replace(''', "'").replace(''', "'")
            chapter_data = json.loads(content)

        return {
            'chap_num': str(chapter_data['chapter_number']),
            'chap_title': chapter_data['chapter_title'],
            'chap_content': chapter_data['content'],
            'chap_len': len(chapter_data['content'])  # 简化的字数统计
        }
    except Exception as e:
        print(f"加载章节数据失败 {chapter_file}: {e}")
        return None


def extract_novel_info_from_json(json_file):
    """
    从JSON文件中提取小说信息
    """
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 适配不同的JSON结构
        if 'novel_info' in data:
            novel_info = data['novel_info']
        elif 'project_info' in data:
            novel_info = data['project_info']
        else:
            print("❌ 未找到小说信息字段")
            return None
        
        novel_title = novel_info['title']
        novel_synopsis = novel_info.get('synopsis', '')
        
        # 处理角色信息
        main_character = "未知主角"
        if 'character_design' in data and 'main_character' in data['character_design']:
            main_character = data['character_design']['main_character'].get('name', '未知主角')
        elif 'characters' in data and 'protagonist' in data['characters']:
            main_character = data['characters']['protagonist'].get('name', '未知主角')

        return {
            'novel_title': novel_title,
            'novel_synopsis': novel_synopsis,
            'main_character': main_character,
            'full_data': data  # 返回完整数据用于后续处理
        }
    except Exception as e:
        print(f"提取小说信息失败 {json_file}: {e}")
        return None