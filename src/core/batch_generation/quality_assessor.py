# -*- coding: utf-8 -*-
"""
分层质量评估器
提供Level 1（轻量）和Level 2（深度）两级评估
"""

import json
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AssessmentLevel(Enum):
    """评估级别"""
    LEVEL_1 = "L1"  # 轻量评估
    LEVEL_2 = "L2"  # 深度评估


@dataclass
class DimensionScore:
    """维度评分"""
    name: str
    score: float
    weight: float
    issues: List[str] = field(default_factory=list)


@dataclass
class AssessmentResult:
    """评估结果"""
    overall_score: float
    level: AssessmentLevel
    dimension_scores: Dict[str, float]
    issues: List[str]
    anomalies: List[Dict]
    can_proceed: bool
    recommendations: List[str] = field(default_factory=list)
    details: Dict = field(default_factory=dict)


class LayeredQualityAssessor:
    """
    分层质量评估器
    
    Level 1: 轻量评估，必做，1次API调用评估整个中型事件
    Level 2: 深度评估，按需触发，针对问题章节详细检查
    """
    
    def __init__(self, api_client):
        self.api_client = api_client
        
        # 评估阈值配置
        self.config = {
            "level2_trigger_score": 7.0,      # Level 1低于此分触发Level 2
            "proceed_threshold": 6.0,          # 可继续的最低分
            "excellent_threshold": 8.5,        # 优秀分数线
            "max_anomalies_for_l1": 3          # Level 1最大可接受异常数
        }
    
    def assess(
        self,
        chapters_content: Dict[int, Dict],
        medium_event: Dict,
        world_state_before: Dict,
        style_guide: Dict,
        novel_title: str = ""
    ) -> AssessmentResult:
        """
        执行分层评估
        
        Args:
            chapters_content: {chapter_num: chapter_data}
            medium_event: 中型事件数据
            world_state_before: 生成前的世界状态
            style_guide: 写作风格指南
            novel_title: 小说标题
            
        Returns:
            AssessmentResult: 评估结果
        """
        logger.info(f"[QualityAssessor] 开始Level 1评估: {medium_event.get('name', 'Unknown')}")
        
        # ========== Level 1: 必做轻量评估 ==========
        level1_result = self._level1_assess(
            chapters_content=chapters_content,
            medium_event=medium_event,
            world_state_before=world_state_before,
            style_guide=style_guide,
            novel_title=novel_title
        )
        
        # 判断是否需要Level 2
        need_level2 = (
            level1_result["overall_score"] < self.config["level2_trigger_score"] or
            len(level1_result.get("anomalies", [])) > self.config["max_anomalies_for_l1"] or
            level1_result.get("has_critical_issues", False)
        )
        
        if not need_level2:
            logger.info(f"[QualityAssessor] Level 1通过，无需Level 2: score={level1_result['overall_score']}")
            return self._build_result_from_l1(level1_result)
        
        # ========== Level 2: 按需深度评估 ==========
        logger.info(f"[QualityAssessor] 触发Level 2评估: score={level1_result['overall_score']}")
        
        level2_result = self._level2_assess(
            chapters_content=chapters_content,
            medium_event=medium_event,
            world_state_before=world_state_before,
            style_guide=style_guide,
            level1_issues=level1_result.get("issues", []),
            novel_title=novel_title
        )
        
        return self._merge_l1_l2_results(level1_result, level2_result)
    
    def _level1_assess(
        self,
        chapters_content: Dict[int, Dict],
        medium_event: Dict,
        world_state_before: Dict,
        style_guide: Dict,
        novel_title: str
    ) -> Dict:
        """
        Level 1评估：整体事件连贯性（1次API调用）
        """
        # 准备评估数据摘要
        chapter_summaries = []
        for ch_num in sorted(chapters_content.keys()):
            ch = chapters_content[ch_num]
            chapter_summaries.append({
                "chapter": ch_num,
                "title": ch.get("title", ""),
                "key_events": ch.get("key_events", []),
                "character_states": ch.get("character_states", {}),
                "time_progression": ch.get("time_progression", "0天")
            })
        
        # 构建Prompt
        prompt = f"""
你是一位专业的叙事连贯性分析师。请评估以下多章内容的整体质量。

【小说】{novel_title}
【中型事件】{medium_event.get('name', 'Unknown')}
【事件目标】{medium_event.get('main_goal', '')}

【评估维度】（每项0-10分，总分50分）

1. **番茄风格符合度** (10分)
   - 段落是否短小适合手机阅读？
   - 开篇是否有吸引力？
   - 卡点是否强力？
   - 节奏是否快速？

2. **风格指南符合度** (10分)
   - 是否符合风格指南的核心要求？
   - 语言风格是否一致？

3. **事件完整性** (10分)
   - 中型事件目标是否完成？
   - 关键情节点是否都有体现？

4. **连贯性** (10分)
   - 角色状态变化是否合理连贯？
   - 章与章之间过渡是否自然？
   - 时间线是否合理？

5. **可读性** (10分)
   - 叙事是否清晰？
   - 是否有明显AI痕迹？

6. **字数合规性** (关键项，不达标直接降级)
   - 每章字数是否在1800-2500字范围内？
   - 字数不足（<1800字）或过多（>2500字）都视为严重问题
   - 当前各章字数: {json.dumps({ch_num: len(ch.get('content', '')) for ch_num, ch in chapters_content.items()}, ensure_ascii=False)}

【风格指南核心要求】
{json.dumps(style_guide.get('key_principles', []), ensure_ascii=False, indent=2)}

【章节摘要】
{json.dumps(chapter_summaries, ensure_ascii=False, indent=2)}

【生成前角色状态】
{json.dumps(world_state_before.get('characters', {}), ensure_ascii=False, indent=2)}

【输出格式】
```json
{{
  "overall_score": 7.5,
  "dimension_scores": {{
    "fanqie_style": 8,
    "style_compliance": 7,
    "event_completion": 8,
    "consistency": 7,
    "readability": 8
  }},
  "issues": ["问题描述1", "问题描述2"],
  "anomalies": [
    {{"type": "character_jump", "description": "韩立状态突变", "chapter": 6}}
  ],
  "has_critical_issues": false,
  "summary": "整体质量良好，但角色状态变化有轻微跳跃"
}}
```
"""
        
        try:
            result = self.api_client.generate_content_with_retry(
                content_type="chapter_quality_assessment",
                user_prompt=prompt,
                purpose=f"Level 1质量评估: {medium_event.get('name', '')}"
            )
            
            if result and isinstance(result, dict):
                return {
                    "overall_score": result.get("overall_score", 5.0),
                    "dimension_scores": result.get("dimension_scores", {}),
                    "issues": result.get("issues", []),
                    "anomalies": result.get("anomalies", []),
                    "has_critical_issues": result.get("has_critical_issues", False),
                    "summary": result.get("summary", "")
                }
        except Exception as e:
            logger.error(f"[QualityAssessor] Level 1评估失败: {e}")
        
        # 失败返回默认值
        return {
            "overall_score": 5.0,
            "dimension_scores": {},
            "issues": ["评估失败，使用默认分数"],
            "anomalies": [],
            "has_critical_issues": True,
            "summary": "评估失败"
        }
    
    def _level2_assess(
        self,
        chapters_content: Dict[int, Dict],
        medium_event: Dict,
        world_state_before: Dict,
        style_guide: Dict,
        level1_issues: List[str],
        novel_title: str
    ) -> Dict:
        """
        Level 2评估：深度一致性检查（按需，1-2次API调用）
        针对Level 1发现的问题进行深入分析
        """
        # 找出问题最严重的章节
        problematic_chapters = self._identify_problematic_chapters(
            chapters_content, level1_issues
        )
        
        # 构建详细检查Prompt
        prompt = f"""
你是一位严格的内容质量审查员。请对以下章节进行深度一致性检查。

【小说】{novel_title}
【中型事件】{medium_event.get('name', 'Unknown')}

【Level 1发现的问题】
{json.dumps(level1_issues, ensure_ascii=False, indent=2)}

【需要重点检查的章节】
{json.dumps(problematic_chapters, ensure_ascii=False, indent=2)}

【深度检查清单】

1. **角色状态详细审查**
   - 检查每个角色的状态变化是否有情节支撑
   - 标记任何突兀的状态跳跃
   - 验证角色能力/物品的获得是否合理

2. **时间线精确核对**
   - 验证时间推进是否符合逻辑
   - 检查是否有时间矛盾
   - 确认天数累加是否正确

3. **物品流转追踪**
   - 追踪重要物品的来源和去向
   - 检查是否有凭空出现/消失的物品
   - 验证物品状态变化是否合理

4. **世界观一致性**
   - 检查是否有违背世界观设定的内容
   - 验证修炼体系/力量体系是否一致
   - 确认地点/势力信息是否准确

5. **写作风格深度检查**
   - 逐段检查段落长度是否合适
   - 标记AI痕迹词汇
   - 评估卡点质量

【输出格式】
```json
{{
  "detailed_scores": {{
    "1": {{"score": 7, "issues": ["第1章问题"]}},
    "2": {{"score": 6, "issues": ["第2章问题"]}}
  }},
  "critical_issues": [
    {{"type": "consistency", "description": "具体问题", "chapter": 5, "severity": "high"}}
  ],
  "fix_suggestions": ["修复建议1", "修复建议2"],
  "overall_assessment": "深度评估总结"
}}
```
"""
        
        try:
            result = self.api_client.generate_content_with_retry(
                content_type="chapter_quality_assessment",
                user_prompt=prompt,
                purpose=f"Level 2深度评估: {medium_event.get('name', '')}"
            )
            
            if result and isinstance(result, dict):
                return result
        except Exception as e:
            logger.error(f"[QualityAssessor] Level 2评估失败: {e}")
        
        return {
            "detailed_scores": {},
            "critical_issues": [],
            "fix_suggestions": [],
            "overall_assessment": "Level 2评估失败"
        }
    
    def _identify_problematic_chapters(
        self,
        chapters_content: Dict[int, Dict],
        issues: List[str]
    ) -> List[Dict]:
        """识别有问题的章节"""
        # 简单实现：提取所有章节摘要
        problematic = []
        for ch_num, ch in chapters_content.items():
            problematic.append({
                "chapter": ch_num,
                "title": ch.get("title", ""),
                "content_preview": ch.get("content", "")[:500] + "...",
                "key_events": ch.get("key_events", [])
            })
        return problematic
    
    def _build_result_from_l1(self, level1_result: Dict) -> AssessmentResult:
        """从Level 1结果构建最终评估结果"""
        score = level1_result.get("overall_score", 5.0)
        
        return AssessmentResult(
            overall_score=score,
            level=AssessmentLevel.LEVEL_1,
            dimension_scores=level1_result.get("dimension_scores", {}),
            issues=level1_result.get("issues", []),
            anomalies=level1_result.get("anomalies", []),
            can_proceed=score >= self.config["proceed_threshold"],
            recommendations=self._generate_recommendations(level1_result),
            details={"summary": level1_result.get("summary", "")}
        )
    
    def _merge_l1_l2_results(
        self,
        level1_result: Dict,
        level2_result: Dict
    ) -> AssessmentResult:
        """合并Level 1和Level 2结果"""
        # 计算综合分数（Level 1占60%，Level 2占40%）
        l1_score = level1_result.get("overall_score", 5.0)
        l2_scores = level2_result.get("detailed_scores", {})
        l2_avg = sum(s.get("score", 5.0) for s in l2_scores.values()) / len(l2_scores) if l2_scores else 5.0
        
        final_score = l1_score * 0.6 + l2_avg * 0.4
        
        # 合并问题列表
        all_issues = level1_result.get("issues", []) + level2_result.get("fix_suggestions", [])
        
        # 合并异常
        all_anomalies = level1_result.get("anomalies", [])
        critical_issues = level2_result.get("critical_issues", [])
        
        return AssessmentResult(
            overall_score=round(final_score, 1),
            level=AssessmentLevel.LEVEL_2,
            dimension_scores={**level1_result.get("dimension_scores", {}), **l2_scores},
            issues=all_issues,
            anomalies=all_anomalies + critical_issues,
            can_proceed=final_score >= self.config["proceed_threshold"],
            recommendations=level2_result.get("fix_suggestions", []),
            details={
                "level1_summary": level1_result.get("summary", ""),
                "level2_assessment": level2_result.get("overall_assessment", ""),
                "critical_issues": critical_issues
            }
        )
    
    def _generate_recommendations(self, level1_result: Dict) -> List[str]:
        """基于Level 1结果生成建议"""
        recommendations = []
        
        dim_scores = level1_result.get("dimension_scores", {})
        
        if dim_scores.get("fanqie_style", 10) < 7:
            recommendations.append("加强番茄风格：缩短段落，加快节奏，强化卡点")
        
        if dim_scores.get("consistency", 10) < 7:
            recommendations.append("增强连贯性：注意角色状态过渡，保持时间线清晰")
        
        if dim_scores.get("event_completion", 10) < 7:
            recommendations.append("完善事件：确保中型事件目标充分完成")
        
        if dim_scores.get("readability", 10) < 7:
            recommendations.append("提升可读性：消除AI痕迹，增强画面感")
        
        return recommendations


# 便捷函数
def quick_assess_batch(
    api_client,
    chapters_content: Dict[int, Dict],
    medium_event: Dict,
    world_state_before: Dict,
    style_guide: Dict,
    novel_title: str = ""
) -> AssessmentResult:
    """
    快速评估函数
    
    使用示例:
    result = quick_assess_batch(
        api_client=api_client,
        chapters_content={5: ch5_data, 6: ch6_data},
        medium_event=medium_event,
        world_state_before=world_state,
        style_guide=style_guide,
        novel_title="凡人修仙传"
    )
    
    if result.can_proceed:
        print(f"通过！分数: {result.overall_score}")
    else:
        print(f"需要优化: {result.issues}")
    """
    assessor = LayeredQualityAssessor(api_client)
    return assessor.assess(
        chapters_content=chapters_content,
        medium_event=medium_event,
        world_state_before=world_state_before,
        style_guide=style_guide,
        novel_title=novel_title
    )
