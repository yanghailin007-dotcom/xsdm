"""
使用示例：短剧剧本多轮优化框架

运行方式:
    python -m src.core.script_optimization.example
"""
import json
import sys
from pathlib import Path

# 确保可以导入
if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from src.core.script_optimization.pipeline import ScriptOptimizationPipeline
from src.core.script_optimization.config import OptimizationConfig


def example_1_optimize_beats():
    """示例1：优化节拍表"""
    print("=" * 60)
    print("示例1：优化节拍表结构")
    print("=" * 60)
    
    # 创建一个存在问题的节拍表
    beats_json = {
        "version": "1.0",
        "title": "测试剧集",
        "episode": 1,
        "target_duration": 46,
        "beats": [
            {"beat_number": 1, "beat_type": "setup", "description": "主角出场", "duration_seconds": 5, "emotion": "日常"},
            {"beat_number": 2, "beat_type": "rising", "description": "危机出现", "duration_seconds": 4, "emotion": "紧张"},
            {"beat_number": 3, "beat_type": "rising", "description": "紧张升级", "duration_seconds": 5, "emotion": "紧张"},
            {"beat_number": 4, "beat_type": "setup", "description": "平淡过渡", "duration_seconds": 6, "emotion": "日常"},
            {"beat_number": 5, "beat_type": "setup", "description": "平淡结尾", "duration_seconds": 4, "emotion": "日常"}
        ]
    }
    
    pipeline = ScriptOptimizationPipeline()
    optimized_beats, log = pipeline.optimize_beats(beats_json)
    
    print(f"优化前评分: {log['score_before']}")
    print(f"优化后评分: {log['score_after']}")
    print(f"修复项目:")
    for fix in log['fixes']:
        print(f"  - {fix}")
    print()


def example_2_optimize_shots():
    """示例2：优化分镜剧本"""
    print("=" * 60)
    print("示例2：优化分镜剧本")
    print("=" * 60)
    
    # 创建一个存在问题的分镜剧本
    shots_v2 = {
        "version": "2.0",
        "language": "en",
        "title": "测试剧集",
        "episode": 1,
        "total_shots": 4,
        "shots": [
            {
                "shot_number": 1,
                "shot_type": "全景",
                "scene_title": "Slow Start",
                "veo_prompt_standard": "City view wide shot",
                "visual_description_standard": "Wide city view",
                "dialogue": {"speaker": "None", "lines_en": "None", "tone_en": "None", "audio_note_en": ""},
                "duration_seconds": 6
            },
            {
                "shot_number": 2,
                "shot_type": "中景",
                "scene_title": "Dialogue",
                "veo_prompt_standard": "Character talking",
                "visual_description_standard": "Character medium shot",
                "dialogue": {
                    "speaker": "Hero",
                    "lines_en": "You should remember this lesson next time.",
                    "tone_en": "Teaching",
                    "audio_note_en": ""
                },
                "duration_seconds": 5
            },
            {
                "shot_number": 3,
                "shot_type": "特写",
                "scene_title": "Reaction",
                "veo_prompt_standard": "Reaction close-up",
                "visual_description_standard": "Face close-up",
                "dialogue": {"speaker": "None", "lines_en": "None", "tone_en": "None", "audio_note_en": ""},
                "duration_seconds": 4
            },
            {
                "shot_number": 4,
                "shot_type": "全景",
                "scene_title": "Ending",
                "veo_prompt_standard": "Wide ending shot",
                "visual_description_standard": "Wide ending view",
                "dialogue": {"speaker": "None", "lines_en": "None", "tone_en": "None", "audio_note_en": ""},
                "duration_seconds": 5
            }
        ]
    }
    
    config = OptimizationConfig(
        dialogue=True,
        visual=True,
        validation=True
    )
    
    pipeline = ScriptOptimizationPipeline(config)
    optimized_shots, logs = pipeline.optimize_shots(shots_v2)
    
    print(f"执行了 {len(logs)} 轮优化:")
    for log in logs:
        print(f"  第{log['round']}轮 - {log['stage']}")
        if 'changes_count' in log:
            print(f"    修改数: {log['changes_count']}")
        if 'score' in log:
            print(f"    评分: {log['score']}")
        if 'issues' in log:
            print(f"    问题: {len(log['issues'])}个")
            for issue in log['issues'][:2]:  # 只显示前2个
                print(f"      - {issue}")
    print()


def example_3_quick_optimize():
    """示例3：快速优化"""
    print("=" * 60)
    print("示例3：快速优化（只优化对白）")
    print("=" * 60)
    
    shots_v2 = {
        "version": "2.0",
        "language": "en",
        "title": "测试剧集",
        "episode": 1,
        "total_shots": 2,
        "shots": [
            {
                "shot_number": 1,
                "shot_type": "Medium",
                "scene_title": "Scene1",
                "dialogue": {
                    "speaker": "A",
                    "lines_en": "This is... the truth you need to know.",
                    "tone_en": "Serious",
                    "audio_note_en": ""
                },
                "duration_seconds": 3
            },
            {
                "shot_number": 2,
                "shot_type": "Close-up",
                "scene_title": "Scene2",
                "dialogue": {
                    "speaker": "B",
                    "lines_en": "You should be more careful next time.",
                    "tone_en": "Warning",
                    "audio_note_en": ""
                },
                "duration_seconds": 3
            }
        ]
    }
    
    pipeline = ScriptOptimizationPipeline()
    result, report = pipeline.quick_optimize(shots_v2, focus='dialogue')
    
    print(f"优化重点: {report['focus']}")
    print(f"总修改数: {report['total_changes']}")
    print()
    print("修改详情:")
    for log in report['logs']:
        for change in log.get('changes', []):
            print(f"  - {change}")
    print()


def example_4_full_config():
    """示例4：使用完整配置"""
    print("=" * 60)
    print("示例4：使用完整配置进行优化")
    print("=" * 60)
    
    config = OptimizationConfig(
        platform="douyin",
        target_duration=46,
        beat_structure=True,
        dialogue=True,
        visual=True,
        info_layer=True,
        validation=True,
        quality_threshold=7.5
    )
    
    print(f"平台: {config.platform}")
    print(f"目标时长: {config.target_duration}秒")
    print(f"质量阈值: {config.quality_threshold}")
    print(f"启用的轮次:")
    if config.beat_structure:
        print("  - 节拍结构优化")
    if config.dialogue:
        print("  - 对白优化")
    if config.visual:
        print("  - 视觉优化")
    if config.info_layer:
        print("  - 信息层次优化")
    if config.validation:
        print("  - 平台质检")
    print()


if __name__ == "__main__":
    print("\n")
    print("█" * 60)
    print("短剧剧本多轮AI优化框架 - 使用示例")
    print("█" * 60)
    print("\n")
    
    example_1_optimize_beats()
    example_2_optimize_shots()
    example_3_quick_optimize()
    example_4_full_config()
    
    print("=" * 60)
    print("所有示例执行完成！")
    print("=" * 60)
