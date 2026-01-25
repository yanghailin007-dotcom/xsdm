"""
重新生成章节场景的脚本

用法：
1. 首先清空现有章节场景
2. 然后调用重新生成方法
"""
import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))


def clear_chapter_scenes(plan_file_path: str) -> bool:
    """
    清空计划文件中的章节场景

    Args:
        plan_file_path: 计划文件路径

    Returns:
        是否成功
    """
    try:
        print(f"正在读取计划文件: {plan_file_path}")

        with open(plan_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # 获取 stage_writing_plan
        if "stage_writing_plan" not in data:
            print("错误: 文件中没有 stage_writing_plan 字段")
            return False

        stage_writing_plan = data["stage_writing_plan"]
        event_system = stage_writing_plan.get("event_system", {})

        # 保存原有的场景数量（用于备份）
        original_scenes = event_system.get("chapter_scene_events", [])
        scene_count = len(original_scenes)
        total_scene_events = sum(len(ch.get("scene_events", [])) for ch in original_scenes)

        print(f"原有章节场景数据: {scene_count} 章, 共 {total_scene_events} 个场景事件")

        # 备份原文件
        backup_path = plan_file_path.replace(".json", "_backup_before_clear.json")
        with open(backup_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"已备份原文件到: {backup_path}")

        # 清空章节场景
        event_system["chapter_scene_events"] = []

        # 保存修改后的文件
        with open(plan_file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        print(f"[OK] 已清空章节场景，文件已保存")

        return True

    except Exception as e:
        print(f"[ERROR] 清空章节场景时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def regenerate_chapter_scenes(plan_file_path: str, novel_project_path: str) -> bool:
    """
    重新生成章节场景

    Args:
        plan_file_path: 计划文件路径
        novel_project_path: 小说项目路径

    Returns:
        是否成功
    """
    try:
        print(f"\n开始重新生成章节场景...")

        # 读取计划文件
        with open(plan_file_path, 'r', encoding='utf-8') as f:
            plan_data = json.load(f)

        stage_writing_plan = plan_data.get("stage_writing_plan", plan_data)
        stage_name = stage_writing_plan.get("stage_name", "opening_stage")
        stage_range = stage_writing_plan.get("chapter_range", "1-20")

        # 获取小说元数据
        novel_metadata = stage_writing_plan.get("novel_metadata", {})
        novel_title = novel_metadata.get("title", "")
        novel_synopsis = novel_metadata.get("synopsis", "")
        creative_seed = novel_metadata.get("creative_seed", {})

        # 获取重大事件
        event_system = stage_writing_plan.get("event_system", {})
        major_events = event_system.get("major_events", [])

        if not major_events:
            print("错误: 没有找到重大事件数据")
            return False

        print(f"找到 {len(major_events)} 个重大事件")

        # 初始化必要的组件
        from src.core.APIClient import APIClient
        from src.managers.stage_plan.event_decomposer import EventDecomposer
        from src.utils.SceneContextBuilder import get_scene_context_builder
        from config.config import CONFIG

        # 获取全局小说数据
        global_novel_data = _load_global_novel_data(novel_project_path)

        api_client = APIClient(CONFIG)
        event_decomposer = EventDecomposer(api_client)

        # 准备 overall_stage_plan
        overall_stage_plan = global_novel_data.get("overall_stage_plans", {})

        # 收集情节约束上下文（防止重复）
        consistency_guidance = _build_consistency_guidance_from_existing_scenes(plan_data)

        # 为每个重大事件分解中型事件为章节场景
        print("开始分解中型事件为章节场景...")

        # 用于收集所有章节场景的映射
        chapter_scene_map = {}

        for major_event in major_events:
            print(f"\n处理重大事件: {major_event.get('name')}")

            # 调用智能分解方法
            decomposed_event = event_decomposer.smart_decompose_medium_events(
                major_event=major_event,
                stage_name=stage_name,
                novel_title=novel_title,
                novel_synopsis=novel_synopsis,
                creative_seed=creative_seed,
                overall_stage_plan=overall_stage_plan,
                global_novel_data=global_novel_data,
                consistency_guidance=consistency_guidance
            )

            if decomposed_event:
                # 从分解结果中提取章节场景
                _extract_chapter_scenes_from_decomposed_event(
                    decomposed_event, chapter_scene_map
                )
                print(f"    [OK] 成功分解并提取场景")

        # 将章节映射转换为列表
        chapter_scene_events_list = _convert_chapter_map_to_list(chapter_scene_map)

        # 更新计划文件
        event_system["chapter_scene_events"] = chapter_scene_events_list

        # 保存文件
        with open(plan_file_path, 'w', encoding='utf-8') as f:
            json.dump(plan_data, f, ensure_ascii=False, indent=2)

        print(f"\n[OK] 章节场景重新生成完成！")
        print(f"   共生成 {len(chapter_scene_events_list)} 章的场景数据")

        return True

    except Exception as e:
        print(f"[ERROR] 重新生成章节场景时出错: {e}")
        import traceback
        traceback.print_exc()
        return False


def _load_global_novel_data(novel_project_path: str) -> dict:
    """加载全局小说数据"""
    from pathlib import Path

    project_path = Path(novel_project_path)

    # 尝试加载项目信息文件
    project_info_files = list(project_path.glob("*_项目信息.json"))
    if project_info_files:
        with open(project_info_files[0], 'r', encoding='utf-8') as f:
            return json.load(f)

    # 尝试加载第一阶段产物
    materials_dirs = [
        project_path / "materials" / "phase_one_products",
        project_path / "materials",
    ]

    for materials_dir in materials_dirs:
        if materials_dir.exists():
            # 加载各种产物文件
            result = {}
            for file_path in materials_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 根据文件名确定数据类型
                        if "世界观" in file_path.name:
                            result["core_worldview"] = data
                        elif "角色" in file_path.name:
                            result["character_design"] = data
                        elif "成长" in file_path.name:
                            result["global_growth_plan"] = data
                        elif "阶段" in file_path.name:
                            result["overall_stage_plans"] = data
                        elif "写作风格" in file_path.name:
                            result["writing_style_guide"] = data
                except:
                    pass

            if result:
                return result

    return {}


def _build_consistency_guidance_from_existing_scenes(plan_data: dict) -> str:
    """从现有场景构建情节约束（防止重复）"""
    # 由于我们已经清空了场景，这里返回空
    return ""


def _extract_chapter_scenes_from_decomposed_event(decomposed_event: dict, chapter_scene_map: dict):
    """从分解后的事件中提取章节场景"""
    from src.managers.StagePlanUtils import parse_chapter_range

    composition = decomposed_event.get("composition", {})

    for phase_name, phase_events in composition.items():
        for medium_event in phase_events:
            decomposition_type = medium_event.get("decomposition_type", "")
            chapter_range = medium_event.get("chapter_range", "1-1")

            # 处理 ai_free_direct_scenes 类型
            if decomposition_type == "ai_free_direct_scenes":
                scene_sequences = medium_event.get("scene_sequences", [])

                for seq in scene_sequences:
                    chapter_num = seq.get("chapter_num")  # 注意这里是用 chapter_num
                    scene_events = seq.get("scene_events", [])
                    chapter_goal = seq.get("chapter_goal", "")
                    writing_focus = seq.get("writing_focus", "深化情感，推进剧情")

                    if chapter_num not in chapter_scene_map:
                        chapter_scene_map[chapter_num] = {
                            "chapter_goal": chapter_goal,
                            "writing_focus": writing_focus,
                            "scene_events": []
                        }
                    chapter_scene_map[chapter_num]["scene_events"].extend(scene_events)

            # 处理 ai_free_chapter_events 类型
            elif decomposition_type == "ai_free_chapter_events":
                chapter_events = medium_event.get("chapter_events", [])

                for ch_event in chapter_events:
                    chapter_num = ch_event.get("chapter_index")  # 注意这里是用 chapter_index
                    scene_structure = ch_event.get("scene_structure", {})
                    scenes = scene_structure.get("scenes", [])

                    # 从chapter_index转换为实际的章节号
                    # 需要根据chapter_range计算
                    start_ch, end_ch = parse_chapter_range(chapter_range)
                    # chapter_index 是相对于 chapter_range 的偏移
                    actual_chapter_num = start_ch + (chapter_num - start_ch)

                    if actual_chapter_num not in chapter_scene_map:
                        chapter_scene_map[actual_chapter_num] = {
                            "chapter_goal": ch_event.get("summary", ""),
                            "writing_focus": scene_structure.get("overall_mood", "深化情感，推进剧情"),
                            "scene_events": []
                        }
                    chapter_scene_map[actual_chapter_num]["scene_events"].extend(scenes)

            # 处理 single_chapter_complete_arc 类型
            elif decomposition_type == "single_chapter_complete_arc":
                scene_sequences = medium_event.get("scene_sequences", [])

                for seq in scene_sequences:
                    scene_events = seq.get("scene_events", [])
                    chapter_goal = seq.get("chapter_goal", "")
                    writing_focus = seq.get("writing_focus", "深化情感，推进剧情")

                    # 单章事件，使用 chapter_range 的起始章节
                    start_ch, _ = parse_chapter_range(chapter_range)

                    if start_ch not in chapter_scene_map:
                        chapter_scene_map[start_ch] = {
                            "chapter_goal": chapter_goal,
                            "writing_focus": writing_focus,
                            "scene_events": []
                        }
                    chapter_scene_map[start_ch]["scene_events"].extend(scene_events)

            # 兼容旧格式：direct_scene
            elif decomposition_type == "direct_scene":
                scene_sequences = medium_event.get("scene_sequences", [])

                for seq in scene_sequences:
                    seq_range = seq.get("chapter_range", chapter_range)
                    scene_events = seq.get("scene_events", [])
                    chapter_goal = seq.get("chapter_goal", "")
                    writing_focus = seq.get("writing_focus", "深化情感，推进剧情")

                    start_ch, end_ch = parse_chapter_range(seq_range)

                    for ch_num in range(start_ch, end_ch + 1):
                        if ch_num not in chapter_scene_map:
                            chapter_scene_map[ch_num] = {
                                "chapter_goal": chapter_goal,
                                "writing_focus": writing_focus,
                                "scene_events": []
                            }
                        chapter_scene_map[ch_num]["scene_events"].extend(scene_events)


def _convert_chapter_map_to_list(chapter_scene_map: dict) -> list:
    """将章节映射转换为列表"""
    chapter_scene_events_list = []
    all_chapter_nums = sorted(chapter_scene_map.keys())

    for chapter_num in all_chapter_nums:
        chapter_info = chapter_scene_map[chapter_num]
        chapter_scene_events_list.append({
            "chapter_number": chapter_num,
            "chapter_goal": chapter_info.get("chapter_goal", f"完成第{chapter_num}章内容"),
            "writing_focus": chapter_info.get("writing_focus", "深化情感，推进剧情"),
            "scene_events": chapter_info.get("scene_events", [])
        })

    return chapter_scene_events_list


def main():
    """主函数"""
    # 配置路径
    plan_file = r"D:\work6.06\小说项目\全族偷听心声，我被迫无敌\plans\全族偷听心声，我被迫无敌_opening_stage_writing_plan.json"
    novel_project = r"D:\work6.06\小说项目\全族偷听心声，我被迫无敌"

    import argparse
    parser = argparse.ArgumentParser(description="重新生成章节场景")
    parser.add_argument("--clear-only", action="store_true", help="只清空场景，不重新生成")
    parser.add_argument("--regenerate-only", action="store_true", help="只重新生成，不先清空")
    args = parser.parse_args()

    if args.clear_only:
        # 只清空
        success = clear_chapter_scenes(plan_file)
        if success:
            print("\n[OK] 章节场景已清空，可以手动调用重新生成方法")
        return

    if args.regenerate_only:
        # 只重新生成
        success = regenerate_chapter_scenes(plan_file, novel_project)
        return

    # 默认：清空 + 重新生成
    print("=" * 60)
    print("步骤 1: 清空现有章节场景")
    print("=" * 60)

    if clear_chapter_scenes(plan_file):
        print("\n" + "=" * 60)
        print("步骤 2: 重新生成章节场景")
        print("=" * 60)
        regenerate_chapter_scenes(plan_file, novel_project)


if __name__ == "__main__":
    main()
