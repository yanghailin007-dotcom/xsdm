# WritingGuidanceManager.py
import json
import re
from typing import Dict, List, Optional
from utils import parse_chapter_range, is_chapter_in_range

class WritingGuidanceManager:
    """写作指导管理器 - 负责章节写作上下文、指导生成、事件时间线等"""
    
    def __init__(self, stage_plan_manager):
        self.stage_plan_manager = stage_plan_manager
        self.generator = stage_plan_manager.generator

    def get_chapter_writing_context(self, chapter_number: int) -> Dict:
        """获取指定章节的写作上下文 - 增强版本，包含前后事件信息"""
        print(f"  🔍 开始获取第{chapter_number}章写作上下文")
        
        current_stage = self.stage_plan_manager._get_current_stage(chapter_number)
        print(f"  🔍 当前阶段: {current_stage}")
        
        if not current_stage:
            print(f"  ⚠️ 无法确定第{chapter_number}章所属阶段")
            return {}
        
        writing_plan = self.stage_plan_manager.get_stage_writing_plan_by_name(current_stage)
        print(f"  🔍 写作计划获取结果: {bool(writing_plan)}")
        
        if not writing_plan:
            print(f"  ⚠️ 第{chapter_number}章没有找到写作计划")
            return {}
        
        # 获取事件时间线信息
        event_timeline = self._get_chapter_event_timeline(chapter_number, writing_plan)
        print(f"  🔍 事件时间线获取结果: {len(event_timeline.get('events', []))}个事件")
        
        # 获取情绪计划
        print(f"  🔍 开始获取情绪计划...")
        emotional_plan = self.stage_plan_manager.emotional_manager.get_emotional_plan_for_stage(current_stage)
        print(f"  🔍 情绪计划获取结果: {bool(emotional_plan)}")
        
        # 生成章节特定的写作指导
        chapter_context = self._generate_chapter_writing_context(chapter_number, writing_plan)
        
        # 添加事件时间线信息
        chapter_context["event_timeline"] = event_timeline
        
        # 增强：添加详细情绪指导
        if emotional_plan:
            print(f"  🔍 开始生成情绪指导...")
            emotional_guidance = self.stage_plan_manager.emotional_manager.generate_emotional_guidance_for_chapter(
                chapter_number, emotional_plan, current_stage
            )
            chapter_context["emotional_guidance"] = emotional_guidance
            print(f"  💖 成功为第{chapter_number}章生成情绪指导")
            print(f"    情感重点: {emotional_guidance.get('current_emotional_focus', '未知')}")
            print(f"    情感强度: {emotional_guidance.get('target_intensity', '未知')}")
        else:
            print(f"  ⚠️ 第{chapter_number}章的情绪计划为空")
            chapter_context["emotional_guidance"] = {}
        
        # 🆕 获取特殊事件指导
        special_guidance = self.stage_plan_manager.romance_manager.get_special_event_guidance(chapter_number)
        chapter_context["special_guidance"] = special_guidance
        
        if special_guidance.get("has_special_event", False):
            print(f"  💝 第{chapter_number}章有情感特殊事件，重点抓住读者兴趣")

        return chapter_context

    def generate_writing_guidance_prompt(self, chapter_number: int) -> str:
        """生成章节写作指导提示词 - 增强版本，包含事件时间线"""
        writing_context = self.get_chapter_writing_context(chapter_number)
        
        if not writing_context:
            return "# 🎯 写作指导\n\n暂无特定的写作指导。"
        
        prompt_parts = ["\n\n# 🎯 写作指导"]
        
        # 🆕 添加事件时间线指导
        event_timeline = writing_context.get("event_timeline", {})
        timeline_summary = event_timeline.get("timeline_summary", "")
        
        if timeline_summary:
            prompt_parts.append(f"## ⏰ 事件时间线")
            prompt_parts.append(f"{timeline_summary}")
            
            # 添加上下文事件详情
            previous_event = event_timeline.get("previous_event")
            if previous_event:
                prompt_parts.append(f"\n### 📖 前情回顾 (第{previous_event['chapter']}章)")
                prompt_parts.append(f"- **事件**: {previous_event['name']}")
                prompt_parts.append(f"- **类型**: {previous_event['type']}事件")
                if previous_event.get('subtype'):
                    prompt_parts.append(f"- **子类型**: {previous_event['subtype']}")
                prompt_parts.append(f"- **影响**: {previous_event.get('significance', '推进情节发展')}")
                if previous_event.get('description'):
                    prompt_parts.append(f"- **详情**: {previous_event['description']}")
            
            current_events = event_timeline.get("current_events", [])
            if current_events:
                prompt_parts.append(f"\n### 🎯 本章核心事件")
                for event in current_events:
                    event_type = f"{event['type']}({event.get('subtype', '')})" if event.get('subtype') else event['type']
                    prompt_parts.append(f"- **{event['name']}** ({event_type})")
                    prompt_parts.append(f"  - 重要性: {event.get('significance', '推进情节')}")
                    if event.get('description'):
                        prompt_parts.append(f"  - 内容: {event['description']}")
            else:
                prompt_parts.append(f"\n### 📝 本章推进重点")
                prompt_parts.append(f"- 无重大事件，重点推进日常情节和角色发展")
                prompt_parts.append(f"- 利用本章深化情感联系或铺垫后续冲突")
            
            next_event = event_timeline.get("next_event")
            if next_event:
                prompt_parts.append(f"\n### 🔮 后续展望 (第{next_event['chapter']}章)")
                prompt_parts.append(f"- **即将发生**: {next_event['name']}")
                event_type = f"{next_event['type']}({next_event.get('subtype', '')})" if next_event.get('subtype') else next_event['type']
                prompt_parts.append(f"- **事件类型**: {event_type}") 
                prompt_parts.append(f"- **重要性**: {next_event.get('significance', '重要情节发展')}")
                prompt_parts.append(f"- **本章铺垫**: 适当为下一章事件埋下伏笔")
        
        # 添加本章写作重点
        prompt_parts.append(f"\n## ✍️ 本章写作重点")
        prompt_parts.append(f"{writing_context['writing_focus']}")
        
        # 添加特殊事件指导
        special_guidance = writing_context.get("special_guidance", {})
        if special_guidance.get("has_special_event", False):
            prompt_parts.append(f"\n## 💝 情感特殊事件指导")
            
            for event in special_guidance.get("special_events", []):
                prompt_parts.append(f"### {event.get('name', '情感特殊事件')}")
                prompt_parts.append(f"- **情感风格**: {event.get('romance_style', '情感发展')}")
                prompt_parts.append(f"- **情节设计**: {event.get('plot_design', '情感互动')}")
                prompt_parts.append(f"- **读者吸引**: {event.get('reader_hook', '保持读者兴趣')}")
                prompt_parts.append(f"- **写作重点**: {event.get('writing_focus', '情感描写')}")
                
                key_moments = event.get("key_moments", [])
                if key_moments:
                    prompt_parts.append(f"- **关键时刻**: {', '.join(key_moments)}")
        
        # 添加情节结构指导
        if writing_context.get("plot_structure"):
            prompt_parts.append(f"\n## 🎭 情节结构指导")
            plot_struct = writing_context["plot_structure"]
            prompt_parts.append(f"- **开场方式**: {plot_struct.get('opening_approach', '自然承接上一章')}")
            prompt_parts.append(f"- **冲突设计**: {plot_struct.get('conflict_design', '推进现有冲突')}")
            prompt_parts.append(f"- **高潮设置**: {plot_struct.get('climax_point', '情感或情节高潮')}")
            prompt_parts.append(f"- **结尾处理**: {plot_struct.get('ending_approach', '设置悬念吸引下一章')}")
        
        # 添加角色表现指导
        if writing_context.get("character_guidance"):
            prompt_parts.append(f"\n## 👥 角色表现指导")
            char_guide = writing_context["character_guidance"]
            prompt_parts.append(f"- **主角发展**: {char_guide.get('protagonist_development', '自然展现成长')}")
            if char_guide.get("supporting_characters_focus"):
                prompt_parts.append(f"- **配角重点**: {char_guide['supporting_characters_focus']}")
        
        # 添加事件参与指导
        if writing_context.get("event_participation"):
            prompt_parts.append(f"\n## 🎪 事件参与指导")
            event_part = writing_context["event_participation"]
            prompt_parts.append(f"- **事件角色**: {event_part.get('role_in_events', '推进事件发展')}")
            if event_part.get("key_moments"):
                prompt_parts.append(f"- **关键时刻**: {event_part['key_moments']}")
        
        # 添加伏笔整合指导
        if writing_context.get("foreshadowing_integration"):
            prompt_parts.append(f"\n## 🔮 伏笔整合指导")
            foreshadow_guide = writing_context["foreshadowing_integration"]
            prompt_parts.append(f"- **伏笔任务**: {foreshadow_guide.get('foreshadowing_tasks', '自然融入情节')}")
        
        # 添加写作技巧建议
        if writing_context.get("writing_techniques"):
            prompt_parts.append(f"\n## 📚 写作技巧建议")
            techniques = writing_context["writing_techniques"]
            prompt_parts.append(f"- **叙事重点**: {techniques.get('narrative_focus', '保持故事连贯性')}")
            prompt_parts.append(f"- **描写重点**: {techniques.get('description_priority', '关键场景和情感')}")
        
        return "\n".join(prompt_parts)

    def _get_chapter_event_timeline(self, chapter_number: int, writing_plan: Dict) -> Dict:
        """获取章节的事件时间线信息"""
        # 获取当前阶段的所有事件
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        
        # 构建完整的事件列表
        all_events = []
        
        # 添加重大事件
        for event in event_system.get("major_events", []):
            all_events.append({
                "type": "major",
                "name": event.get("name", "未命名重大事件"),
                "chapter": event.get("start_chapter", 0),
                "end_chapter": event.get("end_chapter", event.get("start_chapter", 0)),
                "description": event.get("description", ""),
                "significance": event.get("significance", "重大事件")
            })
        
        # 添加中型事件
        for event in event_system.get("medium_events", []):
            all_events.append({
                "type": "medium", 
                "name": event.get("name", "未命名中型事件"),
                "chapter": event.get("chapter", event.get("start_chapter", 0)),
                "end_chapter": event.get("chapter", event.get("start_chapter", 0)),
                "description": event.get("description", ""),
                "significance": event.get("significance", event.get("main_goal", "中型事件"))
            })
        
        # 添加小型事件
        for event in event_system.get("minor_events", []):
            all_events.append({
                "type": "minor",
                "name": event.get("name", "未命名小型事件"), 
                "chapter": event.get("chapter", event.get("start_chapter", 0)),
                "end_chapter": event.get("chapter", event.get("start_chapter", 0)),
                "description": event.get("description", ""),
                "significance": event.get("significance", event.get("function", "小型事件"))
            })
        
        # 添加特殊事件
        for event in event_system.get("special_events", []):
            all_events.append({
                "type": "special",
                "subtype": event.get("subtype", "特殊事件"),
                "name": event.get("name", "未命名特殊事件"),
                "chapter": event.get("chapter", event.get("start_chapter", 0)),
                "end_chapter": event.get("chapter", event.get("start_chapter", 0)),
                "description": event.get("description", ""),
                "significance": event.get("significance", event.get("emotional_development", "情感特殊事件")),
                "event_category": event.get("event_category", "特殊事件")
            })
        
        # 按章节排序
        all_events.sort(key=lambda x: x["chapter"])
        
        # 找到当前章节的事件
        current_events = [event for event in all_events if event["chapter"] == chapter_number]
        
        # 找到前一个事件（最近的发生在当前章节之前的事件）
        previous_events = [event for event in all_events if event["chapter"] < chapter_number]
        previous_event = previous_events[-1] if previous_events else None
        
        # 找到下一个事件（最近的发生在当前章节之后的事件）
        next_events = [event for event in all_events if event["chapter"] > chapter_number]
        next_event = next_events[0] if next_events else None
        
        return {
            "current_events": current_events,
            "previous_event": previous_event,
            "next_event": next_event,
            "events": all_events,  # 所有事件用于调试
            "timeline_summary": self._generate_timeline_summary(previous_event, current_events, next_event)
        }

    def _generate_timeline_summary(self, previous_event: Optional[Dict], current_events: List[Dict], next_event: Optional[Dict]) -> str:
        """生成时间线摘要"""
        summary_parts = []
        
        if previous_event:
            summary_parts.append(f"📖 前情回顾: 第{previous_event['chapter']}章《{previous_event['name']}》")
        
        if current_events:
            event_names = [f"《{event['name']}》" for event in current_events]
            summary_parts.append(f"🎯 本章事件: {', '.join(event_names)}")
        else:
            summary_parts.append("📝 本章事件: 日常推进或情感发展")
        
        if next_event:
            summary_parts.append(f"🔮 后续展望: 第{next_event['chapter']}章《{next_event['name']}》")
        
        return " | ".join(summary_parts)

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
        start_chap, end_chap = parse_chapter_range(stage_range)
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
        special_events = event_system.get("special_events", [])
        
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
        
        # 检查特殊事件参与
        for event in special_events:
            event_chapter = event.get("chapter", event.get("start_chapter", 0))
            if event_chapter == chapter_number:
                participation["role_in_events"] = f"参与{event.get('name', '情感特殊事件')}"
                participation["key_moments"].append("情感特殊事件时刻")
        
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

    def generate_chapter_outline_template(self, chapter_number: int) -> Dict:
        """生成章节大纲模板"""
        writing_context = self.get_chapter_writing_context(chapter_number)
        
        template = {
            "chapter_number": chapter_number,
            "chapter_title": f"第{chapter_number}章",
            "word_count_target": 3000,
            "structure": {
                "opening": {
                    "purpose": "承接上一章，引入本章内容",
                    "suggested_length": "300-500字",
                    "key_elements": []
                },
                "development": {
                    "purpose": "推进情节，发展角色",
                    "suggested_length": "1500-2000字", 
                    "key_elements": []
                },
                "climax": {
                    "purpose": "本章高潮或关键转折",
                    "suggested_length": "500-800字",
                    "key_elements": []
                },
                "ending": {
                    "purpose": "设置悬念，准备下一章",
                    "suggested_length": "200-400字",
                    "key_elements": []
                }
            },
            "key_scenes": [],
            "character_development": [],
            "foreshadowing_opportunities": []
        }
        
        # 根据写作上下文填充模板
        if writing_context:
            # 填充结构元素
            if writing_context.get("plot_structure"):
                plot_struct = writing_context["plot_structure"]
                template["structure"]["opening"]["key_elements"].append(plot_struct.get("opening_approach", ""))
                template["structure"]["development"]["key_elements"].append(plot_struct.get("conflict_design", ""))
                template["structure"]["climax"]["key_elements"].append(plot_struct.get("climax_point", ""))
                template["structure"]["ending"]["key_elements"].append(plot_struct.get("ending_approach", ""))
            
            # 填充关键场景
            if writing_context.get("event_participation"):
                event_part = writing_context["event_participation"]
                if event_part.get("key_moments"):
                    template["key_scenes"].extend(event_part["key_moments"])
            
            # 填充角色发展
            if writing_context.get("character_guidance"):
                char_guide = writing_context["character_guidance"]
                if char_guide.get("protagonist_development"):
                    template["character_development"].append(char_guide["protagonist_development"])
                if char_guide.get("supporting_characters_focus"):
                    template["character_development"].append(char_guide["supporting_characters_focus"])
            
            # 填充伏笔机会
            if writing_context.get("foreshadowing_integration"):
                foreshadow_guide = writing_context["foreshadowing_integration"]
                if foreshadow_guide.get("foreshadowing_tasks"):
                    template["foreshadowing_opportunities"].append(foreshadow_guide["foreshadowing_tasks"])
        
        return template

    def validate_writing_guidance_completeness(self, chapter_number: int) -> Dict:
        """验证写作指导的完整性"""
        writing_context = self.get_chapter_writing_context(chapter_number)
        
        validation_result = {
            "chapter_number": chapter_number,
            "is_complete": True,
            "missing_elements": [],
            "strengths": [],
            "improvement_suggestions": []
        }
        
        # 检查必需元素
        required_elements = [
            "writing_focus",
            "plot_structure", 
            "character_guidance",
            "event_participation"
        ]
        
        for element in required_elements:
            if element not in writing_context:
                validation_result["missing_elements"].append(element)
                validation_result["is_complete"] = False
        
        # 检查事件时间线
        if not writing_context.get("event_timeline", {}).get("current_events") and \
           not writing_context.get("event_timeline", {}).get("previous_event") and \
           not writing_context.get("event_timeline", {}).get("next_event"):
            validation_result["improvement_suggestions"].append("事件时间线信息不足")
        
        # 检查情绪指导
        if not writing_context.get("emotional_guidance"):
            validation_result["improvement_suggestions"].append("缺少情绪指导")
        else:
            emotional_guide = writing_context["emotional_guidance"]
            if emotional_guide.get("current_emotional_focus") == "未匹配到情绪分段":
                validation_result["improvement_suggestions"].append("情绪指导不够具体")
            else:
                validation_result["strengths"].append("情绪指导详细")
        
        # 检查特殊事件指导
        if writing_context.get("special_guidance", {}).get("has_special_event"):
            validation_result["strengths"].append("包含特殊事件指导")
        
        return validation_result

    def get_writing_techniques_for_chapter(self, chapter_number: int) -> List[str]:
        """获取章节特定的写作技巧建议"""
        writing_context = self.get_chapter_writing_context(chapter_number)
        techniques = []
        
        # 基于写作上下文生成技巧建议
        if writing_context.get("emotional_guidance", {}).get("is_emotional_turning_point"):
            techniques.append("使用强烈的情感描写和内心独白")
            techniques.append("通过环境描写烘托情感氛围")
            techniques.append("运用对比手法增强情感冲击力")
        
        if writing_context.get("emotional_guidance", {}).get("is_emotional_break_chapter"):
            techniques.append("采用轻松自然的叙事节奏")
            techniques.append("注重日常细节和角色互动")
            techniques.append("使用幽默或温馨的元素调节情绪")
        
        if writing_context.get("event_timeline", {}).get("current_events"):
            techniques.append("重点描写关键事件场景")
            techniques.append("运用动作和对话推进情节")
            techniques.append("保持紧张感和节奏感")
        else:
            techniques.append("注重角色发展和关系建设")
            techniques.append("运用伏笔和暗示推进主线")
            techniques.append("保持叙事的连贯性和流畅性")
        
        # 添加通用技巧
        techniques.extend([
            "注意段落间的过渡和衔接",
            "平衡对话、描写和叙事的比例",
            "保持角色性格的一致性",
            "运用感官描写增强场景真实感"
        ])
        
        return techniques