"""
修复中型事件的情节点数量问题

问题：
- 2章的事件只有6-7个情节点，应该有8-12个（每章4-6个）
- 1章的事件有7个情节点，应该有4-6个

解决方案：调用AI重新生成情节大纲
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))


def fix_plot_outline_for_medium_events(plan_file_path: str):
    """修复中型事件的情节大纲"""
    # 读取计划文件
    with open(plan_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    stage_plan = data.get('stage_writing_plan', data)
    event_system = stage_plan.get('event_system', {})
    major_events = event_system.get('major_events', [])

    # 收集需要修复的中型事件
    events_to_fix = []

    for major_idx, major_event in enumerate(major_events):
        composition = major_event.get('composition', {})
        for phase_name, phase_events in composition.items():
            for medium_event in phase_events:
                name = medium_event.get('name', '')
                chapter_range = medium_event.get('chapter_range', '')
                plot_outline = medium_event.get('plot_outline', [])

                # 解析章节数
                if '-' in chapter_range:
                    try:
                        parts = chapter_range.replace('章', '').split('-')
                        start = int(parts[0])
                        end = int(parts[1]) if len(parts) > 1 else start
                        chapter_count = end - start + 1
                    except:
                        chapter_count = 1
                else:
                    chapter_count = 1

                plot_count = len(plot_outline) if plot_outline else 0
                expected_min = chapter_count * 4
                expected_max = chapter_count * 6

                # 判断是否需要修复
                needs_fix = False
                fix_reason = ""

                if chapter_count == 1 and plot_count > 6:
                    needs_fix = True
                    fix_reason = f"1章事件有{plot_count}个情节点，应该4-6个"
                elif chapter_count >= 2 and plot_count < chapter_count * 4:
                    needs_fix = True
                    fix_reason = f"{chapter_count}章事件只有{plot_count}个情节点，应该{chapter_count * 4}-{chapter_count * 6}个"

                if needs_fix:
                    events_to_fix.append({
                        'major_idx': major_idx,
                        'major_name': major_event.get('name', ''),
                        'phase': phase_name,
                        'medium_event': medium_event,
                        'name': name,
                        'chapter_range': chapter_range,
                        'chapter_count': chapter_count,
                        'current_count': plot_count,
                        'expected_min': expected_min,
                        'expected_max': expected_max,
                        'reason': fix_reason
                    })

    print(f"找到 {len(events_to_fix)} 个需要修复的中型事件：\n")

    for i, event in enumerate(events_to_fix, 1):
        print(f"{i}. [{event['phase']}] {event['name']}")
        print(f"   章节范围: {event['chapter_range']} ({event['chapter_count']}章)")
        print(f"   当前情节点: {event['current_count']}个")
        print(f"   预期范围: {event['expected_min']}-{event['expected_max']}个")
        print(f"   原因: {event['reason']}")
        print()

    # 初始化API客户端
    from src.core.APIClient import APIClient
    from config.config import CONFIG

    api_client = APIClient(CONFIG)

    # 获取上下文信息
    novel_metadata = stage_plan.get('novel_metadata', {})
    creative_seed = novel_metadata.get('creative_seed', {})
    novel_title = novel_metadata.get('title', '')
    novel_synopsis = novel_metadata.get('synopsis', '')

    # 逐个修复
    fixed_count = 0
    for i, event_info in enumerate(events_to_fix, 1):
        print(f"\n[{i}/{len(events_to_fix)}] 正在修复: {event_info['name']}")

        # 构建修复提示
        medium_event = event_info['medium_event']
        chapter_count = event_info['chapter_count']

        prompt = f"""# 任务：修复中型事件的情节大纲数量

你是一个小说情节规划专家。我发现当前中型事件的情节大纲数量不合理，需要你重新生成。

## 小说信息
- 标题: {novel_title}
- 简介: {novel_synopsis}

## 当前中型事件信息
- 事件名称: {medium_event.get('name')}
- 章节范围: {medium_event.get('chapter_range')} (共{chapter_count}章)
- 事件目标: {medium_event.get('main_goal')}

## 当前情节大纲（问题版）
{json.dumps(medium_event.get('plot_outline', []), ensure_ascii=False, indent=2)}

## 问题分析
当前只有 {event_info['current_count']} 个情节点，但 {chapter_count} 章的事件应该有 {event_info['expected_min']}-{event_info['expected_max']} 个情节点（每章4-6个）。

## 修复要求
请重新生成情节大纲，确保：
1. 总共 {event_info['expected_min']}-{event_info['expected_max']} 个情节点
2. 平均每章 4-6 个情节点
3. 情节点之间有时间递进关系（不要重复同一时间点）
4. 每个情节点应该具体、可展开为300-500字的场景
5. 保持原有的情节走向和目标不变，只是扩充/调整情节点数量

## 输出格式
直接返回JSON数组的字符串格式，例如：
[
  "情节点1：...",
  "情节点2：...",
  ...
]

请开始生成修复后的情节大纲："""

        try:
            # 直接调用API
            system_prompt = """你是一个小说情节规划专家。请严格按照用户要求生成情节大纲。
返回格式必须是JSON数组，例如：["情节点1", "情节点2", ...]
只返回JSON数组，不要有其他说明文字。"""

            result = api_client.call_api(
                system_prompt=system_prompt,
                user_prompt=prompt,
                purpose=f"修复中型事件'{event_info['name']}'的情节大纲"
            )

            if result:
                # 结果通常是字典，提取内容
                if isinstance(result, dict) and 'content' in result:
                    result = result['content']
                elif isinstance(result, dict) and 'raw_content' in result:
                    result = result['raw_content']
                elif not isinstance(result, str):
                    result = str(result)

                # 解析JSON数组
                import re
                # 尝试提取JSON数组
                json_match = re.search(r'\[\s*\{.*\}\s*\]', result, re.DOTALL)
                if json_match:
                    json_str = json_match.group(0)
                else:
                    # 尝试提取简单的字符串数组
                    json_match = re.search(r'\[.*?\]', result, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        print(f"   无法从返回结果中提取JSON")
                        print(f"   返回结果: {result[:500]}...")
                        continue

                try:
                    new_plot_outline = json.loads(json_str)

                    # 如果返回的不是字符串数组，尝试提取字符串
                    if not isinstance(new_plot_outline, list):
                        print(f"   返回的不是列表格式")
                        continue

                    # 确保每个元素是字符串
                    new_plot_outline = [str(item) for item in new_plot_outline]

                    print(f"   成功生成 {len(new_plot_outline)} 个情节点")
                    print(f"   新情节点: {new_plot_outline[0][:50]}...")

                    # 更新数据
                    medium_event['plot_outline'] = new_plot_outline
                    fixed_count += 1
                except json.JSONDecodeError as je:
                    print(f"   JSON解析失败: {je}")
                    print(f"   提取的字符串: {json_str[:200]}...")
            else:
                print(f"   API调用失败")

        except Exception as e:
            print(f"   修复出错: {e}")
            import traceback
            traceback.print_exc()

    # 保存修复后的文件
    backup_path = plan_file_path.replace(".json", "_before_fix_plot.json")
    with open(backup_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"\n已备份原文件到: {backup_path}")

    with open(plan_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\n修复完成！")
    print(f"成功修复: {fixed_count}/{len(events_to_fix)} 个事件")
    print(f"文件已保存: {plan_file_path}")


if __name__ == "__main__":
    plan_file = r"D:\work6.06\小说项目\全族偷听心声，我被迫无敌\plans\全族偷听心声，我被迫无敌_opening_stage_writing_plan.json"
    fix_plot_outline_for_medium_events(plan_file)
