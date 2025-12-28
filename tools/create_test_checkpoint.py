"""
创建测试检查点 - 用于测试恢复生成功能
"""
import json
import os
from pathlib import Path
from datetime import datetime


def create_test_checkpoint(novel_title: str = "测试小说"):
    """创建一个测试检查点"""
    
    # 构建检查点目录
    safe_title = novel_title.replace('/', '_').replace('\\', '_').replace(':', '_')
    project_dir = Path("小说项目") / safe_title
    checkpoint_dir = project_dir / ".generation"
    checkpoint_file = checkpoint_dir / "checkpoint.json"
    
    # 创建目录
    os.makedirs(checkpoint_dir, exist_ok=True)
    
    # 创建检查点数据
    checkpoint_data = {
        "novel_title": novel_title,
        "phase": "phase_one",
        "current_step": "development_stage_plan",
        "timestamp": datetime.now().isoformat(),
        "data": {
            "generation_params": {
                "title": novel_title,
                "synopsis": "这是一个测试用的小说简介",
                "core_setting": "这是一个测试用的核心设定",
                "total_chapters": 200
            },
            "generated_data": {
                "worldview": {"test": "worldview data"},
                "characters": {"test": "character data"}
            },
            "resume_count": 0,
            "status": "in_progress"
        }
    }
    
    # 保存检查点
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(checkpoint_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 测试检查点已创建：{checkpoint_file}")
    print(f"   小说标题：{novel_title}")
    print(f"   当前步骤：{checkpoint_data['current_step']}")
    print(f"   进度：37.5%")
    print(f"\n现在可以测试恢复功能了！")
    
    return checkpoint_file


if __name__ == "__main__":
    import sys
    
    # 从命令行参数获取小说标题
    title = sys.argv[1] if len(sys.argv) > 1 else "修仙：我是一柄魔剑，专治各种不服"
    
    print("=" * 60)
    print("创建测试检查点")
    print("=" * 60)
    
    create_test_checkpoint(title)
    
    print("\n" + "=" * 60)
    print("下一步：")
    print("1. 在创意库中选择该标题的创意")
    print("2. 查看'生成模式'下拉框是否显示恢复选项")
    print("3. 如果没有显示，检查浏览器控制台的日志")
    print("=" * 60)