# -*- coding: utf-8 -*-
"""
黄金三章整体质量评估器

区别于普通章节的评估，黄金三章评估侧重：
1. 吸引力 - 是否能抓住读者
2. 类型卖点契合 - 是否符合该类型读者的期待
3. 开篇强度 - 黄金三章的核心使命
4. 目标读者匹配 - 是否符合预设的读者画像
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .quality_assessor import AssessmentResult, AssessmentLevel
from .multi_chapter_generator import ChapterContent

logger = logging.getLogger(__name__)


@dataclass
class GoldenChaptersAssessment:
    """黄金三章专用评估结果"""
    overall_score: float  # 总分10分
    level: AssessmentLevel
    
    # 核心维度评分
    opening_hook: float  # 开篇钩子强度（0-10）
    type_match: float  # 类型卖点契合度（0-10）
    reader_attraction: float  # 目标读者吸引力（0-10）
    chapter_flow: float  # 三章流畅度（0-10）
    payoff_quality: float  # 爽点/回报质量（0-10）
    
    # 详细评价
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    
    # 类型特定评价
    genre_specific: Dict[str, Any] = field(default_factory=dict)
    
    # 读者反馈模拟
    reader_reactions: Dict[str, str] = field(default_factory=dict)
    
    # 改进建议
    improvement_suggestions: List[str] = field(default_factory=list)
    
    can_proceed: bool = True


class GoldenChaptersAssessor:
    """
    黄金三章整体评估器
    
    评估重点：
    1. 吸引力 - 15秒内抓住读者
    2. 类型卖点 - 神豪文要有神豪味，修仙文要有修仙味
    3. 目标读者匹配 - 是否符合预设读者画像的期待
    4. 三章整体性 - 不是三篇独立文章，而是一个完整开篇
    """
    
    # 各类型核心卖点检查清单
    GENRE_CHECKLIST = {
        "神豪文": {
            "核心卖点": ["金钱装逼", "身份反差", "打脸反转", "升级爽感"],
            "必备元素": ["金手指激活（系统/遗产）", "第一次花钱装逼", "周围人震惊反应"],
            "情绪曲线": "压抑→突然获得→质疑→装逼成功→震惊→期待"
        },
        "修仙文": {
            "核心卖点": ["金手指获得", "升级突破", "打脸欺凌者", "探索世界"],
            "必备元素": ["金手指激活（神秘物品/系统）", "初次修炼效果", "他人轻视→震惊"],
            "情绪曲线": "平凡→奇遇→质疑→验证成功→震惊→踏上仙途"
        },
        "赘婿文": {
            "核心卖点": ["身份反转", "隐忍爆发", "打脸羞辱者", "家人态度转变"],
            "必备元素": ["被羞辱铺垫", "金手指/身份揭露", "第一次反击成功"],
            "情绪曲线": "屈辱→隐忍→契机→反转→打脸→震惊→期待"
        },
        "都市异能": {
            "核心卖点": ["能力觉醒", "解决困境", "隐藏身份", "逐步变强"],
            "必备元素": ["能力觉醒场景", "初次使用能力", "效果超预期"],
            "情绪曲线": "困境→觉醒→尝试→成功→惊讶→新目标"
        },
        "历史穿越": {
            "核心卖点": ["现代知识碾压", "改变历史", "建立势力", "装逼不翻车"],
            "必备元素": ["穿越场景", "第一次用现代知识", "古人震惊"],
            "情绪曲线": "迷茫→适应→展示→震惊→认可→野心"
        },
        "无敌文": {
            "核心卖点": ["一路碾压", "扮猪吃虎", "敌人绝望", "读者爽感"],
            "必备元素": ["展示部分实力", "敌人轻视", "轻松碾压", "周围人震惊"],
            "情绪曲线": "隐藏→挑衅→出手→碾压→震惊→期待"
        }
    }
    
    def __init__(self, api_client):
        self.api_client = api_client
        self.logger = logging.getLogger(__name__)
    
    def assess(
        self,
        chapters_content: Dict[int, ChapterContent],
        novel_data: Dict,
        creative_seed: Dict,
        selected_plan: Dict
    ) -> GoldenChaptersAssessment:
        """
        整体评估黄金三章
        
        Args:
            chapters_content: {1: ch1, 2: ch2, 3: ch3} 三章内容
            novel_data: 小说数据
            creative_seed: 创意种子
            selected_plan: 选定方案
            
        Returns:
            GoldenChaptersAssessment: 专用评估结果
        """
        novel_title = novel_data.get("novel_title", "Unknown")
        category = selected_plan.get("category", "未分类")
        
        self.logger.info(f"[GoldenAssessor] 开始评估黄金三章: {novel_title}")
        
        # 1. 提取三章内容摘要
        chapters_summary = self._extract_chapters_summary(chapters_content)
        
        # 2. 确定小说类型和核心卖点
        genre_type = self._detect_genre_type(category, selected_plan)
        genre_checklist = self.GENRE_CHECKLIST.get(genre_type, self.GENRE_CHECKLIST["神豪文"])
        
        # 3. 提取目标读者画像
        target_audience = selected_plan.get("target_audience", "")
        core_selling_points = selected_plan.get("core_settings", {}).get("core_selling_points", [])
        
        # 4. 构建专用评估Prompt
        prompt = self._build_assessment_prompt(
            novel_title=novel_title,
            genre_type=genre_type,
            genre_checklist=genre_checklist,
            target_audience=target_audience,
            core_selling_points=core_selling_points,
            chapters_summary=chapters_summary,
            creative_seed=creative_seed
        )
        
        # 5. 调用API评估
        try:
            result = self.api_client.generate_content_with_retry(
                content_type="chapter_quality_assessment",
                user_prompt=prompt,
                purpose=f"评估《{novel_title}》黄金三章吸引力",
                chapter_number=1
            )
            
            if result:
                return self._parse_assessment_result(result, genre_type)
            else:
                self.logger.warning("[GoldenAssessor] 评估返回空，使用默认")
                return self._default_assessment()
                
        except Exception as e:
            self.logger.error(f"[GoldenAssessor] 评估失败: {e}")
            return self._default_assessment()
    
    def _extract_chapters_summary(self, chapters_content: Dict[int, ChapterContent]) -> Dict:
        """提取三章内容摘要（控制token长度）"""
        summary = {}
        
        for ch_num in [1, 2, 3]:
            if ch_num not in chapters_content:
                continue
                
            ch = chapters_content[ch_num]
            content = ch.content
            
            # 每章只取关键部分：开头500字 + 结尾500字
            beginning = content[:500] if len(content) > 500 else content
            ending = content[-500:] if len(content) > 500 else ""
            
            summary[ch_num] = {
                "title": ch.title,
                "word_count": len(content),
                "key_events": ch.key_events,
                "character_states": ch.character_states,
                "beginning": beginning,
                "ending": ending,
                "hook": ch.title  # 标题作为钩子参考
            }
        
        return summary
    
    def _detect_genre_type(self, category: str, selected_plan: Dict) -> str:
        """检测小说类型"""
        # 从分类中提取类型
        category_lower = category.lower()
        
        if any(kw in category_lower for kw in ["神豪", "富豪", "花钱", "返利"]):
            return "神豪文"
        elif any(kw in category_lower for kw in ["修仙", "修真", "玄幻", "仙侠"]):
            return "修仙文"
        elif any(kw in category_lower for kw in ["赘婿", "上门", "女婿", "窝囊"]):
            return "赘婿文"
        elif any(kw in category_lower for kw in ["异能", "超能力", "系统", "金手指"]):
            return "都市异能"
        elif any(kw in category_lower for kw in ["历史", "穿越", "古代", "王朝"]):
            return "历史穿越"
        elif any(kw in category_lower for kw in ["无敌", "碾压", "最强", "至尊"]):
            return "无敌文"
        
        # 从创意种子推断
        creative = str(selected_plan.get("creative_seed", "")).lower()
        if any(kw in creative for kw in ["神豪", "花钱", "返利", "百倍"]):
            return "神豪文"
        elif any(kw in creative for kw in ["修仙", "宗门", "境界", "功法"]):
            return "修仙文"
        
        # 默认
        return "神豪文"
    
    def _build_assessment_prompt(
        self,
        novel_title: str,
        genre_type: str,
        genre_checklist: Dict,
        target_audience: str,
        core_selling_points: List[str],
        chapters_summary: Dict,
        creative_seed: Dict
    ) -> str:
        """构建黄金三章专用评估Prompt"""
        
        prompt = f"""# 角色：资深网文编辑 + 目标读者代表

你正在评估小说《{novel_title}》的黄金三章（第1-3章）。

## 小说类型
**{genre_type}**

## 该类型核心要求
**核心卖点**：{', '.join(genre_checklist['核心卖点'])}

**必备元素**：
{chr(10).join(f"- {item}" for item in genre_checklist['必备元素'])}

**情绪曲线**：{genre_checklist['情绪曲线']}

## 目标读者画像
{target_audience}

## 核心卖点承诺
{chr(10).join(f"- {point}" for point in core_selling_points)}

## 黄金三章内容摘要

### 第1章：{chapters_summary.get(1, {}).get('title', '未提供')}
- 字数：{chapters_summary.get(1, {}).get('word_count', 0)}
- 关键事件：{chapters_summary.get(1, {}).get('key_events', [])}
- 开头：{chapters_summary.get(1, {}).get('beginning', '')[:200]}...
- 结尾卡点：{chapters_summary.get(1, {}).get('ending', '')[-200:]}...

### 第2章：{chapters_summary.get(2, {}).get('title', '未提供')}
- 字数：{chapters_summary.get(2, {}).get('word_count', 0)}
- 关键事件：{chapters_summary.get(2, {}).get('key_events', [])}
- 开头：{chapters_summary.get(2, {}).get('beginning', '')[:200]}...
- 结尾卡点：{chapters_summary.get(2, {}).get('ending', '')[-200:]}...

### 第3章：{chapters_summary.get(3, {}).get('title', '未提供')}
- 字数：{chapters_summary.get(3, {}).get('word_count', 0)}
- 关键事件：{chapters_summary.get(3, {}).get('key_events', [])}
- 开头：{chapters_summary.get(3, {}).get('beginning', '')[:200]}...
- 结尾卡点：{chapters_summary.get(3, {}).get('ending', '')[-200:]}...

## 评估维度（每项0-10分，总分50分）

### 1. 开篇钩子强度 (10分)
- 第1章前300字是否能15秒内抓住读者？
- 是否有强烈冲突、悬念或情绪张力？
- 读者是否会产生"我想知道接下来发生什么"的想法？

### 2. 类型卖点契合度 (10分)
- 是否符合{genre_type}的核心卖点？
- 必备元素是否都有体现？
- 是否让读者觉得"这就是我想看的类型"？

### 3. 目标读者吸引力 (10分)
- 是否符合目标读者画像的期待？
- 是否能引发目标读者的共鸣？
- 读者是否会因为主角处境而产生代入感？

### 4. 三章流畅度 (10分)
- 三章是否像一个完整的开篇，而非三篇独立文章？
- 情绪曲线是否自然递进？
- 伏笔和呼应是否到位？

### 5. 爽点/回报质量 (10分)
- 第3章是否给出了足够的爽感/满足感？
- 铺垫和爆发的比例是否合适？
- 读者读完是否会期待第4章？

## 输出格式

```json
{{
  "overall_score": 7.5,
  "dimension_scores": {{
    "opening_hook": 8,
    "type_match": 7,
    "reader_attraction": 8,
    "chapter_flow": 7,
    "payoff_quality": 8
  }},
  "strengths": [
    "优点1：具体描述",
    "优点2：具体描述"
  ],
  "weaknesses": [
    "缺点1：具体描述",
    "缺点2：具体描述"
  ],
  "genre_specific": {{
    "type_matched": true,
    "missing_elements": ["缺少的元素"],
    "emotion_curve": "情绪曲线评价"
  }},
  "reader_reactions": {{
    "chapter1": "读完第1章的反应",
    "chapter2": "读完第2章的反应",
    "chapter3": "读完第3章的反应"
  }},
  "improvement_suggestions": [
    "具体改进建议1",
    "具体改进建议2"
  ],
  "can_proceed": true,
  "verdict": "总体评价：优秀/良好/合格/需要修改"
}}
```

## 特别提醒

1. **站在读者角度**：如果你是目标读者，这黄金三章能吸引你继续读吗？
2. **类型纯度**：{genre_type}的读者看了会觉得"对味"吗？
3. **期待感建立**：读完第3章，读者是否对第4章有明确期待？
4. **避免泛泛而谈**：评价要具体，指出具体段落或情节
"""
        return prompt
    
    def _parse_assessment_result(
        self,
        result: Dict,
        genre_type: str
    ) -> GoldenChaptersAssessment:
        """解析评估结果"""
        dim_scores = result.get("dimension_scores", {})
        
        return GoldenChaptersAssessment(
            overall_score=result.get("overall_score", 7.0),
            level=AssessmentLevel.LEVEL_1 if result.get("overall_score", 7) >= 7 else AssessmentLevel.LEVEL_2,
            opening_hook=dim_scores.get("opening_hook", 7.0),
            type_match=dim_scores.get("type_match", 7.0),
            reader_attraction=dim_scores.get("reader_attraction", 7.0),
            chapter_flow=dim_scores.get("chapter_flow", 7.0),
            payoff_quality=dim_scores.get("payoff_quality", 7.0),
            strengths=result.get("strengths", []),
            weaknesses=result.get("weaknesses", []),
            genre_specific=result.get("genre_specific", {}),
            reader_reactions=result.get("reader_reactions", {}),
            improvement_suggestions=result.get("improvement_suggestions", []),
            can_proceed=result.get("can_proceed", True)
        )
    
    def _default_assessment(self) -> GoldenChaptersAssessment:
        """默认评估结果（评估失败时使用）"""
        return GoldenChaptersAssessment(
            overall_score=7.0,
            level=AssessmentLevel.LEVEL_1,
            opening_hook=7.0,
            type_match=7.0,
            reader_attraction=7.0,
            chapter_flow=7.0,
            payoff_quality=7.0,
            strengths=["评估失败，使用默认分数"],
            can_proceed=True
        )
    
    def generate_improvement_guide(
        self,
        assessment: GoldenChaptersAssessment,
        chapters_content: Dict[int, ChapterContent]
    ) -> str:
        """
        生成改进指导报告
        
        根据评估结果生成具体的改进建议文档
        """
        guide_parts = [
            f"# 《黄金三章》改进指导报告",
            f"",
            f"## 总体评分：{assessment.overall_score}/10",
            f"",
            f"## 各维度评分",
            f"- 开篇钩子：{assessment.opening_hook}/10",
            f"- 类型契合：{assessment.type_match}/10",
            f"- 读者吸引：{assessment.reader_attraction}/10",
            f"- 三章流畅：{assessment.chapter_flow}/10",
            f"- 爽点质量：{assessment.payoff_quality}/10",
            f"",
            f"## 优势",
        ]
        
        for strength in assessment.strengths:
            guide_parts.append(f"- {strength}")
        
        guide_parts.extend([
            f"",
            f"## 需要改进",
        ])
        
        for weakness in assessment.weaknesses:
            guide_parts.append(f"- {weakness}")
        
        guide_parts.extend([
            f"",
            f"## 读者反馈模拟",
        ])
        
        for ch, reaction in assessment.reader_reactions.items():
            guide_parts.append(f"- {ch}：{reaction}")
        
        guide_parts.extend([
            f"",
            f"## 具体改进建议",
        ])
        
        for i, suggestion in enumerate(assessment.improvement_suggestions, 1):
            guide_parts.append(f"{i}. {suggestion}")
        
        return "\n".join(guide_parts)


def assess_golden_chapters(
    api_client,
    chapters_content: Dict[int, ChapterContent],
    novel_data: Dict,
    creative_seed: Dict,
    selected_plan: Dict
) -> GoldenChaptersAssessment:
    """
    便捷函数：评估黄金三章
    
    使用示例:
    assessment = assess_golden_chapters(
        api_client=api_client,
        chapters_content={1: ch1, 2: ch2, 3: ch3},
        novel_data=novel_data,
        creative_seed=creative_seed,
        selected_plan=selected_plan
    )
    
    print(f"总体评分：{assessment.overall_score}")
    print(f"类型契合：{assessment.type_match}")
    print(f"读者评价：{assessment.reader_reactions}")
    
    if assessment.overall_score < 7:
        print("需要改进：", assessment.improvement_suggestions)
    """
    assessor = GoldenChaptersAssessor(api_client)
    return assessor.assess(
        chapters_content=chapters_content,
        novel_data=novel_data,
        creative_seed=creative_seed,
        selected_plan=selected_plan
    )
