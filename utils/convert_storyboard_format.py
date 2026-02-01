"""
分镜头剧本格式转换工具

将旧格式分镜头转换为新标准格式：
- shots -> scenes
- screen_action -> visual.description
- dialogue -> dialogue.speaker, dialogue.lines, dialogue.tone, dialogue.audio_note
- 添加 visual.shot_type, visual.veo_prompt
- 添加 plot_content
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Any


def parse_dialogue(dialogue_str: str) -> Dict[str, str]:
    """
    解析台词字符串，提取说话者、台词内容、语气等

    支持格式:
    - "林战: 你还是离开林家吧。"
    - "(旁白): 我……这是在哪？"
    - "林战: (身体僵硬) 这…这是什么声音？"
    """
    if not dialogue_str or dialogue_str.strip() == "":
        return {
            "speaker": "无",
            "lines": "",
            "tone": "纯画面",
            "audio_note": ""
        }

    # 尝试匹配说话者
    speaker = ""
    lines = dialogue_str
    tone = ""

    # 匹配 "(说话者): 内容" 或 "说话者: 内容"
    patterns = [
        r'^\(([^)]+)\):\s*(.+)$',  # (旁白): 内容
        r'^([^:(]+):\s*\(([^)]+)\)\s*(.+)$',  # 说话者: (语气) 内容
        r'^([^:(]+):\s*(.+)$',  # 说话者: 内容
    ]

    for pattern in patterns:
        match = re.match(pattern, dialogue_str.strip())
        if match:
            if match.lastindex == 1:  # (说话者): 内容
                speaker = match.group(1)
                lines = match.group(2)
            elif match.lastindex == 2:  # 说话者: (语气) 内容
                speaker = match.group(1)
                tone = match.group(2)
                lines = match.group(3)
            else:
                speaker = match.group(1)
                lines = match.group(2)
            break

    if not speaker:
        speaker = "无"

    return {
        "speaker": speaker,
        "lines": lines,
        "tone": tone,
        "audio_note": ""
    }


def convert_shot_to_scene(shot: Dict[str, Any], idx: int) -> Dict[str, Any]:
    """将旧格式的shot转换为新格式的scene"""

    # 获取镜头类型（从shot_type或推断）
    shot_type = shot.get("shot_type", "中景")

    # 获取画面描述
    screen_action = shot.get("screen_action", "")
    veo_prompt = shot.get("veo_prompt", screen_action)

    # 解析台词
    dialogue_str = shot.get("dialogue", "")
    if isinstance(dialogue_str, dict):
        # 如果已经是对象格式，直接使用
        dialogue_obj = dialogue_str
    else:
        dialogue_obj = parse_dialogue(dialogue_str)

    # 获取音频备注
    audio_note = shot.get("audio", "")
    if audio_note and not dialogue_obj.get("audio_note"):
        dialogue_obj["audio_note"] = audio_note

    # 获取情节点
    plot_content = shot.get("plot_content", f"镜头{idx}内容")

    # 构建新格式
    scene = {
        "scene_number": idx,
        "duration": shot.get("duration", 8),
        "visual": {
            "shot_type": shot_type,
            "description": screen_action,
            "veo_prompt": veo_prompt
        },
        "dialogue": dialogue_obj,
        "plot_content": plot_content
    }

    return scene


def convert_storyboard_file(input_path: Path, output_path: Path = None) -> bool:
    """转换单个分镜头文件"""

    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 检查是否已经是新格式
        if "scenes" in data:
            print(f"[OK] {input_path.name} 已经是新格式，跳过")
            return True

        # 转换 shots 到 scenes
        shots = data.get("shots", [])
        scenes = []

        for idx, shot in enumerate(shots, start=1):
            scene = convert_shot_to_scene(shot, idx)
            scenes.append(scene)

        # 构建新格式
        new_data = {
            "video_title": data.get("video_title", ""),
            "hook": data.get("hook", ""),
            "total_duration": data.get("total_duration", len(scenes) * 8),
            "scenes": scenes,
            "ending_hook": data.get("ending_hook", "")
        }

        # 保存
        output_path = output_path or input_path
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)

        print(f"[OK] 转换完成: {input_path.name} -> {len(scenes)} 个场景")
        return True

    except Exception as e:
        print(f"[ERROR] 转换失败 {input_path.name}: {e}")
        return False


def convert_all_storyboards(project_dir: Path):
    """转换项目目录下所有分镜头文件"""

    # 查找所有分镜头目录
    storyboard_dirs = list(project_dir.rglob("storyboards"))

    if not storyboard_dirs:
        print("未找到 storyboards 目录")
        return

    converted_count = 0

    for storyboard_dir in storyboard_dirs:
        print(f"\n[*] 处理目录: {storyboard_dir.relative_to(project_dir)}")

        for json_file in storyboard_dir.glob("*.json"):
            if convert_storyboard_file(json_file):
                converted_count += 1

    print(f"\n[OK] 总共转换了 {converted_count} 个分镜头文件")


if __name__ == "__main__":
    # 转换指定项目
    project_dir = Path(r"D:\work6.06\视频项目\心声泄露：我成了家族老阴比\1集_黄金开局：退婚流当场变'舔狗流'")

    print("[*] 开始转换分镜头文件格式...")
    convert_all_storyboards(project_dir)
    print("\n[OK] 转换完成！")
