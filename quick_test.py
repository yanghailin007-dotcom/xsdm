"""快速测试阶段规划生成 - 测试模式快捷方法"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# 启用测试模式
os.environ['USE_MOCK_API'] = 'true'

from src.managers.StagePlanManager import StagePlanManager
from src.utils.logger import get_logger

logger = get_logger("quick_test")

class MockGenerator:
    """Mock生成器用于测试"""
    def __init__(self):
        self.novel_data = {
            "novel_title": "Test Novel",
            "novel_synopsis": "Test synopsis",
            "current_progress": {"total_chapters": 200},
            "use_mock_api": True
        }
        self.project_path = BASE_DIR

def test_stage_plan_generation():
    """测试阶段规划生成"""
    logger.info("🧪 开始测试阶段规划生成（测试模式快捷方法）")
    
    mock_gen = MockGenerator()
    manager = StagePlanManager(mock_gen)
    
    overall_stage_plan = {
        "overall_stage_plan": {
            "rising_action_stage": {"stage_arc_goal": "上升阶段"},
            "climax_stage": {"stage_arc_goal": "高潮阶段"},
            "falling_action_stage": {"stage_arc_goal": "下降阶段"},
            "ending_stage": {"stage_arc_goal": "结尾阶段"}
        }
    }
    
    stages = [
        ("rising_action_stage", "1-50"),
        ("climax_stage", "51-150"),
        ("falling_action_stage", "151-180"),
        ("ending_stage", "181-200")
    ]
    
    logger.info(f"📋 测试 {len(stages)} 个阶段")
    success_count = 0
    
    for stage_name, stage_range in stages:
        try:
            logger.info(f"  ⏳ {stage_name} ({stage_range})...")
            result = manager.generate_stage_writing_plan(
                stage_name=stage_name,
                stage_range=stage_range,
                overall_stage_plan=overall_stage_plan,
                novel_title="Test Novel",
                novel_synopsis="Test synopsis",
                creative_seed={"coreSetting": "Test"}
            )
            
            if result and "stage_writing_plan" in result:
                logger.info(f"  ✅ 成功")
                success_count += 1
            else:
                logger.info(f"  ❌ 失败 - 返回格式错误")
        except Exception as e:
            logger.info(f"  ❌ 异常: {str(e)[:100]}")
    
    logger.info("="*50)
    logger.info(f"📊 结果: {success_count}/{len(stages)} 个阶段成功")
    return success_count == len(stages)

if __name__ == "__main__":
    test_stage_plan_generation()