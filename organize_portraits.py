"""
整理现有的剧照文件到视频项目目录
结构: 视频项目/{小说名}/{角色名}.png
"""
import os
import re
import shutil
import sys
from pathlib import Path

# 设置输出编码为UTF-8
if sys.stdout.encoding != 'utf-8':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')


def sanitize_path(name):
    """清理文件名，移除Windows不允许的字符"""
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '：', '、', '？', '！', '＊', '＂', '＜', '＞', '／', '＼', '｜']
    result = name
    for char in invalid_chars:
        result = result.replace(char, '_')
    return result.strip('_')


def extract_info_from_nanobanana_filename(filename):
    """从nanobanana生成的文件名中提取角色信息"""
    info = {
        'novel_title': None,
        'character_name': None,
    }

    base_name = os.path.splitext(filename)[0]

    # 提取角色名称
    match = re.search(r'角色名称([^角色定位]+)(?=角色定位|$)', base_name)
    if match:
        info['character_name'] = match.group(1).strip()

    return info


def extract_info_from_structured_filename(filename):
    """从结构化文件名中提取信息
    格式: {novel_title}_{character_name}_{type}_{timestamp}.png
    或: {novel_title}_{character_name}.png
    """
    info = {
        'novel_title': None,
        'character_name': None,
    }

    base_name = os.path.splitext(filename)[0]

    # 查找日期部分 (YYYYMMDD)
    parts = base_name.split('_')
    date_index = -1
    for i, part in enumerate(parts):
        if re.match(r'\d{8}', part):
            date_index = i
            break

    if date_index > 1:
        # 格式: novel_character_type
        info['novel_title'] = '_'.join(parts[:date_index-1])
        info['character_name'] = parts[date_index-1]
    elif len(parts) >= 2 and date_index == -1:
        # 可能是 novel_character.png 格式
        info['novel_title'] = parts[0]
        info['character_name'] = '_'.join(parts[1:])

    return info


def extract_info_from_existing_dir(dir_name):
    """从现有目录名提取信息
    格式: {小说名}_{角色名}_剧照 或类似
    """
    info = {
        'novel_title': None,
        'character_name': None,
    }

    # 移除常见的后缀
    dir_name = dir_name.replace('_portrait', '').replace('剧照', '').strip()

    # 尝试分割
    parts = dir_name.split('_')
    if len(parts) >= 2:
        # 最后部分通常是角色名
        info['character_name'] = parts[-1]
        info['novel_title'] = '_'.join(parts[:-1])

    return info


def organize_portraits():
    """整理剧照文件到正确的目录结构"""
    source_dir = Path('D:/work6.06/generated_images')
    target_base = Path('D:/work6.06/视频项目')

    # 手动映射：角色名 -> 小说名
    character_novel_mapping = {
        '林长生': '心声泄露：我成了家族老阴比',
        '林青竹': '心声泄露：我成了家族老阴比',
        '姜清歌': '吞噬万界：从一把生锈铁剑开始',
        '赤': '吞噬万界：从一把生锈铁剑开始',
    }

    if not source_dir.exists():
        print(f"源目录不存在: {source_dir}")
        return

    target_base.mkdir(exist_ok=True)

    # 首先处理 generated_images 中的文件
    png_files = list(source_dir.glob('*.png'))
    print(f"=== 处理 generated_images 目录 ===")
    print(f"找到 {len(png_files)} 个PNG文件\n")

    results = {
        'copied': 0,
        'skipped': 0,
        'error': 0
    }

    for png_file in png_files:
        filename = png_file.name
        info = None

        # 跳过非剧照文件
        if filename.startswith('portrait_') or 'test' in filename.lower():
            continue

        # 判断文件类型并提取信息
        if filename.startswith('nanobanana_'):
            info = extract_info_from_nanobanana_filename(filename)
        elif '_' in filename:
            info = extract_info_from_structured_filename(filename)

        if info and info.get('character_name'):
            character_name = info['character_name']

            # 使用映射查找小说名
            if not info.get('novel_title') and character_name in character_novel_mapping:
                info['novel_title'] = character_novel_mapping[character_name]

            novel_title = info.get('novel_title')
            if not novel_title:
                print(f"跳过 (无法确定小说): {filename}")
                results['skipped'] += 1
                continue

            # 清理路径
            safe_novel = sanitize_path(novel_title)
            safe_character = sanitize_path(character_name)

            # 目标目录: 视频项目/{小说名}/
            target_dir = target_base / safe_novel
            target_dir.mkdir(exist_ok=True)

            # 目标文件: 视频项目/{小说名}/{角色名}.png
            target_file = target_dir / f"{safe_character}.png"

            # 如果目标文件已存在，添加序号
            if target_file.exists():
                base = safe_character
                counter = 1
                while target_file.exists():
                    target_file = target_dir / f"{base}_{counter}.png"
                    counter += 1

            try:
                shutil.copy2(png_file, target_file)
                print(f"复制: {safe_novel}/{safe_character}.png")
                results['copied'] += 1
            except Exception as e:
                print(f"错误: {filename} - {e}")
                results['error'] += 1
        else:
            results['skipped'] += 1

    # 处理现有的旧结构目录
    print(f"\n=== 整理现有目录结构 ===")
    for item in target_base.iterdir():
        if not item.is_dir():
            continue

        dir_name = item.name
        # 跳过已经是正确结构的目录（不包含下划线分隔的角色）
        if '_' not in dir_name or dir_name.endswith('_portrait') or '剧照' in dir_name or '自定义' in dir_name:
            info = extract_info_from_existing_dir(dir_name)
            if info and info.get('novel_title') and info.get('character_name'):
                # 重新组织
                safe_novel = sanitize_path(info['novel_title'])
                safe_character = sanitize_path(info['character_name'])

                new_dir = target_base / safe_novel
                new_dir.mkdir(exist_ok=True)

                # 移动文件
                for png_file in item.glob('*.png'):
                    new_file = new_dir / f"{safe_character}.png"
                    if new_file.exists():
                        base = safe_character
                        counter = 1
                        while new_file.exists():
                            new_file = new_dir / f"{base}_{counter}.png"
                            counter += 1

                    try:
                        shutil.move(str(png_file), str(new_file))
                        print(f"移动: {safe_novel}/{safe_character}.png")
                        results['copied'] += 1
                    except Exception as e:
                        print(f"移动错误: {png_file.name} - {e}")

                # 删除空目录
                try:
                    if not list(item.glob('*')):
                        item.rmdir()
                        print(f"删除空目录: {dir_name}")
                except:
                    pass

    print(f"\n{'='*50}")
    print(f"整理完成:")
    print(f"  成功: {results['copied']} 个文件")
    print(f"  跳过: {results['skipped']} 个文件")
    print(f"  错误: {results['error']} 个文件")

    # 显示最终目录结构
    print(f"\n=== 最终目录结构 ===")
    for novel_dir in sorted(target_base.iterdir()):
        if novel_dir.is_dir():
            files = list(novel_dir.glob('*.png'))
            if files:
                print(f"\n{novel_dir.name}/")
                for f in sorted(files):
                    print(f"  └── {f.name}")


if __name__ == '__main__':
    organize_portraits()
