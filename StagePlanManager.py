# StagePlanManager.py
import json
import re
import os
from typing import Dict, Optional, List
from pathlib import Path
from EventManager import EventManager
from EmotionalPlanManager import EmotionalPlanManager
from WritingGuidanceManager import WritingGuidanceManager
from RomancePatternManager import RomancePatternManager
from utils import parse_chapter_range, is_chapter_in_range

class StagePlanManager:
    """剧情骨架设计器 - 专注如何将内容转化为剧情（怎么写）"""
    
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.overall_stage_plans = None
        self.stage_boundaries = {}
        self.stage_writing_plans_cache = {}
        
        # 初始化各个管理器
        self.event_manager = EventManager(self)
        self.writing_guidance_manager = WritingGuidanceManager(self)

        # 为阶段计划创建专用的存储目录
        self.plans_dir = Path("./quality_data/plans")
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
        print("=== 生成全书阶段计划 ===")
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
            "overall_stage_plan", user_prompt, purpose="制定全书阶段计划"
        )
        
        if result and isinstance(result, dict):
            self.overall_stage_plans = result
            self.stage_boundaries = boundaries
            self.generator.novel_data["overall_stage_plans"] = result
            print("✓ 全书阶段计划生成成功")
            return result
        else:
            print("❌ 全书阶段计划生成失败")
            return None

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
            print("暂无阶段计划数据")
            return
        
        print("\n" + "=" * 60)
        print("                   小说阶段计划概览")
        print("=" * 60)
        
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
            
            print(f"\n📚 阶段 {i}: {stage_name}")
            print(f"   📖 章节: {start_ch}-{end_ch}章 (共{chapter_count}章)")
            print(f"   🎯 目标: {stage_info.get('stage_goal', stage_info.get('core_tasks', '暂无目标描述'))}")
            print(f"   ⚡ 关键发展: {stage_info.get('key_developments', stage_info.get('key_content', '暂无关键事件'))}")
            if stage_info.get('core_conflicts'):
                print(f"   ⚔️ 核心冲突: {stage_info.get('core_conflicts')}")
        
        print(f"\n📈 总计: {len(stage_plan_dict)}个阶段，{total_chapters}章")
        print("=" * 60)

    def generate_stage_writing_plan(self, stage_name: str, stage_range: str, creative_seed: str,
                                    novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """【重构版】生成阶段详细写作计划 - 采用分形设计工作流，并保存到独立文件。"""
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]

        print(f"🎬 开始为【{stage_name}】生成分形写作计划...")

        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        emotional_blueprint = self.generator.novel_data.get("emotional_blueprint", {})
        stage_emotional_plan = self.generator.emotional_plan_manager.generate_stage_emotional_plan(
            stage_name, stage_range, emotional_blueprint
        )
        density_requirements = self.event_manager.calculate_optimal_event_density_by_stage(stage_name, stage_length)

        print("   fase 1: 规划阶段的'主龙骨' (重大事件框架)...")
        major_event_skeletons = self._generate_major_event_skeleton(
            stage_name, stage_range, novel_title, novel_synopsis, creative_seed,
            stage_emotional_plan, overall_stage_plan, density_requirements
        )

        if not major_event_skeletons:
            print(f"  ❌ 阶段主龙骨生成失败，无法继续。")
            return {}

        print("   fase 2: 逐一'解剖'重大事件，填充中型事件血肉...")
        fleshed_out_major_events = []
        for skeleton in major_event_skeletons:
            print(f"    -> 正在解剖重大事件: '{skeleton['name']}' ({skeleton['chapter_range']})")
            fleshed_out_event = self._decompose_major_event(
                skeleton, stage_name, stage_range, novel_title, novel_synopsis, creative_seed
            )
            fleshed_out_major_events.append(fleshed_out_event)

        print("  fase 3: 组装并验证最终的写作计划...")
        final_writing_plan = self._assemble_final_plan(
            stage_name, stage_range, fleshed_out_major_events, overall_stage_plan
        )
        
        # 🆕 新增：进行AI连续性评估和优化
        if final_writing_plan:
            continuity_assessment = self.assess_stage_event_continuity(
                final_writing_plan, stage_name, stage_range, creative_seed, novel_title, novel_synopsis
            )
            if continuity_assessment.get("overall_continuity_score", 10) < 9.5:
                print(f"  ⚠️ 阶段事件连续性评分较低，进行优化...")
                final_writing_plan = self._optimize_based_on_continuity_assessment(
                    final_writing_plan, continuity_assessment, stage_name, stage_range
                )
        
        final_writing_plan = self._validate_and_optimize_writing_plan(
            final_writing_plan, stage_name, stage_range
        )

        if final_writing_plan:
            # 保存到文件，并更新主数据文件中的路径
            file_path = self._save_plan_to_file(stage_name, final_writing_plan)
            
            self.stage_writing_plans_cache[cache_key] = final_writing_plan
            
            if "stage_writing_plans" not in self.generator.novel_data:
                self.generator.novel_data["stage_writing_plans"] = {}
            # 在主数据文件中只保存文件路径的相对字符串，而不是整个计划
            relative_path = os.path.join("plans", f"{stage_name}_writing_plan.json")
            self.generator.novel_data["stage_writing_plans"][stage_name] = {"path": relative_path}
            
            print(f"  ✅ 【{stage_name}】分形写作计划生成完成！")
            self._print_fractal_plan_summary(final_writing_plan)
            return final_writing_plan
        else:
            print(f"  ⚠️ 【{stage_name}】写作计划生成失败。")
            return {}

    def _generate_major_event_skeleton(self, stage_name, stage_range, novel_title, novel_synopsis,
                                       creative_seed, stage_emotional_plan, overall_stage_plan,
                                       density_requirements) -> List[Dict]:
        """工作流第一阶段：仅生成重大事件的框架。"""
        prompt = f"""
# 任务：小说阶段"主龙骨"设计
作为顶级的剧情架构师，你的任务是为小说的【{stage_name}】({stage_range})规划出宏观的"主龙骨"。你只需专注于设计 **{density_requirements['major_events']}个** 相互关联、构成完整"起承转合"结构的**重大事件**。

## 核心上下文
- **小说**: {novel_title} - {novel_synopsis}
- **阶段总体目标**: {overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("stage_goal", "N/A")}
- **阶段情绪弧线**: {stage_emotional_plan.get('main_emotional_arc', 'N/A')}

## 设计要求
1.  **结构**: 你设计的这 {density_requirements['major_events']} 个重大事件，必须共同构成一个服务于【阶段总体目标】的"起、承、转、合"叙事链条。
2.  **分工**: 明确每个重大事件在阶段"起承转合"中的作用。
3.  **章节估算**: 为每个重大事件估算一个大致的章节范围，确保它们能覆盖整个 {stage_range}。

## 输出格式: 严格返回一个JSON列表
[
    {{
        "name": "string // 第一个重大事件的名称",
        "role_in_stage_arc": "起",
        "chapter_range": "string // 估算的章节范围 (例如：'49-58章')",
        "main_goal": "string // 这个重大事件的核心目标",
        "emotional_arc": "string // 此事件要带给读者的核心情感体验",
        "description": "string // 对该事件的简要描述"
    }},
    // ... more major events
]
"""
        result = self.generator.api_client.generate_content_with_retry(
            "stage_major_event_skeleton", prompt, purpose=f"生成{stage_name}主龙骨"
        )
        return result if isinstance(result, list) else None

    def _decompose_major_event(self, major_event_skeleton: Dict, stage_name: str, stage_range: str,
                               novel_title: str, novel_synopsis: str, creative_seed: str) -> Dict:
        """工作流第二阶段：将单个重大事件分解为中型事件的"起承转合"。"""
        prompt = f"""
# 任务：重大事件"分形解剖"
你需要将一个宏观的"重大事件"进行"解剖"，为其设计内部的、更为详细的"起承转合"结构，由3-5个中型事件构成。

## 当前重大事件信息
- **所属阶段**: {stage_name}
- **重大事件名称**: {major_event_skeleton.get('name')}
- **事件章节范围**: {major_event_skeleton.get('chapter_range')}
- **事件核心目标**: {major_event_skeleton.get('main_goal')}

## 输出格式: 严格返回一个包含'composition'字段的JSON对象
{{
    "name": "{major_event_skeleton.get('name')}",
    "type": "major_event",
    "role_in_stage_arc": "{major_event_skeleton.get('role_in_stage_arc')}",
    "main_goal": "{major_event_skeleton.get('main_goal')}",
    "composition": {{
        "起": [ {{ "name": "中型事件名", "type": "medium_event", "chapter": "integer", "main_goal": "目标", "description": "描述" }} ],
        "承": [ {{ "name": "中型事件名", "type": "medium_event", "chapter": "integer", "main_goal": "目标", "description": "描述" }} ],
        "转": [ {{ "name": "中型事件名", "type": "medium_event", "chapter": "integer", "main_goal": "目标", "description": "描述" }} ],
        "合": [ {{ "name": "中型事件名", "type": "medium_event", "chapter": "integer", "main_goal": "目标", "description": "描述" }} ]
    }},
    "aftermath": "string // 整个重大事件结束后的长远影响"
}}
"""
        result = self.generator.api_client.generate_content_with_retry(
            "major_event_decomposition", prompt, purpose=f"解剖事件'{major_event_skeleton.get('name')}'"
        )
        
        start_ch, end_ch = parse_chapter_range(major_event_skeleton.get('chapter_range', '0-0'))
        if result and isinstance(result, dict):
            result["start_chapter"] = start_ch
            result["end_chapter"] = end_ch
        
        return result

    def _assemble_final_plan(self, stage_name, stage_range, fleshed_out_major_events, overall_stage_plan) -> Dict:
        """工作流第三阶段：将所有生成的部分组装成最终的JSON计划。"""
        medium_events_flat = []
        for major_event in fleshed_out_major_events:
            composition = major_event.get("composition", {})
            for phase_events in composition.values():
                medium_events_flat.extend(phase_events)
        medium_events_flat.sort(key=lambda x: x.get('chapter', 0))

        stage_plan = {
            "stage_writing_plan": {
                "stage_name": stage_name,
                "chapter_range": stage_range,
                "stage_overview": overall_stage_plan.get("overall_stage_plan", {}).get(stage_name, {}).get("stage_goal", "N/A"),
                "event_system": {
                    "overall_approach": "采用分形设计，将阶段分解为多个具有独立'起承转合'的重大事件，再将重大事件分解为中型事件链条，确保结构严密，节奏可控。",
                    "major_events": fleshed_out_major_events,
                    "medium_events": medium_events_flat,
                    "minor_events": []
                },
            }
        }
        return stage_plan

    def _validate_and_optimize_writing_plan(self, writing_plan: Dict, stage_name: str, stage_range: str) -> Dict:
        """验证并优化写作计划"""
        if not writing_plan:
            print(f"  ⚠️ {stage_name}写作计划为空，跳过验证")
            return {}
        
        print(f"  🔍 对 {stage_name} 进行最终验证和优化...")
        
        # 增强大事件结构
        writing_plan = self.event_manager.enhance_major_events_structure(writing_plan, stage_name, stage_range)
        
        # 验证事件密度
        event_density_ok = self.event_manager.validate_stage_event_density(writing_plan, stage_name, stage_range)
        if not event_density_ok:
            print(f"  ⚠️ {stage_name} 最终事件密度不符合要求。")
        
        # 验证大事件结构
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        major_events = events.get("major_events", [])
        major_validation = self.event_manager.validate_major_event_structure(major_events)
        
        if not major_validation["is_valid"]:
            print(f"  ⚠️ {stage_name}大事件结构存在问题，进行优化...")
            writing_plan = self.event_manager.enhance_major_events_structure(writing_plan, stage_name, stage_range)
        
        # 验证主线连贯性
        is_continuous = self.event_manager.validate_main_thread_continuity(writing_plan, stage_name)
        if not is_continuous:
            print(f"  ⚠️ {stage_name}写作计划存在事件间隔过长问题")
        
        return writing_plan
    
    def _print_fractal_plan_summary(self, writing_plan: Dict):
        """打印分形设计写作计划的摘要。"""
        plan = writing_plan.get("stage_writing_plan", {})
        event_system = plan.get("event_system", {})
        major_events = event_system.get("major_events", [])
        
        print("-" * 40)
        print(f"📄 计划摘要: {plan.get('stage_name')} ({plan.get('chapter_range')})")
        print(f"  主龙骨包含 {len(major_events)} 个重大事件：")
        
        for i, major_event in enumerate(major_events):
            name = major_event.get('name')
            role = major_event.get('role_in_stage_arc')
            ch_range = f"{major_event.get('start_chapter', 'N/A')}-{major_event.get('end_chapter', 'N/A')}章"
            composition = major_event.get('composition', {})
            sub_event_count = sum(len(v) for v in composition.values())
            print(f"    {i+1}. 【{role}】{name} ({ch_range})")
            print(f"       - 目标: {major_event.get('main_goal')}")
            print(f"       - 分解为 {sub_event_count} 个中型事件。")
        print("-" * 40)

    def get_chapter_writing_context(self, chapter_number: int) -> Dict:
        """获取指定章节的写作上下文，适配分形结构。"""
        context = self.writing_guidance_manager.get_chapter_writing_context(chapter_number)
        
        stage_name = self._get_current_stage(chapter_number)
        if not stage_name:
            return context

        stage_plan_data = self.get_stage_writing_plan_by_name(stage_name)
        if not stage_plan_data:
            return context
            
        event_system = stage_plan_data.get("stage_writing_plan", {}).get("event_system", {})
        major_events = event_system.get("major_events", [])

        current_major_event = None
        current_medium_event = None

        for major_event in major_events:
            if major_event.get('start_chapter', 0) <= chapter_number <= major_event.get('end_chapter', 0):
                current_major_event = major_event
                all_medium_events = []
                for phase_events in major_event.get("composition", {}).values():
                    all_medium_events.extend(phase_events)
                
                relevant_medium_events = [me for me in all_medium_events if me.get('chapter', 0) <= chapter_number]
                if relevant_medium_events:
                    current_medium_event = sorted(relevant_medium_events, key=lambda x: x.get('chapter', 0), reverse=True)[0]
                break
        
        context['current_major_event'] = current_major_event
        context['current_medium_event'] = current_medium_event
        
        return context

    def generate_writing_guidance_prompt(self, chapter_number: int) -> str:
        """生成章节写作指导提示词"""
        return self.writing_guidance_manager.generate_writing_guidance_prompt(chapter_number)

    def get_stage_writing_plan_by_name(self, stage_name: str) -> Dict:
        """【重构版】通过阶段名称获取写作计划，优先从缓存和文件加载。"""
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        
        # 尝试从文件加载
        plan = self._load_plan_from_file(stage_name)
        if plan:
            print(f"  📂 从文件加载了 {stage_name} 的写作计划。")
            self.stage_writing_plans_cache[cache_key] = plan
            return plan
        
        # 如果文件不存在，则可能需要触发生成流程
        print(f"  ⚠️ {stage_name} 的写作计划文件未找到，需要生成。")
        return {}
    
    def _save_plan_to_file(self, stage_name: str, plan_data: Dict) -> Path:
        """将阶段计划保存到JSON文件。"""
        file_path = self.plans_dir / f"{stage_name}_writing_plan.json"
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(plan_data, f, ensure_ascii=False, indent=4)
            print(f"  💾 阶段计划已保存到: {file_path}")
            return file_path
        except Exception as e:
            print(f"  ❌ 保存计划文件失败: {file_path}, 错误: {e}")
            return None

    def _load_plan_from_file(self, stage_name: str) -> Optional[Dict]:
        """从JSON文件加载阶段计划。"""
        path_info = self.generator.novel_data.get("stage_writing_plans", {}).get(stage_name, {})
        if "path" not in path_info:
            return None
        
        file_path = self.generator.project_path / path_info["path"]

        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                print(f"  ❌ 加载或解析计划文件失败: {file_path}, 错误: {e}")
                return None
        return None

    def get_stage_plan_for_chapter(self, chapter_number: int) -> Dict:
        """为指定章节获取阶段计划 - 此方法现在会通过文件加载。"""
        current_stage = self._get_current_stage(chapter_number)
        if not current_stage:
            print(f"  ⚠️ 无法确定第{chapter_number}章所属的阶段")
            return {}
        
        stage_plan_data = self.get_stage_writing_plan_by_name(current_stage)
        
        if not stage_plan_data:
            print(f"  ⚠️ 没有找到或加载 {current_stage} 的写作计划")
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
            print("  ⚠️ 没有可用的整体阶段计划来确定当前阶段")
            return None
        
        for stage_name, stage_info in stage_plan_dict.items():
            chapter_range_str = stage_info.get("chapter_range", "")
            if is_chapter_in_range(chapter_number, chapter_range_str):
                return stage_name
        
        print(f"  ⚠️ 第{chapter_number}章不在任何已定义的阶段范围内")
        return None

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
            "ending_stage": "## 🏁 合 (结局阶段): 尘埃落定与意蕴悠长。核心是解决所有问题，回收所有伏笔，给予读者情感满足和回味空间。"
        }
        return stage_guidance.get(stage_name, "## 阶段写作指导\n\n请根据故事发展需要合理安排事件。")

    def get_current_stage_plan(self, chapter_number: int) -> Optional[Dict]:
        """获取当前章节所属阶段的详细计划（兼容性方法）"""
        return self.get_chapter_writing_context(chapter_number)

    def _get_stage_range(self, stage_name: str) -> str:
        """获取阶段章节范围"""
        overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
        if not overall_plans or "overall_stage_plan" not in overall_plans:
            print(f"  ⚠️ 无法从整体计划中找到 {stage_name} 的范围，使用默认值。")
            return "1-100" 
        
        stage_plan_dict = overall_plans["overall_stage_plan"]
        stage_info = stage_plan_dict.get(stage_name)
        
        if stage_info and "chapter_range" in stage_info:
            return stage_info["chapter_range"]
        
        print(f"  ⚠️ 在整体计划字典中未找到 {stage_name} 的章节范围，使用默认值。")
        return "1-100"

    def assess_stage_event_continuity(self, stage_writing_plan: Dict, stage_name: str, 
                                    stage_range: str, creative_seed: str, 
                                    novel_title: str, novel_synopsis: str) -> Dict:
        """AI评估阶段事件连续性 - 新增方法"""
        print(f"  🤖 AI评估{stage_name}阶段事件连续性...")
        
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
                "stage_event_continuity",
                continuity_prompt,
                purpose=f"评估{stage_name}阶段事件连续性"
            )
            
            if continuity_assessment:
                # 将评估结果整合到写作计划中
                if "stage_writing_plan" in stage_writing_plan:
                    stage_writing_plan["stage_writing_plan"]["continuity_assessment"] = continuity_assessment
                else:
                    stage_writing_plan["continuity_assessment"] = continuity_assessment
                
                print(f"  ✅ {stage_name}阶段事件连续性评估完成")
                return continuity_assessment
            else:
                print(f"  ⚠️ {stage_name}阶段事件连续性评估失败")
                return {}
                
        except Exception as e:
            print(f"  ❌ AI连续性评估出错: {e}")
            return {}

    def _build_stage_continuity_prompt(self, event_system: Dict, stage_name: str, stage_range: str,
                                    creative_seed: str, novel_title: str, novel_synopsis: str) -> str:
        """构建阶段事件连续性评估提示词"""
        
        # 提取和格式化事件信息
        major_events = event_system.get("major_events", [])
        medium_events = event_system.get("medium_events", [])
        minor_events = event_system.get("minor_events", [])
        
        prompt_parts = [
            "# 🎯 阶段事件连续性深度评估",
            "",
            "## 评估任务",
            f"请对**{stage_name}**阶段（{stage_range}）的事件安排进行连续性深度评估。",
            "重点分析事件之间的逻辑连贯性、节奏合理性和情感发展连续性。",
            "",
            "## 小说基本信息",
            f"- 标题: {novel_title}",
            f"- 简介: {novel_synopsis}",
            f"- 创意种子: {creative_seed}",
            f"- 阶段: {stage_name} ({stage_range})",
            "",
            "## 事件安排详情"
        ]
        
        # 重大事件详情
        if major_events:
            prompt_parts.extend([
                "### 🚨 重大事件安排",
                "| 事件名称 | 开始章节 | 结束章节 | 持续时间 | 核心目标 |",
                "|---------|---------|---------|---------|----------|"
            ])
            for event in major_events:
                duration = event.get('end_chapter', 0) - event.get('start_chapter', 0) + 1
                prompt_parts.append(
                    f"| {event.get('name', '未命名')} | 第{event.get('start_chapter', '?')}章 | "
                    f"第{event.get('end_chapter', '?')}章 | {duration}章 | {event.get('main_goal', '未指定')} |"
                )
            prompt_parts.append("")
        
        # 中型事件详情
        if medium_events:
            prompt_parts.extend([
                "### 📈 中型事件安排",
                "| 事件名称 | 章节 | 核心目标 | 关联重大事件 |",
                "|---------|------|----------|-------------|"
            ])
            for event in medium_events:
                prompt_parts.append(
                    f"| {event.get('name', '未命名')} | 第{event.get('chapter', event.get('start_chapter', '?'))}章 | "
                    f"{event.get('main_goal', '未指定')} | {event.get('connection_to_major', '独立')} |"
                )
            prompt_parts.append("")
        
        # 小型事件详情
        if minor_events:
            prompt_parts.extend([
                "### 🔍 小型事件安排",
                f"共{len(minor_events)}个小型事件，分布在各个章节"
            ])
            # 只显示前几个小型事件作为示例
            for i, event in enumerate(minor_events[:3]):
                prompt_parts.append(f"- {event.get('name', '未命名')} (第{event.get('chapter', event.get('start_chapter', '?'))}章): {event.get('function', '未指定功能')}")
            if len(minor_events) > 3:
                prompt_parts.append(f"- ... 还有{len(minor_events)-3}个小型事件")
            prompt_parts.append("")
        
        # 事件时间线分析
        prompt_parts.extend([
            "## 📊 事件时间线分析",
            "请基于以上事件安排，分析以下维度：",
            "",
            "### 1. 逻辑连贯性分析",
            "- 事件之间的因果关系是否清晰？",
            "- 是否存在逻辑断层或跳跃？", 
            "- 事件发展是否符合角色动机和世界观设定？",
            "- 伏笔设置和回收是否合理？",
            "",
            "### 2. 节奏合理性分析",
            "- 事件密度分布是否合理？",
            "- 高潮与平缓的交替是否恰当？",
            "- 是否有事件过于密集或稀疏的区域？",
            "- 节奏是否符合该阶段的特点？",
            "",
            "### 3. 情感发展连续性",
            "- 情感弧线是否连贯自然？",
            "- 情感高潮的铺垫是否充分？",
            "- 情感变化是否符合角色发展轨迹？",
            "",
            "### 4. 主线推进连贯性", 
            "- 主线情节是否持续有推进？",
            "- 是否存在主线停滞过久的问题？",
            "- 支线与主线的关联是否合理？",
            "",
            "### 5. 阶段过渡合理性",
            "- 与前后阶段的衔接是否自然？",
            "- 阶段内部的事件安排是否服务于阶段目标？",
            "",
            "## 🎯 评估要求",
            "请提供具体的、可操作的评估结果和改进建议。",
            "",
            "## 📋 输出格式",
            "请以严格的JSON格式返回评估结果：",
            "{",
            '  "overall_continuity_score": 0-10的带一位小数的评分,',
            '  "logic_coherence_analysis": "逻辑连贯性详细分析",',
            '  "rhythm_analysis": "节奏合理性详细分析",',
            '  "emotional_continuity_analysis": "情感发展连续性分析",',
            '  "main_thread_analysis": "主线推进连贯性分析",',
            '  "stage_transition_analysis": "阶段过渡合理性分析",',
            '  "critical_issues": ["关键问题1", "关键问题2", ...],',
            '  "improvement_recommendations": [',
            '    {"issue": "具体问题", "suggestion": "改进建议", "priority": "high/medium/low"},',
            '    ...',
            '  ],',
            '  "event_adjustment_suggestions": [',
            '    {"event_name": "事件名称", "current_arrangement": "当前安排", "suggested_adjustment": "调整建议"},',
            '    ...',
            '  ],',
            '  "risk_chapters": ["存在风险的章节列表"],',
            '  "strengths": ["优势1", "优势2", ...]',
            "}"
        ])
        
        return "\n".join(prompt_parts)

    def _optimize_based_on_continuity_assessment(self, writing_plan: Dict, assessment: Dict, 
                                            stage_name: str, stage_range: str) -> Dict:
        """
        【AI驱动版】基于连续性评估结果，调用AI来执行事件安排的优化。
        """
        all_suggestions = assessment.get("improvement_recommendations", []) + \
                        assessment.get("event_adjustment_suggestions", [])

        if not all_suggestions:
            print("  ✅ AI评估未提出具体事件调整建议，无需优化。")
            return writing_plan
        
        print(f"  🔧 指示AI根据评估建议，开始优化 {stage_name} 阶段事件安排...")

        # 1. 构建一个清晰的指令，让AI执行自己的建议
        optimization_prompt = self._build_optimization_prompt(writing_plan, assessment, stage_name, stage_range)

        # 2. 调用AI，让它返回一个修改后的完整事件系统
        try:
            optimization_result = self.generator.api_client.generate_content_with_retry(
                "ai_event_plan_optimization",
                optimization_prompt,
                purpose=f"执行对{stage_name}阶段的事件优化"
            )
            
            if optimization_result and "optimized_event_system" in optimization_result:
                # 3. 用AI返回的优化后的事件系统，替换旧的
                if "stage_writing_plan" in writing_plan:
                    plan_container = writing_plan["stage_writing_plan"]
                else:
                    plan_container = writing_plan

                # **核心操作：替换整个事件系统**
                plan_container["event_system"] = optimization_result["optimized_event_system"]
                plan_container["optimized_based_on_continuity"] = True
                
                # 打印AI提供的修改摘要，让日志清晰可查
                summary = optimization_result.get("summary_of_changes", "AI未提供修改摘要。")
                print(f"  ✅ AI优化执行完成。修改摘要: {summary}")

                # 别忘了对AI修改后的事件列表进行排序
                for key in ["major_events", "medium_events", "minor_events", "special_events"]:
                    if key in plan_container["event_system"]:
                        sort_key = "start_chapter" if key == "major_events" else "chapter"
                        plan_container["event_system"][key].sort(key=lambda x: x.get(sort_key, 0))

            else:
                print("  ⚠️ AI优化失败，未能返回有效的优化后事件系统。")

        except Exception as e:
            print(f"  ❌ 在执行AI优化时发生错误: {e}")

        return writing_plan

    def _build_optimization_prompt(self, writing_plan: Dict, assessment: Dict, 
                            stage_name: str, stage_range: str) -> str:
        """构建一个提示词，指示AI根据评估建议来修改事件计划。"""

        # 提取当前事件系统和优化建议
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})

        all_suggestions = assessment.get("improvement_recommendations", []) + \
                        assessment.get("event_adjustment_suggestions", [])

        prompt = f"""
# 任务：小说事件计划修订

作为一名顶尖的剧情编辑，你刚刚对一份小说事件计划进行了评估，并提出了一些改进建议。现在，你的任务是**亲自动手**，根据你自己的建议来修订这份计划。

## 1. 当前的事件计划 ({stage_name}, {stage_range})

这是你需要修改的原始事件计划：
```json
{json.dumps(event_system, ensure_ascii=False, indent=2)}
2. 你的评估与改进建议
这是你之前提出的需要执行的修改清单：

json
{json.dumps(all_suggestions, ensure_ascii=False, indent=2)}
3. 修订指令
请严格遵循你的建议，对上述的"当前事件计划"进行修改。

对于"插入事件"的建议：请在对应的事件列表（如 medium_events）中添加一个新的事件对象。请确保新事件有 name, chapter, description 字段。

对于"调整事件"的建议：请找到对应的事件，并在其 description 字段中追加一条备注，说明进行了何种调整。例如："description": "原有描述... [AI优化备注：增加与主角的情感互动，激化矛盾]"。

对于"拆分/合并"等复杂建议：尽力执行。如果一个事件被拆分，请删除旧事件，并添加两个或多个新事件。

保持结构完整：确保你返回的最终结果是一个完整且格式正确的 event_system JSON 对象。

4. 返回格式
请严格按照以下JSON格式返回你的工作成果。不要包含任何额外的解释。

{{
"optimized_event_system": {{
    "major_events": [
    // ... 修改后的重大事件列表
    ],
    "medium_events": [
    // ... 修改后的中型事件列表（可能包含你新插入的事件）
    ],
    "minor_events": [
    // ... 修改后的小型事件列表
    ],
    "special_events": [
    // ... 修改后的特殊事件列表
    ]
}},
    "summary_of_changes": "用一句话总结你所做的主要修改。例如：'根据建议，在第72章插入了一个中型事件"前哨战"，并调整了"神之子降生"事件的描述。'"
}}
"""
        return prompt