# StagePlanManager.py
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import copy
import json
import re
import os
from typing import Any, Dict, Optional, List, Tuple
from pathlib import Path as PathlibPath
from src.managers.EventManager import EventManager
from datetime import datetime
from src.managers.EmotionalPlanManager import EmotionalPlanManager
from src.managers.StagePlanUtils import is_chapter_in_range, parse_chapter_range
from src.managers.WritingGuidanceManager import WritingGuidanceManager
from src.managers.RomancePatternManager import RomancePatternManager
from src.utils.logger import get_logger
class StagePlanManager:
    """剧情骨架设计器 - 专注如何将内容转化为剧情（怎么写）"""
    # ============================================================================
    # 内部辅助类 - 事件分解器 (已整合多个分解策略)
    # ============================================================================
    class _EventDecomposer:
        """统一的事件分解器 - 使用策略模式处理不同的分解方式"""
        def __init__(self, manager):
            self.logger = get_logger("_EventDecomposer")
            self.manager = manager
        def decompose(self, event: Dict, strategy: str = "smart") -> List[Dict]:
            if strategy == "chapter_scene":
                return self._decompose_to_chapter_then_scene(event)
            elif strategy == "direct_scene":
                return self._decompose_direct_to_scene(event)
            else:  # default: smart
                return self._smart_decompose(event)
        def _smart_decompose(self, major_event: Dict) -> List[Dict]:
            """智能分解策略 - 根据事件大小自动选择分解方式"""
            event_scale = major_event.get("scale", "medium")
            chapter_range = major_event.get("chapters", "1-10")
            if event_scale == "major":
                return self._decompose_to_chapter_then_scene(major_event)
            else:
                return self._decompose_direct_to_scene(major_event)
        def _decompose_to_chapter_then_scene(self, event: Dict) -> List[Dict]:
            """分解为 chapter → scene 的两层结构"""
            # 基本实现，可根据需要扩展
            result = []
            chapter_range = event.get("chapters", "1-10")
            scene_count = event.get("scene_count", 3)
            for i in range(scene_count):
                result.append({
                    "type": "scene",
                    "event": event,
                    "index": i + 1,
                    "chapter_context": chapter_range
                })
            return result
        def _decompose_direct_to_scene(self, event: Dict) -> List[Dict]:
            """直接分解为 scene 的一层结构"""
            result = []
            scene_count = event.get("scene_count", 2)
            for i in range(scene_count):
                result.append({
                    "type": "scene",
                    "event": event,
                    "index": i + 1
                })
            return result
    # ============================================================================
    # 内部辅助类 - 计划验证器 (已整合多个验证策略)
    # ============================================================================
    class _PlanValidator:
        """统一的计划验证器 - 整合所有验证逻辑"""
        def __init__(self, manager):
            self.logger = get_logger("_PlanValidator")
            self.manager = manager
        def validate(self, plan: Dict, level: str = "full") -> Dict:
            results = {}
            if level in ["chapters", "full"]:
                results["chapter_ranges"] = self._validate_chapter_ranges(plan)
            if level in ["hierarchy", "full"]:
                results["hierarchy"] = self._validate_goal_hierarchy(plan)
            if level in ["scenes", "full"]:
                results["scenes"] = self._validate_scene_coverage(plan)
            return results
        def _validate_chapter_ranges(self, plan: Dict) -> Dict:
            """验证章节范围的有效性"""
            events = plan.get("major_events", [])
            errors = []
            for event in events:
                chapter_range = event.get("chapters", "")
                if not chapter_range or "- " not in chapter_range:
                    errors.append(f"事件 '{event.get('name')}' 的章节范围无效")
            return {"valid": len(errors) == 0, "errors": errors}
        def _validate_goal_hierarchy(self, plan: Dict) -> Dict:
            """验证目标层级的一致性"""
            # 基本实现
            goals = plan.get("goals", [])
            return {"valid": len(goals) > 0, "goals_count": len(goals)}
        def _validate_scene_coverage(self, plan: Dict) -> Dict:
            """验证场景覆盖的完整性"""
            scenes = plan.get("scenes", [])
            return {"valid": len(scenes) > 0, "scenes_count": len(scenes)}
    # ============================================================================
    # StagePlanManager 主类初始化
    # ============================================================================
    # ============================================================================
    # StagePlanManager 主类初始化
    # ============================================================================
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.overall_stage_plans = None
        self.stage_boundaries = {}
        self.stage_writing_plans_cache = {}
        # 初始化日志系统
        self.logger = get_logger("StagePlanManager")
        # 初始化各个管理器
        self.event_manager = EventManager(self)
        self.writing_guidance_manager = WritingGuidanceManager(self)
        # 初始化辅助类实例
        self._event_decomposer = self._EventDecomposer(self)
        self._plan_validator = self._PlanValidator(self)
        # 为阶段计划创建专用的存储目录
        self.plans_dir = Path("./小说项目").resolve()
        os.makedirs(self.plans_dir, exist_ok=True)
        # 阶段特性描述（"起承转合"四段式）
        self.stage_characteristics = {
            "opening_stage": {
                "name": "起 (开局阶段)",
                "focus": "快速建立强烈冲突，立即吸引读者",
                "pace": "极快节奏，前3章必须建立核心冲突",
                "key_elements": "主角惊艳登场、立即冲突、强力悬念、读者共鸣",
                "critical_requirements": [
                    "前3000字内必须建立强烈冲突",
                    "第1章结尾必须有强力追读钩子", 
                    "减少世界观介绍，增加行动和冲突",
                    "主角特质在前2章完全展现"
                ]
            },
            "development_stage": {
                "name": "承 (发展阶段)",
                "focus": "深化矛盾，推进角色成长，扩展世界",
                "pace": "变化节奏，快慢结合，包含多个小高潮",
                "key_elements": "能力提升、盟友敌人、支线展开、伏笔埋设"
            },
            "climax_stage": {
                "name": "转 (高潮阶段)",
                "focus": "主要矛盾全面爆发，剧情发生重大转折",
                "pace": "紧张节奏，逐步加速，直至顶点",
                "key_elements": "关键对决、真相揭露、角色蜕变、情感宣泄"
            },
            "ending_stage": {
                "name": "合 (结局阶段)",
                "focus": "解决所有核心矛盾，收束全部线索，升华主题",
                "pace": "逐渐放缓，情感升华，带来圆满或引人深思的结局",
                "key_elements": "矛盾解决、伏笔回收、角色归宿、主题升华、情感共鸣"
            }
        }
    @property
    def emotional_manager(self):
        return self.generator.emotional_plan_manager
    @property
    def romance_manager(self):
        return getattr(self.generator, 'romance_manager', None)
    def generate_overall_stage_plan(self, creative_seed: str, novel_title: str, novel_synopsis: str, 
                                market_analysis: Dict, global_growth_plan: Dict, 
                                emotional_blueprint: Dict,
                                total_chapters: int) -> Optional[Dict]:
        """生成全书阶段计划（"起承转合"四段式）"""
        self.logger.info("=== 生成全书阶段计划 ===")
        stage_arcs = emotional_blueprint.get("stage_emotional_arcs", {})
        emotional_goals_prompt = []
        if stage_arcs:
            stage_name_map = {
                "opening_stage": "起 (开局阶段)",
                "development_stage": "承 (发展阶段)",
                "climax_stage": "转 (高潮阶段)",
                "ending_stage": "合 (结局阶段)" 
            }
            for stage_key, arc_info in stage_arcs.items():
                stage_name_cn = stage_name_map.get(stage_key, stage_key)
                emotional_goals_prompt.append(f"- **{stage_name_cn}**: {arc_info.get('description', '无特定情绪目标')}")
        emotional_goals_str = "\n".join(emotional_goals_prompt)
        boundaries = self.calculate_stage_boundaries(total_chapters)
        user_prompt = f"""
最高指令：以"情绪发展蓝图"和"创意种子"为绝对准则。
你的任务是设计一个服务于小说情绪发展的【剧情阶段规划】。所有剧情安排都必须为了实现预设的读者情绪目标。
# 情感战略目标 (来自情绪蓝图)
{emotional_goals_str}
# 核心参考资料 
创意种子: {creative_seed}
小说标题: {novel_title}
小说简介: {novel_synopsis}
总章节数: {total_chapters}
# 阶段划分要求
请将全书{total_chapters}章，按照经典的"起、承、转、合"四阶段结构进行划分，并为每个阶段制定详细的写作重点：
## 1. 起 (开局阶段，约前15%)
- **章节范围**: 第1章-第{boundaries['opening_end']}章
- **核心任务**: 快速建立故事基础，引入核心冲突，用强力钩子吸引读者。
- **【强制指令：开局核心目标】**: 你必须为这个阶段设定一个明确、具体、能驱动读者追读到第{boundaries['opening_end']}章的"开局核心目标 (opening_arc_goal)"。
## 2. 承 (发展阶段，约35%)
- **章节范围**: 第{boundaries['development_start']}章-第{boundaries['development_end']}章  
- **核心任务**: 深化并扩大矛盾，角色获得成长，世界观逐步展开。
## 3. 转 (高潮阶段，约30%)
- **章节范围**: 第{boundaries['climax_start']}章-第{boundaries['climax_end']}章
- **核心任务**: 主要矛盾全面爆发，迎来决定性的重大转折，情感集中宣泄。  
## 4. 合 (结局阶段，约20%)
- **章节范围**: 第{boundaries['ending_start']}章-第{total_chapters}章
- **核心任务**: 解决所有核心冲突，回收全部重要伏笔，交代角色归宿，升华主题。
"""
        result = self.generator.api_client.generate_content_with_retry(
            content_type="overall_stage_plan", 
            user_prompt=user_prompt, 
            purpose="制定全书阶段计划"
        )
        if result and isinstance(result, dict):
            self.overall_stage_plans = result
            self.stage_boundaries = boundaries
            self.generator.novel_data["overall_stage_plans"] = result
            self.logger.info("✓ 全书阶段计划生成成功")
            return result
        else:
            self.logger.error("❌ 全书阶段计划生成失败")
            return None
    def load_and_merge_all_plans(self):
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        stage_plan_dict = overall_plans.get("overall_stage_plan", {})
        if not stage_plan_dict:
            self.logger.warn("  ⚠️ 在 overall_stage_plans 中未找到阶段定义，无法预加载写作计划。")
            return 0
        available_stages = list(stage_plan_dict.keys())
        self.logger.info(f"📋 发现 {len(available_stages)} 个阶段，开始加载并合并写作计划到内存: {available_stages}")
        loaded_count = 0
        for stage_name in available_stages:
            # get_stage_writing_plan_by_name 会负责从文件加载并存入缓存
            if self.get_stage_writing_plan_by_name(stage_name):
                loaded_count += 1
        if loaded_count > 0:
            self.logger.info(f"  ✅ 成功加载 {loaded_count}/{len(available_stages)} 个阶段的写作计划到内存。")
        else:
            self.logger.warn("  ⚠️ 未能加载任何阶段的写作计划。")
        return loaded_count
    def calculate_stage_boundaries(self, total_chapters: int) -> Dict:
        """计算"起承转合"四阶段的边界"""
        # 比例: 起(15%), 承(35%), 转(30%), 合(20%)
        ratios = [0.15, 0.35, 0.30, 0.20]
        chapters = [0]
        cumulative_ratio = 0
        for ratio in ratios[:-1]:
            cumulative_ratio += ratio
            chapters.append(int(total_chapters * cumulative_ratio))
        chapters.append(total_chapters)
        return {
            "opening_end": chapters[1],
            "development_start": chapters[1] + 1,
            "development_end": chapters[2], 
            "climax_start": chapters[2] + 1,
            "climax_end": chapters[3],
            "ending_start": chapters[3] + 1,
        }
    def print_stage_overview(self):
        """打印详细的阶段计划概览"""
        if not self.overall_stage_plans:
            self.logger.info("暂无阶段计划数据")
            return
        self.logger.info("\n" + "=" * 60)
        self.logger.info("                   小说阶段计划概览")
        self.logger.info("=" * 60)
        total_chapters = 0
        stage_plan_dict = self.overall_stage_plans.get("overall_stage_plan", {})
        stage_map = {
            "opening_stage": "起 (开局阶段)",
            "development_stage": "承 (发展阶段)",
            "climax_stage": "转 (高潮阶段)",
            "ending_stage": "合 (结局阶段)"
        }
        for i, (stage_key, stage_info) in enumerate(stage_plan_dict.items(), 1):
            stage_name = stage_map.get(stage_key, stage_key)
            chapter_range = stage_info.get('chapter_range', '1-1')
            start_ch, end_ch = parse_chapter_range(chapter_range)
            chapter_count = end_ch - start_ch + 1
            total_chapters += chapter_count
            self.logger.info(f"\n📚 阶段 {i}: {stage_name}")
            self.logger.info(f"   📖 章节: {start_ch}-{end_ch}章 (共{chapter_count}章)")
            self.logger.info(f"   🎯 目标: {stage_info.get('stage_goal', stage_info.get('core_tasks', '暂无目标描述'))}")
            self.logger.info(f"   ⚡ 关键发展: {stage_info.get('key_developments', stage_info.get('key_content', '暂无关键事件'))}")
            if stage_info.get('core_conflicts'):
                self.logger.info(f"   ⚔️ 核心冲突: {stage_info.get('core_conflicts')}")
        self.logger.info(f"\n📈 总计: {len(stage_plan_dict)}个阶段，{total_chapters}章")
        self.logger.info("=" * 60)
    def _generate_basic_stage_plan(self, stage_name: str, stage_range: str, creative_seed: str,
                                novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        user_prompt = f"""
    请为小说阶段生成基础写作计划。
    ## 阶段信息
    - 阶段名称: {stage_name}
    - 章节范围: {stage_range}
    - 小说标题: {novel_title}
    - 小说简介: {novel_synopsis}
    - 创意种子: {creative_seed}
    ## 阶段总体目标
    {overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("stage_goal", "N/A")}
    请重点描述阶段策略、目标和关键节点，不要输出详细的事件列表。
"""
        result = self.generator.api_client.generate_content_with_retry(
            content_type="stage_writing_plan", 
            user_prompt=user_prompt, 
            purpose=f"生成{stage_name}基础计划"
        )
        return result
    def _assemble_final_plan(self, stage_name, stage_range, final_major_events, overall_stage_plan,
                        novel_title: str = "", novel_synopsis: str = "", creative_seed: str = "") -> Dict:
        self.logger.info(f"\n assembling final plan...")
        self.logger.info(f"  - 正在为阶段 '{stage_name}' ({stage_range}) 组装最终计划。")
        self.logger.info(f"  - 收到 {len(final_major_events)} 个已分解的重大事件。")
        # chapter_scene_map 的结构： 章节号 -> { "chapter_goal": str, "writing_focus": str, "scene_events": List[Dict] }
        chapter_scene_map = {}
        all_special_events = []
        emotional_summary = {
            "stage_emotional_arc": overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("emotional_goal", ""),
            "major_events_emotional_summary": [],
            "medium_events_emotional_focus": [] # 确保这个列表存在
        }
        # 遍历所有重大事件，累积其包含的中型事件场景和特殊情感事件
        for major_event in final_major_events:
            self.logger.info(f"    - 正在处理重大事件: '{major_event.get('name')}'")
            # 1. 收集重大事件的情感摘要
            emotional_summary["major_events_emotional_summary"].append({
                "name": major_event.get("name"),
                "emotional_goal": major_event.get("emotional_goal", ""),
                "emotional_arc_summary": major_event.get("emotional_arc_summary", "")
            })
            # 2. 收集重大事件中包含的特殊情感事件
            if "special_emotional_events" in major_event:
                all_special_events.extend(major_event["special_emotional_events"])
            # 3. 遍历重大事件的 'composition'，获取其中的中型事件并累积场景
            composition = major_event.get("composition", {})
            if not composition:
                self.logger.warn(f"      ⚠️ 警告: 重大事件 '{major_event.get('name')}' 缺少 'composition' 字段。")
                continue
            for phase_name, phase_events in composition.items():
                if not isinstance(phase_events, list):
                    self.logger.warn(f"      ⚠️ 警告: 重大事件 '{major_event.get('name')}' 的 '{phase_name}' 部分不是一个列表。")
                    continue
                for medium_event in phase_events:
                    self.logger.info(f"      - 正在处理中型事件: '{medium_event.get('name')}' (位于'{phase_name}'阶段)")
                    # 收集中型事件的情感焦点
                    if "emotional_focus" in medium_event:
                        emotional_summary["medium_events_emotional_focus"].append({
                            "name": medium_event.get("name"),
                            "emotional_focus": medium_event.get("emotional_focus"),
                            "emotional_intensity": medium_event.get("emotional_intensity", "medium")
                        })
                    # 【核心逻辑】调用辅助函数来累积中型事件中的场景
                    self._add_scenes_from_decomposed_event(medium_event, chapter_scene_map)
        # 将 chapter_scene_map 转换为按章节排序的列表
        chapter_scene_events_list = []
        # 安全地获取所有章节号并排序
        all_chapter_nums = sorted(chapter_scene_map.keys())
        self.logger.info(f"  - 场景累积完成，共覆盖 {len(all_chapter_nums)} 个章节。正在转换为最终列表...")
        for chapter_num in all_chapter_nums:
            chapter_info = chapter_scene_map[chapter_num]
            # 确保每个章节至少有一个空的 scene_events 列表
            if "scene_events" not in chapter_info:
                chapter_info["scene_events"] = []
            chapter_scene_events_list.append({
                "chapter_number": chapter_num,
                "chapter_goal": chapter_info.get("chapter_goal", f"完成第{chapter_num}章内容"),
                "writing_focus": chapter_info.get("writing_focus", "保持章节内容连贯性和吸引力"),
                "scene_events": chapter_info.get("scene_events", [])
            })
        stage_info = overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {})
        stage_overview_text = stage_info.get("stage_goal", stage_info.get("core_tasks", "N/A"))
        stage_plan = {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "stage_overview": stage_overview_text,
                "novel_metadata": {
                    "title": novel_title,
                    "synopsis": novel_synopsis,
                    "creative_seed": creative_seed,
                    "generation_timestamp": datetime.now().isoformat()
                },
                "emotional_summary": emotional_summary,
                "event_system": {
                    "overall_approach": "采用智能分形设计：根据章节数自动选择分解策略，最终基于场景事件构建章节。",
                    "major_events": final_major_events,
                    "special_emotional_events": all_special_events,
                    "chapter_scene_events": chapter_scene_events_list
                },
            }
        }
        self.logger.info(f"  ✅ 阶段 '{stage_name}' 的最终计划组装完成！")
        return stage_plan
    def _validate_chapter_ranges(self, all_events: List[Dict], total_chapters: int) -> bool:
        """验证所有事件的章节范围"""
        self.logger.info(f"  🔍 开始验证章节范围，共{len(all_events)}个事件，总章节数{total_chapters}")
        chapter_occupancy = [[] for _ in range(total_chapters + 1)]
        validation_errors = []
        for event in all_events:
            event_name = event.get("event_name", event.get("name", "未知事件"))
            chapter_range_str = event.get("chapter_range")
            if not chapter_range_str:
                validation_errors.append(f"事件 '{event_name}' 缺少 'chapter_range'")
                continue
            try:
                start_chapter, end_chapter = self.parse_chapter_range(chapter_range_str)
                # 验证章节范围合理性
                if not (1 <= start_chapter <= end_chapter <= total_chapters):
                    validation_errors.append(f"事件 '{event_name}' 的章节范围 {chapter_range_str} 超出总章节数 {total_chapters}")
                    continue
                # 检查重叠
                for chapter_num in range(start_chapter, end_chapter + 1):
                    chapter_occupancy[chapter_num].append(event_name)
            except Exception as e:
                validation_errors.append(f"事件 '{event_name}' 的 chapter_range 格式错误: '{chapter_range_str}' - {e}")
        # 检查重叠情况
        for i, occupied_events in enumerate(chapter_occupancy):
            if i == 0: 
                continue
            if len(occupied_events) > 1:
                validation_errors.append(f"章节 {i} 存在重叠事件: {', '.join(occupied_events)}")
        # 输出验证结果
        if validation_errors:
            self.logger.error(f"  ❌ 章节范围验证失败，发现 {len(validation_errors)} 个问题:")
            for error in validation_errors[:5]:  # 只显示前5个错误
                self.logger.info(f"    - {error}")
            if len(validation_errors) > 5:
                self.logger.info(f"    - ... 还有{len(validation_errors)-5}个错误")
            return False
        else:
            self.logger.info("  ✅ 章节范围验证通过")
            return True
    def _generate_scenes_for_single_chapter_event(self, event_data: Dict, chapter_num: int,
                                                  stage_name: str, major_event_name: str,
                                                  novel_title: str, novel_synopsis: str,
                                                  consistency_guidance: Optional[str] = None) -> List[Dict]:
        event_name = event_data.get("name", "特殊情感事件")
        purpose = event_data.get("main_goal", event_data.get("purpose", "深化情感，调整节奏，作为本章的核心任务。"))
        # 【已补充】提取并使用这两个关键字段
        event_subtype = event_data.get("event_subtype", "emotional_beat")
        placement_hint = event_data.get("placement_hint", "未指定位置")
        emotional_focus = event_data.get("emotional_focus", "未指定")
        description = event_data.get("description", "未提供详细描述")
        key_beats = event_data.get("key_emotional_beats", [])
        contribution = event_data.get("contribution_to_major", "未指定")
        key_beats_str = "\n".join([f"- {beat}" for beat in key_beats]) if key_beats else "未指定"
        consistency_block = ""
        if consistency_guidance:
            consistency_block = f"""
## 一致性铁律 (必须严格遵守)
你在进行场景构建时，必须严格遵守以下已确定的世界事实，确保新生成的场景不会与历史情节产生矛盾。
{consistency_guidance}
"""
        self.logger.info(f"      ⚙️ 正在为事件 '{event_name}' (第{chapter_num}章) 请求多场景生成...")
        prompt = f"""
# 任务：为单一章节的核心事件生成场景序列
你是一名专业的网文白金策划师。你需要为一个占据单一章节的【核心事件】设计详细的场景事件序列。确保本章拥有完整的叙事和情感弧线，服务于该事件的叙事和情感目的。
{consistency_block}
## 当前事件的完整上下文信息 (必须严格参考)
- **小说标题**: {novel_title}
- **小说简介**: {novel_synopsis}
- **当前章节**: 第 {chapter_num} 章
- **所属阶段**: {stage_name}
- **所属重大事件**: {major_event_name}
- **本章核心事件名称**: {event_name}
### **【事件定位与类型】(用于确定本章的基调和节奏)**
- **事件子类型 (Subtype)**: {event_subtype}
- **在情节中的位置 (Placement Hint)**: {placement_hint}
### **【本章叙事和情感核心】**
- **核心目标 (Main Goal)**: {purpose}
- **情感焦点 (Emotional Focus)**: {emotional_focus}
- **对上层事件的贡献**: {contribution}
### **【关键情节与细节参考】**
- **情节描述 (Description)**: {description}
- **关键情感节拍 (Key Emotional Beats)**:
{key_beats_str}
## 场景构建要求
请为第 {chapter_num} 章设计 **4-6个场景事件**，形成一个具备完整戏剧结构的序列。
你的设计必须完全服务于上述提供的所有上下文信息，特别是【事件定位与类型】和【本章叙事和情感核心】，确保本章的氛围、节奏和内容与整体规划完美契合。
"""     
        try:
            result = self.generator.api_client.generate_content_with_retry(
                content_type="special_event_scene_generation",
                user_prompt=prompt,
                purpose=f"为特殊情感事件'{event_name}'在第{chapter_num}章生成场景序列"
            )
            # 验证返回结果是列表且包含有效的场景对象
            if isinstance(result, list) and all(isinstance(item, dict) and "name" in item and "purpose" in item for item in result):
                self.logger.info(f"      ✅ 为特殊事件 '{event_name}' 在第 {chapter_num} 章成功生成了 {len(result)} 个场景。")
                return result
            else:
                self.logger.error(f"      ❌ 为特殊事件 '{event_name}' 在第 {chapter_num} 章生成场景失败：AI返回格式不正确或为空。")
                self.logger.info(f"         AI返回数据: {result}")
                return []
        except Exception as e:
            self.logger.error(f"      ❌ 调用API生成特殊事件场景时出错: {e}")
            return []
    def save_and_cache_stage_plan(self, stage_name: str, plan_data: Dict):
        if not stage_name or not plan_data:
            self.logger.error("  ❌ 保存失败：stage_name 或 plan_data 为空。")
            return
        
        # 获取小说标题
        novel_title = self.generator.novel_data.get("novel_title", "unknown")
        
        # 1. 使用统一路径管理器保存
        from src.utils.path_manager import path_manager
        success = path_manager.save_stage_plan(novel_title, stage_name, plan_data)
        if success:
            self.logger.info(f"  ✅ 阶段 '{stage_name}' 的计划已通过统一路径管理器保存")
        else:
            self.logger.error(f"  ❌ 阶段 '{stage_name}' 的计划保存失败")
            return
        
        # 2. 更新内存缓存
        cache_key = f"{stage_name}_writing_plan"
        self.stage_writing_plans_cache[cache_key] = plan_data
        self.logger.info(f"  ✅ 阶段 '{stage_name}' 的计划已更新缓存")
    def _generate_fallback_scenes_for_chapter(self, chapter_number: int, stage_name: str, 
                                          final_major_events: List[Dict], overall_stage_plan: Dict,
                                          novel_title: str, novel_synopsis: str,
                                          core_worldview: Dict, character_design: Dict, 
                                          writing_style_guide: Dict, previous_chapters_summary: str) -> List[Dict]:
        self.logger.info(f"  🚑 [补救措施] 启动，为第 {chapter_number} 章生成紧急场景规划...")
        # 1. 查找该章节的上下文（它属于哪个事件？）
        event_context = "未知，请根据阶段总体目标进行常规推进。"
        for major_event in final_major_events:
            if self.is_chapter_in_range(chapter_number, major_event.get("chapter_range", "")):
                event_context = (f"本章属于重大事件 '{major_event.get('name')}'，"
                                 f"其目标是: {major_event.get('main_goal')}")
                # 进一步查找中型事件
                for phase_events in major_event.get("composition", {}).values():
                    for medium_event in phase_events:
                        if self.is_chapter_in_range(chapter_number, medium_event.get("chapter_range", "")):
                            event_context += (f"\n更具体地，属于中型事件 '{medium_event.get('name')}'，"
                                              f"其目标是: {medium_event.get('main_goal')}")
                            break
                break
        # 2. 构建紧急生成Prompt
        stage_goal = overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("stage_goal", "N/A")
        # 格式化新增的上下文信息
        worldview_str = json.dumps(core_worldview, ensure_ascii=False, indent=2) if core_worldview else "未提供世界观设定。"
        character_str = json.dumps(character_design, ensure_ascii=False, indent=2) if character_design else "未提供角色设计。"
        style_guide_str = json.dumps(writing_style_guide, ensure_ascii=False, indent=2) if writing_style_guide else "未提供写作风格指南。"
        prompt = f"""
任务：紧急场景补全
你好，我是小说生成系统。在我的计划中，第 {chapter_number} 章的场景规划意外丢失了。我需要你根据以下上下文，为这一章紧急生成一个包含4-6个场景的完整场景列表，以确保故事能够连贯。
上下文信息
小说标题: {novel_title}
小说简介: {novel_synopsis}
当前阶段: {stage_name} (目标: {stage_goal})
本章所属事件: {event_context}
前情提要: {previous_chapters_summary}
核心世界观设定:
JSON
{worldview_str}
角色设计概览:
JSON
{character_str}
写作风格指南:
JSON
{style_guide_str}
场景构建要求
请为本章设计 4 到 6 个场景，确保它们共同构成一个有“起、承、转、合”的完整戏剧结构。
每个场景都必须紧密围绕本章的叙事任务和所属阶段目标展开，并与上述世界观、角色和写作风格保持高度一致。
结尾场景应包含一个明确的钩子 (hook)，以吸引读者继续阅读下一章。
"""
        # 3. 调用API
        try:
            fallback_result = self.generator.api_client.generate_content_with_retry(
                content_type="fallback_scene_generation",
                user_prompt=prompt,
                purpose=f"紧急补全第{chapter_number}章场景"
            )
            # 检查返回的是否是包含 "fallback_scenes" 键的字典
            if (isinstance(fallback_result, dict) and 
                "fallback_scenes" in fallback_result and 
                isinstance(fallback_result["fallback_scenes"], list) and
                len(fallback_result["fallback_scenes"]) > 0):
                scenes_list = fallback_result["fallback_scenes"]
                self.logger.info(f"  ✅ 第 {chapter_number} 章补救成功，生成了 {len(scenes_list)} 个场景。")
                # 为每个场景添加缺失的默认值，增强健壮性
                for scene in scenes_list:
                    scene.setdefault('type', 'scene_event')
                return scenes_list
            else:
                self.logger.error(f"  ❌ 第 {chapter_number} 章补救失败，AI未返回有效格式的场景对象。")
                self.logger.info(f"     收到的数据类型: {type(fallback_result)}")
                return []
        except Exception as e:
            self.logger.error(f"  ❌ 调用补救API时发生错误: {e}")
            return []
    def repair_writing_plan(self, plan_container: dict) -> tuple[dict, bool]:
        self.logger.info("  - 正在检查计划的场景覆盖完整性...")
        repaired_plan = copy.deepcopy(plan_container)
        plan_data = repaired_plan.get("stage_writing_plan", repaired_plan)
        # 提取上下文信息
        novel_title = plan_data.get("novel_metadata", {}).get("title", "未知标题")
        novel_synopsis = plan_data.get("novel_metadata", {}).get("synopsis", "未知简介")
        stage_name = plan_data.get("stage_name", "未知阶段")
        # 使用 validate_scene_planning_coverage 方法来精确找到缺失的章节
        stage_range = plan_data.get("chapter_range", "1-100")
        coverage_analysis = self.validate_scene_planning_coverage(repaired_plan, stage_name, stage_range)
        missing_chapters = coverage_analysis.get("missing_chapters", [])
        if not missing_chapters:
            self.logger.info("  ✅ 场景覆盖完整，无需修复。")
            return repaired_plan, False
        self.logger.warn(f"  ⚠️ 检测到 {len(missing_chapters)} 个章节缺少场景，正在尝试修复: {missing_chapters}")
        chapters_repaired_count = 0
        # 补救方法需要事件上下文
        final_major_events = plan_data.get("event_system", {}).get("major_events", [])
        overall_stage_plan = self.generator.novel_data.get("overall_stage_plans", {})
        # --- 新增获取全局小说数据 ---
        novel_global_data = self.generator.novel_data # 获取完整的 novel_data
        core_worldview = novel_global_data.get("core_worldview", {})
        character_design = novel_global_data.get("character_design", {})
        writing_style_guide = novel_global_data.get("writing_style_guide", {})
        # 在规划阶段的 fallback，前情提要可以简化为小说简介
        previous_chapters_summary_for_fallback = novel_global_data.get("novel_synopsis", "这是章节规划阶段的紧急生成，此前内容不详。")
        # --- 结束新增 ---
        for chapter_num in missing_chapters:
            fallback_scenes = self._generate_fallback_scenes_for_chapter(
                chapter_number=chapter_num,
                stage_name=stage_name,
                final_major_events=final_major_events,
                overall_stage_plan=overall_stage_plan,
                novel_title=novel_title,
                novel_synopsis=novel_synopsis,
                # --- 传递新增参数 ---
                core_worldview=core_worldview,
                character_design=character_design,
                writing_style_guide=writing_style_guide,
                previous_chapters_summary=previous_chapters_summary_for_fallback
                # --- 结束传递 ---
            )
            if fallback_scenes:
                plan_data.get("event_system", {}).get("chapter_scene_events", []).append({
                    "chapter_number": chapter_num,
                    "scene_events": fallback_scenes
                })
                chapters_repaired_count += 1
                self.logger.info(f"    -> 第 {chapter_num} 章修复成功。")
            else:
                self.logger.error(f"    -> ❌ 第 {chapter_num} 章修复失败。")
        if chapters_repaired_count > 0:
            # 修复后重新排序，保证章节顺序
            plan_data.get("event_system", {}).get("chapter_scene_events", []).sort(key=lambda x: x["chapter_number"])
            self.logger.info(f"  🎉 成功修复了 {chapters_repaired_count} 个章节！")
            return repaired_plan, True
        return repaired_plan, False
    def repair_all_stage_plans(self):
        self.logger.info("\n" + "="*25 + " 完整性检查与修复 " + "="*25)
        self.logger.info("🚀 开始对所有已生成的阶段计划进行场景覆盖完整性检查...")
        # 从 novel_data 中获取所有阶段计划的路径信息
        stage_plans_meta = self.generator.novel_data.get("stage_writing_plans", {})
        if not stage_plans_meta:
            self.logger.warn("  ⚠️ 未找到任何已生成的阶段计划信息，跳过修复流程。")
            return
        total_repaired_files = 0
        for stage_name, plan_info in stage_plans_meta.items():
            self.logger.info(f"\n🔍 正在处理阶段: 【{stage_name}】")
            # 使用我们已有的加载逻辑来获取计划数据
            plan_data = self._load_plan_from_file(stage_name)
            if not plan_data:
                self.logger.error(f"  ❌ 无法加载阶段 '{stage_name}' 的计划文件，跳过。")
                continue
            # 调用单个计划的修复工具
            repaired_plan, was_modified = self.repair_writing_plan(plan_data)
            # 如果文件被修改了，就保存回去，覆盖原文件
            if was_modified:
                self.logger.info(f"  💾 检测到计划已更新，正在保存回文件...")
                self._save_plan_to_file(stage_name, repaired_plan)
                total_repaired_files += 1
        if total_repaired_files > 0:
            self.logger.info(f"\n🎉 全局修复完成！共 {total_repaired_files} 个阶段计划文件被更新。")
        else:
            self.logger.info("\n✅ 全局检查完成，所有阶段计划的场景覆盖均完整。")
        self.logger.info("="*68 + "\n")
    @staticmethod
    def parse_chapter_range(range_str: str) -> tuple:
        try:
            if not range_str:
                return 1, 100
            # 清理字符串：移除"第"、"章"、中文括号及其内容等字符，只保留数字和横杠
            # 先移除中文括号及其内容（如：（前段）、（后段）等）
            cleaned_str = re.sub(r'[（(][^）)]*[）)]', '', str(range_str))
            # 再移除"第"、"章"、空白字符
            cleaned_str = re.sub(r'[第章\s]', '', cleaned_str).strip()
            if "-" in cleaned_str:
                parts = cleaned_str.split("-")
                if len(parts) == 2:
                    start = int(parts[0])
                    end = int(parts[1])
                    return start, end
            else:
                # 如果只有单个数字
                chapter = int(cleaned_str)
                return chapter, chapter
        except (ValueError, AttributeError, IndexError) as e:
            # 不能使用self.logger，因为这是静态方法
            # 改为使用模块级日志
            from src.utils.logger import get_logger
            logger = get_logger("StagePlanManager")
            logger.warn(f"⚠️ 解析章节范围失败: '{range_str}'，错误: {e}，使用默认值(1, 100)")
            return 1, 100
    def _smart_decompose_medium_events(self, major_event: Dict, stage_name: str,
                                    novel_title: str, novel_synopsis: str, creative_seed: str,
                                    consistency_guidance: Optional[str] = None) -> Dict:
        # 收集所有中型事件
        all_medium_events = []
        composition = major_event.get("composition", {})
        for phase_events in composition.values():
            all_medium_events.extend(phase_events)
        # 为每个中型事件智能选择分解策略
        decomposed_medium_events = []
        for medium_event in all_medium_events:
            chapter_range = medium_event.get('chapter_range', '0-0')
            start_ch, end_ch = self.parse_chapter_range(chapter_range)
            chapter_count = end_ch - start_ch + 1
            if chapter_count > 3:
                # 章节数>3，先分解为章节事件，再分解为场景事件
                self.logger.info(f"    -> 中型事件'{medium_event['name']}'({chapter_count}章) 进行章节事件+场景事件分解")
                decomposed_event = self._decompose_medium_to_chapter_then_scene(
                    medium_event, major_event, stage_name, novel_title, novel_synopsis, creative_seed,
                    consistency_guidance=consistency_guidance
                )
            else:
                # 章节数<3，直接分解为场景事件
                self.logger.info(f"    -> 中型事件'{medium_event['name']}'({chapter_count}章) 直接进行场景事件分解")
                decomposed_event = self._decompose_medium_direct_to_scene(
                    medium_event, major_event, stage_name, novel_title, novel_synopsis, creative_seed,
                    consistency_guidance=consistency_guidance
                )
            if decomposed_event:
                # 保留中型事件的核心目标信息
                decomposed_event.update({
                    "main_goal": medium_event.get("main_goal", ""),
                    "emotional_focus": medium_event.get("emotional_focus", ""),
                    "emotional_intensity": medium_event.get("emotional_intensity", "medium"),
                    "key_emotional_beats": medium_event.get("key_emotional_beats", []),
                    "contribution_to_major": medium_event.get("contribution_to_major", "")
                })
                decomposed_medium_events.append(decomposed_event)
        # 修复：正确更新重大事件的composition
        major_event_copy = major_event.copy()
        major_event_copy["composition"] = {}
        for phase_name, phase_events in composition.items():
            major_event_copy["composition"][phase_name] = []
            for event in phase_events:
                # 找到对应的分解后中型事件
                decomposed_event = next((de for de in decomposed_medium_events 
                                    if de['name'] == event['name']), event)  # 如果没找到，使用原事件
                major_event_copy["composition"][phase_name].append(decomposed_event)
        return major_event_copy
    def _decompose_medium_to_chapter_then_scene(self, medium_event: Dict, major_event: Dict, stage_name: str,
                                            novel_title: str, novel_synopsis: str, creative_seed: str, consistency_guidance: Optional[str] = None) -> Dict:
        consistency_block = ""
        if consistency_guidance:
            consistency_block = f"""
            一致性铁律 (必须遵守)
            你在进行事件分解时，必须严格遵守以下已确定的世界事实，确保新生成的事件不会与历史情节产生矛盾。
            {consistency_guidance}
            """
            # 第一步：分解为章节事件
        chapter_events_prompt = f"""
# 任务：中型事件"章节分解" - 服务于中型事件目标
{consistency_block}
你需要将一个多章的中型事件分解为具体的章节事件，每个章节事件覆盖1章，确保服务于中型事件的目标。
## 当前中型事件信息
- **所属阶段**: {stage_name}
- **所属重大事件**: {major_event.get('name')}
- **中型事件名称**: {medium_event.get('name')}
- **事件章节范围**: {medium_event.get('chapter_range')}
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
- **服务重大事件**: {medium_event.get('contribution_to_major')}
## 分解要求
请将这个中型事件分解为在{medium_event.get('chapter_range')}范围内的各个章节事件，确保：
1. 每个章节事件有明确的目标，服务于中型事件的核心目标
2. 章节之间要有连贯性和递进关系，服务于中型事件的emotional_focus
3. 形成完整的"起承转合"结构，服务于中型事件在重大事件中的角色
## 输出格式
{{
    "name": "{medium_event.get('name')}",
    "type": "medium_event",
    "chapter_range": "{medium_event.get('chapter_range')}",
    "main_goal": "{medium_event.get('main_goal')}",
    "emotional_focus": "{medium_event.get('emotional_focus')}",
    "description": "{medium_event.get('description')}",
    "decomposition_type": "chapter_then_scene",
    "contribution_to_major": "{medium_event.get('contribution_to_major')}",
    "chapter_events": [
        {{
            "name": "章节事件名称",
            "type": "chapter_event", 
            "chapter_range": "string // 单章范围，例如：'49-49章'",
            "main_goal": "该章节要达成的具体目标（服务于中型事件目标）",
            "emotional_focus": "本章的情绪重点（服务于中型事件emotional_focus）",
            "emotional_turn": "本章的情感转折点",
            "structural_role": "在事件中的结构作用 (起/承/转/合)",
            "contribution_to_medium": "如何服务于中型事件目标"
        }},
        // ... 更多章节事件
    ]
}}
"""
        chapter_events_result = self.generator.api_client.generate_content_with_retry(
            content_type="medium_event_decomposition", 
            user_prompt=chapter_events_prompt, 
            purpose=f"分解中型事件'{medium_event.get('name')}'为章节事件"
        )
        if not chapter_events_result:
            return None
        # 第二步：为每个章节事件分解为场景事件
        scene_structured_chapters = []
        for chapter_event in chapter_events_result.get("chapter_events", []):
            scene_structure_prompt = f"""
    # 任务：章节事件"场景结构构建" - 服务于章节事件目标
    你需要为一个章节事件设计完整的场景结构，确保章节内部有完整的戏剧发展和情感弧线，服务于章节事件的目标。
    ## 当前章节事件信息
    - **所属阶段**: {stage_name}
    - **所属重大事件**: {major_event.get('name')}
    - **所属中型事件**: {medium_event.get('name')}
    - **章节事件名称**: {chapter_event.get('name')}
    - **章节范围**: {chapter_event.get('chapter_range')}
    - **章节目标**: {chapter_event.get('main_goal')}
    - **章节情绪重点**: {chapter_event.get('emotional_focus')}
    - **情感转折**: {chapter_event.get('emotional_turn')}
    - **结构作用**: {chapter_event.get('structural_role')}
    - **服务中型事件**: {chapter_event.get('contribution_to_medium')}
    ## 场景构建要求
    请为这个章节设计4-6个场景事件，形成完整的戏剧结构，服务于章节目标：
    ### 每章的结构要求：
    1. **开场场景** (15-20%)：建立情境，引入冲突，服务于章节目标
    2. **发展场景1** (20-25%)：推进情节，深化冲突，服务于章节目标  
    3. **发展场景2** (20-25%)：冲突升级，逼近高潮，服务于章节目标
    4. **高潮场景** (15-20%)：情感爆发，关键转折，服务于章节目标
    5. **回落场景** (10-15%)：处理后果，情感沉淀，服务于章节目标
    6. **结尾场景** (5-10%)：设置悬念，引导下一章，服务于章节目标
    ## 输出格式
    {{
        "name": "{chapter_event.get('name')}",
        "type": "chapter_event",
        "chapter_range": "{chapter_event.get('chapter_range')}",
        "main_goal": "{chapter_event.get('main_goal')}",
        "emotional_focus": "{chapter_event.get('emotional_focus')}",
        "emotional_turn": "{chapter_event.get('emotional_turn')}",
        "structural_role": "{chapter_event.get('structural_role')}",
        "contribution_to_medium": "{chapter_event.get('contribution_to_medium')}",
        "scene_structure": {{
            "overall_pace": "string // 本章节奏描述",
            "emotional_arc": "string // 本章情感发展曲线",
            "scenes": [
                {{
                    "name": "场景名称",
                    "type": "scene_event",
                    "position": "opening/development1/development2/climax/falling/ending",
                    "purpose": "场景的戏剧目的（服务于章节目标）",
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "场景的情感冲击（服务于章节emotional_focus）",
                    "dialogue_highlights": ["关键对话1", "关键对话2"],
                    "conflict_point": "冲突的具体表现",
                    "sensory_details": "需要突出的感官细节",
                    "transition_to_next": "如何过渡到下一个场景",
                    "estimated_word_count": "预估字数范围，需要非常精炼",
                    "contribution_to_chapter": "如何服务于章节目标"
                }},
                // ... 更多场景事件 (总共4-6个)
            ],
            "chapter_hook": "string // 章节结尾的悬念钩子",
            "writing_focus": "string // 本章写作重点提示"
        }}
    }}
"""
            scene_result = self.generator.api_client.generate_content_with_retry(
                content_type="chapter_event_design", 
                user_prompt=scene_structure_prompt, 
                purpose=f"为章节事件'{chapter_event.get('name')}'构建场景结构"
            )
            if scene_result:
                scene_structured_chapters.append(scene_result)
            else:
                # 如果场景结构生成失败，至少保留章节事件
                scene_structured_chapters.append(chapter_event)
        # 修复：确保更新章节事件为场景结构化版本
        if scene_structured_chapters:
            chapter_events_result["chapter_events"] = scene_structured_chapters
        return chapter_events_result
    def validate_goal_hierarchy_coherence(self, stage_writing_plan: Dict, stage_name: str) -> Dict:
        self.logger.info(f"  🤖 【网文白金策划师】正在评估{stage_name}阶段目标层级一致性...")
        # 提取阶段计划中的关键信息
        if "stage_writing_plan" in stage_writing_plan:
            plan_data = stage_writing_plan["stage_writing_plan"]
        else:
            plan_data = stage_writing_plan
        event_system = plan_data.get("event_system", {})
        major_events = event_system.get("major_events", [])
        # 构建目标层级评估提示词
        coherence_prompt = self._build_goal_hierarchy_prompt(
            stage_name, plan_data, major_events
        )
        try:
            coherence_assessment = self.generator.api_client.generate_content_with_retry(
                content_type="goal_hierarchy_coherence_assessment_master_reviewer", # 新ID
                user_prompt=coherence_prompt,
                purpose=f"【网文白金策划师】评估{stage_name}阶段目标层级一致性"
            )
            if coherence_assessment:
                self.logger.info(f"  ✅ 【网文白金策划师】评估{stage_name}阶段目标层级一致性完成。")
                return coherence_assessment
            else:
                self.logger.warn(f"  ⚠️ 【网文白金策划师】评估{stage_name}阶段目标层级一致性失败，使用默认结果。")
                return self._create_default_coherence_assessment()
        except Exception as e:
            self.logger.error(f"  ❌ 【网文白金策划师】目标层级评估出错: {e}，使用默认结果。")
            return self._create_default_coherence_assessment()
    def _build_goal_hierarchy_prompt(self, stage_name: str, plan_data: Dict, major_events: List[Dict]) -> str:
        # 构建事件层级结构的详细描述
        hierarchy_description = self._build_hierarchy_description(major_events)
        prompt_parts = [
            "# 🎯 【AI网文白金策划师】对阶段事件目标层级一致性进行“商业价值”深度评估",
            "",
            "## 评估任务",
            f"作为一位对网文爆款打造和读者留存有着极致追求的【网文白金策划师】，你将对**{stage_name}**阶段的事件目标层级进行“商业价值”深度评估。",
            "你的目标是：确保从最高层（阶段目标）到最低层（场景事件目标）的每一次分解都**高效精准、逻辑自洽、能最大化地服务于小说的爆款潜力、商业价值和读者留存率**。你不能容忍任何模糊、断裂或拖沓之处。",
            "",
            "## 事件层级结构详情",
            hierarchy_description,
            "",
            "## 评估维度 (请以“爆款网文”的标准进行评判，1-10分制，并给出极其详细的评语)：",
            "",
            "### 1. 目标传递连贯性与效率 (权重 20%)",
            "- 重大事件目标是否**高效且清晰地分解**到中型事件，没有丝毫断裂或浪费？",
            "- 中型事件目标是否**精准地**服务于重大事件目标？", 
            "- 章节事件目标是否**有力地支持**中型事件目标，且具备足够的驱动力？",
            "- 场景事件目标是否**直接地服务**于章节事件目标，且每个场景都不可或缺？",
            "- 是否存在任何目标传递的断裂、模糊、冗余或拖沓之处？",
            "",
            "### 2. 情绪目标一致性与爽点分布 (权重 20%)",
            "- 情绪目标在层级间是否**连贯且能有效调动读者情绪**？",
            "- 情绪强度和节奏变化是否**张弛有度，高潮迭起，具备强烈爽感**？",
            "- 情感节拍是否**精准无误地服务于整体情绪目标**，且能引发读者共鸣？",
            "- 是否存在情感曲线的突兀、平淡或刻意之处？",
            "",
            "### 3. 贡献关系明确性与驱动力 (权重 15%)",
            "- 每个事件是否**极其明确地说明了对上一级事件的核心贡献**？",
            "- 贡献描述是否**具体、可执行、且具有强大的情节推动力**？",
            "- 是否存在贡献关系模糊、缺乏深度或驱动力不足的情况？",
            "",
            "### 4. 逻辑自洽性与新意融合 (权重 15%)",
            "- 事件分解是否**逻辑自洽，读者可接受**？",
            "- 章节分配是否**合理支撑目标实现的需求**，且没有一丝冗余或拖沓？",
            "- 场景安排是否**新颖且有效地支持事件目标的达成**，避免无趣的套路？",
            "- 是否存在任何逻辑漏洞、重复情节或缺乏新意之处？",
            "",
            "### 5. 可执行性与写作指导性 (权重 10%)",
            "- 最底层的事件目标是否**足够具体、清晰，可以直接指导写作，且可直接转化为写作细节**？",
            "- 是否存在目标过于抽象、模糊，或在实际写作中难以操作的情况？",
            "",
            "### 6. 主题融合度 (权重 10%)",
            "- 各层级事件目标是否**自然地融合并体现阶段和全书的主题**？",
            "- 在事件推进中，主题是否得到**有效且直接的表达**？",
            "- 是否有任何偏离主题或未能有效表达主题之处？",
            "",
            "### 7. 角色成长驱动力 (权重 10%)",
            "- 各层级事件目标是否**强力驱动主要角色的成长和蜕变**，符合读者的期待？",
            "- 角色在这些事件中是否有**足够的行动空间、内心挣扎和高光时刻**？",
            "- 是否存在未能有效促进角色发展，或使角色行为僵化之处？",
            "",
            "## 🎯 评估要求",
            "请提供**极其具体、可操作的评估结果**和**提升至爆款网文的改进建议**。",
            "对于每个维度，请给出1-10分的评分，并附上详细的评语和建议。",
            "",
            "## 📋 输出格式",
            "请以严格的JSON格式返回评估结果：",
            "{",
            '  "overall_coherence_score": "float // 根据上述权重计算出的总一致性评分 (满分10分)",',
            '  "goal_transfer_score": "float // 目标传递连贯性与效率评分 (1-10)",',
            '  "goal_transfer_comment": "string // 详细评语及优化建议",',
            '  "emotional_coherence_score": "float // 情绪目标一致性与爽点分布评分 (1-10)",',
            '  "emotional_coherence_comment": "string // 详细评语及优化建议",',
            '  "contribution_clarity_score": "float // 贡献关系明确性与驱动力评分 (1-10)",',
            '  "contribution_clarity_comment": "string // 详细评语及优化建议",',
            '  "logic_innovation_score": "float // 逻辑自洽性与新意融合评分 (1-10)",',
            '  "logic_innovation_comment": "string // 详细评语及优化建议",',
            '  "executability_score": "float // 可执行性与写作指导性评分 (1-10)",',
            '  "executability_comment": "string // 详细评语及优化建议",',
            '  "thematic_deepening_score": "float // 主题融合度评分 (1-10)",',
            '  "thematic_deepening_comment": "string // 详细评语及优化建议",',
            '  "character_growth_score": "float // 角色成长驱动力评分 (1-10)",',
            '  "character_growth_comment": "string // 详细评语及优化建议",',
            '  "master_reviewer_verdict": "string // 网文白金策划师的最终总结性评语，如“结构稳健，爆点可期，细节仍需打磨以提升读者体验”",',
            '  "perfection_suggestions": ["string // 提升至“爆款网文”的3-5条核心建议，每条建议都应具体、可操作"]',
            "}"
        ]
        return "\n".join(prompt_parts)
    def _build_hierarchy_description(self, major_events: List[Dict]) -> str:
            if not major_events:
                return "当前阶段没有重大事件。"
            description_parts = []
            for i, major_event in enumerate(major_events, 1):
                # 1. 处理重大事件本身
                major_event_name = major_event.get('name', '未命名')
                description_parts.append(f"### 🚨 重大事件 {i}: {major_event_name}")
                description_parts.append(f"- **章节范围**: {major_event.get('chapter_range', '未指定')}")
                description_parts.append(f"- **核心目标**: {major_event.get('main_goal', '未指定')}")
                description_parts.append(f"- **情绪目标**: {major_event.get('emotional_goal', '未指定')}")
                description_parts.append(f"- **在阶段中的角色**: {major_event.get('role_in_stage_arc', '未指定')}")
                composition = major_event.get("composition", {})
                # 2. 严格校验 'composition' 字段本身
                if not isinstance(composition, dict):
                    raise TypeError(
                        f"\n\n[严格模式数据校验失败]\n"
                        f"❌ 在处理重大事件 '{major_event_name}' 时，其 'composition' 字段本应是字典，但实际类型为 '{type(composition).__name__}'。\n"
                        f"   请检查上游AI生成的数据结构。"
                    )
                medium_events_count = sum(len(events) for events in composition.values() if isinstance(events, list))
                description_parts.append(f"- **包含 {medium_events_count} 个中型事件**:")
                # 3. 遍历 'composition' 中的各个阶段 (起/承/转/合)
                for phase_name, medium_events in composition.items():
                    if not isinstance(medium_events, list):
                        # 如果AI为'起'等阶段返回的不是列表，也应该被视为一个错误，但这里暂时跳过以聚焦核心问题
                        continue
                    # 4. 遍历该阶段下的所有中型事件
                    for j, medium_event in enumerate(medium_events, 1):
                        # ▼▼▼【核心修改：严格的类型校验】▼▼▼
                        # 如果 medium_event 不是一个字典，则构造详细错误信息并立即抛出异常。
                        if not isinstance(medium_event, dict):
                            # 为了调试，将整个列表转换为易于阅读的字符串
                            full_list_context = "\n".join([f"    - item[{idx}]: {repr(item)}" for idx, item in enumerate(medium_events)])
                            # 构造一个信息量极大的错误消息
                            error_message = (
                                f"\n\n"
                                f"==================== [严格模式数据校验失败] ====================\n"
                                f"❌ 在解析事件层级时，发现数据类型错误，流程已中止。\n\n"
                                f"   [位置]:\n"
                                f"     - 重大事件: '{major_event_name}'\n"
                                f"     - 事件阶段: '{phase_name}'\n"
                                f"     - 目标元素: 列表中的第 {j} 个中型事件 (索引 {j-1})\n\n"
                                f"   [问题]:\n"
                                f"     - 期望类型: dict (一个包含 'name', 'type' 等键的事件对象)\n"
                                f"     - 实际类型: {type(medium_event).__name__}\n"
                                f"     - 实际内容: {repr(medium_event)}\n\n"
                                f"   [完整上下文]:\n"
                                f"     '-- '{phase_name}' 阶段的完整列表内容如下 --'\n{full_list_context}\n\n"
                                f"👉 [根本原因分析]:\n"
                                f"   这几乎总是因为上游的AI模型在生成JSON时没有遵循预设格式，\n"
                                f"   直接返回了一个描述性的字符串，而不是一个结构化的事件字典。\n"
                                f"   请检查触发此错误的AI调用的Prompt以及模型返回的完整原始JSON数据，\n"
                                f"   以定位并修复格式问题。\n"
                                f"===================================================================="
                            )
                            # 主动抛出 TypeError 异常，中断整个程序
                            raise TypeError(error_message)
                        # ▲▲▲【核心修改结束】▲▲▲
                        # 如果校验通过，则继续正常执行，并使用 .get() 保证安全访问
                        description_parts.append(f"  #### 📈 中型事件 {j} ({phase_name}): {medium_event.get('name', '未命名')}")
                        description_parts.append(f"  - **章节范围**: {medium_event.get('chapter_range', '未指定')}")
                        description_parts.append(f"  - **核心目标**: {medium_event.get('main_goal', '未指定')}")
                        description_parts.append(f"  - **情绪重点**: {medium_event.get('emotional_focus', '未指定')}")
                        description_parts.append(f"  - **服务重大事件**: {medium_event.get('contribution_to_major', '未指定')}")
                        # (此处可以添加更深层次的解析逻辑，但当前的核心修复已完成)
                description_parts.append("") # 在每个重大事件后添加一个空行，以增加可读性
            return "\n".join(description_parts)
    def _create_default_coherence_assessment(self) -> Dict:
        return {
            "overall_coherence_score": 5.0,
            "hierarchy_strengths": ["基础结构完整"],
            "critical_breakpoints": [
                {
                    "level": "评估系统暂时不可用",
                    "event_name": "系统",
                    "issue": "AI评估服务暂时不可用",
                    "severity": "medium"
                }
            ],
            "goal_alignment_analysis": {
                "major_to_medium": "无法进行评估",
                "medium_to_chapter": "无法进行评估", 
                "chapter_to_scene": "无法进行评估"
            },
            "emotional_consistency_analysis": "无法进行评估",
            "improvement_recommendations": [
                {
                    "breakpoint": "评估系统",
                    "suggestion": "等待AI评估服务恢复后重新评估",
                    "priority": "medium"
                }
            ],
            "exemplary_chains": [],
            "risk_events": ["所有事件（因无法评估）"]
        }
    def _assess_goal_alignment(self, sub_goal: str, parent_goal: str) -> str:
        if not sub_goal or not parent_goal:
            return "low"
        sub_goal_lower = sub_goal.lower()
        parent_goal_lower = parent_goal.lower()
        # 简单的关键词匹配
        parent_keywords = parent_goal_lower.split()
        matches = sum(1 for keyword in parent_keywords if keyword in sub_goal_lower)
        if matches >= 2:
            return "high"
        elif matches >= 1:
            return "medium"
        else:
            return "low"
    def _decompose_medium_direct_to_scene(self, medium_event: Dict, major_event: Dict, stage_name: str,
                                        novel_title: str, novel_synopsis: str, creative_seed: str, consistency_guidance: Optional[str] = None) -> Dict:
        chapter_range = medium_event.get('chapter_range', '0-0')
        start_ch, end_ch = parse_chapter_range(chapter_range)
        chapter_count = end_ch - start_ch + 1
        # ▼▼▼【新增】构建一致性指令块 ▼▼▼
        consistency_block = ""
        if consistency_guidance:
            consistency_block = f"""
## 2. 已确定的事实 (一致性铁律 - 必须严格遵守)
你在进行场景构建时，必须严格遵守以下已确定的世界事实。你的规划不能与这些事实产生任何矛盾，更不能重复已经发生过的关键情节（如主角已觉醒金手指）。
{consistency_guidance}
"""
        # 构建详细的章节分配说明
        chapter_breakdown = ""
        for i in range(chapter_count):
            chapter_num = start_ch + i
            chapter_breakdown += f"- 第{chapter_num}章: 需要完成中型事件目标的{['起始','发展','高潮','收尾'][min(i, 3)]}部分\n"
        prompt = f"""
# 任务：中型事件"多章场景构建" - 明确章节归属和服务关系
{consistency_block}
你需要为一个跨{chapter_count}章的中型事件设计详细的场景事件序列，明确每个场景的章节归属，确保每章都有完整的场景结构。
## 当前中型事件信息
- **所属阶段**: {stage_name}
- **所属重大事件**: {major_event.get('name')}
- **中型事件名称**: {medium_event.get('name')}
- **事件章节范围**: {medium_event.get('chapter_range')} (共{chapter_count}章)
- **事件核心目标**: {medium_event.get('main_goal')}
- **事件情绪重点**: {medium_event.get('emotional_focus')}
- **事件描述**: {medium_event.get('description')}
- **服务重大事件**: {medium_event.get('contribution_to_major')}
## 章节分配要求
{chapter_breakdown}
## 场景构建要求
请为这{chapter_count}章分别设计完整的场景事件序列，确保：
### 每章的结构要求：
1. **第1章** (起始章): 建立情境，引入冲突，开启中型事件
- 开场场景：建立基础情境
- 发展场景：引入主要冲突
- 高潮场景：确立本章核心冲突点
- 结尾场景：设置悬念，引导下一章
2. **中间章节** (发展章): 深化冲突，推进情节
- 开场场景：承接上一章悬念
- 发展场景1：推进情节发展
- 发展场景2：冲突升级
- 高潮场景：本章情感爆发点
- 结尾场景：新的悬念或转折
3. **最后一章** (收尾章): 解决冲突，完成中型事件目标
- 开场场景：处理上一章遗留问题
- 发展场景：向最终解决推进
- 高潮场景：中型事件的核心解决时刻
- 回落场景：处理后果和影响
- 结尾场景：中型事件收尾，衔接后续内容
### 跨章连贯性要求：
- 确保章节间场景的平滑过渡
- 保持情绪发展的连贯性
- 每章都要有明确的服务于中型事件目标的贡献
## 输出格式
{{
    "name": "{medium_event.get('name')}",
    "type": "medium_event", 
    "chapter_range": "{medium_event.get('chapter_range')}",
    "main_goal": "{medium_event.get('main_goal')}",
    "emotional_focus": "{medium_event.get('emotional_focus')}",
    "description": "{medium_event.get('description')}",
    "decomposition_type": "direct_scene",
    "contribution_to_major": "{medium_event.get('contribution_to_major')}",
    "chapter_breakdown": {{
        "overall_arc": "整个中型事件的情节发展弧线",
        "emotional_progression": "跨章情绪发展轨迹",
        "key_turning_points": ["转折点1", "转折点2"]
    }},
    "scene_sequences": [
        {{
            "chapter_range": "{start_ch}-{start_ch}",
            "chapter_role": "起始章",
            "chapter_goal": "本章要达成的具体目标（服务于中型事件目标的起始部分）",
            "emotional_focus": "本章的情绪重点",
            "structural_arc": "本章的结构弧线",
            "contribution_to_medium": "本章如何服务于中型事件目标",
            "scene_events": [
                {{
                    "name": "场景1名称",
                    "type": "scene_event",
                    "position": "opening",
                    "purpose": "场景的戏剧目的（服务于本章目标）", 
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "场景的情感冲击",
                    "dialogue_highlights": ["关键对话1", "关键对话2"],
                    "conflict_point": "冲突的具体表现",
                    "sensory_details": "需要突出的感官细节",
                    "transition_to_next": "如何过渡到下一个场景",
                    "estimated_word_count": "300-500字",
                    "contribution_to_chapter": "如何服务于本章目标"
                }},
                {{
                    "name": "场景2名称", 
                    "type": "scene_event",
                    "position": "development1",
                    "purpose": "推进情节发展",
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "深化情感冲突",
                    "dialogue_highlights": ["关键对话1", "关键对话2"], 
                    "conflict_point": "冲突升级表现",
                    "sensory_details": "需要突出的感官细节",
                    "transition_to_next": "如何过渡到下一个场景",
                    "estimated_word_count": "300-500字",
                    "contribution_to_chapter": "如何服务于本章目标"
                }},
                {{
                    "name": "场景3名称",
                    "type": "scene_event", 
                    "position": "climax",
                    "purpose": "本章情感爆发点",
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "强烈情感冲击",
                    "dialogue_highlights": ["关键对话1", "关键对话2"],
                    "conflict_point": "核心冲突解决或升级",
                    "sensory_details": "需要突出的感官细节", 
                    "transition_to_next": "如何过渡到下一个场景",
                    "estimated_word_count": "300-500字",
                    "contribution_to_chapter": "如何服务于本章目标"
                }},
                {{
                    "name": "场景4名称",
                    "type": "scene_event",
                    "position": "ending", 
                    "purpose": "设置悬念，引导下一章",
                    "key_actions": ["关键动作1", "关键动作2"],
                    "emotional_impact": "悬念带来的期待感",
                    "dialogue_highlights": ["关键对话1", "关键对话2"],
                    "conflict_point": "未解决的冲突或新出现的矛盾",
                    "sensory_details": "需要突出的感官细节",
                    "transition_to_next": "如何过渡到下一章",
                    "estimated_word_count": "300-500字", 
                    "contribution_to_chapter": "如何服务于本章目标"
                }},
                // ... 更多章节的场景序列
            ],
            "chapter_hook": "本章结尾的悬念钩子",
            "writing_focus": "本章写作重点提示",
            "connection_to_next": "如何连接到下一章"
        }}        ]
}}
"""
        result = self.generator.api_client.generate_content_with_retry(
            content_type="multi_chapter_scene_design", 
            user_prompt=prompt, 
            purpose=f"为中型事件'{medium_event.get('name')}'构建多章场景序列"
        )
        return result
    def validate_scene_planning_coverage(self, stage_writing_plan: Dict, stage_name: str, stage_range: str) -> Dict:
        if "stage_writing_plan" in stage_writing_plan:
            plan_data = stage_writing_plan["stage_writing_plan"]
        else:
            plan_data = stage_writing_plan
        event_system = plan_data.get("event_system", {})
        chapter_scene_events = event_system.get("chapter_scene_events", [])
        # 解析阶段范围
        start_ch, end_ch = parse_chapter_range(stage_range)
        expected_chapters = set(range(start_ch, end_ch + 1))
        # 获取实际覆盖的章节
        covered_chapters = set(chapter["chapter_number"] for chapter in chapter_scene_events)
        # 找出缺失的章节
        missing_chapters = expected_chapters - covered_chapters
        extra_chapters = covered_chapters - expected_chapters
        # 分析场景分布
        scene_distribution = {}
        for chapter in chapter_scene_events:
            chapter_num = chapter["chapter_number"]
            scene_count = len(chapter.get("scene_events", []))
            scene_distribution[chapter_num] = scene_count
        coverage_analysis = {
            "stage_name": stage_name,
            "stage_range": stage_range,
            "expected_chapters": len(expected_chapters),
            "covered_chapters": len(covered_chapters),
            "coverage_rate": len(covered_chapters) / len(expected_chapters) if expected_chapters else 0,
            "missing_chapters": sorted(missing_chapters),
            "extra_chapters": sorted(extra_chapters),
            "average_scenes_per_chapter": sum(scene_distribution.values()) / len(scene_distribution) if scene_distribution else 0,
            "scene_distribution": scene_distribution,
            "issues": []
        }
        # 识别问题
        if missing_chapters:
            coverage_analysis["issues"].append(f"缺失{len(missing_chapters)}个章节的场景规划: {sorted(missing_chapters)}")
        if extra_chapters:
            coverage_analysis["issues"].append(f"存在{len(extra_chapters)}个超出阶段范围的章节: {sorted(extra_chapters)}")
        # 检查场景数量合理性
        for chapter_num, scene_count in scene_distribution.items():
            if scene_count < 3:
                coverage_analysis["issues"].append(f"第{chapter_num}章场景数量过少({scene_count}个)，可能无法形成完整结构")
            elif scene_count > 8:
                coverage_analysis["issues"].append(f"第{chapter_num}章场景数量过多({scene_count}个)，可能导致节奏过快")
        return coverage_analysis    
    def _optimize_based_on_coherence_assessment(self, writing_plan: Dict, assessment: Dict, 
                                            stage_name: str, stage_range: str) -> Dict:
        critical_breakpoints = assessment.get("critical_breakpoints", [])
        improvement_recommendations = assessment.get("improvement_recommendations", [])
        if not critical_breakpoints and not improvement_recommendations:
            self.logger.info("  ✅ AI评估未发现严重的目标层级问题，无需优化。")
            return writing_plan
        self.logger.info(f"  🔧 指示AI根据目标层级评估，开始优化 {stage_name} 阶段事件目标链...")
        # 构建优化指令
        optimization_prompt = self._build_hierarchy_optimization_prompt(
            writing_plan, assessment, stage_name, stage_range
        )
        # 调用AI进行优化
        try:
            optimization_result = self.generator.api_client.generate_content_with_retry(
                content_type="ai_hierarchy_optimization",
                user_prompt=optimization_prompt,
                purpose=f"优化{stage_name}阶段事件目标层级"
            )
            if optimization_result and "optimized_event_system" in optimization_result:
                # 用AI返回的优化后的事件系统替换旧的
                if "stage_writing_plan" in writing_plan:
                    plan_container = writing_plan["stage_writing_plan"]
                else:
                    plan_container = writing_plan
                # 核心操作：替换整个事件系统
                plan_container["event_system"] = optimization_result["optimized_event_system"]
                plan_container["hierarchy_optimized"] = True
                # 打印AI提供的修改摘要
                summary = optimization_result.get("summary_of_hierarchy_changes", "AI未提供修改摘要。")
                self.logger.info(f"  ✅ AI目标层级优化执行完成。修改摘要: {summary}")
            else:
                self.logger.warn("  ⚠️ AI目标层级优化失败，未能返回有效的优化后事件系统。")
        except Exception as e:
            self.logger.error(f"  ❌ 在执行AI目标层级优化时发生错误: {e}")
        return writing_plan
    def _build_hierarchy_optimization_prompt(self, writing_plan: Dict, assessment: Dict, 
                                    stage_name: str, stage_range: str) -> str:
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        # 将复杂的dict转换为格式化的JSON字符串，以便在prompt中清晰展示
        event_system_str = json.dumps(event_system, ensure_ascii=False, indent=2)
        assessment_str = json.dumps(assessment, ensure_ascii=False, indent=2)
        # 构建优化提示词
        prompt = f"""
# 任务：小说事件目标层级优化 (保持结构)
作为一名顶尖的剧情架构师，你刚刚对一份小说事件计划的目标层级进行了评估，发现了一些目标传递断裂的问题。现在，你的任务是**亲自动手**，根据评估建议来修复这些目标层级问题，同时**严格保持原始的JSON数据结构**。
## 1. 待优化的事件计划 ({stage_name}, {stage_range})
这是你需要修复的原始事件计划，你必须在**这个结构内部**进行修改：
```json
{event_system_str}
2. 目标层级评估发现的问题与建议
JSON
{assessment_str}
3. 修复指令
请严格遵循评估建议，对上述的“待优化的事件计划”进行目标层级修复。
修复重点：
目标传递断裂: 修复重大事件→中型事件→章节事件→场景事件之间的目标传递断裂。
贡献关系模糊: 为缺少明确贡献关系的事件添加具体的contribution_to_*字段。
情绪目标不一致: 确保情绪目标在层级间保持连贯。
目标过于抽象: 将抽象的目标转化为具体、可执行的目标。
【最高优先级指令】保持结构完整性：
你返回的最终结果必须是一个与输入结构完全相同的 event_system JSON对象。这意味着 major_events 列表中的每个事件都必须包含其 composition 和 special_emotional_events。严禁将中型事件或特殊事件从 composition 中提取出来，形成独立的顶级列表。你的所有修改都必须在原始的嵌套结构内完成。
4. 返回格式
请严格按照以下JSON格式返回你的工作成果。不要包含任何额外的解释。返回的optimized_event_system必须与输入的event_system具有完全相同的顶级键和嵌套结构。
JSON
{{
  "optimized_event_system": {{
    "major_events": [
      {{
        "name": "修复后的重大事件1名称",
        "main_goal": "优化后的核心目标",
        "composition": {{
          "起": [
            {{
              "name": "修复后的中型事件",
              "main_goal": "优化后的、服务于重大事件目标的目标",
              "contribution_to_major": "明确的服务关系说明"
            }}
          ],
          "承": [ /* ... 类似地，优化内部的中型事件 ... */ ]
          // ... 其他阶段
        }},
        "special_emotional_events": [
            // ... 同样保持在此处
        ]
      }}
      // ... 更多优化后的重大事件, 每个都保持着完整的嵌套结构
    ]
    // 确保这里没有 "medium_events", "minor_events" 等扁平化的键
  }},
  "summary_of_hierarchy_changes": "用一句话总结你在目标层级方面所做的主要修改。例如：'修复了3处目标传递断裂，为5个事件添加了明确的贡献关系说明。'"
}}
"""
        return prompt
    def generate_stage_writing_plan(self, stage_name: str, stage_range: str, creative_seed: str,
                                    novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        # [TEST MODE SHORTCUT] - In test mode, return minimal valid structure quickly
        import os
        if os.getenv('USE_MOCK_API', 'false').lower() == 'true':
            self.logger.info(f"   [测试模式快速通道] 为【{stage_name}】返回简化版写作计划...")
            return self._generate_simple_stage_plan_for_test(stage_name, stage_range, overall_stage_plan)
        # Defensive normalization: creative_seed may be a dict or a JSON/string.
        try:
            from src.utils.seed_utils import ensure_seed_dict
            creative_seed = ensure_seed_dict(creative_seed)
        except Exception:
            # If normalization fails, fall back to wrapping as string
            if not isinstance(creative_seed, dict):
                creative_seed = {"coreSetting": str(creative_seed)}
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            self.logger.info(f"🎬 从缓存加载【{stage_name}】分形写作计划...")
            return self.stage_writing_plans_cache[cache_key]
        self.logger.info(f"🎬 开始为【{stage_name}】生成智能分形写作计划...")
        start_chap, end_chap = self.parse_chapter_range(stage_range)
        stage_length = max(1, end_chap - start_chap + 1)
        emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
        stage_emotional_plan = self.generator.emotional_plan_manager.generate_stage_emotional_plan(
            stage_name, stage_range, emotional_blueprint
        )
        density_requirements = self.event_manager.calculate_optimal_event_density_by_stage(stage_name, stage_length)
        # fase 1: 规划阶段的'主龙骨' (重大事件框架)
        self.logger.info("   fase 1: 规划阶段的'主龙骨' (重大事件框架)...")
        major_event_skeletons_container = None 
        for attempt in range(3):
            try:
                major_event_skeletons_container = self._generate_major_event_skeleton(
                    stage_name, stage_range, novel_title, novel_synopsis, creative_seed,
                    stage_emotional_plan, overall_stage_plan, density_requirements
                )
                if major_event_skeletons_container and isinstance(major_event_skeletons_container, dict) \
                    and "major_event_skeletons" in major_event_skeletons_container \
                    and isinstance(major_event_skeletons_container["major_event_skeletons"], list):
                    break
                else:
                    self.logger.warn(f"    ⚠️ 第{attempt+1}次生成主龙骨失败")
            except Exception as e:
                self.logger.error(f"    ❌ 第{attempt+1}次生成主龙骨出错: {e}")
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)
        if not major_event_skeletons_container or not major_event_skeletons_container.get("major_event_skeletons"):
            self.logger.info(f"    🚨 主龙骨生成失败，所有重试均失败")
            return {}
        major_event_skeletons = major_event_skeletons_container["major_event_skeletons"]
        if not major_event_skeletons:
            self.logger.info(f"    🚨 主龙骨生成失败，所有重试均失败")
            return {}
        # fase 2: 逐一'解剖'重大事件，填充中型事件
        self.logger.info("   fase 2: 逐一'解剖'重大事件，填充中型事件...")
        fleshed_out_major_events = []
        for skeleton in major_event_skeletons:
            self.logger.info(f"    -> 正在解剖重大事件: '{skeleton['name']}' ({skeleton['chapter_range']})")
            fleshed_out_event = None
            for attempt in range(3):
                try:
                    if True:  # Always use default decomposer
                        fleshed_out_event = self._decompose_major_event(
                            major_event_skeleton=skeleton, 
                            stage_name=stage_name, 
                            stage_range=stage_range, 
                            novel_title=novel_title, 
                            novel_synopsis=novel_synopsis, 
                            creative_seed=creative_seed,
                            overall_stage_plan=overall_stage_plan
                        )
                    if fleshed_out_event:
                        break
                    else:
                        self.logger.warn(f"      ⚠️ 第{attempt+1}次解剖失败")
                except Exception as e:
                    self.logger.error(f"      ❌ 第{attempt+1}次解剖出错: {e}")
                    if attempt < 2:
                        import time
                        time.sleep(2 ** attempt)
            if fleshed_out_event:
                # ▼▼▼【核心修复·方法一】▼▼▼
                # 在此阶段立即验证并修正AI生成内容的章节覆盖率，防止问题扩散到下游
                fleshed_out_event = self._validate_and_correct_major_event_coverage(skeleton, fleshed_out_event)
                # ▲▲▲【核心修复·方法一】▲▲▲
                fleshed_out_major_events.append(fleshed_out_event)
            else:
                self.logger.info(f"    🚨 重大事件 '{skeleton['name']}' 解剖失败，所有重试均失败")
        if not fleshed_out_major_events:
            self.logger.info(f"    🚨 所有重大事件解剖失败，无法继续生成写作计划")
            return {}
        # fase 2.5: 验证并优化事件层级和连续性 (重大事件 -> 中型事件)
        # 在生成场景细节之前，评估事件骨架和肌肉的合理性
        self.logger.info("   fase 2.5: 验证并优化事件层级和连续性 (重大事件 -> 中型事件)...")
        # 构建一个临时的计划结构，只包含重大和中型事件，用于评估
        temp_plan_for_event_structure = {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "novel_metadata": {
                    "title": novel_title,
                    "synopsis": novel_synopsis,
                    "creative_seed": creative_seed,
                    "generation_timestamp": datetime.now().isoformat()
                },
                "event_system": {
                    "major_events": fleshed_out_major_events, # 仅包含重大和中型事件
                },
            }
        }
        # 1. 验证目标层级一致性
        goal_coherence = self.validate_goal_hierarchy_coherence(temp_plan_for_event_structure, stage_name)
        # 2. 验证事件连续性
        continuity_assessment = self.assess_stage_event_continuity(
            temp_plan_for_event_structure, stage_name, stage_range, creative_seed, novel_title, novel_synopsis
        )
        # 3. 根据验证结果优化事件结构 (注意：这里直接修改 fleshed_out_major_events)
        # 处理类型：可能是字符串或数字
        try:
            coherence_score = goal_coherence.get("overall_coherence_score", 10)
            if isinstance(coherence_score, str):
                coherence_score = float(coherence_score)
            elif coherence_score is None:
                coherence_score = 10
        except (ValueError, TypeError):
            coherence_score = 10
        
        if coherence_score < 8.0:
            self.logger.warn(f"  ⚠️ 目标层级一致性评分较低 ({coherence_score:.1f})，进行优化...")
            optimized_temp_plan_coherence = self._optimize_based_on_coherence_assessment(
                temp_plan_for_event_structure, goal_coherence, stage_name, stage_range
            )
            # 更新 fleshed_out_major_events 以便后续场景分解使用优化后的结构
            fleshed_out_major_events = optimized_temp_plan_coherence["stage_writing_plan"]["event_system"]["major_events"]
            # 确保 temp_plan_for_event_structure 也更新，以防后续连续性优化需要最新的数据
            temp_plan_for_event_structure["stage_writing_plan"]["event_system"]["major_events"] = fleshed_out_major_events
        continuity_score = continuity_assessment.get("overall_continuity_score", 10)
        # 处理类型：可能是字符串或数字
        try:
            if isinstance(continuity_score, str):
                continuity_score = float(continuity_score)
            elif continuity_score is None:
                continuity_score = 10
        except (ValueError, TypeError):
            continuity_score = 10
        
        if continuity_score < 9.5:
            self.logger.warn(f"  ⚠️ 阶段事件连续性评分较低 ({continuity_score:.1f})，进行优化...")
            optimized_temp_plan_continuity = self._optimize_based_on_continuity_assessment(
                temp_plan_for_event_structure, continuity_assessment, stage_name, stage_range
            )
            # 更新 fleshed_out_major_events 以便后续场景分解使用优化后的结构
            fleshed_out_major_events = optimized_temp_plan_continuity["stage_writing_plan"]["event_system"]["major_events"]
            # 确保 temp_plan_for_event_structure 也更新
            temp_plan_for_event_structure["stage_writing_plan"]["event_system"]["major_events"] = fleshed_out_major_events
        # fase 4: 组装最终的写作计划
        self.logger.info("   fase 4: 组装最终的写作计划...")
        final_writing_plan = self._assemble_final_plan(
            stage_name, stage_range, fleshed_out_major_events, overall_stage_plan,
            novel_title, novel_synopsis, creative_seed
        )
        # ▼▼▼【新增或保留】将评估结果添加到最终计划中 ▼▼▼
        plan_container = final_writing_plan.get("stage_writing_plan", final_writing_plan)
        if goal_coherence:
            plan_container["goal_hierarchy_assessment"] = goal_coherence 
        if continuity_assessment:
            plan_container["continuity_assessment"] = continuity_assessment
        # ▲▲▲【新增或保留】结束 ▲▲▲
        # fase 6: 进行最终整体验证和保存
        self.logger.info("   fase 6: 进行最终整体验证和保存...")
        final_writing_plan = self._validate_and_optimize_writing_plan(
            final_writing_plan, stage_name, stage_range
        )
        if final_writing_plan:
            # 保存到文件，并更新主数据文件中的路径
            file_path = self._save_plan_to_file(stage_name, final_writing_plan)
            self.stage_writing_plans_cache[cache_key] = final_writing_plan
            if "stage_writing_plans" not in self.generator.novel_data:
                self.generator.novel_data["stage_writing_plans"] = {}
            # 修复：使用安全的路径处理方式
            if file_path:
                # 尝试获取项目路径，如果不存在则使用当前工作目录
                try:
                    project_path = getattr(self.generator, 'project_path', Path.cwd())
                    relative_path = file_path.relative_to(project_path)
                except (AttributeError, ValueError):
                    # 如果无法获取相对路径，则使用绝对路径
                    relative_path = file_path
            else:
                relative_path = f"plans/{stage_name}_writing_plan.json"
            self.generator.novel_data["stage_writing_plans"][stage_name] = {"path": str(relative_path)}
            self.logger.info(f"  ✅ 【{stage_name}】分形写作计划生成完成！")
            self._print_fractal_plan_summary(final_writing_plan)
            return final_writing_plan
        else:
            self.logger.info(f"  🚨 【{stage_name}】写作计划生成失败。")
            return {}
    def _optimize_based_on_continuity_assessment(self, writing_plan: Dict, assessment: Dict, 
                                            stage_name: str, stage_range: str) -> Dict:
        self.logger.info(f"  🔧 指示AI根据连续性评估，开始优化 {stage_name} 阶段事件连续性...")
        # 提取当前事件系统
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        # 构建连续性优化提示词
        optimization_prompt = self._build_continuity_optimization_prompt(
            event_system, assessment, stage_name, stage_range
        )
        # 调用AI进行优化
        try:
            optimization_result = self.generator.api_client.generate_content_with_retry(
                content_type="ai_event_plan_optimization",
                user_prompt=optimization_prompt,
                purpose=f"优化{stage_name}阶段事件连续性"
            )
            if optimization_result and "optimized_event_system" in optimization_result:
                # 用AI返回的优化后的事件系统替换旧的
                if "stage_writing_plan" in writing_plan:
                    plan_container = writing_plan["stage_writing_plan"]
                else:
                    plan_container = writing_plan
                # 核心操作：替换整个事件系统
                plan_container["event_system"] = optimization_result["optimized_event_system"]
                plan_container["continuity_optimized"] = True
                # 打印AI提供的修改摘要
                summary = optimization_result.get("summary_of_continuity_changes", "AI未提供修改摘要。")
                self.logger.info(f"  ✅ AI连续性优化执行完成。修改摘要: {summary}")
            else:
                self.logger.warn("  ⚠️ AI连续性优化失败，未能返回有效的优化后事件系统。")
        except Exception as e:
            self.logger.error(f"  ❌ 在执行AI连续性优化时发生错误: {e}")
        return writing_plan
    def _build_continuity_optimization_prompt(self, event_system: Dict, assessment: Dict,
                                        stage_name: str, stage_range: str) -> str:
        # 将复杂的dict转换为格式化的JSON字符串，以便在prompt中清晰展示
        critical_issues_str = json.dumps(assessment.get('critical_issues', []), ensure_ascii=False, indent=2)
        recommendations_str = json.dumps(assessment.get('improvement_recommendations', []), ensure_ascii=False, indent=2)
        event_system_str = json.dumps(event_system, ensure_ascii=False, indent=2)
        prompt = f"""
# 任务：小说事件连续性优化 (保持结构)
作为一名顶尖的剧情架构师，你刚刚对一份小说事件计划的连续性进行了评估，发现了一些逻辑断裂和节奏问题。现在，你的任务是**亲自动手**，根据评估建议来修复这些事件连续性问题，同时**严格保持原始的JSON数据结构**。
## 1. 待优化的事件计划 ({stage_name}, {stage_range})
这是你需要修复的原始事件计划，你必须在**这个结构内部**进行修改：
```json
{event_system_str}
2. 连续性评估发现的关键问题
JSON
{critical_issues_str}
3. 具体的改进建议
JSON
{recommendations_str}
4. 修复指令
请严格遵循上述评估和建议，对**“1. 待优化的事件计划”**进行优化。
修复重点：
逻辑断裂: 修复事件之间的逻辑断层，确保因果关系合理。
节奏问题: 调整事件密度和分布，确保张弛有度。
情感连续性: 确保情感发展连贯，高潮铺垫充分。
主线推进: 确保主线持续高效推进，避免支线喧宾夺主。
修复方法：
对于逻辑断裂: 重新设计事件顺序，修改事件目标，或在composition内部添加/合并中型事件。
对于节奏问题: 调整事件的chapter_range，优化高潮和平缓章节的交替。
对于情感连续性: 调整emotional_focus和emotional_goal，确保情感曲线自然。
对于主线推进: 强化核心重大事件的目标，弱化或删除偏离主线的次要中型事件。
【最高优先级指令】保持结构完整性：
你返回的最终结果必须是一个与输入结构完全相同的 event_system JSON对象。这意味着 major_events 列表中的每个事件都必须包含其 composition 和 special_emotional_events。严禁将中型事件或特殊事件提取到顶级的 "medium_events" 或 "special_events" 列表中。你的所有修改都必须在原始的嵌套结构内完成。
5. 返回格式
请严格按照以下JSON格式返回你的工作成果，不要包含任何额外的解释。返回的optimized_event_system必须与输入的event_system具有完全相同的顶级键和嵌套结构。
JSON
{{
  "optimized_event_system": {{
    "major_events": [
      {{
        "name": "修复后的重大事件1名称",
        "type": "major_event",
        "role_in_stage_arc": "起",
        "main_goal": "优化后的核心目标",
        "emotional_goal": "优化后的情绪目标",
        "chapter_range": "调整后的章节范围",
        "composition": {{
          "起": [
            {{
              "name": "修复或重组后的中型事件",
              "type": "medium_event",
              "chapter_range": "调整后的章节范围",
              "main_goal": "优化后的目标",
              "emotional_focus": "优化后的情绪重点",
              "contribution_to_major": "明确的服务关系说明"
            }}
          ],
          "承": [ /* ... 类似地，优化内部的中型事件 ... */ ],
          "转": [ /* ... */ ],
          "合": [ /* ... */ ]
        }},
        "special_emotional_events": [
          // ... 修复或重组后的特殊情感事件，如果存在
        ]
      }}
      // ... 更多优化后的重大事件, 每个都保持着完整的嵌套结构
    ]
  }},
  "summary_of_continuity_changes": "用一句话总结你在连续性方面所做的主要修改。例如：'重组了事件顺序以优化节奏，并为事件'XXX'增加了前置铺垫，确保逻辑连贯。'"
}}
"""
        return prompt
    def _add_scenes_from_decomposed_event(self, decomposed_event_data: Dict, chapter_scene_map: Dict):
        chapter_range = decomposed_event_data.get("chapter_range")
        if not chapter_range:
            self.logger.warn(f"  ⚠️ 分解事件缺少 'chapter_range'，跳过场景累积: {decomposed_event_data.get('name', '未知事件')}")
            return
        # 使用已有的解析函数
        start_chapter, end_chapter = self.parse_chapter_range(chapter_range)
        decomposition_type = decomposed_event_data.get("decomposition_type", "")
        if decomposition_type == "chapter_then_scene":
            # 这表示一个中型事件被分解成了多个章节事件 (chapter_events)，
            # 每个章节事件内部再包含 scene_structure 和 scenes。
            chapter_events = decomposed_event_data.get("chapter_events", [])
            for chapter_entry in chapter_events:
                # chapter_entry 包含了章节事件的信息，如章节范围、目标、场景结构等
                target_chapter_num_start, target_chapter_num_end = self.parse_chapter_range(chapter_entry.get('chapter_range', '0-0'))
                chapter_goal = chapter_entry.get("main_goal", "")
                scene_structure = chapter_entry.get("scene_structure", {})
                # 优先从 scene_structure 获取 writing_focus，其次从 chapter_entry 本身
                writing_focus = scene_structure.get("writing_focus", chapter_entry.get("writing_focus", "未指定写作重点"))
                scenes = scene_structure.get("scenes", [])
                # 假设每个 chapter_entry 代表一个单一章节的事件
                target_chapter_num = target_chapter_num_start 
                # 确保目标章节在父事件（中型事件）的整体章节范围内
                if start_chapter <= target_chapter_num <= end_chapter:
                    if target_chapter_num not in chapter_scene_map:
                        chapter_scene_map[target_chapter_num] = {
                            "chapter_goal": chapter_goal,
                            "writing_focus": writing_focus,
                            "scene_events": []
                        }
                    # 确保 scene_events 键存在且为列表
                    elif "scene_events" not in chapter_scene_map[target_chapter_num]:
                        chapter_scene_map[target_chapter_num]["scene_events"] = []
                    chapter_scene_map[target_chapter_num]["scene_events"].extend(scenes)
                else:
                    self.logger.warn(f"  ⚠️ 分解出的章节事件 {target_chapter_num} 超出中型事件 {decomposed_event_data.get('name', '')} 的 chapter_range {chapter_range}，跳过场景累积。")
        elif decomposition_type == "direct_scene":
            # 这表示一个中型事件直接被分解成了一个或多个场景序列 (scene_sequences)，
            # 每个场景序列可能覆盖一个或多个章节，并包含具体的场景 (scene_events)。
            scene_sequences = decomposed_event_data.get("scene_sequences", [])
            if not scene_sequences:
                self.logger.warn(f"  ⚠️ direct_scene 类型中型事件缺少场景序列: {decomposed_event_data.get('name', '未知事件')}")
                return
            for sequence in scene_sequences:
                seq_chapter_range = sequence.get('chapter_range', '0-0')
                seq_start_ch, seq_end_ch = self.parse_chapter_range(seq_chapter_range)
                chapter_goal = sequence.get("chapter_goal", "")
                writing_focus = sequence.get("writing_focus", "")
                scene_events = sequence.get("scene_events", [])
                # 遍历该场景序列覆盖的所有章节
                for chapter_num_in_seq in range(seq_start_ch, seq_end_ch + 1):
                    # 确保这个章节在父事件（中型事件）的整体章节范围内
                    if start_chapter <= chapter_num_in_seq <= end_chapter:
                        if chapter_num_in_seq not in chapter_scene_map:
                            chapter_scene_map[chapter_num_in_seq] = {
                                "chapter_goal": chapter_goal,
                                "writing_focus": writing_focus,
                                "scene_events": []
                            }
                        # 确保 scene_events 键存在且为列表
                        elif "scene_events" not in chapter_scene_map[chapter_num_in_seq]:
                            chapter_scene_map[chapter_num_in_seq]["scene_events"] = []
                        chapter_scene_map[chapter_num_in_seq]["scene_events"].extend(scene_events)
                    else:
                        self.logger.warn(f"  ⚠️ 场景序列的章节 {chapter_num_in_seq} 超出中型事件 {decomposed_event_data.get('name', '')} 的 chapter_range {chapter_range}，跳过场景累积。")
            self.logger.info(f"  💡 direct_scene 中型事件 '{decomposed_event_data.get('name', '')}' 的场景已分配到对应章节。")
        else:
            self.logger.warn(f"  ⚠️ 分解事件 '{decomposed_event_data.get('name', '')}' 缺少有效的 'decomposition_type'，无法累积场景。")

    def _generate_major_event_skeleton(self, stage_name: str, stage_range: str, novel_title: str, novel_synopsis: str,
                                   creative_seed: Dict[str, Any], stage_emotional_plan: Dict[str, Any], 
                                   overall_stage_plan: Dict[str, Any],
                                   density_requirements: Dict[str, Any]) -> Dict:
        self.logger.info(f"    -> 正在为【{stage_name}】构建主龙骨，开始注入顶层设计上下文...")
        # ▼▼▼【核心修复：创建“上下文注入”区块】▼▼▼
        # 将最关键的顶层设计文档转化为字符串，准备注入Prompt。这是解决上下文丢失问题的关键。
        try:
            # 1. 注入创意种子 (最高优先级)
            creative_seed_str = json.dumps(creative_seed, ensure_ascii=False, indent=2)
            # 2. 注入全书成长规划 (第二优先级)
            # 从 self.generator.novel_data 获取最新的全局规划，确保数据一致性
            global_growth_plan = self.generator.novel_data.get("global_growth_plan", {})
            if not global_growth_plan:
                self.logger.warn("    ⚠️ 警告：无法从 novel_data 中获取'global_growth_plan'。")
            global_growth_plan_str = json.dumps(global_growth_plan, ensure_ascii=False, indent=2)
            # 3. 注入整体阶段计划 (第三优先级)
            overall_stage_plan_str = json.dumps(overall_stage_plan, ensure_ascii=False, indent=2)
            context_injection_block = f"""
# 1. 最高指令：核心创意种子 (Creative Seed)
你的一切创作都必须是这份文档的具象化。如果其他资料与此冲突，以此为准。
```json
{creative_seed_str}
# 2. 战略蓝图：全书成长规划 (Global Growth Plan)
这份规划定义了主角和故事在每个阶段的成长目标和里程碑。你设计的事件必须服务于这些目标。
JSON
{global_growth_plan_str}
# 3. 战术地图：整体阶段计划 (Overall Stage Plans)
这份计划将全书划分了“起承转合”，明确了各阶段的核心任务。当前正处于【{stage_name}】。
JSON
{overall_stage_plan_str}
"""
        except Exception as e:
            self.logger.error(f"    ❌ 构建上下文注入区块失败: {e}")
            return {} # 关键上下文缺失，终止生成以防错误扩大
        prompt_header = f"""
任务：基于顶层设计，为【{stage_name}】阶段编排“主龙骨”
作为一名顶级的AI剧情架构师，你的任务是严格遵循下方提供的三份核心设计文档，为小说的【{stage_name}】({stage_range})规划出宏观的"主龙骨"（重大事件列表）。你的任务是演绎和细化，不是原创。
【绝对核心参考资料 (必须严格遵守)】
{context_injection_block}
"""
        # --- 根据阶段选择不同的设计要求和格式示例 ---
        if stage_name == "opening_stage":
            design_requirements = f"""
【{stage_name}】设计要求
1.  **忠于蓝图**: 你设计的 {density_requirements['major_events']} 个重大事件，必须共同构成一个服务于核心参考资料中【{stage_name}】阶段目标的"起、承、转、合"叙事链条。
2.  **【强制】黄金开局改编**: 第一个重大事件必须被设计为一个特殊的【黄金开局弧光】，后续流程将强制使用它来**精准演绎**`creative_seed.completeStoryline.opening`中的开篇情节（例如“观战韩立和温天仁的大战”），这是确保创意不丢失的最高优先级任务。
3.  **后续衔接**: 剩余的重大事件，则用于完成`global_growth_plan`和`creative_seed`中为本阶段设定的其他目标，特别是承接“黄金开局”结尾留下的危机钩子。
"""
            json_format_example = f"""
## 输出格式: 严格返回一个JSON对象，其中包含一个键名为`major_event_skeletons`的列表。
{{
    "major_event_skeletons": [
        {{
            "name": "黄金开局弧光 (例如：观战韩立与温天仁)",
            "is_golden_arc": true,
            "role_in_stage_arc": "起 (引爆器)",
            "chapter_range": "1-3",
            "main_goal": "此事件为特殊容器，后续流程必须【精准演绎】核心创意种子中的开篇商业设计，将其分解为具体的起承转合，确保核心创意不丢失。",
            "emotional_arc": "{stage_emotional_plan.get('main_emotional_arc', '高能开局，极速入戏')}",
            "description": "这是决定小说生死的黄金三章，必须100%忠于创意种子中的商业化设计（例如，观战大战），快速建立冲突、展现核心卖点、并留下强力追读钩子。"
        }},
        {{
            "name": "string // 后续重大事件的名称 (必须改编自核心参考资料)",
            "is_golden_arc": false,
            "role_in_stage_arc": "承",
            "chapter_range": "string // 估算的章节范围 (例如：'4-15')",
            "main_goal": "string // 此事件的核心目标 (例如：开始应对“黄金开局”结尾留下的短期危机)",
            "emotional_arc": "string // 此事件的情感体验",
            "description": "string // 简要描述该事件如何推进核心参考资料中的情节"
        }}
    ]
}}
"""
        else: # for development_stage, climax_stage, ending_stage
            design_requirements = f"""
【{stage_name}】设计要求
1.  **忠于蓝图**: 你的任务是演绎和编排，不是原创。你设计的 {density_requirements['major_events']} 个重大事件，必须共同构成一个服务于核心参考资料中【{stage_name}】阶段目标的"起、承、转、合"叙事链条。
2.  **目标对齐**: 确保每个重大事件的`main_goal`都直接对应`global_growth_plan`和`creative_seed`中为本阶段设定的某个核心目标或里程碑。
3.  **承上启下**: 第一个事件要承接上一阶段的结尾，最后一个事件要为下一阶段埋下伏笔。
"""
            json_format_example = f"""
## 输出格式: 严格返回一个JSON对象，其中包含一个键名为`major_event_skeletons`的列表。
{{
    "major_event_skeletons": [
        {{
            "name": "string // 第一个重大事件的名称 (必须基于核心参考资料改编)",
            "role_in_stage_arc": "起",
            "chapter_range": "string // 估算的章节范围 (例如：'31-50章')",
            "main_goal": "string // 这个重大事件的核心目标 (必须对应核心参考资料中为本阶段设定的某个里程碑或情节要点)",
            "emotional_arc": "{stage_emotional_plan.get('main_emotional_arc', 'N/A')}",
            "description": "string // 对该事件的简要描述，体现其在蓝图中的作用，以及它如何开启本阶段的叙事弧光。"
        }},
        {{
            "name": "string // 第二个重大事件的名称 (必须基于核心参考资料改编)",
            "role_in_stage_arc": "承",
            "chapter_range": "string // 估算的章节范围 (例如：'51-70章')",
            "main_goal": "string // 此事件的核心目标 (例如：主角在新地图上站稳脚跟，或者掌握了某个关键能力)",
            "emotional_arc": "string // 例如：'探索与成长'",
            "description": "string // 描述此事件如何发展'起'事件留下的线索，并为后续的转折做铺垫。"
        }}
    ]
}}
"""
        # --- 组合并生成最终的Prompt ---
        userPrompts = prompt_header + design_requirements + json_format_example
        result = self.generator.api_client.generate_content_with_retry(
            content_type="stage_major_event_skeleton",
            user_prompt = userPrompts,
            purpose=f"【顶层设计注入】生成 {novel_title} 的【{stage_name}】主龙骨"
        )
        return result
    def _decompose_major_event(self, major_event_skeleton: Dict, stage_name: str, stage_range: str,
                            novel_title: str, novel_synopsis: str, creative_seed: Dict, # <- 确保传入的是字典
                            overall_stage_plan: Dict) -> Dict:
        # ▼▼▼【核心升级：注入完整的顶层设计，杜绝任何信息丢失】▼▼▼
        try:
            # 确保 creative_seed 是字典，如果不是则尝试解析
            if isinstance(creative_seed, str):
                creative_seed = json.loads(creative_seed)
            # 将完整的创意种子、成长规划、阶段规划转化为字符串
            creative_seed_str = json.dumps(creative_seed, ensure_ascii=False, indent=2)
            global_growth_plan = self.generator.novel_data.get("global_growth_plan", {})
            global_growth_plan_str = json.dumps(global_growth_plan, ensure_ascii=False, indent=2)
            current_stage_plan_str = json.dumps(overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}), ensure_ascii=False, indent=2)
            top_level_context_block = f"""
# 1. 最高指令：核心创意种子 (Creative Seed)
你的一切创作都必须是这份文档的具象化，尤其是要参考`completeStoryline`中为当前阶段设计的剧情。

{creative_seed_str}
# 2. 战略蓝图：全书成长规划 (Global Growth Plan)
你设计的事件必须服务于这些主角成长目标。

{global_growth_plan_str}
# 3. 当前阶段任务 (Current Stage Plan)
你正在为这个阶段设计情节，必须完成其核心任务。

{current_stage_plan_str}
"""
        except Exception as e:
            self.logger.warn(f"    ⚠️ 构建顶层上下文时发生错误: {e}, 使用简化版上下文。")
            top_level_context_block = f"""
# 顶层战略背景
- **当前重大事件核心目标**: {major_event_skeleton.get('main_goal')}
"""
        # ▲▲▲【核心修正结束】▲▲▲        
        prompt = f"""
# 任务：重大事件"分形解剖"与"情感点缀"
你的任务是将一个宏观的“重大事件”，根据其在全书蓝图中的战略地位，分解为具体的、可执行的【中型事件】和【特殊情感事件】。
{top_level_context_block}
## 当前待分解的重大事件信息
- **所属阶段**: {stage_name}
- **重大事件名称**: {major_event_skeleton.get('name')}
- **事件章节范围**: {major_event_skeleton.get('chapter_range')}
- **事件情绪目标**: {major_event_skeleton.get('emotional_goal', major_event_skeleton.get('emotional_arc'))}
## 分解原则与规则 (必须严格遵守)
1.  **目标继承与服务**: 你设计的每一个【中型事件】都必须是为实现【当前重大事件核心目标】和【顶层战略背景】服务的。在每个中型事件的`contribution_to_major`字段中明确说明其贡献。
2.  **结构完整**: 所有中型事件必须共同构成一个服务于重大事件目标的、逻辑连贯的“起、承、转、合”结构。
3.  **情感点缀**: 在情节推进的间隙，巧妙设计【特殊情感事件】，用于深化情感、调整节奏、塑造人物弧光。
4. 【绝对覆盖指令】: 你生成的所有中型事件和特殊情感事件的chapter_range，必须完整且无缝地覆盖父级“重大事件”的整个章节范围 ({major_event_skeleton.get('chapter_range')})。不允许存在任何空白章节。请在生成后自行检查，确保从头到尾的每一章都被分配。
## 输出格式: 严格遵守规则，返回包含'composition'和'special_emotional_events'字段的JSON对象
{{
    "name": "{major_event_skeleton.get('name')}",
    "type": "major_event",
    "role_in_stage_arc": "{major_event_skeleton.get('role_in_stage_arc')}",
    "main_goal": "{major_event_skeleton.get('main_goal')}",
    "emotional_goal": "{major_event_skeleton.get('emotional_goal')}",
    "chapter_range": "{major_event_skeleton.get('chapter_range')}",
    "composition": {{
        "起": [ 
            {{ 
                "name": "中型事件名", 
                "type": "medium_event", 
                "chapter_range": "string // 章节范围，例如：'49-52章'", 
                "decomposition_type": "string // 【重要规则】根据本中型事件的'chapter_range'跨度决定：若跨度 > 3章，则值为 'chapter_then_scene'；若跨度 <= 3章，则值为 'direct_scene'。",
                "main_goal": "目标（服务于重大事件目标的起部分）",
                "emotional_focus": "string // 此中型事件的情绪重点（服务于重大事件情绪目标的起始部分）",
                "emotional_intensity": "low/medium/high",
                "key_emotional_beats": ["情感节拍1", "情感节拍2"],
                "description": "描述",
                "contribution_to_major": "string // 如何服务于重大事件目标"
            }} 
        ],
        "承": [ /* ... */ ],
        "转": [ /* ... */ ],
        "合": [ /* ... */ ]
    }},
    "special_emotional_events": [
        {{
            "name": "string // 特殊情感事件的名称，例如：'风暴前夜的独白'",
            "type": "special_emotional_event",
            "placement_hint": "string // 应该放置在哪个中型事件之后？例如：'在'起'部分之后，'承'部分之前'",
            "chapter_range": "string // 【重要】严格使用预留出的单一章节。例如: '49-49章'",
            "purpose": "string // 该事件的目的，例如：'情绪过渡，展现主角在获得初步胜利后的迷茫与决心，为后续的挑战积蓄情感力量'",
            "event_subtype": "string // (例如：dialogue, introspection, flashback, quiet_moment, romance_beat)"
        }}
    ],
    "emotional_arc_summary": "string // 整个重大事件的情绪发展总结",
    "aftermath": "string // 整个重大事件结束后的长远影响"
}}
"""
        result = self.generator.api_client.generate_content_with_retry(
            content_type="major_event_decomposition", 
            user_prompt=prompt, 
            purpose=f"解剖事件'{major_event_skeleton.get('name')}'（服务重大事件目标）"
        )
        return result
    # 新增函数：用于验证和修正单个重大事件内部的章节覆盖率
    def _validate_and_correct_major_event_coverage(self, major_event_skeleton: Dict, fleshed_out_major_event: Dict) -> Dict:
        if not major_event_skeleton or not fleshed_out_major_event:
            return fleshed_out_major_event
        target_range_str = major_event_skeleton.get("chapter_range")
        if not target_range_str:
            self.logger.warn(f"  ⚠️ 警告：重大事件骨架 '{major_event_skeleton.get('name')}' 缺少 'chapter_range'，跳过覆盖率修正。")
            return fleshed_out_major_event
        try:
            target_start, target_end = self.parse_chapter_range(target_range_str)
            target_chapters = set(range(target_start, target_end + 1))
        except Exception as e:
            self.logger.error(f"  ❌ 错误：解析重大事件骨架范围 '{target_range_str}' 失败: {e}，跳过修正。")
            return fleshed_out_major_event
        # 1. 收集所有已覆盖的章节
        covered_chapters = set()
        all_sub_events = []
        composition = fleshed_out_major_event.get("composition", {})
        if composition:
            for phase_events in composition.values():
                if isinstance(phase_events, list):
                    all_sub_events.extend(phase_events)
        special_events = fleshed_out_major_event.get("special_emotional_events", [])
        if special_events:
            all_sub_events.extend(special_events)
        if not all_sub_events:
            self.logger.warn(f"  ⚠️ 警告：重大事件 '{fleshed_out_major_event.get('name')}' 内部分解后没有任何子事件，无法检查覆盖率。")
            return fleshed_out_major_event
        for event in all_sub_events:
            range_str = event.get("chapter_range")
            if range_str:
                try:
                    start, end = self.parse_chapter_range(range_str)
                    for i in range(start, end + 1):
                        covered_chapters.add(i)
                except Exception:
                    # 忽略解析错误的子事件，继续处理
                    pass
        # 2. 找出遗漏的章节
        missing_chapters = sorted(list(target_chapters - covered_chapters))
        if not missing_chapters:
            # 如果没有遗漏章节，直接返回
            return fleshed_out_major_event
        self.logger.info(f"  🔧 检测到重大事件 '{fleshed_out_major_event.get('name')}' 遗漏章节: {missing_chapters}，启动自动修正...")
        # 3. 找到最后一个事件并扩展其范围
        last_event_to_extend = None
        max_end_chapter = -1
        for event in all_sub_events:
            range_str = event.get("chapter_range")
            if range_str:
                try:
                    _, end = self.parse_chapter_range(range_str)
                    if end > max_end_chapter:
                        max_end_chapter = end
                        last_event_to_extend = event
                except Exception:
                    continue
        if last_event_to_extend:
            original_range = last_event_to_extend["chapter_range"]
            start, end = self.parse_chapter_range(original_range)
            # 新的结束章节应该是当前结束点和所有遗漏章节中的最大值
            new_end = max(end, max(missing_chapters))
            # 构建新的章节范围字符串，保持格式一致
            if start == new_end:
                new_range_str = f"{start}-{start}章"
            else:
                new_range_str = f"{start}-{new_end}章"
            last_event_to_extend["chapter_range"] = new_range_str
            self.logger.info(f"  ✅ 自动修正成功：将事件 '{last_event_to_extend.get('name')}' 的章节范围从 '{original_range}' 扩展为 '{new_range_str}'。")
        else:
            self.logger.error(f"  ❌ 自动修正失败：在 '{fleshed_out_major_event.get('name')}' 中未找到可供扩展范围的子事件。")
        return fleshed_out_major_event
    def _extract_all_event_ranges(self, major_events: List[Dict]) -> List[Tuple[int, int]]:
        all_ranges = []
        for major_event in major_events:
            # 1. 提取中型事件的范围
            if 'composition' in major_event and major_event['composition']:
                for phase_key, phase_events in major_event['composition'].items():
                    if isinstance(phase_events, list):
                        for medium_event in phase_events:
                            if 'chapter_range' in medium_event:
                                try:
                                    start, end = parse_chapter_range(medium_event['chapter_range'])
                                    all_ranges.append((start, end))
                                except (ValueError, TypeError):
                                    self.logger.warn(f"  ⚠️ 警告: 解析中型事件 '{medium_event.get('name')}' 的章节范围失败: {medium_event.get('chapter_range')}")
            # 2. 提取特殊情感事件的范围
            if 'special_emotional_events' in major_event and major_event['special_emotional_events']:
                for special_event in major_event['special_emotional_events']:
                    if 'chapter_range' in special_event:
                        try:
                            start, end = parse_chapter_range(special_event['chapter_range'])
                            all_ranges.append((start, end))
                        except (ValueError, TypeError):
                             self.logger.warn(f"  ⚠️ 警告: 解析特殊事件 '{special_event.get('name')}' 的章节范围失败: {special_event.get('chapter_range')}")
        return all_ranges
    # 文件: StagePlanManager.py
    def _validate_and_optimize_writing_plan(self, writing_plan: Dict, stage_name: str, stage_range: str) -> Dict:
        self.logger.info(f"  🔍 对 {stage_name} 进行章节覆盖率验证...")
        if not writing_plan or "stage_writing_plan" not in writing_plan:
            self.logger.warn(f"  ⚠️ {stage_name} 写作计划为空或结构错误，跳过验证。")
            return writing_plan
        event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        major_events = event_system.get("major_events", [])
        if not major_events:
            self.logger.warn(f"  ⚠️ {stage_name} 计划中不包含任何重大事件，无法验证。")
            return writing_plan
        try:
            stage_start, stage_end = parse_chapter_range(stage_range)
        except (ValueError, TypeError):
            self.logger.error(f"  ❌ 关键错误: 无法解析阶段章节范围 '{stage_range}'。")
            return writing_plan
        # 使用新的辅助函数提取所有事件的章节范围
        all_event_ranges = self._extract_all_event_ranges(major_events)
        if not all_event_ranges:
            self.logger.warn(f"  ⚠️ {stage_name} 计划中未找到任何有效的事件章节范围。")
            # 这种情况通常意味着整个阶段都是空白的
            self.logger.error(f"  ❌ 覆盖率检查失败: 阶段 {stage_start}-{stage_end} 完全没有内容覆盖。")
            return writing_plan
        # 创建一个布尔数组来标记每个章节是否被覆盖
        total_chapters = stage_end - stage_start + 1
        coverage_map = [False] * total_chapters
        for start, end in all_event_ranges:
            for i in range(start, end + 1):
                if stage_start <= i <= stage_end:
                    coverage_map[i - stage_start] = True
        # 检查并报告未被覆盖的章节
        uncovered_chapters = [i + stage_start for i, covered in enumerate(coverage_map) if not covered]
        if not uncovered_chapters:
            self.logger.info(f"  ✅ 章节覆盖率验证通过！阶段 {stage_start}-{stage_end} 已被完全覆盖。")
        else:
            # 为了更清晰地显示，将连续的未覆盖章节合并
            from itertools import groupby
            from operator import itemgetter
            gaps = []
            for k, g in groupby(enumerate(uncovered_chapters), lambda ix: ix[0] - ix[1]):
                group = list(map(itemgetter(1), g))
                if len(group) > 1:
                    gaps.append(f"{group[0]}-{group[-1]}")
                else:
                    gaps.append(str(group[0]))
            self.logger.error(f"  ❌ 覆盖率检查失败: {stage_name} ({stage_range}) 存在内容空白章节。")
            self.logger.info(f"    - 未覆盖的章节: {', '.join(gaps)}")
            self.logger.info(f"    - 这可能导致剧情断裂。请检查上游的事件生成逻辑和Prompt。")
        return writing_plan
    def _print_fractal_plan_summary(self, writing_plan: Dict):
        """打印分形设计写作计划的摘要，包含场景规划信息"""
        plan = writing_plan.get("stage_writing_plan", {})
        event_system = plan.get("event_system", {})
        major_events = event_system.get("major_events", [])
        chapter_scene_events = event_system.get("chapter_scene_events", [])
        # 获取分析结果
        hierarchy_assessment = plan.get("goal_hierarchy_assessment", {})
        coherence_score = hierarchy_assessment.get("overall_coherence_score", "未评估")
        scene_coverage = plan.get("scene_coverage_analysis", {})
        coverage_rate = scene_coverage.get("coverage_rate", 0)
        self.logger.info("=" * 60)
        self.logger.info(f"📄 阶段计划摘要: {plan.get('stage_name')} ({plan.get('chapter_range')})")
        self.logger.info(f"🎯 目标层级一致性: {coherence_score}/10 | 🎬 场景覆盖: {coverage_rate:.1%}")
        # 场景规划统计
        total_scenes = sum(len(chapter["scene_events"]) for chapter in chapter_scene_events)
        avg_scenes = total_scenes / len(chapter_scene_events) if chapter_scene_events else 0
        self.logger.info(f"📊 场景规划: {len(chapter_scene_events)}章, {total_scenes}个场景 (平均{avg_scenes:.1f}场景/章)")
        if hierarchy_assessment.get("hierarchy_strengths"):
            self.logger.info(f"✅ 优势: {', '.join(hierarchy_assessment['hierarchy_strengths'][:2])}")
        if scene_coverage.get("issues"):
            self.logger.info(f"⚠️  场景问题: {scene_coverage['issues']}" if scene_coverage['issues'] else "")
        self.logger.info(f"\n🚨 主龙骨包含 {len(major_events)} 个重大事件:")
        for i, major_event in enumerate(major_events, 1):
            name = major_event.get('name')
            role = major_event.get('role_in_stage_arc')
            ch_range = major_event.get('chapter_range', 'N/A')
            composition = major_event.get('composition', {})
            sub_event_count = sum(len(v) for v in composition.values())
            self.logger.info(f"    {i}. 【{role}】{name} ({ch_range})")
            self.logger.info(f"       - 目标: {major_event.get('main_goal')}")
            self.logger.info(f"       - 情绪目标: {major_event.get('emotional_goal', '未指定')}")
            self.logger.info(f"       - 分解为 {sub_event_count} 个中型事件")
            # 显示中型事件简要信息
            for phase, events in composition.items():
                for event in events[:2]:  # 只显示前2个中型事件
                    decomp_type = event.get('decomposition_type', '')
                    scene_count = len(event.get('scene_sequences', [])) if decomp_type == 'direct_scene' else '多层分解'
                    self.logger.info(f"         ◦ {event.get('name')} ({phase}, {scene_count}场景序列)")
        self.logger.info("=" * 60)
    def get_chapter_writing_context(self, chapter_number: int) -> Dict:
        """获取指定章节的写作上下文 - 基于场景事件（支持分层上下文压缩）"""
        context = self.writing_guidance_manager.get_chapter_writing_context(chapter_number)
        stage_name = self._get_current_stage(chapter_number)
        if not stage_name:
            return context
        stage_plan_data = self.get_stage_writing_plan_by_name(stage_name)
        if not stage_plan_data:
            return context
        event_system = stage_plan_data.get("stage_writing_plan", {}).get("event_system", {})
        # 获取该章节的场景事件
        chapter_scene_events = event_system.get("chapter_scene_events", [])
        current_chapter_scenes = None
        for chapter_scene in chapter_scene_events:
            if chapter_scene.get("chapter_number") == chapter_number:
                current_chapter_scenes = chapter_scene.get("scene_events", [])
                break
        # 🆕 应用分层上下文压缩
        from src.utils.LayeredContextManager import LayeredContextManager
        context_manager = LayeredContextManager()
        # 对阶段计划数据进行压缩
        compressed_stage_plan = context_manager.compress_context(
            stage_plan_data, chapter_number,
            self._get_stage_start_chapter(stage_name) if stage_name else 1,
            "plot"
        )
        # 对历史场景事件进行压缩
        compressed_chapter_scene_events = []
        for chapter_scene in chapter_scene_events:
            scene_chapter = chapter_scene.get("chapter_number", 1)
            compressed_chapter_scene = context_manager.compress_context(
                chapter_scene, chapter_number, scene_chapter, "plot"
            )
            compressed_chapter_scene_events.append(compressed_chapter_scene)
        context['scene_events'] = current_chapter_scenes
        # 🆕 添加压缩后的完整上下文
        context['stage_plan'] = compressed_stage_plan
        context['all_chapter_scenes'] = compressed_chapter_scene_events
        # 添加上下文大小信息用于调试
        context_size_info = context_manager.get_context_size_info(context)
        if context_size_info.get("is_large", False):
            self.logger.info(f"⚠️ 第{chapter_number}章阶段计划上下文较大: {context_size_info['estimated_tokens']} tokens")
        return context
    def generate_writing_guidance_prompt(self, chapter_number: int) -> str:
        """生成章节写作指导提示词"""
        return self.writing_guidance_manager.generate_writing_guidance_prompt(chapter_number)
    def get_stage_writing_plan_by_name(self, stage_name: str) -> Dict:
        """【重构版】通过阶段名称获取写作计划，优先从缓存和文件加载。"""
        # ... (此函数保持不变，它的逻辑是正确的) ...
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        # 尝试从文件加载
        plan = self._load_plan_from_file(stage_name)
        if plan:
            self.logger.info(f"  📂 从文件加载了 {stage_name} 的写作计划。")
            self.stage_writing_plans_cache[cache_key] = plan
            return plan
        # 如果文件不存在，则可能需要触发生成流程
        # self.logger.warn(f"  ⚠️ {stage_name} 的写作计划文件未找到，可能需要生成。") # 在加载阶段，找不到是正常现象，减少日志干扰
        return {}
    def _save_plan_to_file(self, stage_name: str, plan_data: Dict) -> Path:
        """将阶段计划保存到JSON文件。【已修复】兼容不同数据结构并增强日志。"""
        # 1. 规范化数据结构，找到真正的计划内容
        plan_content = {}
        # 检查传入的数据是否是带 "stage_writing_plan" 包装的完整结构
        if "stage_writing_plan" in plan_data and isinstance(plan_data["stage_writing_plan"], dict):
            plan_content = plan_data["stage_writing_plan"]
            self.logger.info(f"  💾 (日志) 保存: 检测到 'stage_writing_plan' 包装器，使用其内部数据。")
        else:
            # 假设传入的是解包后的核心内容
            plan_content = plan_data
            self.logger.info(f"  💾 (日志) 保存: 未检测到 'stage_writing_plan' 包装器，直接使用传入数据。")
        novel_title = self.generator.novel_data.get("novel_title", "unknown")
        self.logger.info(f"  💾 (日志) 从计划数据中提取到的小说标题为: '{novel_title}'")
        # 增加关键的调试日志，如果标题是 "unknown"
        if novel_title == "unknown":
            self.logger.warn(f"  ⚠️ 警告：无法从计划数据中提取到有效的小说标题，文件名将使用 'unknown'。")
            self.logger.info(f"      请检查传入的 plan_data 中 'novel_metadata' -> 'title' 路径是否存在且有值。")
            # 打印传入数据的一小部分结构以帮助调试
            try:
                partial_data_str = json.dumps(plan_data, ensure_ascii=False, indent=2, default=str)
                self.logger.info(f"      传入的 plan_data 结构预览 (最多500字符):\n{partial_data_str[:500]}...")
            except Exception as e:
                self.logger.info(f"      无法打印 plan_data 结构预览: {e}")
        # 3. 构建小说项目目录路径
        safe_title = "".join(c for c in novel_title if c.isalnum() or c in (' ', '-', '_', ':', '：', '（', '）', '(', ')', '[', ']')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        novel_project_dir = self.plans_dir / safe_title
        plans_dir = novel_project_dir / "plans"
        
        # 4. 构建文件路径
        file_path = plans_dir / f"{safe_title}_{stage_name}_writing_plan.json"
        # 4. 准备要写入文件的数据 (确保保存时始终使用标准的包装结构)
        data_to_write = {}
        if "stage_writing_plan" in plan_data:
            data_to_write = plan_data  # 已经是包装好的，直接使用
        else:
            data_to_write = {"stage_writing_plan": plan_content} # 手动包装，确保文件格式一致性
        # 5. 执行保存操作（原子写入：先写入临时文件，再重命名）
        try:
            # 确保目录存在
            os.makedirs(plans_dir, exist_ok=True)
            temp_path = file_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data_to_write, f, ensure_ascii=False, indent=4)
            # 原子替换（在Windows上使用replace以覆盖目标）
            try:
                temp_path.replace(file_path)
            except Exception:
                # 回退到 os.replace 作为兼容方案
                os.replace(str(temp_path), str(file_path))
            self.logger.info(f"  💾 阶段计划已成功保存到: {file_path}")
            return file_path
        except Exception as e:
            self.logger.error(f"  ❌ 保存计划文件 '{file_path}' 失败: {e}")
            return None  # type: ignore
    def _load_plan_from_file(self, stage_name: str) -> Optional[Dict]:
        self.logger.info(f"\n📂 (日志) 开始加载阶段 '{stage_name}' 的计划文件...")
        # --- 策略 1: 尝试使用标准命名约定加载 ---
        self.logger.info(f"  - (1/2) 尝试使用标准命名约定加载...")
        novel_title = self.generator.novel_data.get("novel_title", "unknown")
        self.logger.info(f"    - 用于构建路径的小说标题: '{novel_title}'")
        if novel_title == "unknown":
            self.logger.warn(f"    - ⚠️ 警告: 小说标题为 'unknown'，可能导致无法找到正确文件。")
        safe_title = "".join(c for c in novel_title if c.isalnum() or c in (' ', '-', '_', ':', '：', '（', '）', '(', ')', '[', ']')).rstrip()
        safe_title = safe_title.replace(' ', '_')
        novel_project_dir = self.plans_dir / safe_title
        plans_dir = novel_project_dir / "plans"
        expected_file_path = plans_dir / f"{safe_title}_{stage_name}_writing_plan.json"
        self.logger.info(f"    - 正在检查标准路径: {expected_file_path}")
        if expected_file_path.exists():
            # ▼▼▼【核心修复】检查文件是否为空，并增强错误处理 ▼▼▼
            try:
                # 在尝试读取前，先判断文件大小
                if expected_file_path.stat().st_size == 0:
                    self.logger.error(f"    - ❌ 警告：文件 '{expected_file_path}' 为空（0字节），将被忽略。")
                    self.logger.info(f"      这通常是上一次程序保存该文件时意外中断导致的。")
                    # 直接返回None，让程序认为文件不存在，后续可能会重新生成
                    return None
                with open(expected_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.logger.info(f"    - ✅ 成功加载并解析文件。")
                    return data
            except json.JSONDecodeError as e:
                self.logger.error(f"    - ❌ 文件 '{expected_file_path}' 存在但JSON格式已损坏，解析失败: {e}")
                self.logger.info(f"    - ℹ️ 建议：请手动删除此损坏文件，程序将在需要时尝试重新生成。")
                return None # 明确返回None，表示加载失败
            except IOError as e:
                self.logger.error(f"    - ❌ 文件 '{expected_file_path}' 存在但读取时发生IO错误: {e}")
                return None # 明确返回None，表示加载失败
            # ▲▲▲【核心修复】结束 ▲▲▲
        else:
            self.logger.info(f"    - ℹ️ 标准路径文件未找到。")
        # --- 策略 2: 尝试使用 novel_data 中记录的旧路径加载 (回退逻辑保持不变) ---
        self.logger.info(f"  - (2/2) 尝试使用 novel_data 中的记录路径加载 (作为回退)...")
        path_info = self.generator.novel_data.get("stage_writing_plans", {}).get(stage_name, {})
        if "path" in path_info and path_info["path"]:
            # ... (这部分回退逻辑可以保持原样，因为它本身也有自己的try-except)
            fallback_path_str = path_info["path"]
            fallback_file_path = Path(fallback_path_str)
            if not fallback_file_path.is_absolute():
                # 假设 project_path 存在
                project_path = getattr(self.generator, 'project_path', Path.cwd())
                fallback_file_path = project_path / fallback_path_str
            self.logger.info(f"    - 在 novel_data 中找到记录路径: {fallback_file_path}")
            if fallback_file_path.exists():
                try:
                    if fallback_file_path.stat().st_size == 0:
                        self.logger.error(f"    - ❌ 警告：回退路径文件 '{fallback_file_path}' 为空，将被忽略。")
                        return None
                    with open(fallback_file_path, 'r', encoding='utf-8') as f:
                        self.logger.info(f"    - ✅ 成功加载回退路径的文件。")
                        return json.load(f)
                except (json.JSONDecodeError, IOError) as e:
                    self.logger.error(f"    - ❌ 回退路径文件 '{fallback_file_path}' 存在但加载或解析失败: {e}")
                    return None
            else:
                 self.logger.info(f"    - ℹ️ 回退路径文件未找到。")
        else:
            self.logger.info(f"    - ℹ️ 在 novel_data 中未找到 '{stage_name}' 的记录路径。")
        # --- 如果所有策略都失败 ---
        self.logger.warn(f"  ⚠️ (日志) 加载失败: 未能从任何已知位置找到或加载 '{stage_name}' 的计划文件。")
        return None
    def get_stage_plan_for_chapter(self, chapter_number: int) -> Dict:
        """为指定章节获取阶段计划 - 此方法现在会通过文件加载。"""
        current_stage = self._get_current_stage(chapter_number)
        if not current_stage:
            self.logger.warn(f"  ⚠️ 无法确定第{chapter_number}章所属的阶段")
            return {}
        stage_plan_data = self.get_stage_writing_plan_by_name(current_stage)
        if not stage_plan_data:
            self.logger.warn(f"  ⚠️ 没有找到或加载 {current_stage} 的写作计划")
            return {}
        return stage_plan_data.get("stage_writing_plan", stage_plan_data)
    def export_events_to_json(self, file_path: str = "novel_events.json"):
        """导出事件到JSON"""
        return self.event_manager.export_events_to_json(file_path)
    def get_events_summary(self) -> Dict:
        """获取事件摘要"""
        return self.event_manager.get_events_summary()
    def generate_stage_emotional_plan(self, stage_name: str, stage_range: str, global_emotional_plan: Dict) -> Dict:
        """生成阶段情绪计划"""
        return self.emotional_manager.generate_stage_emotional_plan(stage_name, stage_range, global_emotional_plan)
    def _get_current_stage(self, chapter_number: int) -> str:
        """获取当前章节所属的阶段名称。"""
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        stage_plan_dict = overall_plans.get("overall_stage_plan", {})
        if not stage_plan_dict:
            self.logger.warn("  ⚠️ 没有可用的整体阶段计划来确定当前阶段")
            return ""
        for stage_name, stage_info in stage_plan_dict.items():
            chapter_range_str = stage_info.get("chapter_range", "")
            if is_chapter_in_range(chapter_number, chapter_range_str):
                return stage_name
        self.logger.warn(f"  ⚠️ 第{chapter_number}章不在任何已定义的阶段范围内")
        return ""  # 返回空字符串而不是None
    @staticmethod
    def is_chapter_in_range(chapter: int, range_str: str) -> bool:
        try:
            # 移除"章"字、中文括号及其内容、和其他非数字字符（除了横杠和数字）
            # 先移除中文括号及其内容（如：（前段）、（后段）等）
            cleaned_str = re.sub(r'[（(][^）)]*[）)]', '', str(range_str))
            # 再移除"章"字、"第"字、空白字符
            cleaned_str = cleaned_str.replace("章", "").replace("第", "").strip()
            if "-" in cleaned_str:
                parts = cleaned_str.split("-")
                if len(parts) == 2:
                    start = int(parts[0])
                    end = int(parts[1])
                    return start <= chapter <= end
            else:
                # 如果只有单个数字
                target_chapter = int(cleaned_str)
                return chapter == target_chapter
        except (ValueError, AttributeError, IndexError):
            # 不能使用self.logger，因为这是静态方法
            # 改为使用模块级日志
            from src.utils.logger import get_logger
            logger = get_logger("StagePlanManager")
            logger.warn(f"⚠️ 解析章节范围失败: '{range_str}'，返回False")
            return False
    def _get_stage_length(self, stage_range: str) -> int:
        """获取阶段长度"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        return end_chap - start_chap + 1
    def get_stage_specific_guidance(self, stage_name: str) -> str:
        """获取阶段特定的写作指导"""
        stage_guidance = {
            "opening_stage": "## 🚀 起 (开局阶段): 一切为7日留存服务。核心是快速建立冲突，用强力钩子抓住读者。",
            "development_stage": "## 📈 承 (发展阶段): 节奏变化与全面升级。核心是深化矛盾，让角色在挑战中成长，并扩展世界观。",
            "climax_stage": "## ⚡ 转 (高潮阶段): 矛盾总爆与情感宣泄。核心是让所有线索汇集并爆发，带来颠覆性转折和情感顶点。",
            "ending_stage": "## 🏁 合 (结局阶段): 尘埃落定与意蕴悠长。核心是解决所有核心冲突，回收所有重要伏笔，给予读者情感满足和回味空间。"
        }
        return stage_guidance.get(stage_name, "## 阶段写作指导\n\n请根据故事发展需要合理安排事件。")
    def get_current_stage_plan(self, chapter_number: int) -> Optional[Dict]:
        """获取当前章节所属阶段的详细计划（兼容性方法）"""
        return self.get_chapter_writing_context(chapter_number)
    def _get_stage_range(self, stage_name: str) -> str:
        """获取阶段章节范围"""
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        if not overall_plans or "overall_stage_plan" not in overall_plans:
            self.logger.warn(f"  ⚠️ 无法从整体计划中找到 {stage_name} 的范围，使用默认值。")
            return "1-100" 
        stage_plan_dict = overall_plans["overall_stage_plan"]
        stage_info = stage_plan_dict.get(stage_name)
        if stage_info and "chapter_range" in stage_info:
            return stage_info["chapter_range"]
        self.logger.warn(f"  ⚠️ 在整体计划字典中未找到 {stage_name} 的章节范围，使用默认值。")
        return "1-100"
    def assess_stage_event_continuity(self, stage_writing_plan: Dict, stage_name: str, 
                                    stage_range: str, creative_seed: str, 
                                    novel_title: str, novel_synopsis: str) -> Dict:
        self.logger.info(f"  🤖 【网文白金策划师】正在评估{stage_name}阶段事件连续性...")
        # 提取事件系统
        if "stage_writing_plan" in stage_writing_plan:
            event_system = stage_writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = stage_writing_plan.get("event_system", {})
        # 构建连续性评估提示词
        continuity_prompt = self._build_stage_continuity_prompt(
            event_system, stage_name, stage_range, creative_seed, novel_title, novel_synopsis
        )
        try:
            continuity_assessment = self.generator.api_client.generate_content_with_retry(
                content_type="stage_event_continuity_master_reviewer", # 新ID
                user_prompt=continuity_prompt,
                purpose=f"【网文白金策划师】评估{stage_name}阶段事件连续性"
            )
            if continuity_assessment:
                # 将评估结果整合到写作计划中
                if "stage_writing_plan" in stage_writing_plan:
                    stage_writing_plan["stage_writing_plan"]["continuity_assessment"] = continuity_assessment
                else:
                    stage_writing_plan["continuity_assessment"] = continuity_assessment
                self.logger.info(f"  ✅ 【网文白金策划师】评估{stage_name}阶段事件连续性完成。")
                return continuity_assessment
            else:
                self.logger.warn(f"  ⚠️ 【网文白金策划师】评估{stage_name}阶段事件连续性失败，使用默认结果。")
                return self._create_default_continuity_assessment() # 新增一个默认的连续性评估结果
        except Exception as e:
            self.logger.error(f"  ❌ 【网文白金策划师】连续性评估出错: {e}，使用默认结果。")
            return self._create_default_continuity_assessment()
    def _build_stage_continuity_prompt(self, event_system: Dict, stage_name: str, stage_range: str,
                                    creative_seed: str, novel_title: str, novel_synopsis: str) -> str:
        # 提取和格式化事件信息
        major_events = event_system.get("major_events", [])
        medium_events = event_system.get("medium_events", [])
        minor_events = event_system.get("minor_events", [])
        prompt_parts = [
            "# 🎯 【AI网文白金策划师】对阶段事件安排进行“商业价值”连续性深度评估",
            "",
            "## 评估任务",
            f"作为一位对网文叙事流畅性和商业价值有着极致要求的【网文白金策划师】，你将对**{stage_name}**阶段（{stage_range}）的事件安排进行“商业价值”连续性深度评估。",
            "你的目标是：确保所有事件之间的**逻辑链条清晰合理**，叙事节奏**张弛有度、高潮迭起，保持读者追读热情**，情感发展**流畅自然，能有效调动读者情绪**，主线推进**高效且富有张力**。你不能容忍任何突兀、平淡或无趣之处。",
            "",
            "## 小说基本信息",
            f"- 标题: {novel_title}",
            f"- 简介: {novel_synopsis}",
            f"- 创意种子: {creative_seed}",
            f"- 阶段: {stage_name} ({stage_range})",
            "",
            "## 事件安排详情",
            "(请详细阅读以下事件安排，这是你进行评估的唯一依据)"
        ]
        # 重大事件详情 (保持和_build_hierarchy_description类似，但可以更精炼)
        if major_events:
            prompt_parts.extend([
                "### 🚨 重大事件安排 (主线骨架)",
                "| 事件名称 | 章节范围 | 核心目标 | 情绪目标 |",
                "|---------|---------|----------|----------|"
            ]) # FIX: Added closing parenthesis
            for event in major_events:
                prompt_parts.append(
                    f"| {event.get('name', '未命名')} | {event.get('chapter_range', '?')} | {event.get('main_goal', '未指定')} | {event.get('emotional_goal', '未指定')} |"
                )
            prompt_parts.append("")
        # 中型事件详情 (同样精炼)
        if medium_events:
            prompt_parts.extend([
                "### 📈 中型事件安排 (主线肌肉)",
                "| 事件名称 | 章节范围 | 核心目标 | 情绪重点 | 贡献关系 |",
                "|---------|---------|----------|----------|----------|"
            ]) # FIX: Added closing parenthesis
            for event in medium_events:
                prompt_parts.append(
                    f"| {event.get('name', '未命名')} | {event.get('chapter_range', '?')} | "
                    f"{event.get('main_goal', '未指定')} | {event.get('emotional_focus', '未指定')} | {event.get('contribution_to_major', '独立')} |"
                )
            prompt_parts.append("")
        # 小型事件和特殊情感事件可以合并处理或仅提及数量
        # 这里为了简化，只保留主要事件结构
        prompt_parts.extend([
            "## 📊 事件时间线与叙事商业价值分析 (请你以“爆款网文”的标准进行评判，1-10分制，并给出极其详细的评语)：",
            "",
            "### 1. 逻辑连贯性与因果关系合理度 (权重 20%)",
            "- 事件之间的因果关系是否**清晰合理，不易产生逻辑漏洞**？",
            "- 是否存在任何逻辑断层、跳跃，或**需要读者脑补的低级错误**？", 
            "- 事件发展是否**符合角色动机和世界观设定**，没有一丝违和？",
            "- 伏笔的埋设与回收是否**有效巧妙，能带来阅读爽感**？",
            "",
            "### 2. 叙事节奏与爽点分布 (权重 20%)",
            "- 事件密度分布是否**张弛有度，高潮密集，低谷不拖沓，适合日更连载节奏**？",
            "- 是否有事件过于密集导致压迫感过强，或过于稀疏导致平淡无趣的区域？",
            "- 节奏是否**符合该阶段的读者期待**，并能有效引导读者情绪？",
            "",
            "### 3. 情感发展连续性与读者代入感 (权重 15%)",
            "- 情感弧线是否**连贯自然，富有层次，且能有效调动读者情绪，产生强烈代入感**？",
            "- 情感高潮的铺垫是否**充分且巧妙**，爆发点是否震撼人心？",
            "- 情感变化是否**符合角色发展轨迹和人物命运**，没有一丝生硬？",
            "",
            "### 4. 主线推进效率与核心冲突张力 (权重 15%)", 
            "- 主线情节是否**持续、高效、且富有张力地推进**？",
            "- 是否存在主线停滞过久、核心冲突弱化的问题？",
            "- 支线与主线的关联是否**精巧，能互相促进，而非喧宾夺主**？",
            "",
            "### 5. 阶段过渡与整体结构流畅度 (权重 10%)",
            "- 与前后阶段的衔接是否**流畅衔接，不显突兀**？",
            "- 阶段内部的事件安排是否**极致地服务于阶段目标，且具备清晰的内在结构**？",
            "",
            "### 6. 新意与爆点评估 (权重 10%)",
            "- 剧情设计中是否有**在流行设定中的新颖创意和爆点**？",
            "- 是否过度依赖无趣的网文套路，缺乏新颖度和吸引力？",
            "",
            "### 7. 细节伏笔与回收有效性 (权重 10%)",
            "- 剧情中的细节（伏笔、暗示、巧合）是否**被有效地铺垫和回收**，而非简单的推进？",
            "- 是否能感受到作者（AI）在细节上的用心和巧思，提升阅读爽感？",
            "",
            "## 🎯 评估要求",
            "请提供**极其具体、可操作的评估结果**和**提升至爆款网文的改进建议**。",
            "对于每个维度，请给出1-10分的评分，并附上详细的评语和建议。",
            "",
            "## 📋 输出格式",
            "请以严格的JSON格式返回评估结果：",
            "{",
            '  "overall_continuity_score": "float // 根据上述权重计算出的总连续性评分 (满分10分)",',
            '  "logic_coherence_score": "float // 逻辑连贯性与因果关系合理度评分 (1-10)",',
            '  "logic_coherence_comment": "string // 详细评语及优化建议",',
            '  "narrative_rhythm_score": "float // 叙事节奏与爽点分布评分 (1-10)",',
            '  "narrative_rhythm_comment": "string // 详细评语及优化建议",',
            '  "emotional_continuity_score": "float // 情感发展连续性与读者代入感评分 (1-10)",',
            '  "emotional_continuity_comment": "string // 详细评语及优化建议",',
            '  "main_thread_efficiency_score": "float // 主线推进效率与核心冲突张力评分 (1-10)",',
            '  "main_thread_efficiency_comment": "string // 详细评语及优化建议",',
            '  "stage_transition_score": "float // 阶段过渡与整体结构流畅度评分 (1-10)",',
            '  "stage_transition_comment": "string // 详细评语及优化建议",',
            '  "innovation_score": "float // 新意与爆点评估评分 (1-10)",',
            '  "innovation_comment": "string // 详细评语及优化建议",',
            '  "detail_foreshadowing_score": "float // 细节伏笔与回收有效性评分 (1-10)",',
            '  "detail_foreshadowing_comment": "string // 详细评语及优化建议",',
            '  "master_reviewer_verdict": "string // 网文白金策划师的最终总结性评语，如“结构合理，高潮迭起，但部分细节仍可加强以提升读者爽感”",',
            '  "perfection_suggestions": ["string // 提升至“爆款网文”的3-5条核心建议，每条建议都应具体、可操作"]',
            "}"
        ])
        return "\n".join(prompt_parts)
    def _create_default_continuity_assessment(self) -> Dict:
        """创建默认的连续性评估结果，当AI评估失败时使用"""
        return {
            "overall_continuity_score": 5.0,
            "logic_coherence_score": 5.0,
            "logic_coherence_comment": "AI评估服务暂时不可用，无法进行详细评估。",
            "narrative_rhythm_score": 5.0,
            "narrative_rhythm_comment": "AI评估服务暂时不可用，无法进行详细评估。",
            "emotional_continuity_score": 5.0,
            "emotional_continuity_comment": "AI评估服务暂时不可用，无法进行详细评估。",
            "main_thread_efficiency_score": 5.0,
            "main_thread_efficiency_comment": "AI评估服务暂时不可用，无法进行详细评估。",
            "stage_transition_score": 5.0,
            "stage_transition_comment": "AI评估服务暂时不可用，无法进行详细评估。",
            "innovation_score": 5.0,
            "innovation_comment": "AI评估服务暂时不可用，无法进行详细评估。",
            "detail_foreshadowing_score": 5.0,
            "detail_foreshadowing_comment": "AI评估服务暂时不可用，无法进行详细评估。",
            "master_reviewer_verdict": "评估系统暂时不可用，无法提供商业价值评估。",
            "perfection_suggestions": ["等待AI评估服务恢复后重新评估。"]
        }
    def _generate_simple_stage_plan_for_test(self, stage_name: str, stage_range: str, overall_stage_plan: Dict) -> Dict:
        """在测试模式下返回简化版阶段写作计划，跳过复杂的AI分解流程"""
        start, end = self.parse_chapter_range(stage_range)
        # Get stage info from overall_stage_plan if available
        stage_info = overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {})
        stage_goal = stage_info.get("stage_arc_goal", f"{stage_name} stage goal")
        return {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "stage_overview": stage_goal,
                "event_system": {
                    "major_events": [
                        {
                            "name": f"{stage_name} - Major Event 1",
                            "chapter_range": f"{start}-{start + (end-start)//2}",
                            "main_goal": "推进主情节",
                            "composition": {
                                "起": [{
                                    "name": "Scene 1",
                                    "chapter_range": f"{start}-{start + (end-start)//4}",
                                    "main_goal": "引入事件"
                                }],
                                "承": [{
                                    "name": "Scene 2",
                                    "chapter_range": f"{start + (end-start)//4 + 1}-{start + (end-start)//2}",
                                    "main_goal": "推进情节"
                                }]
                            }
                        },
                        {
                            "name": f"{stage_name} - Major Event 2",
                            "chapter_range": f"{start + (end-start)//2 + 1}-{end}",
                            "main_goal": "高潮与转折",
                            "composition": {
                                "转": [{
                                    "name": "Scene 3",
                                    "chapter_range": f"{start + (end-start)//2 + 1}-{start + 3*(end-start)//4}",
                                    "main_goal": "创造转折"
                                }],
                                "合": [{
                                    "name": "Scene 4",
                                    "chapter_range": f"{start + 3*(end-start)//4 + 1}-{end}",
                                    "main_goal": "阶段收尾"
                                }]
                            }
                        }
                    ]
                },
                "summary": f"Simplified test plan for {stage_name}"
            }
        }
