"""
智能权重压缩管理器 - 专为小说创作优化

核心思想：
1. 基于元素重要性权重，而不是简单的章节距离
2. 保护关键情节、主角相关、重要伏笔
3. 动态评估上下文的"创作价值"
4. 智能保留故事连贯性和一致性所需的信息
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from typing import Dict, List, Optional, Any, Tuple, Set
import json
import re
import math
from src.utils.logger import get_logger

class IntelligentWeightedCompressionManager:
    """智能权重压缩管理器 - 小说创作专用"""

    def __init__(self):
        self.logger = get_logger("IntelligentWeightedCompressionManager")

        # 权重配置
        self.weights = {
            # 内容类型权重
            "content_types": {
                "protagonist": 1.0,        # 主角相关 - 最高权重
                "main_plot": 0.9,          # 主线剧情 - 很高权重
                "major_event": 0.8,        # 重大事件 - 高权重
                "relationship": 0.7,       # 重要关系 - 较高权重
                "character_arc": 0.6,      # 角色成长 - 中高权重
                "subplot": 0.4,           # 支线剧情 - 中等权重
                "supporting_char": 0.3,    # 配角相关 - 较低权重
                "background": 0.2,         # 背景设定 - 低权重
                "minor_event": 0.1         # 次要事件 - 最低权重
            },

            # 时间衰减权重（章节距离的影响）
            "time_decay": {
                "decay_factor": 0.05,      # 每章衰减5%
                "min_weight": 0.1,         # 最低保留10%权重
                "critical_decay_resistance": 0.02,  # 关键事件衰减更慢
            },

            # 情节影响权重
            "plot_impact": {
                "plot_twist": 1.2,         # 情节转折 - 权重加成
                "emotional_peak": 1.1,     # 情感高潮 - 权重加成
                "setup": 0.8,             # 伏笔设置 - 权重加成
                "payoff": 1.0,             # 伏笔回收 - 权重加成
            }
        }

        # 关键词汇定义（用于识别重要内容）
        self.critical_keywords = {
            "protagonist": ["主角", "林云", "我"],  # 主角相关词汇
            "major_plot": ["突破", "觉醒", "传承", "重生"],  # 主线情节
            "critical_moments": ["决战", "死亡", "初恋", "背叛"],  # 关键时刻
            "important_places": ["秘境", "禁地", "圣地", "魔窟"],  # 重要地点
        }

        # 压缩策略
        self.compression_strategies = {
            "preserve_all": self._preserve_completely,      # 完全保留
            "smart_reduce": self._smart_reduction,          # 智能简化
            "essence_only": self._extract_essence,          # 提取精华
            "minimal": self._minimal_compression,           # 最小压缩
        }

        # 智能分析缓存
        self._analysis_cache = {}
        self._compression_stats = {
            "total_compressions": 0,
            "weight_adjustments": 0,
            "critical_preservations": 0
        }

    def compress_context_intelligently(self, context_data: Dict, current_chapter: int,
                                     context_chapter: int = None,
                                     context_type: str = "general",
                                     max_tokens: int = 1000,
                                     preserve_critical: bool = True) -> Dict:
        """
        智能压缩上下文 - 基于权重重要性而非简单距离

        Args:
            context_data: 原始上下文数据
            current_chapter: 当前章节号
            context_chapter: 上下文所属章节号
            context_type: 上下文类型
            max_tokens: 目标最大token数
            preserve_critical: 是否强制保留关键信息
        """
        self.logger.debug(f"开始智能压缩: 章节{current_chapter} -> 章节{context_chapter}, 目标tokens: {max_tokens}")

        # 分析上下文并计算权重
        analyzed_context = self._analyze_context_weights(context_data, current_chapter, context_chapter)

        # 评估压缩策略
        compression_strategy = self._determine_compression_strategy(analyzed_context, max_tokens)

        # 执行智能压缩
        compressed_data = self._execute_intelligent_compression(
            analyzed_context, compression_strategy, max_tokens, preserve_critical
        )

        # 更新统计
        self._compression_stats["total_compressions"] += 1

        return compressed_data

    def _analyze_context_weights(self, context_data: Dict, current_chapter: int, context_chapter: int) -> Dict:
        """分析上下文并计算每个元素的权重"""
        analyzed = {
            "original_data": context_data,
            "weighted_elements": {},
            "total_weight": 0,
            "critical_elements": [],
            "time_distance": current_chapter - context_chapter if context_chapter else 0
        }

        # 按数据类型分别计算权重
        if isinstance(context_data, dict):
            for key, value in context_data.items():
                element_analysis = self._analyze_element_weight(key, value, analyzed["time_distance"])
                analyzed["weighted_elements"][key] = element_analysis
                analyzed["total_weight"] += element_analysis["effective_weight"]

                if element_analysis["is_critical"]:
                    analyzed["critical_elements"].append(key)

        elif isinstance(context_data, list):
            for i, item in enumerate(context_data):
                element_analysis = self._analyze_element_weight(f"item_{i}", item, analyzed["time_distance"])
                analyzed["weighted_elements"][f"item_{i}"] = element_analysis
                analyzed["total_weight"] += element_analysis["effective_weight"]

                if element_analysis["is_critical"]:
                    analyzed["critical_elements"].append(f"item_{i}")

        return analyzed

    def _analyze_element_weight(self, element_key: str, element_value: Any, time_distance: int) -> Dict:
        """分析单个元素的权重"""
        analysis = {
            "key": element_key,
            "value": element_value,
            "content_type": self._identify_content_type(element_key, element_value),
            "base_weight": 0,
            "time_factor": 1.0,
            "impact_factor": 1.0,
            "effective_weight": 0,
            "is_critical": False,
            "importance_reasons": []
        }

        # 1. 确定内容类型和基础权重
        content_type = analysis["content_type"]
        analysis["base_weight"] = self.weights["content_types"].get(content_type, 0.5)

        # 2. 时间衰减计算
        if time_distance > 0:
            decay_factor = self.weights["time_decay"]["decay_factor"]
            min_weight = self.weights["time_decay"]["min_weight"]

            # 关键内容衰减更慢
            if content_type in ["protagonist", "main_plot", "major_event"]:
                decay_factor = self.weights["time_decay"]["critical_decay_resistance"]

            analysis["time_factor"] = max(min_weight,
                                        math.pow(1 - decay_factor, time_distance))
            analysis["importance_reasons"].append(f"时间衰减因子: {analysis['time_factor']:.2f}")

        # 3. 情节影响因子
        content_str = str(element_value) if element_value else ""
        for impact_type, factor in self.weights["plot_impact"].items():
            if self._contains_impact_keywords(content_str, impact_type):
                analysis["impact_factor"] *= factor
                analysis["importance_reasons"].append(f"{impact_type}影响: x{factor}")

        # 4. 关键词检测
        if self._contains_critical_keywords(element_key, content_str):
            analysis["is_critical"] = True
            analysis["importance_reasons"].append("包含关键元素")
            analysis["effective_weight"] = 1.0  # 关键元素最高权重
        else:
            # 5. 综合权重计算
            analysis["effective_weight"] = (analysis["base_weight"] *
                                          analysis["time_factor"] *
                                          analysis["impact_factor"])

        return analysis

    def _identify_content_type(self, element_key: str, element_value: Any) -> str:
        """识别内容类型"""
        key_lower = element_key.lower()
        value_str = str(element_value).lower() if element_value else ""

        # 主角相关
        if any(keyword in key_lower or keyword in value_str for keyword in ["protagonist", "主角", "林云", "我"]):
            return "protagonist"

        # 主线剧情
        if any(keyword in key_lower or keyword in value_str for keyword in ["main_plot", "主线", "核心", "传承", "突破"]):
            return "main_plot"

        # 重大事件
        if any(keyword in key_lower for keyword in ["major_event", "重大事件", "关键事件", "战斗", "决战"]):
            return "major_event"

        # 重要关系
        if any(keyword in key_lower or keyword in value_str for keyword in ["relationship", "关系", "爱人", "师父", "朋友"]):
            return "relationship"

        # 角色成长
        if any(keyword in key_lower or keyword in value_str for keyword in ["成长", "arc", "development", "变化"]):
            return "character_arc"

        # 支线剧情
        if any(keyword in key_lower for keyword in ["subplot", "支线", "side"]):
            return "subplot"

        # 配角
        if any(keyword in key_lower or keyword in value_str for keyword in ["配角", "配角", "supporting"]):
            return "supporting_char"

        # 背景设定
        if any(keyword in key_lower or keyword in value_str for keyword in ["background", "背景", "设定", "世界观"]):
            return "background"

        # 次要事件
        if any(keyword in key_lower for keyword in ["minor", "次要", "日常", "normal"]):
            return "minor_event"

        return "general"  # 默认类型

    def _contains_impact_keywords(self, content: str, impact_type: str) -> bool:
        """检测是否包含影响因子关键词"""
        impact_keywords = {
            "plot_twist": ["转折", "反转", "意外", "shock", "twist"],
            "emotional_peak": ["高潮", "激动", "情感", "emotional", "peak"],
            "setup": ["伏笔", "铺垫", "准备", "setup", "foreshadow"],
            "payoff": ["回收", "揭晓", "结果", "payoff", "resolve"]
        }

        keywords = impact_keywords.get(impact_type, [])
        return any(keyword in content for keyword in keywords)

    def _contains_critical_keywords(self, element_key: str, content: str) -> bool:
        """检测是否包含关键元素"""
        combined_text = f"{element_key} {content}".lower()

        # 检查所有类型的关键词
        for keyword_list in self.critical_keywords.values():
            if any(keyword in combined_text for keyword in keyword_list):
                return True

        return False

    def _determine_compression_strategy(self, analyzed_context: Dict, max_tokens: int) -> str:
        """根据分析结果确定压缩策略"""
        total_weight = analyzed_context["total_weight"]
        critical_count = len(analyzed_context["critical_elements"])

        # 估算原始token数量
        original_tokens = self._estimate_tokens_fast(analyzed_context["original_data"])

        # 计算需要的压缩比例
        if original_tokens <= max_tokens:
            return "preserve_all"

        compression_ratio = max_tokens / original_tokens

        # 策略选择逻辑
        if critical_count > 0 and compression_ratio > 0.8:
            return "preserve_all"  # 有关键内容且空间充足，完全保留
        elif compression_ratio > 0.5:
            return "smart_reduce"  # 空间中等，智能简化
        elif compression_ratio > 0.2:
            return "essence_only"  # 空间紧张，提取精华
        else:
            return "minimal"  # 空间极小，最小压缩

    def _execute_intelligent_compression(self, analyzed_context: Dict, strategy: str,
                                       max_tokens: int, preserve_critical: bool) -> Dict:
        """执行智能压缩策略"""
        compression_func = self.compression_strategies[strategy]
        return compression_func(analyzed_context, max_tokens, preserve_critical)

    def _preserve_completely(self, analyzed_context: Dict, max_tokens: int, preserve_critical: bool) -> Dict:
        """完全保留策略"""
        self.logger.debug("使用完全保留策略")
        return analyzed_context["original_data"]

    def _smart_reduction(self, analyzed_context: Dict, max_tokens: int, preserve_critical: bool) -> Dict:
        """智能简化策略 - 保留重要信息，简化次要信息"""
        self.logger.debug("使用智能简化策略")

        compressed = {}
        sorted_elements = sorted(analyzed_context["weighted_elements"].items(),
                               key=lambda x: x[1]["effective_weight"], reverse=True)

        # 优先保留关键元素
        for element_key, element_analysis in sorted_elements:
            if element_analysis["is_critical"] and preserve_critical:
                # 关键元素完全保留
                compressed[element_key] = element_analysis["value"]
            elif element_analysis["effective_weight"] > 0.6:
                # 高权重元素适度压缩
                compressed[element_key] = self._smart_text_compress(
                    element_analysis["value"],
                    target_ratio=0.7
                )
            elif element_analysis["effective_weight"] > 0.3:
                # 中等权重元素大幅压缩
                compressed[element_key] = self._smart_text_compress(
                    element_analysis["value"],
                    target_ratio=0.4
                )
            # 低权重元素可能被丢弃或最小化

        return compressed

    def _extract_essence(self, analyzed_context: Dict, max_tokens: int, preserve_critical: bool) -> Dict:
        """提取精华策略 - 只保留最核心的信息"""
        self.logger.debug("使用精华提取策略")

        compressed = {}

        # 只保留权重最高的前N个元素
        sorted_elements = sorted(analyzed_context["weighted_elements"].items(),
                               key=lambda x: x[1]["effective_weight"], reverse=True)

        for element_key, element_analysis in sorted_elements[:5]:  # 只保留前5个重要元素
            if element_analysis["effective_weight"] > 0.3 or preserve_critical:
                compressed[element_key] = self._extract_core_essence(
                    element_analysis["value"],
                    max_length=200
                )

        return compressed

    def _minimal_compression(self, analyzed_context: Dict, max_tokens: int, preserve_critical: bool) -> Dict:
        """最小压缩策略 - 只保留最基本的标识信息"""
        self.logger.debug("使用最小压缩策略")

        compressed = {}

        # 只保留关键元素的最基本信息
        for element_key, element_analysis in analyzed_context["weighted_elements"].items():
            if element_analysis["is_critical"] and preserve_critical:
                compressed[element_key] = self._create_minimal_summary(element_analysis["value"])

        return compressed

    def _smart_text_compress(self, text_data: Any, target_ratio: float) -> Any:
        """智能文本压缩"""
        if isinstance(text_data, str):
            # 保留关键词和句子结构
            sentences = text_data.split('。')
            target_sentences = max(1, int(len(sentences) * target_ratio))
            return '。'.join(sentences[:target_sentences]) + '。' if sentences else text_data
        elif isinstance(text_data, list):
            # 压缩列表
            target_items = max(1, int(len(text_data) * target_ratio))
            return text_data[:target_items]
        elif isinstance(text_data, dict):
            # 压缩字典
            compressed = {}
            for key, value in text_data.items():
                if isinstance(value, str) and len(value) > 100:
                    compressed[key] = value[:int(100 * target_ratio)] + "..."
                else:
                    compressed[key] = value
            return compressed
        else:
            return text_data

    def _extract_core_essence(self, data: Any, max_length: int = 100) -> Any:
        """提取数据的核心精华"""
        if isinstance(data, str):
            # 提取关键词和重要句子
            sentences = data.split('。')
            essence = []
            current_length = 0

            for sentence in sentences:
                sentence = sentence.strip()
                if sentence and current_length + len(sentence) <= max_length:
                    if self._is_important_sentence(sentence):
                        essence.append(sentence)
                        current_length += len(sentence) + 1  # 加上句号

            return '。'.join(essence) + '。' if essence else data[:max_length]
        elif isinstance(data, dict):
            # 只保留关键字段
            key_fields = ["name", "title", "status", "summary", "main", "key"]
            essence = {}
            for key in key_fields:
                if key in data:
                    value = data[key]
                    if isinstance(value, str) and len(value) > max_length:
                        essence[key] = value[:max_length] + "..."
                    else:
                        essence[key] = value
            return essence
        else:
            return data

    def _create_minimal_summary(self, data: Any) -> Any:
        """创建最小化摘要"""
        if isinstance(data, str):
            # 只保留名称或状态
            words = data.split(' ')
            return words[0] if words else data[:20]
        elif isinstance(data, dict):
            # 只保留名称字段
            summary = {}
            for key in ["name", "title", "status"]:
                if key in data:
                    summary[key] = str(data[key])[:30]
            return summary
        else:
            return str(data)[:30]

    def _is_important_sentence(self, sentence: str) -> bool:
        """判断句子是否重要"""
        important_patterns = [
            r'.*突破.*', r'.*觉醒.*', r'.*传承.*',  # 主线相关
            r'.*决战.*', r'.*生死.*', r'.*关键.*',  # 重要事件
            r'.*决定.*', r'.*选择.*', r'.*命运.*',  # 关键决定
        ]

        return any(re.search(pattern, sentence) for pattern in important_patterns)

    def _estimate_tokens_fast(self, data: Any) -> int:
        """快速估算token数量"""
        if isinstance(data, str):
            return len(data)  # 简化估算：1字符≈1token
        elif isinstance(data, (list, dict)):
            try:
                data_str = json.dumps(data, ensure_ascii=False)
                return len(data_str)
            except:
                return len(str(data))
        else:
            return len(str(data))

    def get_compression_insights(self) -> Dict:
        """获取压缩洞察和统计"""
        insights = self._compression_stats.copy()
        insights.update({
            "strategy_weights": self.weights,
            "critical_keywords_count": sum(len(keywords) for keywords in self.critical_keywords.values()),
            "available_strategies": list(self.compression_strategies.keys())
        })
        return insights

    def update_weights(self, new_weights: Dict):
        """动态调整权重配置"""
        self.weights.update(new_weights)
        self._compression_stats["weight_adjustments"] += 1
        self.logger.info("权重配置已更新")

    def add_critical_keywords(self, category: str, keywords: List[str]):
        """添加新的关键词"""
        if category not in self.critical_keywords:
            self.critical_keywords[category] = []
        self.critical_keywords[category].extend(keywords)
        self.logger.info(f"已添加{len(keywords)}个{category}关键词")