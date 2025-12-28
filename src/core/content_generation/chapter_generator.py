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
                    self.logger.warn(f"⚠️ 质量评估失败，使用默认评分")
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
                
                # 根据质量决定是否优化
                optimize_needed, optimize_reason = self.cg._should_optimize_based_on_config(assessment)
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
                        self.logger.warn(f"  ⚠️ AI开场白生成异常，使用备用模板: {e}")
                
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
                    self.logger.warn(f"  ⚠️ 第{retry+1}次优化失败，返回空结果")
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
            self.logger.warn(f"  ⚠️ 所有优化尝试均失败，保持原内容")
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
                self.logger.warn(f"  ⚠️ 第{attempt + 1}次尝试失败或字数不足 ({word_count}字)。")
        
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
        return f"""
## 章节创作指令 ##
为《{chapter_params.get('novel_title', '')}》创作第{chapter_number}章。

{intensity_guidance}

{scenes_input_str}

## 2. 背景与衔接
- **前情提要**: {chapter_params.get("previous_chapters_summary", "无")}
- **本章核心目标**: {chapter_params.get("chapter_goal_from_plan", "推进主线情节")}
- **本章写作重点**: {chapter_params.get("writing_focus_from_plan", "保持节奏，制造悬念")}

## 3. 角色与世界观
- **世界观设定**: {chapter_params.get("worldview_info", "{}")}
- **人物设定**: {chapter_params.get("character_info", "{}")}
- **一致性铁律**: {chapter_params.get("consistency_guidance", "保持前后文一致")}

## 4. 风格指南
- **小说整体写作风格**: {json.dumps(chapter_params.get("writing_style_guide", {}), ensure_ascii=False)}

---

请你作为一名优秀的小说家，根据以上所有指令，直接创作出本章的完整内容。
你的任务是将【写作蓝图】中的六段式场景要点，流畅地、富有文采地串联成一篇完整的、高质量的小说章节。请特别注意每个场景的【功能定位】和【篇幅占比】，确保章节结构清晰，节奏感强。

**重要提醒**：请严格遵循上述【情绪强度指南】，确保本章的情感表达和节奏控制符合要求的强度级别。
"""