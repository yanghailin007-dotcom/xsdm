"""
测试恢复模式 - 创建测试检查点文件
"""
import json
import os
from pathlib import Path

def create_test_checkpoint():
    """创建测试检查点文件"""
    # 测试项目标题
    test_title = "测试项目_恢复模式"
    
    # 检查点目录
    checkpoint_dir = Path("小说项目") / test_title / ".generation"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    # 检查点数据
    checkpoint_data = {
        'novel_title': test_title,
        'phase': 'phase_one',
        'current_step': 'character_generation',
        'timestamp': '2025-12-29T14:00:00',
        'data': {
            'generation_params': {
                'title': test_title,
                'synopsis': '这是一个测试项目，用于演示恢复模式功能',
                'core_setting': '修仙世界，主角从零开始修炼',
                'total_chapters': 200
            },
            'status': 'in_progress'
        }
    }
    
    # 写入检查点文件
    checkpoint_file = checkpoint_dir / "checkpoint.json"
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    
    print(f"[OK] Test checkpoint created: {checkpoint_file}")
    print(f"[TITLE] Project: {test_title}")
    print(f"[STEP] Current step: {checkpoint_data['current_step']}")
    print(f"\n[USAGE] Instructions:")
    print(f"1. Open browser and navigate to Phase One setup page")
    print(f"2. Enter title in input box: {test_title}")
    print(f"3. You should see the resume mode option appear")
    print(f"\nOr:")
    print(f"1. Add creative idea with title '{test_title}' to creative library")
    print(f"2. Select that creative idea")
    print(f"3. Resume mode option should be displayed")

if __name__ == "__main__":
    create_test_checkpoint()