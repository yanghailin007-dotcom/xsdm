"""
重新生成写作计划 - 使用新的防止重复机制
"""
import sys
import io
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

# 修复编码问题
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from src.core.NovelGenerator import NovelGenerator
from config.config import CONFIG
import json


def main():
    """主函数"""
    print("=" * 60)
    print("重新生成写作计划 - 使用新的防止重复机制")
    print("=" * 60)

    # 初始化生成器
    generator = NovelGenerator(CONFIG)

    # 直接加载项目数据（绕过路径问题）
    project_file = "D:/work6.06/小说项目/全族偷听心声，我被迫无敌/全族偷听心声，我被迫无敌_项目信息.json"

    print(f"\n正在加载项目...")
    print(f"文件路径: {project_file}")

    import json
    try:
        with open(project_file, 'r', encoding='utf-8') as f:
            project_data = json.load(f)
        generator.novel_data = project_data

        # 确保novel_data中有creative_seed字段（可能在novel_info下）
        if 'creative_seed' not in generator.novel_data:
            novel_info = generator.novel_data.get('novel_info', {})
            if 'creative_seed' in novel_info:
                generator.novel_data['creative_seed'] = novel_info['creative_seed']
            else:
                # 使用selected_plan中的数据
                generator.novel_data['creative_seed'] = novel_info.get('selected_plan', {})

        # 确保有其他必需字段
        if 'novel_title' not in generator.novel_data:
            generator.novel_data['novel_title'] = generator.novel_data.get('novel_info', {}).get('title', '未知标题')
        if 'novel_synopsis' not in generator.novel_data:
            generator.novel_data['novel_synopsis'] = generator.novel_data.get('novel_info', {}).get('synopsis', '')

        print(f"[OK] 项目加载成功: {generator.novel_data.get('novel_title', '未知')}")
    except Exception as e:
        print(f"[FAIL] 加载项目失败: {e}")
        import traceback
        traceback.print_exc()
        return

    # 清除缓存的写作计划，强制重新生成
    print("\n清除缓存的写作计划...")
    generator.stage_plan_manager.stage_writing_plans_cache = {}
    print("✅ 缓存已清除")

    # 获取阶段计划信息
    overall_stage_plans = generator.novel_data.get("overall_stage_plans", {})
    if "overall_stage_plan" in overall_stage_plans:
        stage_plan_dict = overall_stage_plans["overall_stage_plan"]
    else:
        stage_plan_dict = overall_stage_plans

    print(f"\n将重新生成以下阶段的写作计划:")
    for stage_name, stage_info in stage_plan_dict.items():
        chapter_range = stage_info.get("chapter_range", "未知")
        print(f"  - {stage_name}: {chapter_range}")

    # 重新生成写作计划
    print("\n" + "=" * 60)
    print("开始重新生成写作计划...")
    print("=" * 60)

    generator.novel_data["stage_writing_plans"] = {}

    for stage_name, stage_info in stage_plan_dict.items():
        chapter_range_str = stage_info["chapter_range"]

        import re
        numbers = re.findall(r'\d+', chapter_range_str)
        if len(numbers) >= 2:
            stage_range = f"{numbers[0]}-{numbers[1]}"
        else:
            stage_range = "1-3"

        print(f"\n📋 正在生成 {stage_name} 的详细写作计划...")
        print(f"   章节范围: {stage_range}")

        stage_plan = generator.stage_plan_manager.generate_stage_writing_plan(
            stage_name=stage_name,
            stage_range=stage_range,
            creative_seed=generator.novel_data["creative_seed"],
            novel_title=generator.novel_data["novel_title"],
            novel_synopsis=generator.novel_data["novel_synopsis"],
            overall_stage_plan=stage_plan_dict
        )

        if stage_plan:
            generator.novel_data["stage_writing_plans"][stage_name] = stage_plan
            print(f"   ✅ {stage_name} 详细计划生成成功")

            # 使用新的验证器检测重复
            if "stage_writing_plan" in stage_plan:
                plan_data = stage_plan["stage_writing_plan"]
            else:
                plan_data = stage_plan

            major_events = plan_data.get("event_system", {}).get("major_events", [])

            if major_events:
                from src.managers.stage_plan.plan_validator import PlanValidator
                validator = PlanValidator()
                duplication_check = validator.detect_plot_duplication_in_events(major_events)
                print(f"   📊 情节重复检测:")
                print(f"      - 是否有重复: {duplication_check.get('has_duplication', False)}")
                print(f"      - 严重程度: {duplication_check.get('severity', 'unknown')}")

                if duplication_check.get('has_duplication'):
                    print(f"   ⚠️ 发现重复问题:")
                    for detail in duplication_check.get('duplication_details', []):
                        print(f"      - {detail['event1']} 与 {detail['event2']}")
                        print(f"        重复内容: {detail['duplicated_content']}")
                else:
                    print(f"   ✅ 未发现情节重复")
        else:
            print(f"   ❌ {stage_name} 详细计划生成失败")

    # 保存更新后的项目数据
    print("\n" + "=" * 60)
    print("保存更新后的项目数据...")
    print("=" * 60)

    # 保存写作计划到文件
    for stage_name, stage_plan in generator.novel_data["stage_writing_plans"].items():
        file_path = generator.stage_plan_manager.plan_persistence.save_plan_to_file(
            stage_name, stage_plan
        )
        print(f"✅ 已保存 {stage_name} 写作计划: {file_path}")

    print("\n" + "=" * 60)
    print("✅ 写作计划重新生成完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
