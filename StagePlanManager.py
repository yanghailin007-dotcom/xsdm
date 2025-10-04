# StagePlanManager.py
import json
from typing import Dict, Optional
from utils import parse_chapter_range, is_chapter_in_range

class StagePlanManager:
    """剧情骨架设计器 - 专注如何将内容转化为剧情（怎么写）"""
    def __init__(self, novel_generator):
        self.generator = novel_generator
        self.overall_stage_plans = None
        self.stage_boundaries = {}
        self.stage_writing_plans_cache = {}  # 缓存各阶段的写作计划
        
        # 阶段特性描述
        self.stage_characteristics = {
            "opening_stage": {
                "focus": "建立故事基础，吸引读者兴趣",
                "pace": "较快节奏，快速建立冲突",
                "key_elements": "主角出场、世界观介绍、初始冲突"
            },
            "development_stage": {
                "focus": "深化矛盾，推进角色成长",
                "pace": "变化节奏，快慢结合",
                "key_elements": "能力提升、盟友敌人、支线展开"
            },
            "climax_stage": {
                "focus": "冲突爆发，重大转折",
                "pace": "紧张节奏，逐步加速",
                "key_elements": "关键对决、真相揭露、角色蜕变"
            },
            "ending_stage": {
                "focus": "解决矛盾，收束线索",
                "pace": "逐渐放缓，情感升华",
                "key_elements": "矛盾解决、伏笔回收、最终准备"
            },
            "final_stage": {
                "focus": "完整收尾，交代后续",
                "pace": "平稳节奏，情感共鸣",
                "key_elements": "最终结局、角色归宿、主题升华"
            }
        }

    def generate_overall_stage_plan(self, creative_seed: str, novel_title: str, novel_synopsis: str, 
                                market_analysis: Dict, total_chapters: int) -> Optional[Dict]:
        """生成全书阶段计划 - 修复版本"""
        print("=== 生成全书阶段计划 ===")
        
        # 计算阶段边界
        boundaries = self.calculate_stage_boundaries(total_chapters)
        
        user_prompt = f"""
    创意种子: {creative_seed}
    小说标题: {novel_title}
    小说简介: {novel_synopsis}
    市场分析: {json.dumps(market_analysis, ensure_ascii=False)}
    总章节数: {total_chapters}
    """

        
        # 添加阶段边界参数
        user_prompt += f"""
# 阶段划分要求
请将全书{total_chapters}章划分为5个主要阶段，并为每个阶段制定详细的写作重点：

## 1. 开局阶段 (约前10-15%章节)
- **章节范围**: 第1章-第{boundaries['opening_end']}章
- **核心任务**: 建立故事基础，引入核心冲突，吸引读者
- **重点内容**: 主角出场，世界观介绍，初始冲突，悬念设置

## 2. 发展阶段 (约25-30%章节)
- **章节范围**: 第{boundaries['development_start']}章-第{boundaries['development_end']}章
- **核心任务**: 深化矛盾，角色成长，支线展开
- **重点内容**: 能力提升，盟友敌人，小高潮，伏笔埋设

## 3. 高潮阶段 (约30-35%章节)
- **章节范围**: 第{boundaries['climax_start']}章-第{boundaries['climax_end']}章
- **核心任务**: 主要冲突爆发，重大转折，情感爆发
- **重点内容**: 关键对决，真相揭露，角色蜕变，核心矛盾激化

## 4. 收尾阶段 (约15-20%章节)
- **章节范围**: 第{boundaries['ending_start']}章-第{boundaries['ending_end']}章
- **核心任务**: 解决主要冲突，收束支线，准备结局
- **重点内容**: 矛盾解决，伏笔回收，情感升华，最终准备

## 5. 结局阶段 (约5-10%章节)
- **章节范围**: 第{boundaries['final_start']}章-第{total_chapters}章
- **核心任务**: 完整收尾，交代后续，情感共鸣
- **重点内容**: 最终结局，角色归宿，主题升华，读者共鸣    
    """
        
        result = self.generator.api_client.generate_content_with_retry(
            "overall_stage_plan", 
            user_prompt,
            purpose="制定全书阶段计划"
        )
        
        if result:
            # 验证数据结构
            if not isinstance(result, dict):
                print("❌ 阶段计划返回数据格式错误")
                return None
            
            self.overall_stage_plans = result
            self.stage_boundaries = boundaries
            print("✓ 全书阶段计划生成成功")
            self.print_stage_overview()  # 调用修复后的方法
            return result
        else:
            print("❌ 全书阶段计划生成失败")
            return None
    
    def calculate_stage_boundaries(self, total_chapters: int) -> Dict:
        ratios = [0.12, 0.28, 0.32, 0.18, 0.10]  # 确保总和为1.0
        
        # 计算累积章节数，确保不重叠
        chapters = [0]
        for ratio in ratios:
            chapters.append(chapters[-1] + int(total_chapters * ratio))
        
        # 确保最后一个章节等于总章节数
        chapters[-1] = total_chapters
        
        return {
            "opening_end": chapters[1],
            "development_start": chapters[1] + 1,
            "development_end": chapters[2],
            "climax_start": chapters[2] + 1,
            "climax_end": chapters[3],
            "ending_start": chapters[3] + 1,
            "ending_end": chapters[4],
            "final_start": chapters[4] + 1
        }    
    
    def print_stage_overview(self):
        """打印详细的阶段计划概览"""
        if not hasattr(self, 'overall_stage_plan') or not self.overall_stage_plan:
            print("暂无阶段计划数据")
            return
        
        print("\n" + "=" * 60)
        print("                   小说阶段计划概览")
        print("=" * 60)
        
        total_chapters = 0
        for i, stage in enumerate(self.overall_stage_plan, 1):
            stage_name = stage.get('name', f'第{i}阶段')
            start_ch = stage.get('start_chapter', 1)
            end_ch = stage.get('end_chapter', start_ch)
            chapter_count = end_ch - start_ch + 1
            total_chapters += chapter_count
            
            print(f"\n📚 阶段 {i}: {stage_name}")
            print(f"   📖 章节: {start_ch}-{end_ch}章 (共{chapter_count}章)")
            print(f"   🎯 目标: {stage.get('goal', '暂无目标描述')}")
            print(f"   ⚡ 关键发展: {stage.get('key_events', '暂无关键事件')}")
            if stage.get('conflicts'):
                print(f"   ⚔️ 核心冲突: {stage.get('conflicts')}")
        
        print(f"\n📈 总计: {len(self.overall_stage_plan)}个阶段，{total_chapters}章")
        print("=" * 60)

    def generate_stage_writing_plan(self, stage_name: str, stage_range: str, creative_seed: str,
                                novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """生成阶段详细写作计划 - 修正参数版本"""
        cache_key = f"{stage_name}_writing_plan"
        
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        
        print(f"  🎬 生成{stage_name}的写作计划...")
        print(f"  🎬 生成{stage_range}的写作计划...")
        # 准备基础数据
        novel_data = self.generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        # 计算章节分段
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        early_end = start_chap + max(1, stage_length // 3) - 1
        middle_start = early_end + 1
        middle_end = start_chap + (2 * stage_length // 3) - 1
        late_start = middle_end + 1
        
        # 构建用户提示词
        user_prompt = f"""
    请为{stage_name}阶段制定详细的写作计划。

    **基本信息**：
    - 阶段名称：{stage_name}
    - 章节范围：{stage_range}
    - 总章节数：{total_chapters}
    - 小说标题：{novel_title}
    - 小说简介：{novel_synopsis}
    - 创意种子：{creative_seed}

    **全书阶段计划**：
    {json.dumps(overall_stage_plan, ensure_ascii=False, indent=2)}
    """
        
        # 生成写作计划
        writing_plan = self.generator.api_client.generate_content_with_retry(
            "stage_writing_planning",
            user_prompt,
            purpose=f"生成{stage_name}写作计划"
        )
        
        if writing_plan:
            self.stage_writing_plans_cache[cache_key] = writing_plan
            
            # 持久化存储到novel_data
            if "stage_writing_plans" not in self.generator.novel_data:
                self.generator.novel_data["stage_writing_plans"] = {}
            self.generator.novel_data["stage_writing_plans"][stage_name] = writing_plan
            
            print(f"  ✅ {stage_name}写作计划生成完成")
            self._print_writing_plan_summary(writing_plan)
            return writing_plan
        else:
            print(f"  ⚠️ {stage_name}写作计划生成失败，使用默认计划")
            return self._create_default_writing_plan(stage_name, stage_range)

    def get_chapter_writing_context(self, chapter_number: int) -> Dict:
        """获取指定章节的写作上下文"""
        # 获取当前阶段
        current_stage = self._get_current_stage(chapter_number)
        if not current_stage:
            return {}
        
        # 获取阶段写作计划
        writing_plan = self.get_stage_writing_plan_by_name(current_stage)
        if not writing_plan:
            return {}
        
        # 生成章节特定的写作指导
        chapter_context = self._generate_chapter_writing_context(chapter_number, writing_plan)
        
        return chapter_context

    def get_stage_writing_plan_by_name(self, stage_name: str) -> Dict:
        """通过阶段名称获取写作计划"""
        # 首先尝试从novel_data中获取
        if "stage_writing_plans" in self.generator.novel_data:
            stage_plans = self.generator.novel_data["stage_writing_plans"]
            if stage_name in stage_plans:
                # 同时更新缓存
                cache_key = f"{stage_name}_writing_plan"
                self.stage_writing_plans_cache[cache_key] = stage_plans[stage_name]
                return stage_plans[stage_name]
        
        # 尝试从缓存获取
        cache_key = f"{stage_name}_writing_plan"
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        
        # 如果没有找到，需要重新生成（但需要内容规划和伏笔计划）
        print(f"  ⚠️ {stage_name}的写作计划未找到，需要内容规划和伏笔计划来生成")
        return {}

    def generate_writing_guidance_prompt(self, chapter_number: int) -> str:
        """生成章节写作指导提示词"""
        writing_context = self.get_chapter_writing_context(chapter_number)
        
        if not writing_context:
            return "# 🎯 写作指导\n\n暂无特定的写作指导。"
        
        prompt_parts = ["\n\n# 🎯 写作指导"]
        
        # 添加本章写作重点
        prompt_parts.append(f"## 本章写作重点")
        prompt_parts.append(f"{writing_context['writing_focus']}")
        
        # 添加情节结构指导
        if writing_context.get("plot_structure"):
            prompt_parts.append(f"\n## 情节结构指导")
            plot_struct = writing_context["plot_structure"]
            prompt_parts.append(f"- **开场方式**: {plot_struct.get('opening_approach', '自然承接上一章')}")
            prompt_parts.append(f"- **冲突设计**: {plot_struct.get('conflict_design', '推进现有冲突')}")
            prompt_parts.append(f"- **高潮设置**: {plot_struct.get('climax_point', '情感或情节高潮')}")
            prompt_parts.append(f"- **结尾处理**: {plot_struct.get('ending_approach', '设置悬念吸引下一章')}")
        
        # 添加角色表现指导
        if writing_context.get("character_guidance"):
            prompt_parts.append(f"\n## 角色表现指导")
            char_guide = writing_context["character_guidance"]
            prompt_parts.append(f"- **主角发展**: {char_guide.get('protagonist_development', '自然展现成长')}")
            if char_guide.get("supporting_characters_focus"):
                prompt_parts.append(f"- **配角重点**: {char_guide['supporting_characters_focus']}")
        
        # 添加事件参与指导
        if writing_context.get("event_participation"):
            prompt_parts.append(f"\n## 事件参与指导")
            event_part = writing_context["event_participation"]
            prompt_parts.append(f"- **事件角色**: {event_part.get('role_in_events', '推进事件发展')}")
            if event_part.get("key_moments"):
                prompt_parts.append(f"- **关键时刻**: {event_part['key_moments']}")
        
        # 添加伏笔整合指导
        if writing_context.get("foreshadowing_integration"):
            prompt_parts.append(f"\n## 伏笔整合指导")
            foreshadow_guide = writing_context["foreshadowing_integration"]
            prompt_parts.append(f"- **伏笔任务**: {foreshadow_guide.get('foreshadowing_tasks', '自然融入情节')}")
        
        # 添加写作技巧建议
        if writing_context.get("writing_techniques"):
            prompt_parts.append(f"\n## 写作技巧建议")
            techniques = writing_context["writing_techniques"]
            prompt_parts.append(f"- **叙事重点**: {techniques.get('narrative_focus', '保持故事连贯性')}")
            prompt_parts.append(f"- **描写重点**: {techniques.get('description_priority', '关键场景和情感')}")
        
        return "\n".join(prompt_parts)

    def _get_stage_range(self, stage_name: str) -> str:
        """获取阶段章节范围"""
        if "global_growth_plan" not in self.generator.novel_data:
            return "1-100"
        
        growth_plan = self.generator.novel_data["global_growth_plan"]
        for stage in growth_plan.get("stage_framework", []):
            if stage["stage_name"] == stage_name:
                return stage["chapter_range"]
        return "1-100"

    def _get_current_stage(self, chapter_number: int) -> Optional[str]:
        """获取当前章节所属的阶段名称"""
        if "global_growth_plan" not in self.generator.novel_data:
            return None
        
        growth_plan = self.generator.novel_data["global_growth_plan"]
        for stage in growth_plan.get("stage_framework", []):
            chapter_range = stage["chapter_range"]
            if is_chapter_in_range(chapter_number, chapter_range):
                return stage["stage_name"]
        return None

    def _generate_chapter_writing_context(self, chapter_number: int, writing_plan: Dict) -> Dict:
        """生成章节特定的写作上下文"""
        # 从写作计划中提取章节相关信息
        chapter_specific_guidance = self._get_chapter_specific_guidance(chapter_number, writing_plan)
        event_participation = self._get_chapter_event_participation(chapter_number, writing_plan)
        
        # 构建完整的写作上下文
        writing_context = {
            "writing_focus": chapter_specific_guidance.get("writing_focus", "推进情节发展"),
            "key_tasks": chapter_specific_guidance.get("key_tasks", []),
            "plot_structure": {
                "opening_approach": "自然承接上一章结尾",
                "conflict_design": "推进现有冲突或引入新冲突",
                "climax_point": "设置情感或情节高潮",
                "ending_approach": "设置悬念吸引下一章阅读"
            },
            "character_guidance": {
                "protagonist_development": "展现主角当前成长状态",
                "supporting_characters_focus": "适当发展配角关系"
            },
            "event_participation": event_participation,
            "foreshadowing_integration": {
                "foreshadowing_tasks": "自然融入需要铺垫的元素"
            },
            "writing_techniques": {
                "narrative_focus": "保持故事连贯性和角色一致性",
                "description_priority": "重点描写关键场景和情感变化"
            }
        }
        
        # 用写作计划中的具体指导覆盖默认值
        if chapter_specific_guidance.get("plot_advice"):
            writing_context["plot_structure"].update(chapter_specific_guidance["plot_advice"])
        
        if chapter_specific_guidance.get("character_advice"):
            writing_context["character_guidance"].update(chapter_specific_guidance["character_advice"])
        
        return writing_context

    def _get_chapter_specific_guidance(self, chapter_number: int, writing_plan: Dict) -> Dict:
        """从写作计划中获取章节特定的指导"""
        chapter_plan = writing_plan.get("chapter_distribution_plan", {})
        chapter_guidance_list = chapter_plan.get("chapter_specific_guidance", [])
        
        for guidance in chapter_guidance_list:
            chapter_range = guidance.get("chapter_range", "")
            if is_chapter_in_range(chapter_number, chapter_range):
                return {
                    "writing_focus": guidance.get("writing_focus", ""),
                    "key_tasks": guidance.get("key_tasks", []),
                    "plot_advice": self._extract_plot_advice(guidance),
                    "character_advice": self._extract_character_advice(guidance)
                }
        
        # 如果没有找到具体指导，基于章节位置生成通用指导
        stage_range = writing_plan.get("chapter_range", "1-100")
        start_chap, end_chap = self._parse_chapter_range(stage_range)
        progress = (chapter_number - start_chap + 1) / (end_chap - start_chap + 1)
        
        if progress < 0.3:
            focus = "建立本阶段基础，引入新元素"
        elif progress < 0.7:
            focus = "推进核心冲突，深化角色发展"
        else:
            focus = "准备阶段收尾，铺垫下一阶段"
        
        return {
            "writing_focus": focus,
            "key_tasks": ["保持情节连贯性", "推进角色成长"]
        }

    def _get_chapter_event_participation(self, chapter_number: int, writing_plan: Dict) -> Dict:
        """获取章节在事件中的参与情况"""
        event_system = writing_plan.get("event_system_design", {})
        major_events = event_system.get("major_events", [])
        supporting_events = event_system.get("supporting_events", [])
        
        participation = {
            "role_in_events": "推进日常情节",
            "key_moments": []
        }
        
        # 检查重大事件参与
        for event in major_events:
            start_chapter = event.get("start_chapter", 0)
            end_chapter = event.get("end_chapter", 0)
            
            if start_chapter <= chapter_number <= end_chapter:
                participation["role_in_events"] = f"参与{event.get('name', '重大事件')}"
                
                # 检查是否为关键时刻
                key_moments = event.get("key_moments", [])
                for moment in key_moments:
                    if moment.get("chapter") == chapter_number:
                        participation["key_moments"].append(moment.get("description", "关键时刻"))
        
        # 检查支撑事件参与
        for event in supporting_events:
            chapters = event.get("chapters", [])
            if chapter_number in chapters:
                participation["role_in_events"] = f"参与{event.get('name', '支撑事件')}"
        
        return participation

    def _extract_plot_advice(self, guidance: Dict) -> Dict:
        """从指导中提取情节建议"""
        writing_focus = guidance.get("writing_focus", "")
        key_tasks = guidance.get("key_tasks", [])
        
        plot_advice = {}
        
        # 基于写作重点生成情节建议
        if "冲突" in writing_focus:
            plot_advice["conflict_design"] = "重点设计或推进冲突"
        if "高潮" in writing_focus:
            plot_advice["climax_point"] = "设置情感或情节高潮"
        if "悬念" in writing_focus:
            plot_advice["ending_approach"] = "设置悬念吸引继续阅读"
        
        return plot_advice

    def _extract_character_advice(self, guidance: Dict) -> Dict:
        """从指导中提取角色建议"""
        writing_focus = guidance.get("writing_focus", "")
        key_tasks = guidance.get("key_tasks", [])
        
        character_advice = {}
        
        # 基于写作重点生成角色建议
        if any(task in writing_focus for task in ["角色", "人物", "主角"]):
            character_advice["protagonist_development"] = "重点展现主角成长"
        if any(task in writing_focus for task in ["配角", "关系", "互动"]):
            character_advice["supporting_characters_focus"] = "发展配角关系"
        
        # 从关键任务中提取
        for task in key_tasks:
            if "角色" in task or "人物" in task:
                character_advice["protagonist_development"] = task
            if "关系" in task or "互动" in task:
                character_advice["supporting_characters_focus"] = task
        
        return character_advice

    def _print_writing_plan_summary(self, writing_plan: Dict):
        """打印写作计划摘要"""
        stage_name = writing_plan.get("stage_name", "未知阶段")
        print(f"    🎬 {stage_name}写作计划摘要:")
        
        # 重大事件
        event_system = writing_plan.get("event_system_design", {})
        major_events = event_system.get("major_events", [])
        print(f"      重大事件: {len(major_events)}个")
        
        # 支撑事件
        supporting_events = event_system.get("supporting_events", [])
        print(f"      支撑事件: {len(supporting_events)}个")
        
        # 章节指导
        chapter_plan = writing_plan.get("chapter_distribution_plan", {})
        chapter_guidance = chapter_plan.get("chapter_specific_guidance", [])
        print(f"      章节分段指导: {len(chapter_guidance)}段")

    def _create_default_writing_plan(self, stage_name: str, content_plan: Dict, 
                                   foreshadowing_plan: Dict) -> Dict:
        """创建默认的写作计划"""
        stage_range = self._get_stage_range(stage_name)
        start_chap, end_chap = self._parse_chapter_range(stage_range)
        
        # 创建章节分段
        chapter_guidance = []
        segment_length = max(1, (end_chap - start_chap + 1) // 3)
        
        for i in range(3):
            segment_start = start_chap + i * segment_length
            segment_end = min(end_chap, segment_start + segment_length - 1)
            
            if i == 0:
                focus = "建立阶段基础，引入新冲突"
            elif i == 1:
                focus = "推进核心情节，深化角色发展"
            else:
                focus = "准备阶段收尾，铺垫后续发展"
            
            chapter_guidance.append({
                "chapter_range": f"{segment_start}-{segment_end}",
                "writing_focus": focus,
                "key_tasks": ["保持情节连贯性", "推进角色成长"]
            })
        
        return {
            "stage_name": stage_name,
            "chapter_range": stage_range,
            "plot_structure_design": {
                "main_plot_architecture": {
                    "opening_approach": "自然承接上一阶段",
                    "conflict_arrangement": "逐步引入和升级冲突",
                    "climax_design": "设置情感和情节高潮",
                    "ending_approach": "为下一阶段做好铺垫"
                },
                "pace_control_strategy": {
                    "fast_pace_chapters": list(range(start_chap + 2, end_chap - 2)),
                    "slow_pace_chapters": [start_chap, start_chap + 1, end_chap - 1, end_chap],
                    "turning_points": [
                        {
                            "chapter": start_chap + segment_length,
                            "description": "阶段第一个转折点",
                            "impact": "改变剧情方向"
                        }
                    ]
                }
            },
            "event_system_design": {
                "major_events": [
                    {
                        "name": f"{stage_name}核心事件",
                        "theme": "体现阶段核心内容",
                        "start_chapter": start_chap + 1,
                        "end_chapter": end_chap - 1,
                        "key_moments": [
                            {
                                "chapter": start_chap + segment_length,
                                "description": "事件关键发展",
                                "purpose": "推动事件进展"
                            }
                        ],
                        "character_roles": {
                            "protagonist": "主角在事件中成长",
                            "supporting_characters": ["配角参与推动剧情"]
                        },
                        "connection_to_content": "基于内容规划设计"
                    }
                ],
                "supporting_events": [
                    {
                        "name": "铺垫事件",
                        "type": "setup",
                        "chapters": [start_chap, start_chap + 1],
                        "purpose": "为重大事件做铺垫",
                        "connection_to_major": "引入重大事件相关元素"
                    }
                ]
            },
            "character_performance_design": {
                "protagonist_showcase": {
                    "personality_evolution_scenes": [
                        {
                            "scene_description": "展现性格变化的场景",
                            "purpose": "体现角色成长",
                            "suggested_chapter": start_chap + segment_length
                        }
                    ],
                    "ability_demonstration": [
                        {
                            "ability": "新获得的能力",
                            "demonstration_method": "通过冲突或事件展现",
                            "impact": "改变局势或关系"
                        }
                    ],
                    "motivation_deepening": "通过事件深化主角目标"
                },
                "supporting_characters_arrangement": {
                    "focus_characters": [
                        {
                            "character": "重要配角",
                            "key_scenes": ["展现角色特点的场景"],
                            "development_arc": "配角的发展轨迹"
                        }
                    ],
                    "new_characters_introduction": [
                        {
                            "character": "新角色",
                            "introduction_method": "自然融入剧情",
                            "first_impression": "给读者留下深刻印象"
                        }
                    ],
                    "relationship_development": {
                        "relationship": "角色关系发展",
                        "key_interactions": ["重要的互动场景"]
                    }
                }
            },
            "faction_conflict_design": {
                "conflict_manifestation": {
                    "direct_conflicts": ["势力间的直接对抗"],
                    "indirect_conflicts": ["通过代理人或事件的间接冲突"],
                    "escalation_pattern": "从轻微到严重的逐步升级"
                },
                "world_building_expansion": {
                    "new_locations_reveal": ["通过剧情自然介绍新地点"],
                    "cultural_revelations": ["通过角色对话或事件揭示文化"],
                    "system_refinement": "逐步完善世界体系"
                }
            },
            "emotional_arc_design": {
                "emotional_development": {
                    "key_emotional_nodes": [
                        {
                            "chapter": start_chap + segment_length,
                            "emotional_change": "情感重要变化",
                            "impact": "影响角色关系和决策"
                        }
                    ],
                    "emotional_conflicts": ["情感与责任的冲突"],
                    "emotional_culmination": "情感达到高潮并升华"
                }
            },
            "foreshadowing_integration": {
                "new_elements_introduction": [
                    {
                        "element": "新元素",
                        "integration_method": "自然融入对话或事件",
                        "naturalness_ensurance": "不过度强调，保持故事流畅"
                    }
                ],
                "existing_elements_development": [
                    {
                        "element": "现有元素",
                        "development_scenes": ["展现元素发展的场景"],
                        "progression_naturalness": "符合故事逻辑的发展"
                    }
                ],
                "foreshadowing_payoff": [
                    {
                        "element": "前期伏笔",
                        "payoff_chapter": end_chap - 1,
                        "payoff_method": "自然揭示重要性",
                        "satisfaction_ensurance": "给读者合理的解释和情感满足"
                    }
                ]
            },
            "chapter_distribution_plan": {
                "early_chapters_focus": "建立基础，引入冲突",
                "middle_chapters_focus": "深化发展，推进情节",
                "late_chapters_focus": "准备收尾，铺垫后续",
                "chapter_specific_guidance": chapter_guidance
            },
            "writing_techniques_guidance": {
                "narrative_approach": "保持连贯的叙事视角",
                "description_priorities": "重点描写关键场景和情感变化",
                "dialogue_design": "通过对话推进剧情和塑造角色",
                "suspense_techniques": "在章节结尾设置悬念"
            },
            "writing_plan_synopsis": f"{stage_name}的常规写作安排"
        }

    # 兼容性方法 - 保持与现有系统的兼容
    def get_current_stage_plan(self, chapter_number: int) -> Optional[Dict]:
        """获取当前章节所属阶段的详细计划（兼容性方法）"""
        return self.get_chapter_writing_context(chapter_number)

    def get_stage_plan_for_chapter(self, chapter_number: int) -> Optional[Dict]:
        """为当前章节生成阶段写作计划（兼容性方法）"""
        return self.get_chapter_writing_context(chapter_number)