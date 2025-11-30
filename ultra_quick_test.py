"""极简测试 - 检查哪里卡住了"""
import sys
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

os.environ['USE_MOCK_API'] = 'true'

print("1️⃣  导入Logger...")
from src.utils.logger import get_logger
logger = get_logger("ultra_test")

print("2️⃣  导入StagePlanManager...")
from src.managers.StagePlanManager import StagePlanManager

print("3️⃣  创建Mock Generator...")
class MockGen:
    def __init__(self):
        self.novel_data = {
            "novel_title": "Test",
            "novel_synopsis": "Test",
            "current_progress": {"total_chapters": 200}
        }
        self.project_path = BASE_DIR
        
print("4️⃣  创建StagePlanManager...")
mock_gen = MockGen()
manager = StagePlanManager(mock_gen)

print("5️⃣  准备测试数据...")
overall_plan = {
    "overall_stage_plan": {
        "rising_action_stage": {"stage_arc_goal": "上升"}
    }
}

print("6️⃣  检查USE_MOCK_API环境变量...")
print(f"   USE_MOCK_API = {os.getenv('USE_MOCK_API')}")

print("7️⃣  调用parse_chapter_range...")
start, end = manager.parse_chapter_range("1-50")
print(f"   Result: {start}-{end}")

print("8️⃣  测试 _generate_simple_stage_plan_for_test...")
result = manager._generate_simple_stage_plan_for_test("test_stage", "1-50", overall_plan)
print(f"   Result: {type(result)} with keys: {list(result.keys()) if isinstance(result, dict) else 'N/A'}")

print("9️⃣  调用generate_stage_writing_plan...")
result2 = manager.generate_stage_writing_plan(
    stage_name="rising_action_stage",
    stage_range="1-50",
    overall_stage_plan=overall_plan,
    novel_title="Test",
    novel_synopsis="Test",
    creative_seed={"coreSetting": "Test"}
)
print(f"   Result: {type(result2)}")
if isinstance(result2, dict):
    print(f"   Keys: {list(result2.keys())}")

print("✅ 测试完成！")
