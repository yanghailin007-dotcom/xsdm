"""
智能重命名音频文件
为没有对话标记的文件添加 _对话1_ 标记
"""

import json
import sys
from pathlib import Path
from shutil import move

if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

AUDIO_DIR = Path(r"D:\work6.06\视频项目\心声泄露：我成了家族老阴比\1集_黄金开局：退婚流当场变'舔狗流'\audio")
STORYBOARDS_DIR = Path(r"D:\work6.06\视频项目\心声泄露：我成了家族老阴比\1集_黄金开局：退婚流当场变'舔狗流'\storyboards")

# 收集所有对话信息：(scene_number, event_name, speaker) -> 是否有对话标记
dialogue_info = {}  # key: (scene_number, event_name, speaker), value: dialogue_index or None

print("[INFO] 读取分镜数据...")
for sb_file in STORYBOARDS_DIR.glob('*.json'):
    event_name = sb_file.stem
    with open(sb_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for scene in data.get('scenes', []):
        scene_number = scene.get('scene_number')

        if 'dialogues' in scene and scene['dialogues']:
            for idx, dlg in enumerate(scene['dialogues'], 1):
                speaker = dlg.get('speaker', '')
                key = (scene_number, event_name, speaker)
                dialogue_info[key] = idx  # 有对话标记
        elif 'dialogue' in scene and scene['dialogue']:
            dlg = scene['dialogue']
            speaker = dlg.get('speaker', '')
            if speaker and speaker != '无':
                key = (scene_number, event_name, speaker)
                dialogue_info[key] = None  # 无对话标记，可能是对话场景

# 扫描并重命名音频文件
print("\n[INFO] 扫描音频文件...")
renamed_count = 0

for audio_file in sorted(AUDIO_DIR.glob('*.mp3')):
    old_name = audio_file.name
    name_without_ext = audio_file.stem  # 文件名去掉扩展名
    # 解析文件名: {scene_number}_{event_name}_{speaker}.mp3 或 {scene_number}_{event_name}_对话{index}_{speaker}.mp3
    if '_对话' in name_without_ext:
        print(f"   [SKIP] {old_name} (已有对话标记)")
        continue

    parts = name_without_ext.split('_', 2)  # 分成最多3部分
    if len(parts) < 3:
        print(f"   [SKIP] {old_name} (格式不符)")
        continue

    try:
        scene_number = int(parts[0])
        # parts[1] 可能是事件名的一部分
        # 事件名可能包含下划线，需要从 parts[1] 和 parts[2] 重组

        # 重建完整路径
        full_path_str = audio_file.stem

        # 找到 speaker (最后一部分)
        last_underscore = full_path_str.rfind('_')
        speaker = full_path_str[last_underscore + 1:]

        # 事件名是中间部分
        event_part = full_path_str[len(str(scene_number)) + 1:last_underscore]

        # 在 storyboard 目录中找到匹配的事件名
        matched_event = None
        for sb_file in STORYBOARDS_DIR.glob('*.json'):
            if event_part in sb_file.stem or sb_file.stem in event_part:
                matched_event = sb_file.stem
                break

        if not matched_event:
            # 直接使用解析出来的 event_part
            matched_event = event_part

        key = (scene_number, matched_event, speaker)

        if key in dialogue_info and dialogue_info[key] is None:
            # 这个对话没有标记，添加 _对话1_
            new_name = f"{scene_number}_{matched_event}_对话1_{speaker}.mp3"
            new_path = audio_file.parent / new_name

            if new_path.exists():
                print(f"   [WARN] {old_name} -> 目标已存在")
            else:
                print(f"   [RENAME] {old_name} -> {new_name}")
                move(audio_file, new_path)
                renamed_count += 1
        else:
            print(f"   [INFO] {old_name} (无需重命名)")
    except Exception as e:
        print(f"   [ERROR] {old_name}: {e}")

print(f"\n[DONE] 完成! 共重命名 {renamed_count} 个文件")
