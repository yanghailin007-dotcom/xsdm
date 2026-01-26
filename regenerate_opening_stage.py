"""
重新生成开局阶段的写作计划
调用API生成重大事件骨架并拆分为中型事件
"""
import sys
import os
import json
import re
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from config.config import CONFIG
from src.core.NovelGenerator import NovelGenerator
from src.utils.logger import get_logger


def load_project_directly(project_dir: Path) -> dict:
    """直接从项目目录加载数据"""
    logger = get_logger("load_project")

    # 1. 加载项目信息文件
    project_info_file = project_dir / "project_info.json"
    if not project_info_file.exists():
        # 尝试旧格式
        project_info_file = Path(f"D:/work6.06/小说项目/{project_dir.name}_项目信息.json")
        if not project_info_file.exists():
            logger.error(f"找不到项目信息文件")
            return None

    with open(project_info_file, 'r', encoding='utf-8') as f:
        project_data = json.load(f)

    # 2. 加载各阶段产物文件
    products_mapping = project_data.get("products_mapping", {})

    novel_data = {
        "novel_title": project_data.get("novel_title", ""),
        "novel_synopsis": project_data.get("novel_synopsis", ""),
        "creative_seed": project_data.get("creative_seed", {}),
        "selected_plan": project_data.get("selected_plan", {}),
        "category": project_data.get("category", "未分类"),
        "current_progress": {
            "completed_chapters": 0,
            "total_chapters": project_data.get("total_chapters", 200),
            "stage": "第一阶段",
            "current_stage": "第一阶段"
        },
        "generated_chapters": {}
    }

    # 3. 加载市场分析
    if "market_analysis" in products_mapping:
        try:
            with open(products_mapping["market_analysis"], 'r', encoding='utf-8') as f:
                novel_data["market_analysis"] = json.load(f)
        except Exception as e:
            logger.warning(f"加载市场分析失败: {e}")
            novel_data["market_analysis"] = {}

    # 4. 加载世界观
    if "core_worldview" in products_mapping:
        try:
            with open(products_mapping["core_worldview"], 'r', encoding='utf-8') as f:
                novel_data["core_worldview"] = json.load(f)
        except Exception as e:
            logger.warning(f"加载世界观失败: {e}")
            novel_data["core_worldview"] = {}

    # 5. 加载角色设计
    if "character_design" in products_mapping:
        try:
            with open(products_mapping["character_design"], 'r', encoding='utf-8') as f:
                novel_data["character_design"] = json.load(f)
        except Exception as e:
            logger.warning(f"加载角色设计失败: {e}")
            novel_data["character_design"] = {}

    # 6. 加载全局成长计划
    if "global_growth_plan" in products_mapping:
        try:
            with open(products_mapping["global_growth_plan"], 'r', encoding='utf-8') as f:
                novel_data["global_growth_plan"] = json.load(f)
        except Exception as e:
            logger.warning(f"加载成长路线失败: {e}")
            novel_data["global_growth_plan"] = {}

    # 7. 加载整体阶段计划
    if "overall_stage_plans" in products_mapping:
        try:
            with open(products_mapping["overall_stage_plans"], 'r', encoding='utf-8') as f:
                novel_data["overall_stage_plans"] = json.load(f)
        except Exception as e:
            logger.warning(f"加载阶段计划失败: {e}")
            novel_data["overall_stage_plans"] = {}

    # 8. 加载情绪蓝图
    if "emotional_blueprint" in products_mapping:
        try:
            with open(products_mapping["emotional_blueprint"], 'r', encoding='utf-8') as f:
                novel_data["emotional_blueprint"] = json.load(f)
        except Exception as e:
            logger.warning(f"加载情绪蓝图失败: {e}")
            novel_data["emotional_blueprint"] = {}

    # 9. 加载势力系统
    if "faction_system" in products_mapping:
        try:
            with open(products_mapping["faction_system"], 'r', encoding='utf-8') as f:
                novel_data["faction_system"] = json.load(f)
        except Exception as e:
            logger.warning(f"加载势力系统失败: {e}")
            novel_data["faction_system"] = {}

    return novel_data


def regenerate_opening_stage_plan():
    """重新生成开局阶段的写作计划"""
    logger = get_logger("regenerate_opening")

    logger.info("=" * 60)
    logger.info("🔄 重新生成开局阶段写作计划")
    logger.info("=" * 60)

    # 查找项目目录
    projects_base = Path("D:/work6.06/小说项目")
    if not projects_base.exists():
        projects_base = Path("小说项目")

    # 找到最新的项目目录
    project_dirs = [d for d in projects_base.iterdir() if d.is_dir() and not d.name.startswith('.')]
    if not project_dirs:
        logger.error("❌ 没有找到任何项目目录")
        return False

    # 使用最新的目录（按修改时间排序）
    project_dir = max(project_dirs, key=lambda p: p.stat().st_mtime)
    logger.info(f"📚 找到项目目录: {project_dir.name}")

    # 加载项目数据
    novel_data = load_project_directly(project_dir)
    if not novel_data:
        logger.error("❌ 加载项目数据失败")
        return False

    novel_title = novel_data["novel_title"]
    logger.info(f"📖 小说标题: {novel_title}")

    # 初始化小说生成器
    generator = NovelGenerator(CONFIG)
    generator.novel_data = novel_data

    # 确保项目路径正确
    generator.project_path = project_dir

    # 获取整体阶段计划
    overall_stage_plans = novel_data.get("overall_stage_plans", {})
    if "overall_stage_plan" in overall_stage_plans:
        stage_plan_dict = overall_stage_plans["overall_stage_plan"]
    else:
        stage_plan_dict = overall_stage_plans

    # 获取开局阶段的章节范围
    opening_stage_info = stage_plan_dict.get("opening_stage")
    if not opening_stage_info:
        logger.error("❌ 在整体阶段计划中没有找到 opening_stage")
        return False

    chapter_range_str = opening_stage_info.get("chapter_range", "1-20")
    numbers = re.findall(r'\d+', chapter_range_str)
    if len(numbers) >= 2:
        stage_range = f"{numbers[0]}-{numbers[1]}"
    else:
        stage_range = "1-20"

    logger.info(f"📋 开局阶段章节范围: {stage_range}")

    # 清空缓存，强制重新生成
    if hasattr(generator.stage_plan_manager, 'stage_writing_plans_cache'):
        cache_key = "opening_stage_writing_plan"
        if cache_key in generator.stage_plan_manager.stage_writing_plans_cache:
            del generator.stage_plan_manager.stage_writing_plans_cache[cache_key]
            logger.info("🗑️ 已清除缓存，将重新生成")

    # 生成开局阶段写作计划
    logger.info("")
    logger.info("🚀 开始调用API生成开局阶段写作计划...")
    logger.info("")

    try:
        stage_plan = generator.stage_plan_manager.generate_stage_writing_plan(
            stage_name="opening_stage",
            stage_range=stage_range,
            creative_seed=novel_data["creative_seed"],
            novel_title=novel_data["novel_title"],
            novel_synopsis=novel_data["novel_synopsis"],
            overall_stage_plan=stage_plan_dict
        )

        if stage_plan:
            logger.info("")
            logger.info("=" * 60)
            logger.info("✅ 开局阶段写作计划生成成功！")
            logger.info("=" * 60)

            # 更新 novel_data
            if "stage_writing_plans" not in novel_data:
                novel_data["stage_writing_plans"] = {}
            novel_data["stage_writing_plans"]["opening_stage"] = stage_plan

            # 保存写作计划到文件
            try:
                safe_title = re.sub(r'[\\/*?:"<>|]', "_", novel_title)
                plan_file = project_dir / "materials" / "phase_one_products" / f"{safe_title}_开局阶段_写作计划.json"
                plan_file.parent.mkdir(parents=True, exist_ok=True)

                with open(plan_file, 'w', encoding='utf-8') as f:
                    json.dump(stage_plan, f, ensure_ascii=False, indent=2)

                logger.info(f"💾 写作计划已保存到: {plan_file}")
            except Exception as e:
                logger.warning(f"保存写作计划失败: {e}")

            # 打印摘要
            plan_container = stage_plan.get("stage_writing_plan", stage_plan)
            event_system = plan_container.get("event_system", {})
            major_events = event_system.get("major_events", [])

            logger.info("")
            logger.info("📊 生成的重大事件:")
            for i, event in enumerate(major_events, 1):
                name = event.get('name', '未命名')
                role = event.get('role_in_stage_arc', '未定义')
                ch_range = event.get('chapter_range', 'N/A')
                goal = event.get('main_goal', '')
                is_golden = event.get('is_golden_arc', False)

                golden_mark = " 🏆 [黄金开局]" if is_golden else ""
                logger.info(f"  {i}. 【{role}】{name} ({ch_range}){golden_mark}")
                logger.info(f"     目标: {goal}")

                # 显示中型事件
                composition = event.get('composition', {})
                total_medium = sum(len(v) for v in composition.values())
                logger.info(f"     分解为 {total_medium} 个中型事件")

                for phase, medium_events in composition.items():
                    for me in medium_events:
                        me_name = me.get('name', '未命名')
                        me_range = me.get('chapter_range', 'N/A')
                        logger.info(f"       - [{phase}] {me_name} ({me_range})")

            return True

        else:
            logger.error("❌ 开局阶段写作计划生成失败")
            return False

    except Exception as e:
        logger.error(f"❌ 生成过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 检查API密钥
    if not any(CONFIG["api_keys"].values()):
        print("❌ 请先设置API密钥")
        sys.exit(1)

    success = regenerate_opening_stage_plan()
    sys.exit(0 if success else 1)
