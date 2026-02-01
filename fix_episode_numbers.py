"""
修正音视频文件的章节序号 - 智能版本

根据章节名（中级事件名）匹配项目信息中的章节序号，
修正文件名开头的章节序号，同时处理句子序号冲突
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


def parse_audio_filename(filename):
    """
    解析音频文件名

    返回: (episode_num, episode_name, dialogue_idx, character, sentence_num, is_new_format)
    """
    stem = Path(filename).stem

    # 新格式: {章节序号:03d}_{章节名}_对话{对话序号:02d}_{角色}_{句子序号:03d}
    match = re.match(r'^(\d+)_(.+?)_对话(\d+)_(.+?)_(\d+)$', stem)
    if match:
        episode_num, episode_name, dialogue_idx, character, sentence_num = match.groups()
        return int(episode_num), episode_name, int(dialogue_idx), character, int(sentence_num), True

    # 旧格式: {镜头号}_{事件名}_对话{序号}_{角色}
    match = re.match(r'^(\d+)_(.+?)_对话(\d+)_(.+)$', stem)
    if match:
        shot_num, event_name, dialogue_idx, character = match.groups()
        return int(shot_num), event_name, int(dialogue_idx), character, None, False

    return None


def parse_video_filename(filename):
    """
    解析视频文件名

    返回: (episode_num, episode_name, dialogue_idx, shot_type, sentence_num, is_new_format)
    """
    stem = Path(filename).stem

    # 新格式: {章节序号:03d}_{章节名}_对话{对话序号:02d}_{镜头类型}_{句子序号:03d}
    match = re.match(r'^(\d+)_(.+?)_对话(\d+)_(.+?)_(\d+)$', stem)
    if match:
        episode_num, episode_name, dialogue_idx, shot_type, sentence_num = match.groups()
        return int(episode_num), episode_name, int(dialogue_idx), shot_type, int(sentence_num), True

    # 旧格式: {镜头号}_{事件名}_{镜头类型}
    match = re.match(r'^(\d+)_(.+?)_(.+)$', stem)
    if match:
        shot_num, event_name, shot_type = match.groups()
        return int(shot_num), event_name, 1, shot_type, None, False

    return None


def collect_audio_files(directory):
    """收集并分类音频文件"""
    if not directory.exists():
        return {}

    files = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))  # {episode_name: {dialogue_idx: {character: [(path, sentence_num)]}}}

    for audio_path in directory.glob("*.mp3"):
        parsed = parse_audio_filename(audio_path.name)
        if parsed:
            episode_num, episode_name, dialogue_idx, character, sentence_num, is_new_format = parsed
            files[episode_name][dialogue_idx][character].append((audio_path, sentence_num))

    return files


def collect_video_files(directory):
    """收集并分类视频文件"""
    if not directory.exists():
        return {}

    files = defaultdict(list)  # {episode_name: [(path, shot_type, sentence_num)]}

    for video_path in directory.glob("*.mp4"):
        parsed = parse_video_filename(video_path.name)
        if parsed:
            episode_num, episode_name, dialogue_idx, shot_type, sentence_num, is_new_format = parsed
            files[episode_name].append((video_path, shot_type, sentence_num))

    return files


def fix_audio_files(directory, episode_map):
    """修正音频文件"""
    files = collect_audio_files(directory)
    if not files:
        return

    rename_plan = []

    for episode_name, dialogues in files.items():
        correct_episode_num = episode_map.get(episode_name)
        if not correct_episode_num:
            continue

        for dialogue_idx, characters in dialogues.items():
            for character, file_list in characters.items():
                # 按句子序号排序
                file_list.sort(key=lambda x: x[1] if x[1] else 0)

                for new_sentence_idx, (old_path, old_sentence_num) in enumerate(file_list, 1):
                    # 生成新文件名
                    new_filename = f"{correct_episode_num:03d}_{episode_name}_对话{dialogue_idx:02d}_{character}_{new_sentence_idx:03d}.mp3"
                    new_path = old_path.parent / new_filename

                    if old_path.name != new_filename:
                        rename_plan.append((old_path, new_path))

    # 按新文件名排序
    rename_plan.sort(key=lambda x: x[1])

    if rename_plan:
        print(f"\n  需要修正 {len(rename_plan)} 个音频文件:")

        for old_path, new_path in rename_plan:
            print(f"    {old_path.name}")
            print(f"    -> {new_path.name}")

            if not DRY_RUN:
                if new_path.exists():
                    print(f"    [!] 跳过: 目标文件已存在")
                else:
                    try:
                        # 确保目标目录存在
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        old_path.rename(new_path)
                        print(f"    [OK] 已修正")
                    except Exception as e:
                        print(f"    [X] 错误: {e}")
            else:
                print(f"    [预览模式]")


def fix_video_files(directory, episode_map):
    """修正视频文件"""
    files = collect_video_files(directory)
    if not files:
        return

    rename_plan = []

    for episode_name, file_list in files.items():
        correct_episode_num = episode_map.get(episode_name)
        if not correct_episode_num:
            continue

        # 按句子序号排序
        file_list.sort(key=lambda x: x[2] if x[2] else 0)

        for new_sentence_idx, (old_path, shot_type, old_sentence_num) in enumerate(file_list, 1):
            # 生成新文件名
            new_filename = f"{correct_episode_num:03d}_{episode_name}_对话01_{shot_type}_{new_sentence_idx:03d}.mp4"
            new_path = old_path.parent / new_filename

            if old_path.name != new_filename:
                rename_plan.append((old_path, new_path))

    # 按新文件名排序
    rename_plan.sort(key=lambda x: x[1])

    if rename_plan:
        print(f"\n  需要修正 {len(rename_plan)} 个视频文件:")

        for old_path, new_path in rename_plan:
            print(f"    {old_path.name}")
            print(f"    -> {new_path.name}")

            if not DRY_RUN:
                if new_path.exists():
                    print(f"    [!] 跳过: 目标文件已存在")
                else:
                    try:
                        new_path.parent.mkdir(parents=True, exist_ok=True)
                        old_path.rename(new_path)
                        print(f"    [OK] 已修正")
                    except Exception as e:
                        print(f"    [X] 错误: {e}")
            else:
                print(f"    [预览模式]")


def main():
    """主函数"""
    print("音视频文件章节序号修正工具 v2")
    print(f"工作目录: {VIDEO_PROJECTS_DIR}")
    print(f"模式: {'预览 (不实际修改)' if DRY_RUN else '执行 (实际修改)'}")

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
            fix_audio_files(audio_dir, episode_map)

            # 处理视频文件
            video_dir = episode_dir / "videos"
            fix_video_files(video_dir, episode_map)

    if DRY_RUN:
        print(f"\n[!] 预览模式: 不会实际修改文件")
        print(f"    如需执行修改，请将脚本中的 DRY_RUN 改为 False")


if __name__ == "__main__":
    main()
