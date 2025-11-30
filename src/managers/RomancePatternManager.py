# RomancePatternManager.py
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
from typing import Dict, List, Optional
from src.utils.logger import get_logger

class RomancePatternManager:
    """情感模式管理器 - 负责情感模式分析、特殊事件生成、情感填充等"""
    
    def __init__(self, stage_plan_manager):
        self.logger = get_logger("RomancePatternManager")
        self.stage_plan_manager = stage_plan_manager
        self.generator = stage_plan_manager.generator

    def analyze_romance_pattern(self, creative_seed: str, novel_synopsis: str) -> Dict:
        """分析小说的情感模式"""
        analysis_prompt = f"""
    请分析以下小说的情感模式：

    创意种子：{creative_seed}
    小说简介：{novel_synopsis}

    请分析：
    1. 这是多女主还是单女主模式？
    2. 情感风格偏向擦边暧昧还是纯爱深情？
    3. 主要女性角色类型有哪些？
    4. 建议的情感事件密度和风格

    请返回JSON格式的分析结果：
    {{
        "romance_type": "harem|single|mixed",
        "emotional_style": "teasing|pure_love|balanced", 
        "female_characters": ["角色1", "角色2", ...],
        "recommended_density": "high|medium|low",
        "style_description": "情感风格描述",
        "filler_focus": "在空窗期应该重点描写的内容"
    }}
    """
        
        analysis_result = self.generator.api_client.generate_content_with_retry(
            "romance_pattern_analysis",
            analysis_prompt,
            purpose="分析小说情感模式"
        )
        
        return analysis_result or {
            "romance_type": "unknown",
            "emotional_style": "balanced",
            "female_characters": ["默认女性角色"],
            "recommended_density": "medium",
            "style_description": "标准情感发展",
            "filler_focus": "角色互动和情感发展"
        }

    def get_romance_pattern(self, creative_seed: str, novel_synopsis: str) -> Dict:
        """获取情感模式（带缓存）"""
        # 首先尝试从novel_data获取
        if "romance_pattern" in self.generator.novel_data:
            return self.generator.novel_data["romance_pattern"]
        
        # 如果没有，进行分析
        self.logger.info("  💞 分析全书情感模式...")
        romance_pattern = self.analyze_romance_pattern(creative_seed, novel_synopsis)
        self.generator.novel_data["romance_pattern"] = romance_pattern
        self.logger.info(f"  ✅ 情感模式分析完成: {romance_pattern['romance_type']}-{romance_pattern['emotional_style']}")
        
        return romance_pattern

    def get_special_event_guidance(self, chapter_number: int) -> Dict:
        """获取指定章节的特殊事件指导"""
        current_stage = self.stage_plan_manager._get_current_stage(chapter_number)
        if not current_stage:
            return {}
        
        writing_plan = self.stage_plan_manager.get_stage_writing_plan_by_name(current_stage)
        if not writing_plan:
            return {}
        
        # 正确处理嵌套结构
        if "stage_writing_plan" in writing_plan:
            event_system = writing_plan["stage_writing_plan"].get("event_system", {})
        else:
            event_system = writing_plan.get("event_system", {})
        
        # 查找当前章节的特殊事件
        special_events = []
        
        for event in event_system.get("special_events", []):
            if (event.get("type") == "特殊事件" and 
                event.get("subtype") == "情感填充" and 
                event.get("chapter") == chapter_number):
                special_events.append(event)
        
        if special_events:
            return {
                "has_special_event": True,
                "special_events": special_events,
                "writing_focus": "本章包含情感特殊事件，重点描写情感内容",
                "purpose": "在主线间隔期保持读者兴趣，推进情感发展",
                "event_type": "情感填充特殊事件"
            }
        else:
            return {
                "has_special_event": False,
                "suggestion": "本章无专门特殊事件，可适当添加情感互动"
            }

    def analyze_romance_development_potential(self, stage_name: str, romance_pattern: Dict) -> Dict:
        """分析阶段的情感发展潜力"""
        self.logger.info(f"  💕 分析{stage_name}情感发展潜力...")
        
        analysis_result = {
            "stage_name": stage_name,
            "romance_type": romance_pattern.get("romance_type", "unknown"),
            "emotional_style": romance_pattern.get("emotional_style", "balanced"),
            "development_potential": "中等",
            "recommended_focus": [],
            "relationship_milestones": [],
            "emotional_intensity_target": "适中"
        }
        
        # 基于阶段和情感模式分析
        if stage_name == "opening_stage":
            analysis_result["recommended_focus"].extend([
                "建立主角与主要女性角色的初次印象",
                "设置情感冲突和吸引力基础",
                "铺垫多角关系可能性（如适用）"
            ])
            analysis_result["relationship_milestones"].append("初次相遇或重要互动")
            analysis_result["emotional_intensity_target"] = "适中"
            
        elif stage_name == "development_stage":
            analysis_result["recommended_focus"].extend([
                "深化情感连接和理解",
                "发展角色间的默契和信任",
                "处理情感冲突和误解"
            ])
            analysis_result["relationship_milestones"].extend([
                "情感确认时刻",
                "关系突破点", 
                "共同经历的重要事件"
            ])
            analysis_result["emotional_intensity_target"] = "中到高"
            analysis_result["development_potential"] = "高"
            
        elif stage_name == "climax_stage":
            analysis_result["recommended_focus"].extend([
                "情感高潮和关键时刻",
                "关系重大转折",
                "情感承诺或牺牲"
            ])
            analysis_result["relationship_milestones"].append("情感关系的决定性时刻")
            analysis_result["emotional_intensity_target"] = "高"
            analysis_result["development_potential"] = "极高"
            
        elif stage_name in ["ending_stage", "final_stage"]:
            analysis_result["recommended_focus"].extend([
                "情感圆满和解决",
                "关系最终状态确认",
                "情感主题升华"
            ])
            analysis_result["relationship_milestones"].append("情感关系的最终确立")
            analysis_result["emotional_intensity_target"] = "中到高"
            analysis_result["development_potential"] = "中等"
        
        # 基于情感模式调整
        if romance_pattern.get("romance_type") == "harem":
            analysis_result["recommended_focus"].append("平衡多角关系发展")
            analysis_result["development_potential"] = "高"
        elif romance_pattern.get("romance_type") == "single":
            analysis_result["recommended_focus"].append("专注深化单一关系")
            analysis_result["development_potential"] = "极高"
        
        self.logger.info(f"  ✅ {stage_name}情感发展潜力分析完成: {analysis_result['development_potential']}")
        return analysis_result

    def generate_romance_event_templates(self, romance_pattern: Dict, count: int = 5) -> List[Dict]:
        """生成情感事件模板"""
        romance_type = romance_pattern.get("romance_type", "unknown")
        emotional_style = romance_pattern.get("emotional_style", "balanced")
        
        base_templates = []
        
        if romance_type == "harem":
            base_templates = [
                {
                    "name": "多角关系微妙时刻",
                    "description": "主角与多位女性角色间的微妙互动，制造竞争感和期待感",
                    "key_elements": ["情感试探", "关系平衡", "未来伏笔"],
                    "suitable_chapters": "任何情感发展阶段",
                    "emotional_impact": "中等"
                },
                {
                    "name": "情感选择困境", 
                    "description": "主角面临情感选择，展现不同女性角色的吸引力",
                    "key_elements": ["内心挣扎", "角色特质展现", "读者期待"],
                    "suitable_chapters": "发展阶段或高潮阶段",
                    "emotional_impact": "高"
                }
            ]
        elif romance_type == "single":
            base_templates = [
                {
                    "name": "深情互动时刻",
                    "description": "主角与唯一女主角的深情互动，深化情感纽带",
                    "key_elements": ["情感确认", "默契建立", "共同目标"],
                    "suitable_chapters": "任何需要情感深化的章节",
                    "emotional_impact": "高"
                },
                {
                    "name": "关系考验事件",
                    "description": "外部因素考验主角与女主角的关系",
                    "key_elements": ["冲突解决", "信任建立", "关系强化"],
                    "suitable_chapters": "发展阶段或高潮阶段", 
                    "emotional_impact": "极高"
                }
            ]
        else:  # mixed or unknown
            base_templates = [
                {
                    "name": "情感发展事件",
                    "description": "推进角色间情感关系的自然发展",
                    "key_elements": ["关系推进", "情感认知", "未来铺垫"],
                    "suitable_chapters": "任何章节",
                    "emotional_impact": "中等"
                },
                {
                    "name": "情感反思时刻",
                    "description": "角色对当前情感状态的反思和认知",
                    "key_elements": ["内心独白", "情感认知", "成长体现"],
                    "suitable_chapters": "缓冲章节或情感过渡期",
                    "emotional_impact": "中到高"
                }
            ]
        
        # 基于情感风格调整模板
        if emotional_style == "teasing":
            for template in base_templates:
                template["description"] += "，侧重暧昧和张力"
                template["key_elements"].append("暧昧氛围")
        elif emotional_style == "pure_love":
            for template in base_templates:
                template["description"] += "，侧重深情和真诚"
                template["key_elements"].append("真挚情感")
        
        return base_templates[:count]

    # === 私有辅助方法 ===

    def _format_gap_contexts_for_prompt(self, gap_chapters_with_context: List[Dict]) -> str:
        """格式化空窗期上下文信息用于提示词"""
        formatted = []
        
        for gap_info in gap_chapters_with_context:
            chapter = gap_info["chapter"]
            context = gap_info["context_summary"]
            
            formatted.append(f"### 第{chapter}章上下文")
            formatted.append(context)
            formatted.append("")  # 空行
        
        return "\n".join(formatted)

    def _generate_context_aware_fallback_events(self, gap_chapters_with_context: List[Dict], romance_pattern: Dict, 
                                            stage_name: str) -> List[Dict]:
        """备用方案：生成上下文关联的情感特殊事件"""
        romance_type = romance_pattern.get("romance_type", "unknown")
        events = []
        
        for gap_info in gap_chapters_with_context[:5]:  # 最多生成5个
            chapter = gap_info["chapter"]
            prev_events = gap_info["previous_events"]
            next_events = gap_info["next_events"]
            
            # 基于上下文生成事件
            if romance_type == "harem":
                event = {
                    "name": f"第{chapter}章多角情感张力",
                    "type": "特殊事件",
                    "subtype": "情感填充", 
                    "chapter": chapter,
                    "romance_style": "擦边暧昧",
                    "connection_to_previous": "承接之前事件的情感余波",
                    "connection_to_next": "为后续冲突制造情感伏笔",
                    "main_thread_integration": "通过情感冲突反映主线矛盾",
                    "emotional_development": "在多女主间制造竞争感和期待感",
                    "plot_design": "基于前后事件逻辑，安排主角与不同女性角色的微妙互动",
                    "key_moments": ["情感试探", "关系平衡", "未来伏笔"],
                    "reader_hook": "让读者猜测情感走向对主线的影响",
                    "writing_focus": "暧昧氛围、心理博弈和主线关联",
                    "significance": "情感张力构建，多角关系推进",
                    "description": f"在第{chapter}章中，主角与多位女性角色之间的情感互动，制造微妙的竞争关系和期待感",
                    "event_category": "情感特殊事件"
                }
            elif romance_type == "single":
                event = {
                    "name": f"第{chapter}章情感纽带深化", 
                    "type": "特殊事件",
                    "subtype": "情感填充",
                    "chapter": chapter,
                    "romance_style": "纯爱深情",
                    "connection_to_previous": "延续之前事件的情感基调",
                    "connection_to_next": "为即将到来的挑战建立情感支撑",
                    "main_thread_integration": "用情感力量强化主角动机",
                    "emotional_development": "深化单女主情感纽带和相互理解",
                    "plot_design": "在日常互动中展现情感深度和主线关联",
                    "key_moments": ["情感确认", "默契建立", "共同目标"],
                    "reader_hook": "让读者为真挚情感感动并关注其对主线影响",
                    "writing_focus": "情感细节、内心成长和主线呼应",
                    "significance": "情感纽带深化，关系里程碑",
                    "description": f"在第{chapter}章中，主角与女主角之间的深情互动，深化彼此理解和情感连接",
                    "event_category": "情感特殊事件"
                }
            else:
                event = {
                    "name": f"第{chapter}章情感关系推进",
                    "type": "特殊事件",
                    "subtype": "情感填充",
                    "chapter": chapter,
                    "romance_style": "情感发展",
                    "connection_to_previous": "基于之前事件发展情感关系",
                    "connection_to_next": "为后续情节建立情感基础", 
                    "main_thread_integration": "情感发展服务于主线推进",
                    "emotional_development": "推进角色间情感关系和理解",
                    "plot_design": "通过情感互动展现角色成长和主线关联",
                    "key_moments": ["关系突破", "情感认知", "未来铺垫"],
                    "reader_hook": "情感发展与主线进展的双重吸引力",
                    "writing_focus": "情感逻辑、角色发展和主线融合",
                    "significance": "情感关系推进，角色成长",
                    "description": f"在第{chapter}章中，角色间情感关系的自然发展和深化",
                    "event_category": "情感特殊事件"
                }
            
            events.append(event)
        
        return events