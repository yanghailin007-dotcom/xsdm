import json
import re
from typing import Dict, Optional, List
import NovelGenerator
from utils import parse_chapter_range, is_chapter_in_range

class StagePlanManager:
    """剧情骨架设计器 - 专注如何将内容转化为剧情（怎么写）"""
    def __init__(self, novel_generator):
        self.generator:NovelGenerator.NovelGenerator = novel_generator
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
                                market_analysis: Dict, global_growth_plan: Dict, total_chapters: int) -> Optional[Dict]:
        """生成全书阶段计划 - 修复版本"""
        print("=== 生成全书阶段计划 ===")
        
        # 计算阶段边界
        boundaries = self.calculate_stage_boundaries(total_chapters)
        
        user_prompt = f"""
    创意种子: {creative_seed}
    小说标题: {novel_title}
    小说简介: {novel_synopsis}
    市场分析: {json.dumps(market_analysis, ensure_ascii=False)}
    全书成长规划: {json.dumps(global_growth_plan, ensure_ascii=False)}
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
        """生成阶段详细写作计划 - 增强黄金三章处理"""
        cache_key = f"{stage_name}_writing_plan"
        
        if cache_key in self.stage_writing_plans_cache:
            return self.stage_writing_plans_cache[cache_key]
        
        print(f"  🎬 生成{stage_name}的写作计划...")
        
        # 检查是否为开局阶段且包含黄金三章
        is_opening_with_golden = (stage_name == "opening_stage" and 
                                stage_range.startswith("1-") and 
                                int(stage_range.split("-")[1]) >= 3)
        
        
        # 准备基础数据
        novel_data = self.generator.novel_data
        total_chapters = novel_data["current_progress"]["total_chapters"]
        
        # 计算章节分段
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 构建用户提示词 - 添加事件密度要求
        user_prompt = f"""
    内容:
    ## 任务指令
    请根据下文提供的小说信息和全书大纲，为 `{stage_name}` 阶段制定详细的写作计划。

    ## 事件规划核心要求
    1. **合理密度**: 请参照重要事件密度要求
    2. **主线贯穿**: 所有事件必须服务于阶段核心目标，避免偏离主线  
    3. **渐进升级**: 事件难度和重要性应逐步提升，形成递进关系
    4. **伏笔衔接**: 每个事件都应包含对后续事件的铺垫

    ## 小说核心信息
    - **小说标题**: {novel_title}
    - **小说简介**: {novel_synopsis}
    - **创意种子**: {creative_seed}

    ## 全书大纲 (上下文)
    {json.dumps(overall_stage_plan, ensure_ascii=False, indent=2)}

    ## 本次任务详情
    - **目标阶段**: {stage_name}
    - **章节范围**: {stage_range}章
    - **阶段长度**: {stage_length}章

    ## 重要事件密度要求
    - **小型事件**: 至少{max(3, stage_length // 5)}个 (日常冲突、角色互动)
    - **中型事件**: 至少{max(2, stage_length // 8)}个 (支线任务、能力突破)  
    - **重大事件**: 至少{max(1, stage_length // 15)}个 (主线推进、重大转折)
    - **最大事件间隔**: 不超过15章必须有核心事件推进
    """
        
        # 如果是开局阶段且包含黄金三章，添加特殊要求
        if is_opening_with_golden:
            golden_chapters_prompt = f"""

    ## 🏆 黄金三章特殊设计要求（第1-3章）

    请为黄金三章制定特别详细的设计方案：

    ### 第1章设计方案：
    - **开篇方式**：设计3种不同的强力开篇方式供选择
    - **主角登场**：具体描述主角如何惊艳登场
    - **冲突设置**：设计开篇冲突的具体场景和对话
    - **悬念钩子**：章节结尾必须设置的悬念内容
    - **字数分配**：建议各部分的字数分配

    ### 第2章设计方案：
    - **情节推进**：具体如何深化第一章的冲突
    - **新元素引入**：需要引入的新角色、新设定
    - **节奏控制**：如何保持快节奏的同时不显得仓促
    - **情感建立**：如何让读者对主角产生情感共鸣

    ### 第3章设计方案：
    - **小高潮设计**：具体的小高潮场景和冲突
    - **伏笔设置**：为哪些后续情节埋下伏笔
    - **追读钩子**：设计让读者必须看下一章的强力理由
    - **阶段总结**：黄金三章整体要达到的效果

    ### 黄金三章评分标准：
    - 必须达到8.5分以上才算合格
    - 重点评估开篇吸引力、情节紧凑度、悬念设置
    - 每章都要有明确的成功标准
    """
            user_prompt += golden_chapters_prompt
        
        # 生成写作计划
        writing_plan = self.generator.api_client.generate_content_with_retry(
            "stage_writing_planning",
            user_prompt,
            purpose=f"生成{stage_name}写作计划"
        )
        # 新增：生成情绪计划
        global_emotional_plan = self.generator.novel_data.get("emotional_development_plan", {})
        emotional_plan = self.generate_stage_emotional_plan(stage_name, stage_range, global_emotional_plan)
        
        if writing_plan:
            # 将情绪计划整合到写作计划中
            if "stage_writing_plan" in writing_plan:
                writing_plan["stage_writing_plan"]["emotional_plan"] = emotional_plan
            else:
                writing_plan["emotional_plan"] = emotional_plan
            # 如果是开局阶段且包含黄金三章，进一步处理
            if is_opening_with_golden:
                writing_plan = self._enhance_golden_chapters_in_writing_plan(writing_plan)
            
            # 新增：验证主线连贯性
            is_continuous = self.validate_main_thread_continuity(writing_plan)
            if not is_continuous:
                print(f"  ⚠️ {stage_name}写作计划存在事件间隔过长问题，进行优化...")
            
            # 新增：验证事件密度
            event_density_ok = self.validate_event_density(writing_plan, stage_range)
            if not event_density_ok:
                print(f"  ⚠️ {stage_name}写作计划事件密度不足，进行补充...")
                writing_plan = self.supplement_events_with_ai(writing_plan, stage_range, creative_seed, novel_title, novel_synopsis, overall_stage_plan)
            
            self.stage_writing_plans_cache[cache_key] = writing_plan
            
            # 持久化存储到novel_data
            if "stage_writing_plans" not in self.generator.novel_data:
                self.generator.novel_data["stage_writing_plans"] = {}
            self.generator.novel_data["stage_writing_plans"][stage_name] = writing_plan
            
            print(f"  ✅ {stage_name}写作计划生成完成")
            self._print_writing_plan_summary(writing_plan)
            return writing_plan
        else:
            print(f"  ⚠️ {stage_name}写作计划生成失败，使用默认计划，请重点检查")

    def _enhance_golden_chapters_in_writing_plan(self, writing_plan: Dict) -> Dict:
        """在阶段写作计划中增强黄金三章设计"""
        
        # 确保有事件系统设计
        if "event_system_design" not in writing_plan:
            writing_plan["event_system_design"] = {}
        
        # 添加黄金三章特殊事件
        writing_plan["event_system_design"]["golden_chapters_events"] = {
            "chapter_1_opening_event": {
                "name": "开篇引爆事件",
                "type": "重大事件",
                "start_chapter": 1,
                "end_chapter": 1,
                "purpose": "快速吸引读者注意力，展现主角特质",
                "success_criteria": "读者在500字内被吸引继续阅读",
                "key_moments": [
                    {
                        "chapter": 1,
                        "description": "强力开篇场景，立即展现冲突",
                        "impact": "高"
                    }
                ]
            },
            "chapter_2_development_event": {
                "name": "冲突深化事件", 
                "type": "重大事件",
                "start_chapter": 2,
                "end_chapter": 2,
                "purpose": "深化开篇冲突，建立人物关系",
                "success_criteria": "读者对主角产生认同和期待",
                "key_moments": [
                    {
                        "chapter": 2,
                        "description": "主角应对冲突，展现能力",
                        "impact": "中高"
                    }
                ]
            },
            "chapter_3_climax_event": {
                "name": "小高潮事件",
                "type": "重大事件", 
                "start_chapter": 3,
                "end_chapter": 3,
                "purpose": "安排情节小高潮，设置追读钩子",
                "success_criteria": "读者产生强烈追读欲望",
                "key_moments": [
                    {
                        "chapter": 3,
                        "description": "情节小高潮和强力悬念结尾",
                        "impact": "高"
                    }
                ]
            }
        }
        
        # 添加黄金三章角色表现设计
        if "character_performance_design" not in writing_plan:
            writing_plan["character_performance_design"] = {}
        
        writing_plan["character_performance_design"]["golden_chapters_focus"] = {
            "chapter_1_character_intro": {
                "focus": "主角惊艳登场",
                "key_scenes": ["开篇亮相", "冲突应对", "特质展现"],
                "success_criteria": "读者立即喜欢上主角"
            },
            "chapter_2_character_development": {
                "focus": "主角能力展现和关系建立", 
                "key_scenes": ["能力演示", "配角互动", "情感共鸣"],
                "success_criteria": "读者对主角产生深度认同"
            },
            "chapter_3_character_growth": {
                "focus": "主角初步成长和魅力强化",
                "key_scenes": ["困境突破", "智慧展现", "魅力时刻"],
                "success_criteria": "读者成为主角粉丝"
            }
        }
        
        return writing_plan

    def get_chapter_writing_context(self, chapter_number: int) -> Dict:
        """获取指定章节的写作上下文 - 增强版本，包含详细情绪指导"""
        current_stage = self._get_current_stage(chapter_number)
        if not current_stage:
            return {}
        
        writing_plan = self.get_stage_writing_plan_by_name(current_stage)
        if not writing_plan:
            return {}
        
        # 新增：获取情绪计划
        emotional_plan = self._get_emotional_plan_for_stage(current_stage)
        
        # 生成章节特定的写作指导
        chapter_context = self._generate_chapter_writing_context(chapter_number, writing_plan)
        
        # 增强：添加详细情绪指导
        emotional_guidance = self._generate_emotional_guidance_for_chapter(
            chapter_number, emotional_plan, current_stage
        )
        chapter_context["emotional_guidance"] = emotional_guidance
        
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
        """打印写作计划摘要 - 移除普通事件统计"""
        print(f"  🔍 开始打印写作计划摘要...")
        print(f"  🔍 传入的writing_plan类型: {type(writing_plan)}")
        print(f"  🔍 传入的writing_plan键: {list(writing_plan.keys()) if writing_plan else 'None'}")
        
        # 检查是否有嵌套结构
        if "stage_writing_plan" in writing_plan:
            print(f"  🔍 检测到嵌套结构 stage_writing_plan")
            actual_plan = writing_plan["stage_writing_plan"]
        else:
            print(f"  🔍 没有嵌套结构，直接使用writing_plan")
            actual_plan = writing_plan
        
        # 获取阶段名称
        stage_name = actual_plan.get("stage_name", "未知阶段")
        print(f"    🎬 {stage_name}写作计划摘要:")
        
        # 事件系统统计 - 只统计重大事件和大事件
        event_system = actual_plan.get("event_system", {})
        
        major_events = event_system.get("major_events", [])
        # 移除普通事件的统计
        
        print(f"      重大事件: {len(major_events)}个")
        # 移除普通事件的打印
        
        # 打印事件详情 - 只打印重大事件和大事件
        if major_events:
            print(f"  🔍 major_events内容:")
            for i, event in enumerate(major_events):
                print(f"    📌 事件{i+1}: {event}")
                print(f"        🎯 {event.get('name', '无名事件')}: 第{event.get('start_chapter', '?')}-{event.get('end_chapter', '?')}章")
        else:
            print(f"  ⚠️ major_events为空列表")
        
    # 兼容性方法 - 保持与现有系统的兼容
    def get_current_stage_plan(self, chapter_number: int) -> Optional[Dict]:
        """获取当前章节所属阶段的详细计划（兼容性方法）"""
        return self.get_chapter_writing_context(chapter_number)

    def get_stage_plan_for_chapter(self, chapter_number: int) -> Optional[Dict]:
        """为指定章节获取阶段计划 - 修复版本"""
        try:
            # 获取当前阶段名称
            current_stage = self._get_current_stage(chapter_number)
            if not current_stage:
                print(f"  ⚠️ 无法确定第{chapter_number}章所属的阶段")
                return None
            
            # 从 novel_data 中获取阶段写作计划
            novel_data = self.generator.novel_data
            stage_writing_plans = novel_data.get("stage_writing_plans", {})
            
            if current_stage not in stage_writing_plans:
                print(f"  ⚠️ 没有找到{current_stage}的写作计划")
                return None
            
            stage_plan_data = stage_writing_plans[current_stage]
            
            # 确保返回正确的数据结构
            if "stage_writing_plan" in stage_plan_data:
                return stage_plan_data["stage_writing_plan"]
            else:
                print(f"  ⚠️ 阶段计划数据缺少stage_writing_plan字段，使用原始数据")
                return stage_plan_data
                
        except Exception as e:
            print(f"❌ 获取第{chapter_number}章阶段计划失败: {e}")
            return None

    def _get_current_stage(self, chapter_number: int) -> Optional[str]:
        """获取当前章节所属的阶段名称 - 修复版本"""
        try:
            # 从 overall_stage_plans 中查找
            overall_plans = self.generator.novel_data.get("overall_stage_plans", {})
            if not overall_plans or "overall_stage_plan" not in overall_plans:
                print("  ⚠️ 没有可用的整体阶段计划")
                return None
            
            stage_plan_dict = overall_plans["overall_stage_plan"]
            
            for stage_name, stage_info in stage_plan_dict.items():
                # 解析章节范围
                chapter_range_str = stage_info.get("chapter_range", "")
                if not chapter_range_str:
                    continue
                    
                # 提取数字范围
                import re
                numbers = re.findall(r'\d+', chapter_range_str)
                if len(numbers) >= 2:
                    start_chap = int(numbers[0])
                    end_chap = int(numbers[1])
                    
                    if start_chap <= chapter_number <= end_chap:
                        return stage_name
            
            print(f"  ⚠️ 第{chapter_number}章不在任何阶段范围内")
            return None
            
        except Exception as e:
            print(f"❌ 确定章节阶段失败: {e}")
            return None
        
    def supplement_events_with_ai(self, writing_plan: Dict, stage_range: str, creative_seed: str, novel_title: str, novel_synopsis: str, overall_stage_plan: Dict) -> Dict:
        """使用AI补充事件以提高密度 - 简化版本"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 提取事件数据
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        # 计算当前事件密度
        current_major = len(events.get("major_events", []))
        current_medium = len(events.get("medium_events", []))
        current_minor = len(events.get("minor_events", []))
        
        target_major = max(1, stage_length // 15)
        target_medium = max(2, stage_length // 8)
        target_minor = max(3, stage_length // 5)
        
        # 如果事件密度不足，提示AI补充
        if current_major < target_major or current_medium < target_medium or current_minor < target_minor:
            print(f"  🤖 事件密度不足，使用AI补充事件...")
            
            # 使用与生成阶段计划相同的提示词结构
            supplement_prompt = f"""
    请为小说阶段补充事件设计，使事件密度更加合理。

    ## 小说核心信息
    - **小说标题**: {novel_title}
    - **小说简介**: {novel_synopsis}
    - **创意种子**: {creative_seed}
    - **阶段范围**: {stage_range}章 (共{stage_length}章)

    ## 全书大纲 (上下文)
    {json.dumps(overall_stage_plan, ensure_ascii=False, indent=2)}

    ## 事件规划核心要求
    1. **合理密度**: 确保每5-8章有一个小型事件，每10-15章有一个中型事件，每15-20章有一个重大事件
    2. **主线贯穿**: 所有事件必须服务于阶段核心目标，避免偏离主线  
    3. **渐进升级**: 事件难度和重要性应逐步提升，形成递进关系
    4. **伏笔衔接**: 每个事件都应包含对后续事件的铺垫

    ## 当前事件统计
    - 重大事件: {current_major}个 (建议{target_major}个)
    - 中型事件: {current_medium}个 (建议{target_medium}个)  
    - 小型事件: {current_minor}个 (建议{target_minor}个)

    ## 现有事件
    {json.dumps(events, ensure_ascii=False, indent=2)}

    ## 补充要求
    请根据现有事件和故事逻辑，补充合适的事件来丰富情节。
    不需要严格按照建议数量，只需补充您认为合理的事件即可。

    请返回补充的事件设计：
    {{
        "supplemental_events": {{
            "major_events": [],
            "medium_events": [],
            "minor_events": []
        }}
    }}
    """
            
            try:
                supplement_result = self.generator.api_client.generate_content_with_retry(
                    "event_supplement",
                    supplement_prompt,
                    purpose="补充事件设计"
                )
                
                if supplement_result and "supplemental_events" in supplement_result:
                    supplemental_events = supplement_result["supplemental_events"]
                    
                    # 验证补充的事件
                    validated_events = self._validate_supplemental_events(supplemental_events, start_chap, end_chap)
                    
                    # 合并补充的事件
                    for event_type in ["major_events", "medium_events", "minor_events"]:
                        if event_type in validated_events and validated_events[event_type]:
                            if event_type not in events:
                                events[event_type] = []
                            events[event_type].extend(validated_events[event_type])
                    
                    # 重新排序事件
                    events = self._sort_events_by_chapter(events)
                    
                    # 更新事件系统
                    if "stage_writing_plan" in writing_plan:
                        writing_plan["stage_writing_plan"]["event_system"] = events
                    else:
                        writing_plan["event_system"] = events
                    
                    # 记录补充结果
                    added_major = len(validated_events.get('major_events', []))
                    added_medium = len(validated_events.get('medium_events', []))
                    added_minor = len(validated_events.get('minor_events', []))
                    
                    if added_major > 0 or added_medium > 0 or added_minor > 0:
                        print(f"  ✅ AI补充了{added_major}个重大事件，{added_medium}个中型事件，{added_minor}个小型事件")
                        
            except Exception as e:
                print(f"  ❌ AI补充事件出错: {e}")
        
        return writing_plan

    def _validate_supplemental_events(self, supplemental_events: Dict, start_chap: int, end_chap: int) -> Dict:
        """简单验证补充的事件 - 只验证章节范围"""
        validated = {
            "major_events": [],
            "medium_events": [], 
            "minor_events": []
        }
        
        # 验证重大事件
        for event in supplemental_events.get("major_events", []):
            if all(key in event for key in ["name", "start_chapter", "end_chapter"]):
                if start_chap <= event["start_chapter"] <= end_chap and start_chap <= event["end_chapter"] <= end_chap:
                    validated["major_events"].append(event)
        
        # 验证中型事件
        for event in supplemental_events.get("medium_events", []):
            if all(key in event for key in ["name", "chapter"]):
                if start_chap <= event["chapter"] <= end_chap:
                    validated["medium_events"].append(event)
        
        # 验证小型事件
        for event in supplemental_events.get("minor_events", []):
            if all(key in event for key in ["name", "chapter"]):
                if start_chap <= event["chapter"] <= end_chap:
                    validated["minor_events"].append(event)
        
        return validated

    def _sort_events_by_chapter(self, events: Dict) -> Dict:
        """按章节排序事件"""
        for event_type in ["major_events", "medium_events", "minor_events"]:
            if event_type in events:
                if event_type == "major_events":
                    events[event_type] = sorted(events[event_type], key=lambda x: x.get('start_chapter', 0))
                else:
                    events[event_type] = sorted(events[event_type], key=lambda x: x.get('chapter', 0))
        
        return events

    def validate_main_thread_continuity(self, writing_plan: Dict) -> bool:
        """验证主线连贯性 - 修正版本"""
        # 修正：正确访问嵌套的事件系统
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        # 确保 major_events 存在
        if "major_events" not in events:
            return False
            
        major_events = events.get("major_events", [])
        
        # 检查事件链条是否完整
        event_chains = self.build_event_chains(major_events)
        
        # 检查是否有超过15章没有核心事件
        max_gap = self.calculate_max_event_gap(major_events)
        
        if max_gap > 30:
            print(f"  ⚠️ 警告：事件间隔过长，最长{max_gap}章没有核心事件")
            return False
        
        print(f"  ✅ 主线连贯性验证通过：最大事件间隔{max_gap}章")
        return True

    def build_event_chains(self, events: List) -> List:
        """构建事件链条，确保逻辑连贯 - 修复版本"""
        if not events:
            return []
            
        chains = []
        current_chain = []
        
        for event in sorted(events, key=lambda x: x.get('start_chapter', 0)):
            if not current_chain:
                current_chain.append(event)
            else:
                last_event = current_chain[-1]
                # 检查事件是否连贯
                last_event_end = last_event.get('end_chapter', last_event.get('start_chapter', 0))
                current_event_start = event.get('start_chapter', 0)
                
                if current_event_start - last_event_end <= 5:
                    current_chain.append(event)
                else:
                    chains.append(current_chain)
                    current_chain = [event]
        
        if current_chain:
            chains.append(current_chain)
        
        return chains

    def calculate_max_event_gap(self, events: List) -> int:
        """计算最大事件间隔 - 修复版本"""
        if not events:
            return 999  # 没有事件，间隔极大
        
        # 按开始章节排序
        sorted_events = sorted(events, key=lambda x: x.get('start_chapter', 0))
        
        max_gap = 0
        
        # 检查第一个事件之前的间隔（假设阶段从第1章开始）
        first_event_start = sorted_events[0].get('start_chapter', 1)
        if first_event_start > 1:
            max_gap = max(max_gap, first_event_start - 1)
        
        # 检查事件之间的间隔
        for i in range(1, len(sorted_events)):
            prev_event = sorted_events[i-1]
            current_event = sorted_events[i]
            
            prev_event_end = prev_event.get('end_chapter', prev_event.get('start_chapter', 0))
            current_event_start = current_event.get('start_chapter', 0)
            
            gap = current_event_start - prev_event_end - 1
            max_gap = max(max_gap, gap)
        
        return max_gap

    def _basic_event_supplement(self, writing_plan: Dict, stage_range: str) -> Dict:
        """基础事件补充方法 - 新增方法"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 确保 event_system 存在
        if "event_system" not in writing_plan:
            writing_plan["event_system"] = {}
        
        events = writing_plan["event_system"]
        
        # 确保各种事件列表存在
        if "major_events" not in events:
            events["major_events"] = []
        if "medium_events" not in events:
            events["medium_events"] = []
        if "minor_events" not in events:
            events["minor_events"] = []
        
        # 如果没有重大事件，在阶段中间添加一个
        if not events["major_events"]:
            mid_chapter = (start_chap + end_chap) // 2
            events["major_events"].append({
                "name": "阶段核心事件",
                "start_chapter": max(start_chap, mid_chapter - 2),
                "end_chapter": min(end_chap, mid_chapter + 2),
                "significance": "推动阶段核心目标",
                "description": "自动生成的核心事件"
            })
        
        return writing_plan
    
    def validate_event_density(self, writing_plan: Dict, stage_range: str) -> bool:
        """验证事件密度是否合理 - 修正版本"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 修正：正确访问嵌套的事件系统
        if "stage_writing_plan" in writing_plan:
            events = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            events = writing_plan.get("event_system", {})
        
        major_events = events.get("major_events", [])
        medium_events = events.get("medium_events", [])
        minor_events = events.get("minor_events", [])
        
        # 计算事件密度
        total_events = len(major_events) + len(medium_events) + len(minor_events)
        
        # 获取最优事件密度
        density_dict = self.calculate_optimal_event_density(stage_length)
        expected_min_events = (
            density_dict.get("major_events", 0) + 
            density_dict.get("medium_events", 0) + 
            density_dict.get("minor_events", 0)
        )
        
        if total_events < expected_min_events:
            print(f"  ⚠️ 事件密度不足：期望至少{expected_min_events}个事件，实际只有{total_events}个")
            print(f"    重大事件: {len(major_events)}, 中型事件: {len(medium_events)}, 小型事件: {len(minor_events)}")
            return False
        
        print(f"  ✅ 事件密度验证通过：实际{total_events}个事件，期望至少{expected_min_events}个")
        return True

    def calculate_optimal_event_density(self, stage_length: int) -> Dict:
        """根据阶段长度智能计算最优事件密度"""
        
        if stage_length <= 20:
            # 短阶段：减少事件数量
            return {
                "major_events": max(1, stage_length // 20),
                "medium_events": max(2, stage_length // 10),
                "minor_events": max(3, stage_length // 6)
            }
        elif stage_length <= 40:
            # 中等阶段：适中密度
            return {
                "major_events": max(1, stage_length // 15),
                "medium_events": max(2, stage_length // 8),
                "minor_events": max(3, stage_length // 5)
            }
        else:
            # 长阶段：控制最大数量，避免过度复杂
            return {
                "major_events": min(5, stage_length // 15),  # 最多5个重大事件
                "medium_events": min(8, stage_length // 8),  # 最多8个中型事件
                "minor_events": min(12, stage_length // 5)   # 最多12个小型事件
            }

    def export_events_to_json(self, file_path: str = "novel_events.json"):
        """导出所有事件到JSON文件，按章节排序 - 修复嵌套结构版本"""
        # 确保保存到 quality_data 目录
        import os
        quality_dir = "quality_data"
        os.makedirs(quality_dir, exist_ok=True)
        
        # 构建完整路径
        full_path = os.path.join(quality_dir, file_path)
        
        print(f"\n📋 开始提取所有事件并保存到 {full_path}")
        
        all_events = []
        
        # 获取所有阶段写作计划
        stage_plans = self.generator.novel_data.get("stage_writing_plans", {})
        
        for stage_name, stage_plan in stage_plans.items():
            print(f"  🔍 处理阶段: {stage_name}")
            
            # 修复：正确处理嵌套结构
            if "stage_writing_plan" in stage_plan:
                # 嵌套结构：stage_plan -> stage_writing_plan -> event_system
                actual_plan = stage_plan["stage_writing_plan"]
                print(f"  🔍 检测到嵌套结构 stage_writing_plan，使用嵌套数据")
            else:
                # 平面结构：stage_plan -> event_system
                actual_plan = stage_plan
                print(f"  🔍 未检测到嵌套结构，使用原始数据")
            
            # 获取事件系统
            event_system = actual_plan.get("event_system", {})
            print(f"  🔍 {stage_name}的事件系统键: {list(event_system.keys())}")
            
            # 提取重大事件
            major_events = event_system.get("major_events", [])
            print(f"  🔍 {stage_name}的重大事件数量: {len(major_events)}")
            for event in major_events:
                event_data = {
                    "name": event.get("name", "未命名事件"),
                    "start_chapter": event.get("start_chapter", 0),
                    "end_chapter": event.get("end_chapter", event.get("start_chapter", 0)),
                    "significance": event.get("significance", "未知重要性"),
                    "description": event.get("description", ""),
                    "type": "major",
                    "stage": stage_name
                }
                all_events.append(event_data)
            
            # 提取中型事件
            medium_events = event_system.get("medium_events", [])
            print(f"  🔍 {stage_name}的中型事件数量: {len(medium_events)}")
            for event in medium_events:
                event_data = {
                    "name": event.get("name", "未命名事件"),
                    "start_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "end_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "significance": event.get("significance", event.get("main_goal", "未知重要性")),
                    "description": event.get("description", ""),
                    "type": "medium", 
                    "stage": stage_name
                }
                all_events.append(event_data)
            
            # 提取小型事件
            minor_events = event_system.get("minor_events", [])
            print(f"  🔍 {stage_name}的小型事件数量: {len(minor_events)}")
            for event in minor_events:
                event_data = {
                    "name": event.get("name", "未命名事件"),
                    "start_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "end_chapter": event.get("chapter", event.get("start_chapter", 0)),
                    "significance": event.get("significance", event.get("function", "未知重要性")),
                    "description": event.get("description", ""),
                    "type": "minor",
                    "stage": stage_name
                }
                all_events.append(event_data)
        
        # 按开始章节排序
        all_events.sort(key=lambda x: x["start_chapter"])
        
        # 构建输出数据结构
        output_data = {
            "novel_title": self.generator.novel_data.get("novel_title", "未知小说"),
            "total_events": len(all_events),
            "events_by_type": {
                "major": len([e for e in all_events if e["type"] == "major"]),
                "medium": len([e for e in all_events if e["type"] == "medium"]),
                "minor": len([e for e in all_events if e["type"] == "minor"])
            },
            "events": all_events
        }
        
        # 保存到JSON文件
        try:
            with open(full_path, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, ensure_ascii=False, indent=2, sort_keys=True)
            
            print(f"✅ 成功导出 {len(all_events)} 个事件到 {full_path}")
            print(f"   📊 事件统计: 重大事件{output_data['events_by_type']['major']}个, "
                f"中型事件{output_data['events_by_type']['medium']}个, "
                f"小型事件{output_data['events_by_type']['minor']}个")
            
            # 打印前几个事件预览
            if all_events:
                print(f"\n📖 事件预览 (前5个):")
                for i, event in enumerate(all_events[:5]):
                    print(f"   {i+1}. 第{event['start_chapter']}章: {event['name']} ({event['type']})")
                    
        except Exception as e:
            print(f"❌ 导出事件到JSON文件失败: {e}")
        
        return output_data
    
    def get_events_summary(self) -> Dict:
        """获取事件摘要统计 - 修复版本"""
        # 不实际保存文件，直接在内存中处理
        all_events = []
        stage_plans = self.generator.novel_data.get("stage_writing_plans", {})
        
        for stage_name, stage_plan in stage_plans.items():
            # 正确处理嵌套结构
            if "stage_writing_plan" in stage_plan:
                actual_plan = stage_plan["stage_writing_plan"]
            else:
                actual_plan = stage_plan
            
            event_system = actual_plan.get("event_system", {})
            
            # 提取所有类型的事件
            for event_type, type_key in [("major", "major_events"), ("medium", "medium_events"), ("minor", "minor_events")]:
                events = event_system.get(type_key, [])
                for event in events:
                    if event_type == "major":
                        start_chapter = event.get("start_chapter", 0)
                        end_chapter = event.get("end_chapter", start_chapter)
                    else:
                        start_chapter = event.get("chapter", event.get("start_chapter", 0))
                        end_chapter = start_chapter
                    
                    event_data = {
                        "name": event.get("name", "未命名事件"),
                        "start_chapter": start_chapter,
                        "end_chapter": end_chapter,
                        "type": event_type,
                        "stage": stage_name
                    }
                    all_events.append(event_data)
        
        # 按阶段统计
        stage_stats = {}
        for event in all_events:
            stage = event["stage"]
            if stage not in stage_stats:
                stage_stats[stage] = {"major": 0, "medium": 0, "minor": 0}
            stage_stats[stage][event["type"]] += 1
        
        summary = {
            "total_events": len(all_events),
            "events_by_type": {
                "major": len([e for e in all_events if e["type"] == "major"]),
                "medium": len([e for e in all_events if e["type"] == "medium"]),
                "minor": len([e for e in all_events if e["type"] == "minor"])
            },
            "events_by_stage": stage_stats,
            "chapter_coverage": self._calculate_chapter_coverage(all_events)
        }
        
        return summary

    def _calculate_chapter_coverage(self, events: List[Dict]) -> Dict:
        """计算章节覆盖情况"""
        if not events:
            return {"covered_chapters": 0, "total_chapters": 0, "coverage_rate": 0}
        
        # 获取总章节数
        total_chapters = self.generator.novel_data["current_progress"]["total_chapters"]
        
        # 计算有事件的章节
        covered_chapters = set()
        for event in events:
            start = event["start_chapter"]
            end = event["end_chapter"]
            for chapter in range(start, end + 1):
                if 1 <= chapter <= total_chapters:
                    covered_chapters.add(chapter)
        
        coverage_rate = len(covered_chapters) / total_chapters if total_chapters > 0 else 0
        
        return {
            "covered_chapters": len(covered_chapters),
            "total_chapters": total_chapters,
            "coverage_rate": round(coverage_rate * 100, 2)
        }
    def generate_stage_emotional_plan(self, stage_name: str, stage_range: str, 
                                    global_emotional_plan: Dict) -> Dict:
        """生成阶段详细情绪计划"""
        print(f"  💞 生成{stage_name}的详细情绪计划...")
        
        novel_data = self.generator.novel_data
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        user_prompt = f"""
    基于全书情绪规划和阶段特点，制定{stage_name}的详细情绪计划：

    **阶段信息**：
    - 阶段：{stage_name}
    - 章节范围：{stage_range} (共{stage_length}章)
    - 全书情绪规划：{json.dumps(global_emotional_plan, ensure_ascii=False)}

    **小说信息**：
    - 标题：{novel_data["novel_title"]}
    - 简介：{novel_data["novel_synopsis"]}
    - 主角：{novel_data.get('custom_main_character_name', '主角')}

    """

        emotional_plan = self.generator.api_client.generate_content_with_retry(
            "stage_emotional_planning",
            user_prompt,
            purpose=f"生成{stage_name}情绪计划"
        )
        
        if emotional_plan:
            # 存储到阶段写作计划中
            if "stage_writing_plans" not in novel_data:
                novel_data["stage_writing_plans"] = {}
            
            if stage_name not in novel_data["stage_writing_plans"]:
                novel_data["stage_writing_plans"][stage_name] = {}
            
            novel_data["stage_writing_plans"][stage_name]["emotional_plan"] = emotional_plan
            print(f"  ✅ {stage_name}情绪计划生成完成")
            return emotional_plan
        else:
            print(f"  ⚠️ {stage_name}情绪计划生成失败，使用默认计划")
            return self._create_default_stage_emotional_plan(stage_name, stage_range)

    def _create_default_stage_emotional_plan(self, stage_name: str, stage_range: str) -> Dict:
        """创建默认的阶段情绪计划"""
        start_chap, end_chap = parse_chapter_range(stage_range)
        stage_length = end_chap - start_chap + 1
        
        # 基于阶段名称设置默认情感特征
        stage_emotional_profiles = {
            "opening_stage": {
                "goal": "建立情感连接和读者认同",
                "pace": "逐步加强情感投入",
                "intensity": "低到中"
            },
            "development_stage": {
                "goal": "深化情感冲突和发展关系",
                "pace": "起伏变化，快慢结合", 
                "intensity": "中"
            },
            "climax_stage": {
                "goal": "情感爆发和高潮体验",
                "pace": "紧张加速，高潮集中",
                "intensity": "高"
            },
            "ending_stage": {
                "goal": "情感解决和成长体现",
                "pace": "逐渐放缓，情感升华",
                "intensity": "中到高"
            },
            "final_stage": {
                "goal": "情感圆满和主题共鸣",
                "pace": "平稳深沉，余韵绵长",
                "intensity": "中"
            }
        }
        
        profile = stage_emotional_profiles.get(stage_name, {
            "goal": "情感发展和角色成长",
            "pace": "自然流畅",
            "intensity": "中"
        })
        
        return {
            "stage_emotional_strategy": {
                "overall_emotional_goal": profile["goal"],
                "emotional_pacing_plan": profile["pace"],
                "key_emotional_arcs": ["主角情感成长", "主要关系发展"],
                "emotional_intensity_curve": f"从{profile['intensity']}强度开始，根据情节需要变化"
            },
            "chapter_emotional_breakdown": [
                {
                    "chapter_range": f"{start_chap}-{start_chap + stage_length//3}",
                    "emotional_focus": "建立阶段情感基础",
                    "target_reader_emotion": "投入和期待",
                    "key_scenes_design": "情感建立场景",
                    "intensity_level": "中"
                }
            ],
            "emotional_turning_points": [
                {
                    "approximate_chapter": f"约第{start_chap + stage_length//2}章",
                    "emotional_shift": "情感深化或转折",
                    "preparation_chapters": f"第{start_chap}章开始铺垫",
                    "impact_description": "推动角色情感成长"
                }
            ],
            "emotional_supporting_elements": {
                "settings_for_emotion": ["适合情感表达的关键场景"],
                "symbolic_elements": ["情感象征物"],
                "relationship_developments": ["重要关系进展"]
            },
            "emotional_break_planning": {
                "break_chapters": [f"第{start_chap + stage_length//4}章", f"第{start_chap + stage_length*3//4}章"],
                "break_activities": ["日常互动", "角色反思", "关系建设"],
                "purpose": "给读者情感缓冲和消化空间"
            }
        }

    def _get_emotional_plan_for_stage(self, stage_name: str) -> Dict:
        """获取阶段的情绪计划"""
        novel_data = self.generator.novel_data
        stage_plans = novel_data.get("stage_writing_plans", {})
        
        if stage_name in stage_plans and "emotional_plan" in stage_plans[stage_name]:
            return stage_plans[stage_name]["emotional_plan"]
        
        # 如果没有情绪计划，生成一个默认的
        stage_range = self._get_stage_range(stage_name)
        return self._create_default_stage_emotional_plan(stage_name, stage_range)

    def _generate_emotional_guidance_for_chapter(self, chapter_number: int, 
                                            emotional_plan: Dict, stage_name: str) -> Dict:
        """为章节生成详细情绪指导"""
        # 获取章节在阶段中的位置
        stage_range = self._get_stage_range(stage_name)
        start_chap, end_chap = parse_chapter_range(stage_range)
        chapter_position = chapter_number - start_chap + 1
        total_chapters_in_stage = end_chap - start_chap + 1
        progress = chapter_position / total_chapters_in_stage
        
        # 基于进度确定情绪重点
        emotional_breakdown = emotional_plan.get("chapter_emotional_breakdown", [])
        current_emotional_focus = "推进情感发展"
        target_intensity = "中"
        
        for breakdown in emotional_breakdown:
            breakdown_range = breakdown.get("chapter_range", "")
            if self._is_chapter_in_emotional_range(chapter_number, breakdown_range):
                current_emotional_focus = breakdown.get("emotional_focus", current_emotional_focus)
                target_intensity = breakdown.get("intensity_level", target_intensity)
                break
        
        # 检查是否为情感转折点
        turning_points = emotional_plan.get("emotional_turning_points", [])
        is_turning_point = False
        turning_point_info = {}
        
        for point in turning_points:
            approx_chapter = point.get("approximate_chapter", "")
            if self._is_chapter_near_turning_point(chapter_number, approx_chapter):
                is_turning_point = True
                turning_point_info = point
                break
        
        # 检查是否为情感缓冲章节
        break_planning = emotional_plan.get("emotional_break_planning", {})
        is_break_chapter = chapter_number in break_planning.get("break_chapters", [])
        
        return {
            "current_emotional_focus": current_emotional_focus,
            "target_intensity": target_intensity,
            "is_emotional_turning_point": is_turning_point,
            "turning_point_info": turning_point_info,
            "is_emotional_break_chapter": is_break_chapter,
            "break_activities": break_planning.get("break_activities", []),
            "emotional_supporting_elements": emotional_plan.get("emotional_supporting_elements", {}),
            "reader_emotional_journey": f"本章读者应该感受到{current_emotional_focus}的情感体验"
        }

    def _is_chapter_in_emotional_range(self, chapter: int, chapter_range: str) -> bool:
        """检查章节是否在情绪范围段内"""
        if not chapter_range or "-" not in chapter_range:
            return False
        
        try:
            start, end = chapter_range.split("-")
            start_chap = int(start.strip())
            end_chap = int(end.strip())
            return start_chap <= chapter <= end_chap
        except:
            return False

    def _is_chapter_near_turning_point(self, chapter: int, approx_chapter: str) -> bool:
        """检查章节是否接近情感转折点"""
        if not approx_chapter:
            return False
        
        try:
            # 解析大致章节描述
            if "第" in approx_chapter and "章" in approx_chapter:
                chap_num = int(approx_chapter.split("第")[1].split("章")[0])
                return abs(chapter - chap_num) <= 2  # 前后2章内视为接近
            return False
        except:
            return False            