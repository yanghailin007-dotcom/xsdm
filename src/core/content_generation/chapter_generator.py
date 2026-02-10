"""章节生成器 - 专门负责章节内容的生成逻辑"""
import copy
import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from src.utils.logger import get_logger


class ChapterGenerator:
    """章节内容生成器 - 处理所有章节相关的生成逻辑"""
    
    def __init__(self, content_generator):
        self.logger = get_logger("ChapterGenerator")
        self.cg = content_generator  # 对主生成器的引用
        self.api_client = content_generator.api_client
        self.quality_assessor = content_generator.quality_assessor
        self.novel_generator = content_generator.novel_generator
        self.custom_main_character_name = content_generator.custom_main_character_name
    
    def generate_chapter_content_for_novel(self, chapter_number: int, novel_data: Dict, context) -> Optional[Dict]:
        """生成章节内容的主入口函数"""
        from src.core.Contexts import GenerationContext
        
        self.logger.info(f"🎬 开始生成第{chapter_number}章内容...")
        
        MAX_CHAPTER_RETRIES = 5
        RETRY_WAIT_SECONDS = 20
        
        for attempt in range(MAX_CHAPTER_RETRIES):
            if attempt > 0:
                self.logger.info(f"  - 章节生成失败，将在 {RETRY_WAIT_SECONDS} 秒后进行第 {attempt + 1}/{MAX_CHAPTER_RETRIES} 次重试...")
                time.sleep(RETRY_WAIT_SECONDS)
            
            self.logger.info(f"  🔄 第 {attempt + 1}/{MAX_CHAPTER_RETRIES} 次尝试生成第 {chapter_number} 章...")
            failure_reason = None
            failure_details = {}
            
            try:
                # 初始化世界状态（仅第一次）
                if chapter_number == 1 and attempt == 0:
                    self.logger.info("🔄 初始化世界状态...")
                    self.quality_assessor.world_state_manager.initialize_world_state_from_novel_data(
                        novel_data["novel_title"], novel_data
                    )
                
                # 存储上下文
                novel_data['_current_generation_context'] = context
                
                # 准备章节参数
                chapter_params = self.cg._prepare_chapter_params(chapter_number, novel_data)
                if not chapter_params or not self._validate_chapter_params(chapter_params):
                    failure_reason = "参数准备失败"
                    failure_details = {"missing_params": [key for key, val in chapter_params.items() if not val]}
                    self.logger.error(f"  ❌ 第{chapter_number}章参数准备失败。")
                    continue
                
                self.logger.info(f"  ✅ 第{chapter_number}章所有参数验证通过。")
                
                # 生成核心内容
                self.logger.info(f"  🚀 开始调用核心内容生成...")
                chapter_data = self.generate_chapter_content(chapter_params)
                
                if not chapter_data:
                    failure_reason = "核心内容生成失败"
                    failure_details = {"step": "generate_chapter_content"}
                    self.logger.error(f"  ❌ 第{chapter_number}章核心内容生成失败。")
                    continue
                
                # 后处理
                self.logger.info(f"  ✨ 核心内容生成完毕，开始后处理...")
                
                # 确保章节标题唯一性
                chapter_data = self.cg._handle_chapter_title_uniqueness(chapter_data, chapter_number, novel_data)
                
                # 提取情绪设计信息
                if chapter_data and chapter_data.get("chapter_design", {}).get("emotional_design"):
                    chapter_data["emotional_design"] = chapter_data["chapter_design"]["emotional_design"]
                    self.logger.info(f"  💖 已从设计蓝图中提取情绪设计: {chapter_data['emotional_design'].get('target_emotion', '未知')}")
                else:
                    chapter_data["emotional_design"] = {}
                
                # 质量评估
                self.logger.info(f"  📊 开始质量评估...")
                chapter_content = chapter_data.get("content", "")
                if not isinstance(chapter_content, str):
                    self.logger.error(f"❌ chapter_content 类型错误: {type(chapter_content)}")
                    chapter_content = str(chapter_content) if chapter_content else ""
                
                assessment = self.quality_assessor.quick_assess_chapter_quality(
                    chapter_content,
                    chapter_data.get("chapter_title", ""),
                    chapter_number,
                    novel_data["novel_title"],
                    chapter_params.get("previous_chapters_summary", ""),
                    chapter_data.get("word_count", 0),
                    novel_data=novel_data
                )
                
                # 处理评估失败的情况
                if assessment is None:
                    self.logger.warning(f"⚠️ 质量评估失败，使用默认评分")
                    assessment = {
                        "overall_score": 6.0,
                        "quality_verdict": "API调用失败，使用默认评分",
                        "weaknesses": [],
                        "strengths": []
                    }
                
                score = assessment.get("overall_score", 0)
                chapter_data["quality_score"] = score
                chapter_data["quality_assessment"] = assessment
                self.logger.info(f"  质量评分: {score:.1f}分")
                
                # 根据质量决定是否优化（使用渐进式阈值）
                optimize_needed, optimize_reason = self.cg._should_optimize_based_on_config(
                    assessment, retry_count=attempt, chapter_number=chapter_number
                )
                if optimize_needed:
                    self.logger.info(f"  🔧 进行优化: {optimize_reason}")
                    chapter_data = self._optimize_chapter_content(
                        chapter_data, assessment, novel_data, chapter_number, chapter_params
                    )
                else:
                    self.logger.info(f"  ✓ {optimize_reason}")
                    chapter_data["quality_assessment"] = assessment
                
                # AI开场白（仅第一章）
                if chapter_number == 1:
                    try:
                        chapter_data = self.novel_generator._add_ai_spicy_opening_to_first_chapter(
                            chapter_data, 
                            novel_data.get("novel_title", ""), 
                            novel_data.get("novel_synopsis", ""), 
                            novel_data.get("category", "默认")
                        )
                    except Exception as e:
                        self.logger.warning(f"  ⚠️ AI开场白生成异常，使用备用模板: {e}")

                # 提取并保存结尾状态（用于下一章衔接）
                chapter_content = chapter_data.get("content", "")
                self.logger.info(f"  🔍 [衔接系统] 章节生成成功，准备提取结尾状态，内容长度: {len(chapter_content)}")
                if chapter_content:
                    end_state = self._extract_and_save_end_state(chapter_content, chapter_number, novel_data)
                    if end_state:
                        chapter_data["end_state"] = end_state
                        self.logger.info(f"  ✅ [衔接系统] 第{chapter_number}章结尾状态已添加到chapter_data")
                    else:
                        self.logger.warning(f"  ⚠️ [衔接系统] 第{chapter_number}章结尾状态提取失败")

                # 成功返回
                self.logger.info(f"🎉 第 {chapter_number} 章在第 {attempt + 1} 次尝试中生成成功！")
                return chapter_data
                
            except Exception as e:
                failure_reason = f"生成过程异常: {str(e)}"
                failure_details = {
                    "exception_type": type(e).__name__,
                    "exception_message": str(e),
                    "chapter_number": chapter_number,
                    "traceback": self._get_traceback_info()
                }
                self.logger.error(f"  ❌ 第{chapter_number}章在第 {attempt + 1} 次尝试中出现严重异常: {e}")
                import traceback
                traceback.print_exc()
        
        # 所有重试都失败
        self.logger.info(f"🔥🔥🔥 严重错误: 第 {chapter_number} 章在 {MAX_CHAPTER_RETRIES} 次尝试后彻底失败！")
        self.cg._save_chapter_failure(novel_data, chapter_number, failure_reason or "未知原因导致所有重试失败", failure_details)
        return None
    
    def _validate_chapter_params(self, params: Dict) -> bool:
        """验证章节参数是否完整"""
        required = ['chapter_number', 'novel_title', 'novel_synopsis', 'plot_direction']
        for key in required:
            if key not in params or not params[key]:
                self.logger.error(f"❌ 参数验证失败: 缺少 {key}")
                return False
        return True
    
    def _get_traceback_info(self) -> str:
        """获取当前异常的堆栈信息"""
        import traceback
        import io
        f = io.StringIO()
        traceback.print_exc(file=f)
        return f.getvalue()
    
    def _optimize_chapter_content(self, chapter_data: Dict, assessment: Dict, novel_data: Dict, 
                                  chapter_number: int, chapter_params: Dict) -> Dict:
        """优化章节内容"""
        max_optimization_retries = 2
        optimized_data = None
        
        for retry in range(max_optimization_retries):
            try:
                optimized_data = self.quality_assessor.optimize_chapter_content({
                    "assessment_results": json.dumps(assessment, ensure_ascii=False),
                    "original_content": chapter_data.get("content", ""),
                    "priority_fix_1": assessment.get("weaknesses", [""])[0] if assessment.get("weaknesses") else "提升质量",
                    "priority_fix_2": assessment.get("weaknesses", [""])[1] if len(assessment.get("weaknesses", [])) > 1 else "",
                    "priority_fix_3": assessment.get("weaknesses", [""])[2] if len(assessment.get("weaknesses", [])) > 2 else "",
                    "novel_title": novel_data["novel_title"],
                    "chapter_number": chapter_number,
                    "chapter_title": chapter_data.get("chapter_title", ""),
                    "writing_style_guide": novel_data.get("writing_style_guide", {})
                })
                
                if optimized_data and optimized_data.get("content"):
                    self.logger.info(f"  ✅ 第{retry+1}次优化成功")
                    break
                else:
                    self.logger.warning(f"  ⚠️ 第{retry+1}次优化失败，返回空结果")
                    optimized_data = None
            except Exception as e:
                self.logger.error(f"  ❌ 第{retry+1}次优化过程异常: {e}")
                optimized_data = None
        
        if optimized_data and optimized_data.get("content"):
            chapter_data["content"] = optimized_data.get("content")
            chapter_data["word_count"] = len(optimized_data.get("content", ""))
            
            # 重新评估
            new_assessment = self.quality_assessor.quick_assess_chapter_quality(
                chapter_data.get("content", ""),
                chapter_data.get("chapter_title", ""),
                chapter_number,
                novel_data["novel_title"],
                chapter_params.get("previous_chapters_summary", ""),
                chapter_data.get("word_count", 0),
                novel_data=novel_data
            )
            
            original_score = assessment.get("overall_score", 0)
            new_score = new_assessment.get("overall_score", 0)
            self.logger.info(f"  ✓ 优化完成，新评分: {new_score:.1f}分 (提升{new_score - original_score:+.1f}分)")
            
            chapter_data["quality_score"] = new_score
            chapter_data["quality_assessment"] = new_assessment
            chapter_data["optimization_info"] = {
                "optimized": True,
                "original_score": original_score,
                "retry_count": retry + 1
            }
        else:
            self.logger.warning(f"  ⚠️ 所有优化尝试均失败，保持原内容")
            chapter_data["optimization_info"] = {
                "optimized": False,
                "reason": "优化过程失败",
                "original_score": assessment.get("overall_score", 0)
            }
        
        return chapter_data
    
    def generate_chapter_content(self, chapter_params: Dict) -> Optional[Dict]:
        """生成章节核心内容"""
        self.logger.info(f"  🔍 进入【优化版】generate_chapter_content方法...")
        chapter_number = chapter_params.get('chapter_number', '未知')
        pre_designed_scenes = chapter_params.get("pre_designed_scenes", [])
        
        if not pre_designed_scenes:
            self.logger.error(f"  ❌ 第 {chapter_number} 章缺少预设的场景事件，无法直接生成内容。")
            return None
        
        # 构建情绪强度指导
        intensity_guidance = self._build_emotional_intensity_guidance(pre_designed_scenes)
        
        # 构建场景结构
        scenes_input_str = self._build_scene_structure_string(pre_designed_scenes)
        
        # 构建完整提示词
        chapter_generation_prompt = self._build_chapter_generation_prompt(
            chapter_params, chapter_number, intensity_guidance, scenes_input_str
        )
        
        # 保存提示词
        self.cg._save_chapter_generation_prompt(
            chapter_params.get('novel_title', ''),
            chapter_number,
            chapter_generation_prompt
        )
        
        # 调用API生成内容
        max_retries = 3
        for attempt in range(max_retries):
            self.logger.info(f"  ✍️ 第{attempt + 1}/{max_retries}次尝试直接生成第{chapter_number}章内容...")
            
            content_result = self.api_client.generate_content_with_retry(
                "chapter_content_generation",
                chapter_generation_prompt,
                purpose=f"直接从场景事件生成第{chapter_number}章内容"
            )
            
            if content_result and isinstance(content_result, dict) and len(content_result.get("content", "")) >= 1800:
                self.logger.info(f"  ✅ 第{chapter_number}章内容生成成功，字数达标。")
                return content_result
            else:
                word_count = len(content_result.get("content", "")) if content_result else 0
                self.logger.warning(f"  ⚠️ 第{attempt + 1}次尝试失败或字数不足 ({word_count}字)。")
        
        self.logger.error(f"  ❌ 第{chapter_number}章所有直接生成尝试均失败")
        return None
    
    def _build_emotional_intensity_guidance(self, pre_designed_scenes: List[Dict]) -> str:
        """构建情绪强度指导"""
        intensity_guidance_map = {
            "low": """
## 🌊 情绪强度指南 - 平和节奏 (LOW INTENSITY)
本章采用【平和、内敛】的情绪节奏：
- **情感表达**: 重点在于角色内心的微妙变化和思考，而非外部冲突爆发
- **语言特点**: 使用细腻、温和的语言，避免过度夸张的情感词汇
- **节奏控制**: 节奏较慢，多用内心独白和细腻描写，让读者感受平静中的暗流
- **适用场景**: 日常描写、角色互动、世界观展示、铺垫性章节
""",
            "medium": """
## 🌊 情绪强度指南 - 标准节奏 (MEDIUM INTENSITY)
本章采用【张弛有度、情绪适中】的节奏：
- **情感表达**: 情感真实自然，不过分夸张，让读者产生共鸣
- **语言特点**: 语言流畅自然，平衡叙述和对话，适当使用感叹和强调
- **节奏控制**: 在平静与紧张之间保持平衡，情节推进稳健
- **适用场景**: 推进情节、建立冲突、展现角色成长的标准章节
""",
            "high": """
## 🌊 情绪强度指南 - 激昂节奏 (HIGH INTENSITY)
本章采用【高强度、强冲击】的情绪节奏：
- **情感表达**: 情感表达要强烈、直接、富有张力，使用短句和感叹增强冲击力
- **语言特点**: 语言紧凑有力，多用短句和感叹，营造紧迫感和氛围
- **节奏控制**: 节奏快速，冲突密集，让读者感受到强烈的情绪冲击
- **适用场景**: 高潮章节、重大转折、强烈冲突、情感爆发的关键章节
"""
        }
        
        # 分析所有场景的情绪强度
        intensity_votes = []
        emotional_focus_list = []
        
        for scene in pre_designed_scenes:
            if "emotional_intensity" in scene:
                intensity_votes.append(scene["emotional_intensity"])
            if "emotional_impact" in scene:
                emotional_focus_list.append(f"- 场景「{scene.get('name', '未知场景')}」的情感冲击: {scene['emotional_impact']}")
        
        # 根据场景的情绪强度投票决定本章的整体强度
        chapter_emotional_intensity = "medium"  # 默认中等强度
        
        if intensity_votes:
            low_count = intensity_votes.count("low")
            medium_count = intensity_votes.count("medium")
            high_count = intensity_votes.count("high")
            
            # 简单的加权逻辑：high的权重最高
            if high_count > 0:
                chapter_emotional_intensity = "high"
            elif low_count > medium_count * 2:  # low占明显多数
                chapter_emotional_intensity = "low"
            else:
                chapter_emotional_intensity = "medium"
        
        self.logger.info(f"  💓 本章情绪强度分析结果: {chapter_emotional_intensity} (投票: {len(intensity_votes)}个场景参与)")
        
        # 构建情绪强度指导
        intensity_guidance = intensity_guidance_map.get(chapter_emotional_intensity, intensity_guidance_map["medium"])
        
        # 如果场景有情感冲击描述，添加到指导中
        if emotional_focus_list:
            intensity_guidance += f"""
## 🎯 本章情感冲击要点
{chr(10).join(emotional_focus_list[:5])}  # 只显示前5个
"""
        
        return intensity_guidance
    
    def _build_scene_structure_string(self, pre_designed_scenes: List[Dict]) -> str:
        """构建场景结构字符串"""
        scene_position_map = {
            "opening": {"name": "开场场景", "function": "建立情境，引入本章核心冲突的起点，快速吸引读者。", "percentage": "15-20%"},
            "development1": {"name": "发展场景1 (Development 1)", "function": "推进情节，深化初始冲突，引入新信息或角色。", "percentage": "20-25%"},
            "development2": {"name": "发展场景2 (Development 2)", "function": "冲突升级，增加紧张感，为高潮做足铺垫。", "percentage": "20-25%"},
            "climax": {"name": "高潮场景", "function": "【本章重点】情感的集中爆发点！这是本章最关键的转折和最强烈的情感冲击所在。", "percentage": "15-20%"},
            "falling": {"name": "回落场景", "function": "处理高潮带来的直接后果，让情绪和节奏得到短暂缓和。", "percentage": "10-15%"},
            "ending": {"name": "结尾场景", "function": "收束本章内容，并设置一个强有力的悬念（钩子），引导读者追读下一章。", "percentage": "5-10%"}
        }
        
        scenes_str_parts = ["# 1. 写作蓝图：本章的六段式场景结构 (必须严格遵守)"]
        scenes_str_parts.append("你必须严格按照下面每个场景的功能定位和内容要点来创作，确保章节节奏张弛有度，高潮突出。")
        
        for scene in pre_designed_scenes:
            position_key = scene.get('position', 'unknown').lower()
            
            # 兼容 development1 和 development2
            if 'development' in position_key and position_key not in scene_position_map:
                if '1' in position_key: 
                    position_key = 'development1'
                elif '2' in position_key: 
                    position_key = 'development2'
                else:
                    position_key = 'development1'
            
            scene_info = scene_position_map.get(position_key, {
                "name": f"场景 ({scene.get('position', '未知')})", 
                "function": "按计划推进情节。", 
                "percentage": "N/A"
            })
            
            scenes_str_parts.append(f"\n## ### {scene_info['name']} - 预估篇幅占比: {scene_info['percentage']}")
            
            # 动态遍历场景字典，防止信息丢失
            key_display_map = {
                "name": "场景名称",
                "purpose": "核心目标",
                "key_actions": "关键动作/事件",
                "emotional_impact": "情感冲击",
                "dialogue_highlights": "关键对话高光",
                "conflict_point": "冲突焦点",
                "sensory_details": "感官细节",
                "transition_to_next": "场景过渡",
                "estimated_word_count": "预估字数",
                "contribution_to_chapter": "对本章贡献"
            }
            
            for key, value in scene.items():
                if key in ['position', 'type']:
                    continue
                
                display_key = key_display_map.get(key, key)
                
                if value:
                    if isinstance(value, list):
                        formatted_value = ', '.join(map(str, value))
                    else:
                        formatted_value = str(value)
                    
                    if formatted_value:
                        scenes_str_parts.append(f"- **{display_key}**: {formatted_value}")
        
        return "\n".join(scenes_str_parts)
    
    def _build_chapter_generation_prompt(self, chapter_params: Dict, chapter_number: int,
                                        intensity_guidance: str, scenes_input_str: str) -> str:
        """构建章节生成提示词"""
        character_info = chapter_params.get("character_info", "{}")
        # 解析分层角色信息，生成更友好的提示词格式
        character_prompt = self._format_character_info_for_prompt(character_info)

        # 获取上一章结尾状态，构建衔接要求
        previous_end_state = chapter_params.get("previous_end_state")
        transition_requirement = self._build_transition_requirement(previous_end_state, chapter_number)

        return f"""
## 章节创作指令 ##
为《{chapter_params.get('novel_title', '')}》创作第{chapter_number}章。

{intensity_guidance}

{scenes_input_str}

## 2. 背景与衔接
{transition_requirement}

- **本章核心目标**: {chapter_params.get("chapter_goal_from_plan", "推进主线情节")}
- **本章写作重点**: {chapter_params.get("writing_focus_from_plan", "保持节奏，制造悬念")}

## 3. 角色与世界观
- **世界观设定**: {chapter_params.get("worldview_info", "{}")}

### 角色信息（按重要性分层）
{character_prompt}

- **一致性铁律**: {chapter_params.get("consistency_guidance", "保持前后文一致")}

## 4. 风格指南
- **小说整体写作风格**: {json.dumps(chapter_params.get("writing_style_guide", {}), ensure_ascii=False)}

---

请你作为一名优秀的小说家，根据以上所有指令，直接创作出本章的完整内容。
你的任务是将【写作蓝图】中的六段式场景要点，流畅地、富有文采地串联成一篇完整的、高质量的小说章节。请特别注意每个场景的【功能定位】和【篇幅占比】，确保章节结构清晰，节奏感强。

**重要提醒**：
1. 请严格遵循上述【情绪强度指南】，确保本章的情感表达和节奏控制符合要求的强度级别。
2. {self._get_end_state_output_instruction(chapter_number)}
"""

    def _build_transition_requirement(self, previous_end_state, chapter_number: int) -> str:
        """构建衔接场景要求"""
        self.logger.info(f"  🔧 [衔接系统] 构建第{chapter_number}章衔接要求...")

        if not previous_end_state or chapter_number == 1:
            self.logger.info(f"  ℹ️ [衔接系统] 第一章或无上一章状态，使用默认衔接")
            return """- **前情提要**: 这是开篇第一章，需要建立故事基础。
- **衔接要求**: 直接开始故事，无需与上一章衔接。

## ⚠️ 时间铁律
- **第一章起始时间**: 建立故事的开端时间点
- **本章任务**: 完成第一章的完整叙事弧"""

        # ============ 核心修正：添加时间铁律警告 ============
        # 根据上一章结尾状态构建衔接要求
        hint = previous_end_state.next_transition_hint or "自然衔接"
        event_status = "已完结" if previous_end_state.event_concluded else "进行中"

        requirement = f"""- **上一章结尾状态**:
  - 时间: {previous_end_state.time_point}
  - 地点: {previous_end_state.location}
  - 氛围: {previous_end_state.atmosphere}
  - 当前事件: {previous_end_state.current_event}（{event_status}）"""

        if previous_end_state.characters:
            requirement += "\n  - 角色状态:"
            for char in previous_end_state.characters[:3]:  # 最多显示3个角色
                char_info = f"    · {char.get('name', '')}"
                if char.get('action'):
                    char_info += f": {char['action']}"
                if char.get('emotion'):
                    char_info += f"（{char['emotion']}）"
                requirement += f"\n{char_info}"

        if previous_end_state.hook:
            requirement += f"\n  - 上一章悬念: {previous_end_state.hook}"

        requirement += f"\n- **衔接建议**: {hint}"

        # 根据事件状态给出具体衔接指导
        if not previous_end_state.event_concluded:
            requirement += "\n- **衔接方式**: 【直接继续】上一章的动作/对话，保持紧迫感，无缝连接。"
        elif hint and "时间" in hint:
            requirement += "\n- **衔接方式**: 【时间跳跃】简述时间流逝和场景变化，然后开始新事件。"
        else:
            requirement += "\n- **衔接方式**: 【事件切换】简短收尾上一事件，自然过渡到本章新事件。"

        # ============ 新增：时间铁律（强约束） ============
        timeline_warning = f"""

## ⚠️⚠️⚠️ 时间铁律（绝对禁止违反）⚠️⚠️⚠️

**第{chapter_number}章必须在第{chapter_number-1}章结束之后继续，严禁倒带重写已发生过的事件！**

- 上一章结束于: {previous_end_state.time_point}
- 上一章结束地点: {previous_end_state.location}
- 上一章最终状态: {previous_end_state.current_event}

**绝对禁止的行为**:
1. ❌ 不要从 '{previous_end_state.time_point}' 之前的时间点重新开始
2. ❌ 不要重写第{chapter_number-1}章已经写过的场景（如"林擎天准备打叶辰"等）
3. ❌ 不要让已发生的事件"重来一遍"

**正确做法**:
1. ✅ 本章必须从 '{previous_end_state.time_point}' 之后的时间点开始
2. ✅ 如果是事件切换，用1-2句话简短过渡，然后开始新事件
3. ✅ 如果是时间跳跃，明确说明时间流逝（如"片刻之后""次日清晨"等）

**记住**: 读者已经看过第{chapter_number-1}章了，重写相同内容会让他们觉得你在水字数！
"""

        return requirement + timeline_warning

    def _get_end_state_output_instruction(self, chapter_number: int) -> str:
        """获取结尾状态输出指令"""
        return f"""在章节内容结束后，请按以下JSON格式输出本章的【结尾状态报告】：

```json
{{
  "chapter_number": {chapter_number},
  "time_point": "本章结束时的具体时间点（如：次日清晨、当晚子时、三日后）",
  "location": "主要角色所在的地点",
  "atmosphere": "氛围基调（紧张/轻松/压抑/欢快/平静等）",
  "characters": [
    {{"name": "角色名", "location": "位置", "action": "正在做什么", "emotion": "情绪状态"}}
  ],
  "current_event": "当前事件名称",
  "event_concluded": true/false,
  "unresolved": ["未解决的悬念"],
  "hook": "结尾悬念",
  "next_transition_hint": "建议下一章如何衔接"
}}
```

**注意**: 结尾状态报告必须放在章节内容之后，用于下一章的衔接。"""

    def _extract_and_save_end_state(self, content: str, chapter_number: int, novel_data: Dict) -> Optional[Dict]:
        """从生成的内容中提取并保存结尾状态

        多层级降级策略：
        1. 尝试从内容中提取完整的JSON格式结尾状态
        2. 使用模式匹配提取关键信息（时间、地点、氛围）
        3. 使用智能默认值（基于章节内容分析）
        """
        self.logger.info(f"  🔍 [衔接系统] 开始提取第{chapter_number}章结尾状态...")
        import re

        # 尝试从内容中提取JSON格式的结尾状态
        end_state = None

        # 模式1: 查找 ```json ... ``` 代码块
        json_pattern = r'```json\s*(\{.*?\n.*?chapter_number.*?\})\s*```'
        match = re.search(json_pattern, content, re.DOTALL)
        if match:
            try:
                import json
                end_state = json.loads(match.group(1))
                self.logger.info(f"  ✅ [衔接系统] 从JSON代码块中提取到结尾状态")
            except json.JSONDecodeError as e:
                self.logger.warning(f"  ⚠️ [衔接系统] JSON解析失败: {e}")

        # 模式2: 查找没有代码块包裹的JSON对象
        if not end_state:
            json_pattern2 = r'\{\s*"chapter_number"\s*:\s*' + str(chapter_number) + r'.*?\n.*?\n.*?\}'
            match2 = re.search(json_pattern2, content, re.DOTALL)
            if match2:
                try:
                    import json
                    # 尝试扩展匹配范围，获取完整JSON
                    start = match2.start()
                    # 向后查找完整的JSON对象
                    brace_count = 0
                    i = start
                    while i < len(content):
                        if content[i] == '{':
                            brace_count += 1
                        elif content[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_state = json.loads(content[start:i+1])
                                self.logger.info(f"  ✅ [衔接系统] 从内容中提取到结尾状态")
                                break
                        i += 1
                except (json.JSONDecodeError, ValueError) as e:
                    self.logger.warning(f"  ⚠️ [衔接系统] 模式2解析失败: {e}")

        # ============ 🔥 P0-1修复：降级策略3 - AI专门提取结尾状态 ============
        if not end_state:
            self.logger.warning(f"  ⚠️ [衔接系统] JSON提取失败，使用AI专门提取结尾状态...")
            end_state = self._extract_end_state_by_ai(content, chapter_number, novel_data)

        # ============ 🔥 P0-1修复：降级策略4 - 增强模式匹配提取 ============
        if not end_state:
            self.logger.warning(f"  ⚠️ [衔接系统] AI提取失败，尝试增强模式匹配提取...")
            end_state = self._extract_end_state_by_enhanced_pattern_matching(content, chapter_number)

        # ============ 🔥 P0-1修复：降级策略5 - 智能内容分析默认值 ============
        if not end_state:
            self.logger.warning(f"  ⚠️ [衔接系统] 模式匹配也失败，使用智能内容分析...")
            end_state = self._generate_intelligent_default_end_state(content, chapter_number, novel_data)

        # ============ 新增：记录时间线信息 ============
        if end_state:
            try:
                self._ensure_timeline_tracker_initialized(novel_data)
                if self.cg._timeline_tracker:
                    from src.core.content_generation.chapter_state_manager import SceneTimelineInfo
                    timeline_info = SceneTimelineInfo(
                        chapter_number=chapter_number,
                        start_time=self._get_chapter_start_time(novel_data, chapter_number),
                        end_time=end_state.get("time_point", "未知"),
                        key_events=end_state.get("unresolved", [])[:3],
                        scene_summary=f"{end_state.get('location', '')} - {end_state.get('atmosphere', '')}"
                    )
                    self.cg._timeline_tracker.record_chapter_timeline(timeline_info)
                    self.logger.info(f"  📍 [时间线追踪] 第{chapter_number}章时间线已记录")
            except Exception as e:
                self.logger.warning(f"  ⚠️ [时间线追踪] 记录时间线失败: {e}")

        if not end_state:
            self.logger.warning(f"  ⚠️ [衔接系统] 所有提取方法均失败，返回None")
            return None

        # 保存结尾状态
        try:
            self._ensure_chapter_state_manager_initialized(novel_data)
            if self.cg._chapter_state_manager:
                from src.core.content_generation.chapter_state_manager import ChapterEndState
                chapter_end_state = ChapterEndState.from_dict(end_state)
                self.cg._chapter_state_manager.set_end_state(chapter_end_state)
                self.logger.info(f"  📌 [衔接系统] 第{chapter_number}章结尾状态已保存到管理器")
                return end_state
        except Exception as e:
            self.logger.warning(f"  ⚠️ [衔接系统] 保存结尾状态失败: {e}")

        return end_state

    # ========================================================================
    # P0-1 修复：新增AI专门提取结尾状态
    # ========================================================================

    def _extract_end_state_by_ai(self, content: str, chapter_number: int, novel_data: Dict) -> Optional[Dict]:
        """
        使用AI专门提取章节结尾状态

        当JSON解析失败时，使用专门的AI调用来分析章节内容并提取结尾状态。
        这比模式匹配更可靠，比依赖生成内容中的JSON更稳定。
        """
        try:
            # 获取上一章的结尾状态作为上下文
            previous_end_state = None
            if hasattr(self.cg, '_chapter_state_manager') and self.cg._chapter_state_manager:
                previous_end_state = self.cg._chapter_state_manager.get_previous_end_state(chapter_number)

            # 构建上下文
            prev_context = ""
            if previous_end_state:
                prev_context = f"""
上一章结束时：
- 时间：{previous_end_state.time_point}
- 地点：{previous_end_state.location}
- 事件：{previous_end_state.current_event}
"""

            # 取章节末尾1000字作为分析样本
            sample = content[-1000:] if len(content) > 1000 else content
            # 清理可能的markdown代码块标记
            sample = re.sub(r'```[a-z]*\n?', '', sample)

            prompt = f"""你是小说结尾状态分析专家。请仔细分析以下章节内容的结尾部分，提取关键的结尾状态信息。

{prev_context}

## 章节内容末尾（约1000字）：
{sample}

## 任务：
请分析上述章节结尾，提取以下信息并以JSON格式返回：

1. **time_point**: 本章结束时的具体时间点（如：次日清晨、当晚子时、三日后、片刻后等）
2. **location**: 主要角色所在的地点（具体到房间或场所）
3. **atmosphere**: 氛围基调（紧张/轻松/压抑/欢快/平静/期待/悬疑等）
4. **current_event**: 当前事件名称（简短描述）
5. **event_concluded**: 本章事件是否完结（true/false）
6. **unresolved**: 未解决的悬念或冲突列表（1-3个）
7. **hook**: 结尾悬念或钩子（吸引读者继续阅读的点）

请严格按照以下JSON格式返回：
```json
{{
  "time_point": "时间点",
  "location": "地点",
  "atmosphere": "氛围",
  "current_event": "事件名称",
  "event_concluded": true,
  "unresolved": ["悬念1", "悬念2"],
  "hook": "结尾钩子"
}}
```

注意：
- 时间点要具体，不要用"未知"或"结束"
- 地点要明确，从内容中推断实际位置
- 氛围要根据结尾的情感基调判断
- 如果事件明显未完，event_concluded设为false
"""

            result = self.api_client.generate_content_with_retry(
                "end_state_extraction",
                prompt,
                purpose=f"提取第{chapter_number}章结尾状态",
                temperature=0.3  # 使用较低温度确保提取稳定
            )

            if result and isinstance(result, dict):
                # 验证必需字段
                required_fields = ["time_point", "location", "atmosphere"]
                missing = [f for f in required_fields if not result.get(f)]
                if missing:
                    self.logger.warning(f"  ⚠️ AI提取缺少必需字段: {missing}")
                    # 补充缺失字段
                    if "time_point" in missing:
                        result["time_point"] = self._infer_time_from_content(sample)
                    if "location" in missing:
                        result["location"] = self._infer_location_from_content(sample)
                    if "atmosphere" in missing:
                        result["atmosphere"] = self._infer_atmosphere_from_content(sample)

                result.setdefault("chapter_number", chapter_number)
                result.setdefault("event_concluded", True)
                result.setdefault("unresolved", [])
                result.setdefault("hook", "")
                result.setdefault("characters", [])
                result.setdefault("current_event", f"第{chapter_number}章内容")

                self.logger.info(f"  ✅ [衔接系统] AI专门提取成功: {result.get('time_point')} @ {result.get('location')}")
                return result
            else:
                self.logger.warning(f"  ⚠️ [衔接系统] AI提取返回无效结果")
                return None

        except Exception as e:
            self.logger.warning(f"  ⚠️ [衔接系统] AI提取异常: {e}")
            return None

    def _extract_end_state_by_enhanced_pattern_matching(self, content: str, chapter_number: int) -> Optional[Dict]:
        """
        增强的模式匹配提取结尾状态

        相比原版增加了：
        - 更多的时间关键词识别
        - 更智能的地点推断
        - 角色状态提取
        - 事件状态判断
        """
        import re

        # 取章节末尾800字作为分析样本
        sample = content[-800:] if len(content) > 800 else content

        # ========== 增强的时间关键词映射 ==========
        time_keywords = {
            # 基础时间
            '清晨': '清晨', '黎明': '黎明', '破晓': '破晓', '东方既白': '清晨',
            '上午': '上午', '中午': '中午', '午时': '中午', '午后': '午后',
            '下午': '下午', '傍晚': '傍晚', '黄昏': '黄昏', '日落': '傍晚',
            '夜晚': '夜晚', '夜间': '夜间', '深夜': '深夜', '午夜': '午夜',
            '子时': '子时',

            # 时间跳跃
            '次日': '次日清晨', '第二天': '次日', '隔日': '次日',
            '三日后': '三日后', '三天后': '三日后', '数日后': '数日后',
            '半月后': '半月后', '半个月后': '半月后',
            '片刻后': '片刻后', '片刻': '片刻', '随即': '随即', '当即': '当即',
            '不久': '不久', '良久': '良久',

            # 修仙/玄幻特定时间
            '一炷香后': '一炷香后', '半柱香': '半柱香',
            '茶香散尽': '茶香散尽', '一盏茶': '一盏茶',

            # 相对时间
            '之后': '之后', '后来': '后来', '这时': '这时',
        }

        # 查找时间关键词（优先匹配更长的关键词）
        time_point = "未知"
        # 按长度排序，优先匹配长的
        sorted_keywords = sorted(time_keywords.items(), key=lambda x: -len(x[0]))
        for keyword, value in sorted_keywords:
            if keyword in sample:
                time_point = value
                # 尝试获取更完整的时间表达
                time_pattern = rf'[^，。]{0,10}{keyword}[^，。]{{0,10}}'
                time_match = re.search(time_pattern, sample)
                if time_match:
                    time_point = time_match.group(0).strip()
                break

        # ========== 增强的地点提取 ==========
        location_patterns = [
            # 建筑物类型
            r'([^，。]{2,15})(殿|阁|楼|台|亭|轩|榭|堂|厅)(中|内|之上|之中)',
            r'([^，。]{2,10})(室|房|屋|舍)(中|内|里)',
            # 自然场所
            r'([^，。]{2,15})(山|河|林|峰|谷|地|崖|洞|湖|海|江)(中|内|之上|旁)',
            # 特殊场所
            r'([^，。]{2,15})(广场|街道|山林|密室|书房|卧室|演武场|练功房|庭院)',
            # 介词引导的地点
            r'(在|于|位于)([^，。]{2,20})',
        ]
        location = "未知"
        for pattern in location_patterns:
            match = re.search(pattern, sample)
            if match:
                # 提取地点部分
                loc_text = match.group(0)
                # 移除介词
                loc_text = re.sub(r'^(在|于|位于)', '', loc_text)
                # 限制长度
                location = loc_text[:20].strip()
                break

        # ========== 增强的氛围推断 ==========
        atmosphere_keywords = {
            '紧张': ['杀意', '战斗', '逃亡', '追击', '危机', '危险', '紧绷', '警惕', '对峙'],
            '轻松': ['欢笑', '闲聊', '宁静', '安详', '温馨', '惬意', '轻松'],
            '压抑': ['沉默', '凝重', '沉重', '压抑', '阴沉', '窒息', '阴霾'],
            '欢快': ['喜悦', '欢快', '兴奋', '激动', '开心', '雀跃'],
            '悬疑': ['疑惑', '不解', '疑惑', '神秘', '诡异', '蹊跷'],
            '期待': ['期待', '盼望', '渴望', '向往'],
        }
        atmosphere = "平静"
        atmosphere_scores = {}
        for mood, keywords in atmosphere_keywords.items():
            score = sum(1 for kw in keywords if kw in sample)
            if score > 0:
                atmosphere_scores[mood] = score
        if atmosphere_scores:
            atmosphere = max(atmosphere_scores, key=atmosphere_scores.get)

        # ========== 尝试提取事件状态 ==========
        event_concluded = True
        if any(kw in sample for kw in ['未完', '未完待续', '还在继续', '尚未结束', '正要']):
            event_concluded = False
        if any(kw in sample for kw in ['终于', '完结', '结束', '完成', '落幕']):
            event_concluded = True

        # ========== 尝试提取悬念 ==========
        hook_patterns = [
            r'然而([^，。]{5,30})',
            r'就在([^，。]{5,30})',
            r'突然([^，。]{5,30})',
            r'原来([^，。]{5,30})',
        ]
        hook = ""
        for pattern in hook_patterns:
            match = re.search(pattern, sample[-300:] if len(sample) > 300 else sample)
            if match:
                hook = match.group(0)[:50]
                break

        # 构建结尾状态
        end_state = {
            "chapter_number": chapter_number,
            "time_point": time_point,
            "location": location,
            "atmosphere": atmosphere,
            "characters": [],
            "current_event": f"第{chapter_number}章内容",
            "event_concluded": event_concluded,
            "unresolved": [hook] if hook else [],
            "hook": hook,
            "next_transition_hint": "自然过渡"
        }

        self.logger.info(f"  ✅ [衔接系统] 增强模式匹配提取: 时间={time_point}, 地点={location}, 氛围={atmosphere}")
        return end_state

    # 辅助方法：从内容推断时间
    def _infer_time_from_content(self, content: str) -> str:
        """当AI提取失败时，从内容推断时间"""
        time_patterns = [
            (r'(次日|第二天|隔日)', '次日清晨'),
            (r'(清晨|黎明|破晓)', '清晨'),
            (r'(中午|午时)', '中午'),
            (r'(傍晚|黄昏|日落)', '傍晚'),
            (r'(夜晚|深夜|午夜)', '夜晚'),
            (r'(片刻|随即|当即|不久)', '片刻后'),
        ]
        import re
        for pattern, default in time_patterns:
            if re.search(pattern, content):
                return default
        return "随后"

    # 辅助方法：从内容推断地点
    def _infer_location_from_content(self, content: str) -> str:
        """当AI提取失败时，从内容推断地点"""
        import re
        location_patterns = [
            r'([^，。]{2,15})(殿|阁|楼|台|亭|轩|榭)',
            r'([^，。]{2,10})(室|房|屋)',
            r'([^，。]{2,15})(山|林|峰|谷)',
        ]
        for pattern in location_patterns:
            match = re.search(pattern, content)
            if match:
                return match.group(0)[:20]
        return "某处"

    # 辅助方法：从内容推断氛围
    def _infer_atmosphere_from_content(self, content: str) -> str:
        """当AI提取失败时，从内容推断氛围"""
        if any(kw in content for kw in ['战斗', '危机', '危险']):
            return "紧张"
        elif any(kw in content for kw in ['欢笑', '喜悦', '温馨']):
            return "轻松"
        elif any(kw in content for kw in ['沉默', '凝重', '压抑']):
            return "压抑"
        return "平静"

    def _extract_end_state_by_pattern_matching(self, content: str, chapter_number: int) -> Optional[Dict]:
        """
        使用模式匹配从内容中提取结尾状态信息

        尝试提取：
        - 时间点（清晨、傍晚、次日等）
        - 地点（从内容末尾提取）
        - 氛围（从关键词推断）
        """
        import re

        # 提取内容最后500字作为分析样本
        sample = content[-500:] if len(content) > 500 else content

        # 时间关键词映射
        time_keywords = {
            '清晨': '清晨', '黎明': '黎明', '破晓': '破晓',
            '上午': '上午', '中午': '中午', '午后': '午后',
            '下午': '下午', '傍晚': '傍晚', '黄昏': '黄昏',
            '夜晚': '夜晚', '夜间': '夜间', '深夜': '深夜',
            '子时': '子时', '午夜': '午夜',
            '次日': '次日清晨', '第二天': '次日',
            '三天后': '三天后', '数日后': '数日后',
            '片刻后': '片刻后', '片刻': '片刻', '随即': '随即'
        }

        # 查找时间关键词
        time_point = "未知"
        for keyword, value in time_keywords.items():
            if keyword in sample:
                time_point = value
                break

        # 尝试提取地点（查找常见的地点描述模式）
        location_patterns = [
            r'(在|于|位于)([^，。]{2,10})(室|厅|殿|阁|山|河|林|峰|谷|地|城|镇|村|家)',
            r'([^，。]{2,15})(殿|阁|楼|台|亭|轩|榭)(中|内|之上)',
            r'([^，。]{2,15})(广场|街道|山林|洞穴|密室|书房|卧室)'
        ]
        location = "未知"
        for pattern in location_patterns:
            match = re.search(pattern, sample)
            if match:
                location = match.group(0)[:20]
                break

        # 推断氛围
        atmosphere_keywords = {
            '紧张': ['杀意', '战斗', '逃亡', '追击', '危机', '危险'],
            '轻松': ['欢笑', '闲聊', '宁静', '安详', '温馨'],
            '压抑': ['沉默', '凝重', '沉重', '压抑', '阴沉'],
            '欢快': ['喜悦', '欢快', '兴奋', '激动', '开心']
        }
        atmosphere = "平静"
        for mood, keywords in atmosphere_keywords.items():
            if any(kw in sample for kw in keywords):
                atmosphere = mood
                break

        # 构建结尾状态
        end_state = {
            "chapter_number": chapter_number,
            "time_point": time_point,
            "location": location,
            "atmosphere": atmosphere,
            "characters": [],
            "current_event": "章节内容",
            "event_concluded": True,
            "unresolved": [],
            "hook": "",
            "next_transition_hint": "自然过渡"
        }

        self.logger.info(f"  ✅ [衔接系统] 模式匹配提取成功: 时间={time_point}, 地点={location}, 氛围={atmosphere}")
        return end_state

    def _generate_intelligent_default_end_state(self, content: str, chapter_number: int, novel_data: Dict) -> Dict:
        """
        生成智能的默认结尾状态（P0-1修复：增强内容分析）

        基于章节内容分析，而不是使用固定默认值
        """
        import re

        # 获取上一章的结束时间
        prev_time = self._get_chapter_start_time(novel_data, chapter_number)
        prev_end_state = None
        if hasattr(self.cg, '_chapter_state_manager') and self.cg._chapter_state_manager:
            prev_end_state = self.cg._chapter_state_manager.get_previous_end_state(chapter_number)

        # ============ 智能推断时间点 ============
        # 分析章节末尾内容
        sample = content[-500:] if len(content) > 500 else content

        # 时间推断逻辑
        inferred_time = None
        time_indicators = [
            # (模式, 时间推断规则)
            (r'(次日|第二天|隔日)', '次日'),
            (r'(三日后|三天后|数日后)', '三日后'),
            (r'(片刻|随即|当即)', '片刻后'),
            (r'(一炷香|半柱香)', '一炷香后'),
        ]

        for pattern, time_hint in time_indicators:
            if re.search(pattern, sample):
                inferred_time = time_hint
                break

        # 根据字数推断时间跨度
        word_count = len(content)
        if inferred_time:
            time_point = inferred_time
        elif word_count > 3000:
            # 长章节可能跨越较长时段
            time_point = f"{prev_time}之后" if prev_time and prev_time != "故事开始" else "稍后"
        else:
            time_point = prev_time if prev_time else "随后"

        # ============ 智能推断地点 ============
        inferred_location = self._infer_location_from_content(sample)
        # 如果上一章有地点，且当前地点未知，可能还在同一地点
        if inferred_location == "某处" and prev_end_state and prev_end_state.location:
            inferred_location = prev_end_state.location

        # ============ 智能推断氛围 ============
        inferred_atmosphere = self._infer_atmosphere_from_content(sample)

        # ============ 智能推断事件状态 ============
        event_concluded = True
        if any(kw in sample for kw in ['未完', '还在继续', '尚未', '正要', '即将']):
            event_concluded = False

        # ============ 尝试提取悬念 ============
        hook = ""
        hook_patterns = [
            r'然而([^，。]{3,20})',
            r'就在([^，。]{3,20})',
            r'突然([^，。]{3,20})',
        ]
        for pattern in hook_patterns:
            match = re.search(pattern, sample[-200:] if len(sample) > 200 else sample)
            if match:
                hook = match.group(0).strip()
                break

        end_state = {
            "chapter_number": chapter_number,
            "time_point": time_point,
            "location": inferred_location,
            "atmosphere": inferred_atmosphere,
            "characters": [],
            "current_event": f"第{chapter_number}章内容",
            "event_concluded": event_concluded,
            "unresolved": [hook] if hook else [],
            "hook": hook,
            "next_transition_hint": "自然过渡到下一章"
        }

        self.logger.info(f"  ✅ [衔接系统] 智能分析默认值: 时间={time_point}, 地点={inferred_location}, 氛围={inferred_atmosphere}")
        return end_state

    def _ensure_timeline_tracker_initialized(self, novel_data: Dict):
        """确保 SceneTimelineTracker 已初始化"""
        if not hasattr(self.cg, '_timeline_tracker') or self.cg._timeline_tracker is None:
            self.cg._ensure_timeline_tracker_initialized(novel_data)

    def _ensure_chapter_state_manager_initialized(self, novel_data: Dict):
        """确保 ChapterStateManager 已初始化（委托给ContentGenerator）"""
        self.cg._ensure_chapter_state_manager_initialized(novel_data)

    def _get_chapter_start_time(self, novel_data: Dict, chapter_number: int) -> str:
        """获取章节的开始时间"""
        # 如果是第一章，返回默认值
        if chapter_number == 1:
            return "故事开始"

        # 尝试从时间线追踪器获取上一章的结束时间
        if hasattr(self.cg, '_timeline_tracker') and self.cg._timeline_tracker:
            prev_timeline = self.cg._timeline_tracker.get_previous_timeline(chapter_number)
            if prev_timeline:
                return prev_timeline.end_time

        # 从上一章的结尾状态获取
        if hasattr(self.cg, '_chapter_state_manager') and self.cg._chapter_state_manager:
            prev_end_state = self.cg._chapter_state_manager.get_previous_end_state(chapter_number)
            if prev_end_state:
                return prev_end_state.time_point

        return "未知"

    def _format_character_info_for_prompt(self, character_info: str) -> str:
        """
        将分层的角色信息格式化为提示词友好的文本（P2修复：增强角色状态传递）

        Args:
            character_info: JSON字符串格式的分层角色信息

        Returns:
            格式化后的角色信息文本
        """
        try:
            import json
            char_data = json.loads(character_info)

            parts = []

            # 主角
            protagonist = char_data.get("protagonist", {})
            if protagonist:
                name = protagonist.get("name", "主角")
                parts.append(f"**【主角】{name}**")
                # P2修复：提供更结构化的主角信息
                parts.append(self._format_character_detail(protagonist, is_protagonist=True))

            # 前5个核心配角（从3个增加到5个）
            key_supporting = char_data.get("key_supporting", [])
            if key_supporting:
                parts.append(f"\n**【核心配角】（前{len(key_supporting)}个，完整信息）**")
                for char in key_supporting:
                    parts.append(f"- **{char.get('name', '未知')}**")
                    parts.append(f"  {self._format_character_detail(char)}")

            # 场景中提到的角色
            mentioned = char_data.get("mentioned_characters", [])
            if mentioned:
                parts.append(f"\n**【本章涉及角色】（场景中提及，完整信息）**")
                for char in mentioned:
                    parts.append(f"- **{char.get('name', '未知')}**")
                    parts.append(f"  {self._format_character_detail(char)}")

            # P2修复：其他角色 - 提供更完整的状态信息
            others = char_data.get("other_characters", [])
            if others:
                parts.append(f"\n**【其他角色】（共{len(others)}个，增强信息）**")
                for char in others[:10]:  # 最多显示10个，避免提示词过长
                    name = char.get('name', '未知')
                    role = char.get('role', '未知角色')
                    tag = char.get('tag', '')
                    core_traits = char.get('core_traits', '')

                    parts.append(f"- **{name}** ({role})")
                    if tag:
                        parts.append(f"  标签: {tag}")
                    if core_traits:
                        parts.append(f"  核心特质: {core_traits}")

                    # P2修复：新增：提供当前状态信息
                    current_status = char.get('current_status', {})
                    if current_status:
                        status_parts = []
                        if current_status.get('location'):
                            status_parts.append(f"位置: {current_status['location']}")
                        if current_status.get('emotion'):
                            status_parts.append(f"情绪: {current_status['emotion']}")
                        if current_status.get('action'):
                            status_parts.append(f"动作: {current_status['action']}")
                        if status_parts:
                            parts.append(f"  当前状态: {'; '.join(status_parts)}")

                    # P2修复：新增：提供关系信息
                    relationships = char.get('relationships', {})
                    if relationships:
                        rel_parts = []
                        for target, rel_type in list(relationships.items())[:3]:
                            rel_parts.append(f"{target}={rel_type}")
                        if rel_parts:
                            parts.append(f"  关系: {', '.join(rel_parts)}")

                if len(others) > 10:
                    parts.append(f"... 还有 {len(others) - 10} 个其他角色")

            return "\n".join(parts) if parts else "暂无角色信息"

        except json.JSONDecodeError:
            # 如果解析失败，直接返回原始信息
            return character_info
        except Exception as e:
            return f"角色信息解析错误: {str(e)}"

    def _format_character_detail(self, char: Dict, is_protagonist: bool = False) -> str:
        """
        格式化单个角色的详细信息（P2新增辅助方法）

        Args:
            char: 角色字典
            is_protagonist: 是否是主角

        Returns:
            格式化后的角色信息字符串
        """
        import json

        # 核心信息
        details = []
        if char.get('age'):
            details.append(f"年龄: {char['age']}")
        if char.get('personality'):
            details.append(f"性格: {char['personality']}")
        if char.get('appearance'):
            details.append(f"外貌: {char['appearance'][:50]}...")  # 限制长度
        if char.get('identity'):
            details.append(f"身份: {char['identity']}")

        # 主角额外信息
        if is_protagonist:
            if char.get('background'):
                details.append(f"背景: {char['background'][:80]}...")
            if char.get('goal'):
                details.append(f"目标: {char['goal']}")

        # 当前状态
        if char.get('current_location'):
            details.append(f"当前位置: {char['current_location']}")
        if char.get('current_emotion'):
            details.append(f"当前情绪: {char['current_emotion']}")

        # 关系
        relationships = char.get('relationships', {})
        if relationships:
            rel_list = [f"{k}={v}" for k, v in list(relationships.items())[:3]]
            details.append(f"关系: {', '.join(rel_list)}")

        # 能力/修为
        if char.get('cultivation_level'):
            details.append(f"修为: {char['cultivation_level']}")
        if char.get('abilities'):
            abilities = char['abilities']
            if isinstance(abilities, list) and abilities:
                details.append(f"能力: {', '.join(abilities[:3])}")

        if details:
            return " | ".join(details)
        else:
            # 如果没有提取到任何信息，返回完整JSON
            return json.dumps(char, ensure_ascii=False)