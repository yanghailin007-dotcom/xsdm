"""
重命名音视频文件为新格式

旧格式:
- 音频: {镜头号}_{事件名}_对话{序号}_{角色}.mp3 或 {镜头号}_{事件名}_{角色}.mp3
- 视频: {镜头号}_{事件名}_{镜头类型}.mp4

新格式:
- 音频: {章节序号:03d}_{章节名}_对话{对话序号:02d}_{角色}_{句子序号:03d}.{ext}
- 视频: {章节序号:03d}_{章节名}_对话{对话序号:02d}_{镜头类型}_{句子序号:03d}.{ext}

示例:
  001_诈尸惊魂_对话01_林战_001.mp3
  001_诈尸惊魂_对话01_中景_特写_001.mp4
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

# 视频项目根目录
VIDEO_PROJECTS_DIR = Path(r"D:\work6.06\视频项目")

# 是否实际执行重命名（False时只显示预览）
DRY_RUN = False  # 设为 True 时只预览，不实际重命名


def load_project_info(project_name):
    """加载项目信息，获取章节列表"""
    project_info_path = VIDEO_PROJECTS_DIR / project_name / "项目信息.json"

    if not project_info_path.exists():
        print(f"  [!] 未找到项目信息文件: {project_info_path}")
        return {}

    try:
        with open(project_info_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        episodes = data.get('episodes', [])
        # 创建章节名到章节序号的映射（从1开始）
        episode_map = {}
        for idx, episode_name in enumerate(episodes, 1):
            episode_map[episode_name] = idx

        print(f"  [OK] 加载了 {len(episodes)} 个章节信息")
        return episode_map

    except Exception as e:
        print(f"  [X] 加载项目信息失败: {e}")
        return {}


def parse_audio_filename(filename):
    """
    解析音频文件名

    旧格式1: {镜头号}_{事件名}_对话{序号}_{角色}.mp3
    旧格式2: {镜头号}_{事件名}_{角色}.mp3
    新格式: {章节序号:03d}_{章节名}_对话{序号}_{角色}_{句子序号:03d}.mp3（跳过）
    """
    stem = Path(filename).stem

    # 跳过新格式的文件
    if re.match(r'^\d+_', stem):
        parts = stem.split('_')
        # 检查是否已经是新格式（有多段且第一段是3位数字）
        if len(parts) >= 4 and parts[0].isdigit() and len(parts[0]) == 3:
            # 可能是新格式，检查是否有句子序号
            if parts[-1].isdigit() and len(parts[-1]) == 3:
                return {'skip': True}

    # 格式1: {镜头号}_{事件名}_对话{序号}_{角色}
    match1 = re.match(r'^(\d+)_(.+?)_对话(\d+)_(.+)$', stem)
    if match1:
        shot_num, event_name, dialogue_idx, character = match1.groups()
        return {
            'shot_num': int(shot_num),
            'event_name': event_name,
            'dialogue_idx': int(dialogue_idx),
            'character': character,
            'has_dialogue': True
        }

    # 格式2: {镜头号}_{事件名}_{角色}
    match2 = re.match(r'^(\d+)_(.+?)_(.+)$', stem)
    if match2:
        shot_num, event_name, character = match2.groups()
        return {
            'shot_num': int(shot_num),
            'event_name': event_name,
            'dialogue_idx': 1,  # 默认对话1
            'character': character,
            'has_dialogue': False
        }

    return None


def parse_video_filename(filename):
    """
    解析视频文件名

    格式: {镜头号}_{事件名}_{镜头类型}.mp4
    或: {镜头号}_{事件名}_{镜头类型1}_{镜头类型2}.mp4
    """
    stem = Path(filename).stem

    # 跳过新格式的文件
    if re.match(r'^\d+_', stem):
        parts = stem.split('_')
        if len(parts) >= 5 and parts[0].isdigit() and len(parts[0]) == 3:
            # 可能是新格式，检查是否有句子序号
            if parts[-1].isdigit() and len(parts[-1]) == 3:
                return {'skip': True}

    # 匹配 {数字}_{事件名}_{其他内容}
    match = re.match(r'^(\d+)_(.+?)_(.+)$', stem)
    if match:
        shot_num, event_name, shot_type = match.groups()
        return {
            'shot_num': int(shot_num),
            'event_name': event_name,
            'shot_type': shot_type
        }

    return None


def generate_new_audio_name(parsed, sentence_idx, episode_map):
    """生成新的音频文件名"""
    event_name = parsed['event_name']
    dialogue_idx = parsed.get('dialogue_idx', 1)
    character = parsed['character']

    # 从章节映射中获取章节序号
    episode_num = episode_map.get(event_name, 1)

    # 新格式: {章节序号:03d}_{章节名}_对话{对话序号:02d}_{角色}_{句子序号:03d}.mp3
    new_name = f"{episode_num:03d}_{event_name}_对话{dialogue_idx:02d}_{character}_{sentence_idx:03d}.mp3"
    return new_name


def generate_new_video_name(parsed, sentence_idx, episode_map):
    """生成新的视频文件名"""
    event_name = parsed['event_name']
    shot_type = parsed['shot_type']

    # 从章节映射中获取章节序号
    episode_num = episode_map.get(event_name, 1)

    # 新格式: {章节序号:03d}_{章节名}_对话{对话序号:02d}_{镜头类型}_{句子序号:03d}.mp4
    # 视频默认对话序号为1
    new_name = f"{episode_num:03d}_{event_name}_对话01_{shot_type}_{sentence_idx:03d}.mp4"
    return new_name


def collect_files_by_event(audio_dir, video_dir):
    """
    按事件分组收集文件，并为每个文件分配句子序号

    返回: {(event_name, dialogue_idx, character): [(old_path, new_name, type)]}
    """
    audio_files = list(audio_dir.glob("*.mp3")) if audio_dir.exists() else []
    video_files = list(video_dir.glob("*.mp4")) if video_dir.exists() else []

    # 按事件分组
    audio_groups = defaultdict(list)
    for audio_path in audio_files:
        parsed = parse_audio_filename(audio_path.name)
        if parsed and not parsed.get('skip'):
            key = (parsed['shot_num'], parsed['event_name'], parsed['dialogue_idx'], parsed['character'])
            audio_groups[key].append((audio_path, parsed))

    # 按事件分组视频
    video_groups = defaultdict(list)
    for video_path in video_files:
        parsed = parse_video_filename(video_path.name)
        if parsed and not parsed.get('skip'):
            key = (parsed['shot_num'], parsed['event_name'])
            video_groups[key].append((video_path, parsed))

    return audio_groups, video_groups


def rename_files_in_project(project_name, episode_name, episode_map):
    """重命名单个项目中的文件"""
    project_dir = VIDEO_PROJECTS_DIR / project_name / episode_name
    audio_dir = project_dir / "audio"
    video_dir = project_dir / "videos"

    print(f"\n{'='*60}")
    print(f"处理项目: {project_name} / {episode_name}")
    print(f"{'='*60}")

    if not audio_dir.exists() and not video_dir.exists():
        print("  跳过: 没有找到 audio 或 videos 目录")
        return

    # 收集文件
    audio_groups, video_groups = collect_files_by_event(audio_dir, video_dir)

    rename_plan = []

    # 处理音频文件
    for key, files in audio_groups.items():
        shot_num, event_name, dialogue_idx, character = key

        # 按原始文件名排序，确保重命名顺序一致
        files.sort(key=lambda x: x[0].name)

        for sentence_idx, (old_path, parsed) in enumerate(files, 1):
            new_name = generate_new_audio_name(parsed, sentence_idx, episode_map)
            new_path = old_path.parent / new_name
            rename_plan.append((old_path, new_path, "音频"))

    # 处理视频文件
    for key, files in video_groups.items():
        shot_num, event_name = key

        # 按原始文件名排序
        files.sort(key=lambda x: x[0].name)

        for sentence_idx, (old_path, parsed) in enumerate(files, 1):
            new_name = generate_new_video_name(parsed, sentence_idx, episode_map)
            new_path = old_path.parent / new_name
            rename_plan.append((old_path, new_path, "视频"))

    # 按新文件名排序显示
    rename_plan.sort(key=lambda x: x[1])

    # 显示重命名计划
    print(f"\n计划重命名 {len(rename_plan)} 个文件:\n")

    for old_path, new_path, file_type in rename_plan:
        print(f"  [{file_type}]")
        print(f"    旧: {old_path.name}")
        print(f"    新: {new_path.name}")

        # 执行重命名
        if not DRY_RUN:
            if new_path.exists():
                print(f"    [!] 跳过: 目标文件已存在")
            else:
                try:
                    old_path.rename(new_path)
                    print(f"    [OK] 已重命名")
                except Exception as e:
                    print(f"    [X] 错误: {e}")
        else:
            print(f"    [预览模式]")

    if DRY_RUN:
        print(f"\n[!] 预览模式: 不会实际重命名文件")
        print(f"    如需执行重命名，请将脚本中的 DRY_RUN 改为 False")


def main():
    """主函数"""
    print("音视频文件重命名工具 v2")
    print(f"工作目录: {VIDEO_PROJECTS_DIR}")
    print(f"模式: {'预览 (不实际重命名)' if DRY_RUN else '执行 (实际重命名)'}")

    # 遍历所有项目
    for project_dir in VIDEO_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        project_name = project_dir.name

        # 加载项目信息（章节列表）
        episode_map = load_project_info(project_name)
        if not episode_map:
            print(f"\n跳过项目: {project_name} (无章节信息)")
            continue

        for episode_dir in project_dir.iterdir():
            if not episode_dir.is_dir():
                continue

            episode_name = episode_dir.name

            # 跳过备份目录
            if episode_name.startswith('.'):
                continue

            try:
                rename_files_in_project(project_name, episode_name, episode_map)
            except Exception as e:
                print(f"\n[X] 处理 {project_name}/{episode_name} 时出错: {e}")
                import traceback
                traceback.print_exc()


if __name__ == "__main__":
    main()
