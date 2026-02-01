"""
重命名音频文件为新格式
旧格式: {scene_number}_{event_name}_{speaker}.mp3
新格式: {scene_number}_{event_name}_对话{index}_{speaker}.mp3 (对话场景)
        {scene_number}_{event_name}_{speaker}.mp3 (普通镜头)
"""

import json
import os
import sys
import re
from pathlib import Path
from shutil import move

# 设置控制台编码为 UTF-8
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 配置
VIDEO_PROJECTS_DIR = Path(r"D:\work6.06\视频项目")
NOVEL_TITLE = "心声泄露：我成了家族老阴比"
EPISODE_TITLE = "1集_黄金开局：退婚流当场变'舔狗流'"

AUDIO_DIR = VIDEO_PROJECTS_DIR / NOVEL_TITLE / EPISODE_TITLE / 'audio'
STORYBOARDS_DIR = VIDEO_PROJECTS_DIR / NOVEL_TITLE / EPISODE_TITLE / 'storyboards'

# 存储所有镜头的应有文件名
expected_files = {}  # 旧文件名 -> 新文件名
scene_info = {}  # (scene_number, event_name) -> scene信息

# 读取所有 storyboard 文件
print(f"[INFO] 扫描分镜目录: {STORYBOARDS_DIR}")
for sb_file in STORYBOARDS_DIR.glob('*.json'):
    event_name = sb_file.stem  # 文件名去掉 .json
    print(f"\n[INFO] 读取分镜: {event_name}")

    with open(sb_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for scene in data.get('scenes', []):
        scene_number = scene.get('scene_number')

        # 检查是对话场景还是普通镜头
        if 'dialogues' in scene and scene['dialogues']:
            # 对话场景: 多个对话
            for idx, dlg in enumerate(scene['dialogues'], 1):
                speaker = dlg.get('speaker', '未知')
                # 旧格式文件名（可能存在）
                old_name = f"{scene_number}_{event_name}_{speaker}.mp3"
                # 新格式文件名
                new_name = f"{scene_number}_{event_name}_对话{idx}_{speaker}.mp3"
                expected_files[old_name] = new_name
                print(f"   [镜头{scene_number}] 对话{idx}: {speaker} -> {new_name}")
        elif 'dialogue' in scene and scene['dialogue']:
            dlg = scene['dialogue']
            speaker = dlg.get('speaker', '')
            if speaker and speaker != '无':
                # 普通镜头: 单个对话
                filename = f"{scene_number}_{event_name}_{speaker}.mp3"
                expected_files[filename] = filename  # 普通镜头不需要改名
                print(f"   [镜头{scene_number}] {speaker} -> {filename}")

# 扫描音频目录并重命名
print(f"\n[INFO] 扫描音频目录: {AUDIO_DIR}")
if not AUDIO_DIR.exists():
    print(f"   [ERROR] 目录不存在!")
else:
    renamed_count = 0
    for audio_file in AUDIO_DIR.glob('*.mp3'):
        old_name = audio_file.name
        print(f"\n   [FILE] {old_name}")

        # 检查是否需要重命名
        if old_name in expected_files and expected_files[old_name] != old_name:
            new_name = expected_files[old_name]
            new_path = audio_file.parent / new_name

            # 检查新文件名是否已存在
            if new_path.exists():
                print(f"      [WARN] 目标文件已存在: {new_name}")
                # 可以选择删除旧文件或重命名
                # os.remove(audio_file)
            else:
                print(f"      [RENAME] {old_name} -> {new_name}")
                # 实际执行重命名（取消注释以启用）
                move(audio_file, new_path)
                renamed_count += 1
        else:
            print(f"      [INFO] 无需重命名")

    print(f"\n[DONE] 完成! 共重命名 {renamed_count} 个文件")
