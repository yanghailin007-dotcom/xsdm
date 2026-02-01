"""
重命名音视频文件为正确格式

正确格式:
- 音频: {章节序号:03d}_{场景序号:02d}_{中级事件名}_对话{对话序号:02d}_{角色}_{句子序号:03d}.{ext}
- 视频: {章节序号:03d}_{场景序号:02d}_{中级事件名}_对话{对话序号:02d}_{镜头类型}_{句子序号:03d}.{ext}

示例:
  001_01_诈尸惊魂_对话01_旁白_001.mp3  (第1章第1场景)
  001_02_诈尸惊魂_对话01_旁白_001.mp3  (第1章第2场景)
"""

import os
import re
import json
from pathlib import Path
from collections import defaultdict

# 视频项目根目录
VIDEO_PROJECTS_DIR = Path(r"D:\work6.06\视频项目")

# 是否实际执行重命名
DRY_RUN = False  # 设为 False 时实际执行


def load_project_info(project_name):
    """加载项目信息，获取章节列表"""
    project_info_path = VIDEO_PROJECTS_DIR / project_name / "项目信息.json"

    if not project_info_path.exists():
        return {}

    try:
        with open(project_info_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        episodes = data.get('episodes', [])
        episode_map = {}
        for idx, episode_name in enumerate(episodes, 1):
            episode_map[episode_name] = idx

        return episode_map

    except Exception as e:
        return {}


def parse_and_collect_files(directory, file_ext):
    """
    解析并收集文件

    按章节分组，然后按原始镜头号排序，分配新的场景序号
    """
    if not directory.exists():
        return {}

    # 结构: {episode_name: [(old_path, old_shot_num, dialogue_idx, character/sentence_type, sentence_num), ...]}
    files = defaultdict(list)

    for file_path in directory.glob(f"*{file_ext}"):
        stem = file_path.stem

        # 尝试解析旧格式: {镜头号}_{事件名}_对话{序号}_{角色}
        match = re.match(r'^(\d+)_(.+?)_(对话\d+)_(.+)$', stem)
        if match:
            shot_num, event_name, dialogue_part, character = match.groups()
            dialogue_idx = int(re.match(r'对话(\d+)', dialogue_part).group(1))
            files[event_name].append((file_path, int(shot_num), dialogue_idx, character, None))
            continue

        # 尝试解析: {镜头号}_{事件名}_{角色}
        match = re.match(r'^(\d+)_(.+?)_(.+)$', stem)
        if match:
            shot_num, event_name, character = match.groups()
            files[event_name].append((file_path, int(shot_num), 1, character, None))
            continue

    return files


def rename_audio_files(directory, episode_map, file_ext):
    """重命名音频文件"""
    files_by_episode = parse_and_collect_files(directory, file_ext)

    if not files_by_episode:
        return

    rename_plan = []

    for episode_name, file_list in files_by_episode.items():
        # 获取章节序号
        episode_num = episode_map.get(episode_name)
        if not episode_num:
            continue

        # 按原始镜头号排序
        file_list.sort(key=lambda x: x[1])

        # 为该章节的文件分组：(dialogue_idx, character) -> [(path, shot_num, sentence_num)]
        dialogue_groups = defaultdict(list)
        for file_path, shot_num, dialogue_idx, character, sentence_num in file_list:
            dialogue_groups[(dialogue_idx, character)].append((file_path, shot_num, sentence_num))

        # 为每个对话组分配场景序号和新的句子序号
        scene_num = 1
        for (dialogue_idx, character), group_files in dialogue_groups.items():
            for sentence_idx, (file_path, shot_num, old_sentence_num) in enumerate(group_files, 1):
                # 新格式: {章节序号:03d}_{场景序号:02d}_{中级事件名}_对话{对话序号:02d}_{角色}_{句子序号:03d}.mp3
                new_filename = f"{episode_num:03d}_{scene_num:02d}_{episode_name}_对话{dialogue_idx:02d}_{character}_{sentence_idx:03d}.{file_ext}"
                new_path = file_path.parent / new_filename

                if file_path.name != new_filename:
                    rename_plan.append((file_path, new_path))

            scene_num += 1

    # 按新文件名排序
    rename_plan.sort(key=lambda x: x[1])

    if rename_plan:
        print(f"\n  需要修正 {len(rename_plan)} 个 {file_ext} 文件:")

        for old_path, new_path in rename_plan:
            print(f"    {old_path.name}")
            print(f"    -> {new_path.name}")

            if not DRY_RUN:
                if new_path.exists():
                    print(f"    [!] 跳过: 目标文件已存在")
                else:
                    try:
                        old_path.rename(new_path)
                        print(f"    [OK] 已修正")
                    except Exception as e:
                        print(f"    [X] 错误: {e}")
            else:
                print(f"    [预览模式]")


def rename_video_files(directory, episode_map, file_ext):
    """重命名视频文件"""
    if not directory.exists():
        return

    # 结构: {episode_name: [(old_path, old_shot_num, shot_type), ...]}
    files_by_episode = defaultdict(list)

    for file_path in directory.glob(f"*{file_ext}"):
        stem = file_path.stem

        # 尝试解析旧格式: {镜头号}_{事件名}_{镜头类型}
        match = re.match(r'^(\d+)_(.+?)_(.+)$', stem)
        if match:
            shot_num, event_name, shot_type = match.groups()
            files_by_episode[event_name].append((file_path, int(shot_num), shot_type))

    rename_plan = []

    for episode_name, file_list in files_by_episode.items():
        # 获取章节序号
        episode_num = episode_map.get(episode_name)
        if not episode_num:
            continue

        # 按原始镜头号排序
        file_list.sort(key=lambda x: x[1])

        # 为每个视频分配场景序号和句子序号
        for scene_idx, (file_path, shot_num, shot_type) in enumerate(file_list, 1):
            # 新格式: {章节序号:03d}_{场景序号:02d}_{中级事件名}_对话01_{镜头类型}_{句子序号:03d}.mp4
            new_filename = f"{episode_num:03d}_{scene_idx:02d}_{episode_name}_对话01_{shot_type}_{scene_idx:03d}.{file_ext}"
            new_path = file_path.parent / new_filename

            if file_path.name != new_filename:
                rename_plan.append((file_path, new_path))

    # 按新文件名排序
    rename_plan.sort(key=lambda x: x[1])

    if rename_plan:
        print(f"\n  需要修正 {len(rename_plan)} 个 {file_ext} 文件:")

        for old_path, new_path in rename_plan:
            print(f"    {old_path.name}")
            print(f"    -> {new_path.name}")

            if not DRY_RUN:
                if new_path.exists():
                    print(f"    [!] 跳过: 目标文件已存在")
                else:
                    try:
                        old_path.rename(new_path)
                        print(f"    [OK] 已修正")
                    except Exception as e:
                        print(f"    [X] 错误: {e}")
            else:
                print(f"    [预览模式]")


def main():
    """主函数"""
    print("音视频文件重命名工具 v3 - 正确格式")
    print(f"工作目录: {VIDEO_PROJECTS_DIR}")
    print(f"模式: {'预览 (不实际修改)' if DRY_RUN else '执行 (实际修改)'}")
    print(f"新格式: {{章节序号:03d}}_{{场景序号:02d}}_{{中级事件名}}_...")

    # 遍历所有项目
    for project_dir in VIDEO_PROJECTS_DIR.iterdir():
        if not project_dir.is_dir():
            continue

        project_name = project_dir.name

        # 加载项目信息（章节列表）
        episode_map = load_project_info(project_name)
        if not episode_map:
            continue

        for episode_dir in project_dir.iterdir():
            if not episode_dir.is_dir():
                continue

            episode_name = episode_dir.name

            # 跳过备份目录
            if episode_name.startswith('.'):
                continue

            print(f"\n{'='*60}")
            print(f"处理: {project_name} / {episode_name}")
            print(f"{'='*60}")

            # 处理音频文件
            audio_dir = episode_dir / "audio"
            rename_audio_files(audio_dir, episode_map, "mp3")

            # 处理视频文件
            video_dir = episode_dir / "videos"
            rename_video_files(video_dir, episode_map, "mp4")

    if DRY_RUN:
        print(f"\n[!] 预览模式: 不会实际修改文件")
        print(f"    如需执行修改，请将脚本中的 DRY_RUN 改为 False")


if __name__ == "__main__":
    main()
