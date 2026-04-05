# -*- coding: utf-8 -*-
"""
AI Market Evaluator
AI 市场化评估器

基于大模型对创意方案进行深度市场化评估，替代代码规则评分
"""

import json
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """风险等级"""
    LOW = "低风险"
    MEDIUM = "中等风险"
    HIGH = "高风险"
    DANGER = "极高风险"


class Grade(Enum):
    """评级"""
    A = "A"
    B_PLUS = "B+"
    B = "B"
    C_PLUS = "C+"
    C = "C"
    D = "D"
    F = "F"


@dataclass
class PredictedMetrics:
    """预测指标"""
    completion_rate_min: float
    completion_rate_max: float
    retention_d3: float
    retention_d7: float
    retention_d30: float
    debut_pass_rate: float


@dataclass
class RiskAnalysis:
    """风险分析"""
    level: RiskLevel
    main_risks: List[str]
    mitigation: str


@dataclass
class SimilarCase:
    """同类案例"""
    title: str
    completion_rate: float
    note: str


@dataclass
class OptimizationSuggestion:
    """优化建议"""
    priority: str  # 高/中/低
    suggestion: str
    expected_impact: str
    target_chapters: Optional[str] = None


@dataclass
class MarketEvaluationResult:
    """市场化评估结果"""
    overall_score: int
    grade: Grade
    verdict: str
    predicted_metrics: PredictedMetrics
    algorithm_potential: Dict[str, Any]
    risk_analysis: RiskAnalysis
    similar_cases: List[SimilarCase]
    optimization_suggestions: List[OptimizationSuggestion]
    detailed_reasoning: str
    created_at: datetime


class AIMarketEvaluator:
    """
    AI 市场化评估器
    
    使用大模型对创意方案进行深度市场化评估
    """
    
    def __init__(self, api_client, provider: str = "kimi"):
        self.api_client = api_client
        self.provider = provider
        
    async def evaluate(
        self,
        genre: str,
        dialog_history: List[Dict],
        final_creative: Dict,
        genre_market_data: Optional[Dict] = None
    ) -> MarketEvaluationResult:
        """
        执行AI市场化评估
        
        Args:
            genre: 题材
            dialog_history: 用户对话历史
            final_creative: 最终创意方案
            genre_market_data: 题材市场数据（可选）
            
        Returns:
            MarketEvaluationResult: 评估结果
        """
        logger.info(f"[AI评估] 开始评估 {genre} 创意方案")
        
        # 构建评估Prompt
        prompt = self._build_evaluation_prompt(
            genre=genre,
            dialog_history=dialog_history,
            final_creative=final_creative,
            genre_market_data=genre_market_data
        )
        
        try:
            # 调用AI进行评估
            response = await self._call_ai_for_evaluation(prompt)
            
            # 解析评估结果
            result = self._parse_evaluation_response(response)
            
            logger.info(f"[AI评估] 完成，综合评分: {result.overall_score}, 等级: {result.grade.value}")
            return result
            
        except Exception as e:
            logger.error(f"[AI评估] 评估失败: {e}")
            # 返回默认评估结果
            return self._get_default_evaluation()
    
    def _build_evaluation_prompt(
        self,
        genre: str,
        dialog_history: List[Dict],
        final_creative: Dict,
        genre_market_data: Optional[Dict]
    ) -> str:
        """构建评估Prompt"""
        
        # 格式化对话历史
        dialog_text = self._format_dialog_history(dialog_history)
        
        # 格式化创意方案
        creative_text = self._format_creative(final_creative)
        
        # 格式化题材市场数据
        market_text = self._format_market_data(genre, genre_market_data)
        
        prompt = f"""你是番茄小说平台的资深编辑兼数据分析师，拥有5年爆款分析经验。
请基于以下信息，对创意方案进行深度市场化评估。

【题材基础信息】
题材：{genre}
{market_text}

【用户对话打磨历史】
{dialog_text}

【最终创意方案】
{creative_text}

【评估要求】
请从以下维度进行专业评估，给出具体数据和理由：

1. **完读率预测**
   - 预估完读率范围（%）
   - 理由：基于哪些设定做出的判断？
   - 对比题材平均：高/持平/低多少？

2. **留存曲线预测**
   - 3日留存预估（%）
   - 7日留存预估（%）
   - 30日留存预估（%）
   - 关键流失点预测：可能在哪些章节？

3. **算法推荐潜力**
   - 新书期给量预测：大/中/小
   - 首秀通过概率（%）
   - 推荐位潜力：能否上书架/完本/分类强推？

4. **差异化风险分析**
   - 创新点市场接受度：高/中/低
   - 可能的读者负面反馈？
   - 建议的风险对冲方案？

5. **番茄平台适配性**
   - 黄金三章吸引力：0-10分
   - 更新节奏适配度：0-10分
   - 评论互动潜力：0-10分

6. **同类成功案例**
   - 最近6个月类似差异化作品表现
   - 数据参考：书名+完读率

7. **优化建议**
   - 优先级高的优化点（可提升完读率3-5%）
   - 优先级中的优化点
   - 每个建议给出预期效果

8. **最终裁决**
   - 综合评分（0-100）
   - 等级（A/B+/B/C+/C/D/F）
   - 是否建议继续？
   - 一句话 verdict

【输出格式】
必须严格按以下JSON格式输出：
{{
  "overall_score": 78,
  "grade": "B+",
  "verdict": "建议继续，但有优化空间",
  "predicted_metrics": {{
    "completion_rate_min": 12,
    "completion_rate_max": 18,
    "retention_d3": 25,
    "retention_d7": 15,
    "retention_d30": 8,
    "debut_pass_rate": 65
  }},
  "algorithm_potential": {{
    "new_book_traffic": "中等偏上",
    "debut_pass_rate": 65,
    "recommendation_potential": ["书架推荐", "分类强推"]
  }},
  "risk_analysis": {{
    "level": "中等风险",
    "main_risks": ["风险1", "风险2"],
    "mitigation": "对冲方案"
  }},
  "similar_cases": [
    {{"title": "《书名1》", "completion_rate": 15, "note": "类似人设"}},
    {{"title": "《书名2》", "completion_rate": 12, "note": "类似金手指"}}
  ],
  "optimization_suggestions": [
    {{
      "priority": "高",
      "suggestion": "具体建议",
      "expected_impact": "完读+3%",
      "target_chapters": "第1-3章"
    }}
  ],
  "detailed_reasoning": "详细分析过程..."
}}

注意：
1. 所有百分比数字不要带%符号
2. 必须基于番茄平台真实数据和特征
3. 评估要客观，不要一味迎合用户
4. 如果创意偏离套路太远，要明确指出风险"""
        
        return prompt
    
    def _format_dialog_history(self, dialog_history: List[Dict]) -> str:
        """格式化对话历史"""
        lines = []
        for i, turn in enumerate(dialog_history, 1):
            role = "用户" if turn.get('role') == 'user' else "AI"
            content = turn.get('content', '')
            lines.append(f"第{i}轮 - {role}: {content[:200]}{'...' if len(content) > 200 else ''}")
        return "\n".join(lines) if lines else "无对话历史"
    
    def _format_creative(self, creative: Dict) -> str:
        """格式化创意方案"""
        lines = []
        
        if 'title' in creative:
            lines.append(f"书名：{creative['title']}")
        if 'worldview' in creative:
            lines.append(f"世界观：{creative['worldview']}")
        if 'protagonist' in creative:
            lines.append(f"主角：{creative['protagonist']}")
        if 'golden_finger' in creative:
            lines.append(f"金手指：{creative['golden_finger']}")
        if 'unique_points' in creative:
            lines.append(f"差异化亮点：{creative['unique_points']}")
        if 'emotion_pacing' in creative:
            lines.append(f"情绪节奏：{creative['emotion_pacing']}")
            
        return "\n".join(lines) if lines else json.dumps(creative, ensure_ascii=False, indent=2)
    
    def _format_market_data(self, genre: str, data: Optional[Dict]) -> str:
        """格式化市场数据"""
        if not data:
            # 默认数据
            return f"""题材平均完读率：10%
题材平均3日留存：20%
头部作品特征：快节奏、强爽点、直播/国运元素
当前市场饱和度：高（同质化严重）"""
        
        lines = [
            f"题材平均完读率：{data.get('avg_completion', 10)}%",
            f"题材平均3日留存：{data.get('avg_retention', 20)}%",
            f"头部作品特征：{data.get('top_features', '快节奏、强爽点')}",
            f"当前市场饱和度：{data.get('saturation', '高')}"
        ]
        return "\n".join(lines)
    
    async def _call_ai_for_evaluation(self, prompt: str) -> str:
        """调用AI进行评估"""
        messages = [
            {
                "role": "system",
                "content": "你是番茄小说平台的资深编辑和数据分析师，专门评估网文创意的市场化潜力。请客观、专业地分析。"
            },
            {
                "role": "user",
                "content": prompt
            }
        ]
        
        try:
            # 使用更强大的模型进行评估
            response = self.api_client.chat_completion(
                messages=messages,
                model="kimi",  # 可根据配置调整
                temperature=0.3,  # 低温度保持客观
                max_tokens=4000
            )
            
            return response.get('content', '')
            
        except Exception as e:
            logger.error(f"[AI评估] API调用失败: {e}")
            raise
    
    def _parse_evaluation_response(self, response: str) -> MarketEvaluationResult:
        """解析AI返回的评估结果"""
        try:
            # 提取JSON部分
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            
            # 构建预测指标
            metrics_data = data.get('predicted_metrics', {})
            metrics = PredictedMetrics(
                completion_rate_min=float(metrics_data.get('completion_rate_min', 10)),
                completion_rate_max=float(metrics_data.get('completion_rate_max', 15)),
                retention_d3=float(metrics_data.get('retention_d3', 20)),
                retention_d7=float(metrics_data.get('retention_d7', 12)),
                retention_d30=float(metrics_data.get('retention_d30', 6)),
                debut_pass_rate=float(metrics_data.get('debut_pass_rate', 50))
            )
            
            # 构建风险分析
            risk_data = data.get('risk_analysis', {})
            risk_level = self._parse_risk_level(risk_data.get('level', '中等'))
            risk_analysis = RiskAnalysis(
                level=risk_level,
                main_risks=risk_data.get('main_risks', []),
                mitigation=risk_data.get('mitigation', '')
            )
            
            # 构建同类案例
            similar_cases = []
            for case in data.get('similar_cases', []):
                similar_cases.append(SimilarCase(
                    title=case.get('title', ''),
                    completion_rate=float(case.get('completion_rate', 0)),
                    note=case.get('note', '')
                ))
            
            # 构建优化建议
            suggestions = []
            for sug in data.get('optimization_suggestions', []):
                suggestions.append(OptimizationSuggestion(
                    priority=sug.get('priority', '中'),
                    suggestion=sug.get('suggestion', ''),
                    expected_impact=sug.get('expected_impact', ''),
                    target_chapters=sug.get('target_chapters')
                ))
            
            # 构建结果
            result = MarketEvaluationResult(
                overall_score=int(data.get('overall_score', 60)),
                grade=self._parse_grade(data.get('grade', 'C')),
                verdict=data.get('verdict', '建议优化后再继续'),
                predicted_metrics=metrics,
                algorithm_potential=data.get('algorithm_potential', {}),
                risk_analysis=risk_analysis,
                similar_cases=similar_cases,
                optimization_suggestions=suggestions,
                detailed_reasoning=data.get('detailed_reasoning', ''),
                created_at=datetime.now()
            )
            
            return result
            
        except Exception as e:
            logger.error(f"[AI评估] 解析结果失败: {e}")
            return self._get_default_evaluation()
    
    def _extract_json(self, text: str) -> str:
        """从文本中提取JSON"""
        # 尝试找到JSON块
        start_idx = text.find('{')
        end_idx = text.rfind('}')
        
        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
            return text[start_idx:end_idx+1]
        
        return text
    
    def _parse_risk_level(self, level_str: str) -> RiskLevel:
        """解析风险等级"""
        if "低" in level_str or "safe" in level_str.lower():
            return RiskLevel.LOW
        elif "高" in level_str or "danger" in level_str.lower():
            return RiskLevel.HIGH
        elif "极高" in level_str:
            return RiskLevel.DANGER
        return RiskLevel.MEDIUM
    
    def _parse_grade(self, grade_str: str) -> Grade:
        """解析等级"""
        grade_map = {
            "A": Grade.A,
            "B+": Grade.B_PLUS,
            "B": Grade.B,
            "C+": Grade.C_PLUS,
            "C": Grade.C,
            "D": Grade.D,
            "F": Grade.F
        }
        return grade_map.get(grade_str.upper(), Grade.C)
    
    def _get_default_evaluation(self) -> MarketEvaluationResult:
        """获取默认评估结果（失败时使用）"""
        return MarketEvaluationResult(
            overall_score=60,
            grade=Grade.C,
            verdict="评估服务暂时不可用，建议基于经验继续",
            predicted_metrics=PredictedMetrics(
                completion_rate_min=8,
                completion_rate_max=12,
                retention_d3=18,
                retention_d7=10,
                retention_d30=5,
                debut_pass_rate=50
            ),
            algorithm_potential={
                "new_book_traffic": "中等",
                "debut_pass_rate": 50,
                "recommendation_potential": ["书架推荐"]
            },
            risk_analysis=RiskAnalysis(
                level=RiskLevel.MEDIUM,
                main_risks=["无法获取详细评估"],
                mitigation="建议参考同类作品数据"
            ),
            similar_cases=[],
            optimization_suggestions=[],
            detailed_reasoning="AI评估服务暂时不可用，使用默认保守估计。",
            created_at=datetime.now()
        )
    
    def to_dict(self, result: MarketEvaluationResult) -> Dict:
        """将结果转换为字典（用于API返回）"""
        return {
            "overall_score": result.overall_score,
            "grade": result.grade.value,
            "verdict": result.verdict,
            "predicted_metrics": {
                "completion_rate": {
                    "min": result.predicted_metrics.completion_rate_min,
                    "max": result.predicted_metrics.completion_rate_max,
                    "unit": "%"
                },
                "retention": {
                    "d3": {"value": result.predicted_metrics.retention_d3, "unit": "%"},
                    "d7": {"value": result.predicted_metrics.retention_d7, "unit": "%"},
                    "d30": {"value": result.predicted_metrics.retention_d30, "unit": "%"}
                },
                "debut_pass_rate": {
                    "value": result.predicted_metrics.debut_pass_rate,
                    "unit": "%"
                }
            },
            "algorithm_potential": result.algorithm_potential,
            "risk_analysis": {
                "level": result.risk_analysis.level.value,
                "main_risks": result.risk_analysis.main_risks,
                "mitigation": result.risk_analysis.mitigation
            },
            "similar_cases": [
                {
                    "title": case.title,
                    "completion_rate": case.completion_rate,
                    "note": case.note
                } for case in result.similar_cases
            ],
            "optimization_suggestions": [
                {
                    "priority": sug.priority,
                    "suggestion": sug.suggestion,
                    "expected_impact": sug.expected_impact,
                    "target_chapters": sug.target_chapters
                } for sug in result.optimization_suggestions
            ],
            "detailed_reasoning": result.detailed_reasoning,
            "created_at": result.created_at.isoformat(),
            "recommendation": self._get_recommendation(result)
        }
    
    def _get_recommendation(self, result: MarketEvaluationResult) -> str:
        """获取推荐操作"""
        if result.overall_score >= 85:
            return "proceed"  # 直接继续
        elif result.overall_score >= 70:
            return "proceed_with_caution"  # 继续但注意优化
        elif result.overall_score >= 55:
            return "suggest_optimization"  # 建议优化
        else:
            return "suggest_redesign"  # 建议重新设计


# 单例模式
evaluator_instance = None

def get_evaluator(api_client=None, provider="kimi"):
    """获取评估器实例"""
    global evaluator_instance
    if evaluator_instance is None and api_client is not None:
        evaluator_instance = AIMarketEvaluator(api_client, provider)
    return evaluator_instance