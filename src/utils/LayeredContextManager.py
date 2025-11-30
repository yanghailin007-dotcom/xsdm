"""分层上下文管理器 - 根据章节距离动态调整上下文详细程度"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from typing import Dict, List, Optional, Any, Tuple
import json
import re
from src.utils.logger import get_logger

class LayeredContextManager:
    """分层上下文管理器 - 解决token超长问题"""

    def __init__(self):
        self.logger = get_logger("LayeredContextManager")

        # 优化的分层阈值配置 - 更激进的压缩策略
        self.layer_thresholds = {
            "immediate": 2,   # 即时：1-2章前，保留完整细节
            "close": 5,        # 近距离：3-5章前，轻度压缩
            "medium": 10,      # 中距离：6-10章前，中度压缩
            "far": 20,         # 远距离：11-20章前，重度压缩
            "distant": None    # 极远：21+章前，极简压缩
        }

        # 上下文压缩策略 - 更细粒度的控制
        self.compression_strategies = {
            "immediate": self._get_full_context,
            "close": self._get_light_compression,
            "medium": self._get_moderate_compression,
            "far": self._get_heavy_compression,
            "distant": self._get_extreme_compression
        }

        # 缓存机制 - 避免重复压缩
        self._compression_cache: Dict[str, Tuple[Dict, int]] = {}

        # 性能统计
        self._compression_stats = {
            "total_compressions": 0,
            "cache_hits": 0,
            "original_tokens": 0,
            "compressed_tokens": 0
        }

    def get_context_layer(self, current_chapter: int, target_chapter: int) -> str:
        """
        根据章节距离确定上下文层别
        Args:
            current_chapter: 当前章节号
            target_chapter: 目标上下文章节号
        Returns:
            上下文层别: "immediate", "close", "medium", "far", "distant"
        """
        distance = current_chapter - target_chapter

        if distance <= 0:
            return "immediate"  # 当前或未来章节，使用完整上下文
        elif distance <= self.layer_thresholds["immediate"]:
            return "immediate"
        elif distance <= self.layer_thresholds["close"]:
            return "close"
        elif distance <= self.layer_thresholds["medium"]:
            return "medium"
        elif distance <= self.layer_thresholds["far"]:
            return "far"
        else:
            return "distant"

    def compress_context(self, context_data: Dict, current_chapter: int,
                        context_chapter: int = None, context_type: str = "general",
                        use_cache: bool = True) -> Dict:
        """
        根据距离压缩上下文数据（优化版）
        Args:
            context_data: 原始上下文数据
            current_chapter: 当前章节号
            context_chapter: 上下文所属章节号（可选）
            context_type: 上下文类型（"general", "event", "character", "plot"等）
            use_cache: 是否使用缓存
        Returns:
            压缩后的上下文数据
        """
        if context_chapter is None:
            layer = "immediate"  # 无章节信息的上下文，使用完整模式
        else:
            layer = self.get_context_layer(current_chapter, context_chapter)

        # 生成缓存键
        cache_key = self._generate_cache_key(context_data, current_chapter, context_chapter, context_type)

        # 检查缓存
        if use_cache and cache_key in self._compression_cache:
            cached_data, cached_chapter = self._compression_cache[cache_key]
            if cached_chapter == current_chapter:
                self._compression_stats["cache_hits"] += 1
                self.logger.debug(f"使用缓存压缩结果: {layer}")
                return cached_data

        self.logger.debug(f"执行上下文压缩: 第{current_chapter}章 -> 第{context_chapter}章, 层级: {layer}")

        # 更新统计
        self._compression_stats["total_compressions"] += 1
        original_tokens = self.estimate_token_count(context_data)
        self._compression_stats["original_tokens"] += original_tokens

        compression_func = self.compression_strategies.get(layer, self._get_extreme_compression)
        compressed_data = compression_func(context_data, context_type)

        # 更新统计
        compressed_tokens = self.estimate_token_count(compressed_data)
        self._compression_stats["compressed_tokens"] += compressed_tokens

        # 缓存结果
        if use_cache:
            self._compression_cache[cache_key] = (compressed_data, current_chapter)

        return compressed_data

    def _get_full_context(self, context_data: Dict, context_type: str) -> Dict:
        """完整上下文 - 适用于即时章节，不压缩"""
        return context_data

    def _get_light_compression(self, context_data: Dict, context_type: str) -> Dict:
        """轻度压缩 - 适用于近距离章节，保留大部分信息"""
        compressed = {}

        if context_type == "event":
            # 事件上下文：保留所有事件，但缩短描述
            compressed = {
                "major_events": self._compress_list_items(context_data.get("major_events", []),
                                                        text_limit=300, keep_all=True),
                "active_events": self._compress_list_items(context_data.get("active_events", []),
                                                         text_limit=200, keep_all=True),
                "trigger_checkpoints": context_data.get("trigger_checkpoints", [])[:3],
                "summary": context_data.get("summary", "")[:500]
            }
        elif context_type == "character":
            # 角色上下文：保留完整结构，缩短文本
            compressed = {
                "main_characters": self._compress_dict_values(context_data.get("main_characters", {}),
                                                           text_limit=400),
                "key_relationships": self._compress_dict_values(context_data.get("key_relationships", {}),
                                                             text_limit=300),
                "character_development_summary": context_data.get("character_development_summary", "")[:600]
            }
        elif context_type == "plot":
            # 情节上下文：保留关键信息，适度缩短
            compressed = {
                "plot_progression": context_data.get("plot_progression", "")[:500],
                "key_plot_points": self._compress_list_items(context_data.get("key_plot_points", []),
                                                          text_limit=200, keep_all=True),
                "current_conflicts": context_data.get("current_conflicts", [])
            }
        else:
            # 通用上下文：保留所有字段，适度缩短
            compressed = self._compress_dict_values(context_data, text_limit=400)

        return compressed

    def _get_moderate_compression(self, context_data: Dict, context_type: str) -> Dict:
        """中度压缩 - 适用于中距离章节"""
        compressed = {}

        if context_type == "event":
            compressed = {
                "major_events": self._compress_list_items(context_data.get("major_events", []),
                                                        text_limit=150, max_items=5),
                "active_events": self._compress_list_items(context_data.get("active_events", []),
                                                         text_limit=100, max_items=8),
                "summary": context_data.get("summary", "")[:300]
            }
        elif context_type == "character":
            compressed = {
                "main_characters": self._compress_dict_values(context_data.get("main_characters", {}),
                                                           text_limit=200),
                "key_relationships": self._summarize_relationships(context_data.get("key_relationships", {})),
                "character_development_summary": context_data.get("character_development_summary", "")[:400]
            }
        elif context_type == "plot":
            compressed = {
                "plot_progression": context_data.get("plot_progression", "")[:300],
                "key_plot_points": self._compress_list_items(context_data.get("key_plot_points", []),
                                                          text_limit=100, max_items=5),
                "current_conflicts": context_data.get("current_conflicts", [])[:3]
            }
        else:
            compressed = self._compress_dict_values(context_data, text_limit=200, max_list_items=5)

        return compressed

    def _get_heavy_compression(self, context_data: Dict, context_type: str) -> Dict:
        """重度压缩 - 适用于远距离章节"""
        compressed = {}

        if context_type == "event":
            compressed = {
                "major_events_summary": self._summarize_events(context_data.get("major_events", [])),
                "active_events_types": self._summarize_event_types(context_data.get("active_events", [])),
                "key_summary": context_data.get("summary", "")[:150]
            }
        elif context_type == "character":
            main_chars = context_data.get("main_characters", {})
            if main_chars:
                first_protagonist = next(iter(main_chars.values())) if isinstance(main_chars, dict) else {}
                compressed = {
                    "protagonist_info": self._extract_character_essence(first_protagonist),
                    "relationship_status": self._summarize_relationships(context_data.get("key_relationships", {}))
                }
        elif context_type == "plot":
            compressed = {
                "main_conflict": self._extract_main_conflict(context_data),
                "plot_status": self._generate_plot_status(context_data.get("plot_progression", ""))
            }
        else:
            compressed = self._extract_core_information(context_data, max_items=3, text_limit=100)

        return compressed

    def _get_extreme_compression(self, context_data: Dict, context_type: str) -> Dict:
        """极简压缩 - 适用于极远距离章节"""
        compressed = {}

        if context_type == "event":
            compressed = {
                "active_status": f"活跃事件: {len(context_data.get('active_events', []))}个",
                "main_event_type": self._get_primary_event_type(context_data.get("major_events", []))
            }
        elif context_type == "character":
            main_chars = context_data.get("main_characters", {})
            if main_chars:
                first_protagonist = next(iter(main_chars.values())) if isinstance(main_chars, dict) else {}
                compressed = {
                    "protagonist_name": first_protagonist.get("name", "未知角色"),
                    "protagonist_status": self._generate_status_summary(first_protagonist)
                }
        elif context_type == "plot":
            compressed = {
                "conflict_level": self._assess_conflict_intensity(context_data.get("current_conflicts", [])),
                "plot_phase": self._determine_plot_phase(context_data.get("plot_progression", ""))
            }
        else:
            compressed = self._extract_minimal_information(context_data)

        return compressed

    # ====== 辅助方法 ======

    def _generate_cache_key(self, context_data: Dict, current_chapter: int,
                          context_chapter: int, context_type: str) -> str:
        """生成缓存键"""
        # 使用数据的哈希值作为键的一部分
        data_str = json.dumps(context_data, sort_keys=True, ensure_ascii=False)[:200]
        import hashlib
        data_hash = hashlib.md5(data_str.encode()).hexdigest()[:8]
        return f"{current_chapter}_{context_chapter}_{context_type}_{data_hash}"

    def _compress_list_items(self, items: List, text_limit: int = 200,
                           max_items: int = None, keep_all: bool = False) -> List:
        """压缩列表中的项目"""
        if not items:
            return []

        if max_items and not keep_all:
            items = items[:max_items]

        compressed_items = []
        for item in items:
            if isinstance(item, dict):
                compressed_item = {}
                for key, value in item.items():
                    if isinstance(value, str) and len(value) > text_limit:
                        compressed_item[key] = value[:text_limit] + "..." if len(value) > text_limit else value
                    else:
                        compressed_item[key] = value
                compressed_items.append(compressed_item)
            elif isinstance(item, str) and len(item) > text_limit:
                compressed_items.append(item[:text_limit] + "..." if len(item) > text_limit else item)
            else:
                compressed_items.append(item)

        return compressed_items

    def _compress_dict_values(self, data: Dict, text_limit: int = 200,
                            max_list_items: int = None) -> Dict:
        """压缩字典中的值"""
        if not isinstance(data, dict):
            return data

        compressed = {}
        for key, value in data.items():
            if isinstance(value, str) and len(value) > text_limit:
                compressed[key] = value[:text_limit] + "..." if len(value) > text_limit else value
            elif isinstance(value, list):
                if max_list_items:
                    compressed[key] = value[:max_list_items]
                else:
                    compressed[key] = self._compress_list_items(value, text_limit=text_limit)
            elif isinstance(value, dict):
                compressed[key] = self._compress_dict_values(value, text_limit)
            else:
                compressed[key] = value

        return compressed

    def _extract_character_essence(self, character_data: Dict) -> Dict:
        """提取角色核心信息"""
        if not isinstance(character_data, dict):
            return {}

        essence = {
            "name": character_data.get("name", ""),
            "role": character_data.get("role", "")
        }

        # 提取关键属性
        if "current_status" in character_data:
            essence["status"] = character_data["current_status"][:100]
        if "description" in character_data:
            essence["desc"] = character_data["description"][:150]

        return essence

    def _summarize_event_types(self, events: List[Dict]) -> str:
        """总结事件类型"""
        if not events:
            return ""

        type_counts = {}
        for event in events:
            event_type = event.get("type", "未分类")
            type_counts[event_type] = type_counts.get(event_type, 0) + 1

        summary_parts = [f"{count}个{event_type}" for event_type, count in type_counts.items()]
        return f"活跃事件: {', '.join(summary_parts[:3])}"

    def _summarize_relationships(self, relationships: Dict) -> str:
        """将关系网络总结为简短描述（兼容方法）"""
        if not isinstance(relationships, dict):
            return ""

        key_relationships = []
        for char, rels in relationships.items():
            if isinstance(rels, list) and rels:
                # 取第一个关系
                key_relationships.append(f"{char}:{rels[0]}")
            elif isinstance(rels, str):
                key_relationships.append(f"{char}:{rels}")

        return "; ".join(key_relationships[:3])  # 只保留前3个关键关系

    def _summarize_events(self, events: List[Dict]) -> str:
        """将事件列表总结为简短描述（兼容方法）"""
        if not events:
            return ""

        event_names = [event.get("name", "事件") for event in events[:3]]
        return f"近期事件: {', '.join(event_names)}"

    def _get_primary_event_type(self, major_events: List[Dict]) -> str:
        """获取主要事件类型"""
        if not major_events:
            return "无主要事件"

        return major_events[0].get("type", "未分类")

    def _generate_status_summary(self, character_data: Dict) -> str:
        """生成状态摘要"""
        if not isinstance(character_data, dict):
            return "状态未知"

        status_parts = []
        if "current_status" in character_data:
            status_parts.append(character_data["current_status"][:50])
        if "role" in character_data:
            status_parts.append(f"角色: {character_data['role']}")

        return " | ".join(status_parts) if status_parts else "状态正常"

    def _extract_main_conflict(self, context_data: Dict) -> str:
        """提取主要冲突"""
        conflicts = context_data.get("current_conflicts", [])
        if conflicts:
            return str(conflicts[0])[:100] if conflicts else ""
        return "无明显冲突"

    def _generate_plot_status(self, plot_progression: str) -> str:
        """生成情节状态"""
        if not plot_progression:
            return "情节状态未知"

        # 简单的情节阶段识别
        if "开始" in plot_progression or "初" in plot_progression:
            return "故事初期"
        elif "发展" in plot_progression or "进行" in plot_progression:
            return "情节发展"
        elif "高潮" in plot_progression or "冲突" in plot_progression:
            return "冲突高潮"
        elif "结尾" in plot_progression or "结局" in plot_progression:
            return "故事收尾"
        else:
            return plot_progression[:50]

    def _assess_conflict_intensity(self, conflicts: List) -> str:
        """评估冲突强度"""
        if not conflicts:
            return "无冲突"
        elif len(conflicts) <= 2:
            return "低强度冲突"
        elif len(conflicts) <= 4:
            return "中等冲突"
        else:
            return "高强度冲突"

    def _determine_plot_phase(self, plot_progression: str) -> str:
        """确定情节阶段"""
        if not plot_progression:
            return "阶段未知"

        phases = {
            "起承转合": ["起", "承", "转", "合"],
            "三幕剧": ["开端", "发展", "结局"],
            "日常": ["日常", "训练", "战斗", "恢复"]
        }

        for phase_name, phase_keywords in phases.items():
            for keyword in phase_keywords:
                if keyword in plot_progression:
                    return phase_name

        return "自定义情节"

    def _extract_core_information(self, context_data: Dict, max_items: int = 3, text_limit: int = 100) -> Dict:
        """提取核心信息"""
        core_info = {}

        # 优先级字段
        priority_keys = ["title", "name", "status", "summary", "current", "active"]

        for key in priority_keys:
            if key in context_data and max_items > 0:
                value = context_data[key]
                if isinstance(value, str) and len(value) > text_limit:
                    core_info[key] = value[:text_limit] + "..."
                else:
                    core_info[key] = value
                max_items -= 1

        return core_info

    def _extract_minimal_information(self, context_data: Dict) -> Dict:
        """提取最小信息"""
        minimal = {}

        # 只保留最关键的字段
        critical_keys = ["name", "title", "status"]
        for key in critical_keys:
            if key in context_data:
                minimal[key] = str(context_data[key])[:50]

        return minimal

    def estimate_token_count(self, data: Any) -> int:
        """
        估算token数量（更精确的方法）
        """
        if isinstance(data, str):
            # 对中文字符使用更精确的估算
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', data))
            english_chars = len(re.findall(r'[a-zA-Z]', data))
            # 中文：1字符≈1.5token，英文：4字符≈3token
            return int(chinese_chars * 1.5 + english_chars * 0.75 + len(data) * 0.1)

        elif isinstance(data, (list, dict)):
            try:
                data_str = json.dumps(data, ensure_ascii=False)
                return self.estimate_token_count(data_str)
            except:
                return len(str(data)) // 2

        else:
            return len(str(data)) // 2

    def get_context_size_info(self, context_data: Dict) -> Dict:
        """获取上下文大小信息（优化版）"""
        try:
            token_count = self.estimate_token_count(context_data)
            context_str = json.dumps(context_data, ensure_ascii=False)

            return {
                "character_count": len(context_str),
                "estimated_tokens": token_count,
                "data_keys": list(context_data.keys()) if isinstance(context_data, dict) else [],
                "is_large": token_count > 1000,  # 超过1000token认为较大
                "compression_level": self._assess_compression_need(token_count)
            }
        except Exception as e:
            return {
                "error": f"无法估算大小: {e}",
                "data_keys": list(context_data.keys()) if isinstance(context_data, dict) else []
            }

    def _assess_compression_need(self, token_count: int) -> str:
        """评估压缩需求级别"""
        if token_count <= 500:
            return "无需压缩"
        elif token_count <= 1000:
            return "轻度压缩"
        elif token_count <= 2000:
            return "中度压缩"
        else:
            return "重度压缩"

    def get_compression_stats(self) -> Dict:
        """获取压缩统计信息"""
        stats = self._compression_stats.copy()

        if stats["total_compressions"] > 0:
            stats["cache_hit_rate"] = f"{(stats['cache_hits'] / stats['total_compressions']) * 100:.1f}%"

            if stats["original_tokens"] > 0:
                compression_ratio = (1 - stats["compressed_tokens"] / stats["original_tokens"]) * 100
                stats["overall_compression_ratio"] = f"{compression_ratio:.1f}%"
        else:
            stats["cache_hit_rate"] = "0.0%"
            stats["overall_compression_ratio"] = "0.0%"

        return stats

    def clear_cache(self):
        """清空缓存"""
        self._compression_cache.clear()
        self.logger.info("已清空压缩缓存")

    def reset_stats(self):
        """重置统计信息"""
        self._compression_stats = {
            "total_compressions": 0,
            "cache_hits": 0,
            "original_tokens": 0,
            "compressed_tokens": 0
        }
        self.logger.info("已重置统计信息")