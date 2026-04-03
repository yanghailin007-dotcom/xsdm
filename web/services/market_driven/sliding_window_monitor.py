# -*- coding: utf-8 -*-
"""
SlidingWindowMonitor - 滑动窗口质量监控器

功能：
1. 维护最近N章的质量滑动窗口
2. 检测质量趋势（上升/下降/波动）
3. 触发告警和自动修复
4. 为TacticalPlanner提供反馈
"""

import json
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class WindowMetrics:
    """窗口质量指标"""
    chapter_num: int
    tomato_score: float
    dialogue_ratio: float
    shuang_density: float
    emotion_density: float
    planned_emotion: str
    passed: bool


class SlidingWindowMonitor:
    """
    滑动窗口质量监控器
    
    监控最近N章的质量，检测异常趋势并触发干预。
    """
    
    DEFAULT_CONFIG_PATH = "prompt_packages/default/market_driven/components/emotion_quality_standards.json"
    
    def __init__(self, window_size: int = 6, config_path: str = None):
        self.window_size = window_size
        self.metrics_history: List[WindowMetrics] = []
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = self._load_config()
        
    def _load_config(self) -> Dict:
        """加载配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"[SlidingWindowMonitor] 无法加载配置: {e}")
            return {}
    
    def add_chapter(self, chapter_num: int, metrics: Dict, 
                    planned_emotion: str = '未知') -> Dict:
        """
        添加章节到滑动窗口并检查
        
        Returns:
            {
                'alert': bool,  # 是否触发告警
                'alert_type': str,  # 告警类型
                'window_state': Dict,  # 窗口状态
                'suggestions': List[str]  # 建议
            }
        """
        # 创建指标记录
        window_metric = WindowMetrics(
            chapter_num=chapter_num,
            tomato_score=metrics.get('tomato_score', 0),
            dialogue_ratio=metrics.get('dialogue_ratio', 0),
            shuang_density=metrics.get('shuang_density', 0),
            emotion_density=metrics.get('emotion_density', 0),
            planned_emotion=planned_emotion,
            passed=metrics.get('tomato_score', 0) >= 60
        )
        
        # 添加到历史
        self.metrics_history.append(window_metric)
        
        # 保持窗口大小
        if len(self.metrics_history) > self.window_size:
            self.metrics_history.pop(0)
        
        # 检查窗口状态
        return self._check_window()
    
    def _check_window(self) -> Dict:
        """检查窗口质量状态"""
        if len(self.metrics_history) < 3:
            return {'alert': False, 'window_state': 'insufficient_data'}
        
        result = {
            'alert': False,
            'alert_type': None,
            'window_state': {},
            'suggestions': []
        }
        
        # 计算窗口统计
        scores = [m.tomato_score for m in self.metrics_history]
        dialogues = [m.dialogue_ratio for m in self.metrics_history]
        emotions = [m.planned_emotion for m in self.metrics_history]
        
        avg_score = sum(scores) / len(scores)
        avg_dialogue = sum(dialogues) / len(dialogues)
        
        result['window_state'] = {
            'chapters': [m.chapter_num for m in self.metrics_history],
            'avg_tomato_score': round(avg_score, 1),
            'avg_dialogue_ratio': round(avg_dialogue, 1),
            'score_trend': self._calculate_trend(scores),
            'emotion_sequence': emotions
        }
        
        # 检查1：窗口平均分过低
        window_config = self.config.get('sliding_window_config', {})
        alert_thresholds = window_config.get('alert_thresholds', {})
        
        min_avg_score = alert_thresholds.get('avg_score_drop', 15)  # 默认比前期低15分
        if avg_score < 60:
            result['alert'] = True
            result['alert_type'] = 'low_window_avg'
            result['message'] = f"窗口平均分{avg_score:.1f}过低"
            result['suggestions'].append("下一batch调整情绪规划，增加爽点章节")
        
        # 检查2：低质量章节过多
        low_score_count = sum(1 for s in scores if s < 60)
        max_low_chapters = alert_thresholds.get('low_score_chapters', 2)
        if low_score_count >= max_low_chapters:
            result['alert'] = True
            result['alert_type'] = 'too_many_low_chapters'
            result['message'] = f"窗口内有{low_score_count}章得分低于60"
            result['suggestions'].append("触发自动修复流程，重写低质量章节")
        
        # 检查3：连续对话比例低
        low_dialogue_count = sum(1 for d in dialogues if d < 40)
        max_low_dialogue = alert_thresholds.get('consecutive_low_dialogue', 3)
        if low_dialogue_count >= max_low_dialogue:
            result['alert'] = True
            result['alert_type'] = 'consecutive_low_dialogue'
            result['message'] = f"连续{low_dialogue_count}章对话比例低于40%"
            result['suggestions'].append("强制增加弹幕和围观反应")
        
        # 检查4：连续压抑情绪
        consecutive_depressing = self._count_consecutive_emotions(
            emotions, ['压抑', '紧张']
        )
        if consecutive_depressing >= 2:
            result['alert'] = True
            result['alert_type'] = 'consecutive_depressing'
            result['message'] = f"连续{consecutive_depressing}章压抑情绪"
            result['suggestions'].append("下一章强制改为爽点情绪")
        
        # 检查5：质量下滑趋势
        if len(scores) >= 3:
            if scores[-1] < scores[0] - 10:
                result['alert'] = True
                result['alert_type'] = 'declining_quality'
                result['message'] = f"质量下滑: {scores[0]:.1f} → {scores[-1]:.1f}"
                result['suggestions'].append("调整战术规划，提升下一batch质量")
        
        if result['alert']:
            logger.warning(f"[SlidingWindowMonitor] 触发告警: {result['alert_type']} - {result['message']}")
        
        return result
    
    def _calculate_trend(self, values: List[float]) -> str:
        """计算趋势"""
        if len(values) < 2:
            return 'stable'
        
        first = values[0]
        last = values[-1]
        diff = last - first
        
        if diff > 5:
            return 'up'
        elif diff < -5:
            return 'down'
        return 'stable'
    
    def _count_consecutive_emotions(self, emotions: List[str], 
                                    target_emotions: List[str]) -> int:
        """统计连续目标情绪数"""
        count = 0
        for emotion in reversed(emotions):
            if emotion in target_emotions:
                count += 1
            else:
                break
        return count
    
    def get_window_report(self) -> Dict:
        """获取窗口质量报告"""
        if not self.metrics_history:
            return {'status': 'empty'}
        
        scores = [m.tomato_score for m in self.metrics_history]
        dialogues = [m.dialogue_ratio for m in self.metrics_history]
        
        return {
            'window_size': self.window_size,
            'current_size': len(self.metrics_history),
            'chapters': [m.chapter_num for m in self.metrics_history],
            'avg_tomato_score': round(sum(scores) / len(scores), 1),
            'avg_dialogue_ratio': round(sum(dialogues) / len(dialogues), 1),
            'min_score': min(scores),
            'max_score': max(scores),
            'score_trend': self._calculate_trend(scores),
            'emotions': [m.planned_emotion for m in self.metrics_history],
            'low_quality_chapters': [
                {'ch': m.chapter_num, 'score': m.tomato_score}
                for m in self.metrics_history if m.tomato_score < 60
            ]
        }
    
    def should_trigger_auto_fix(self) -> Dict:
        """
        判断是否触发自动修复
        
        Returns:
            {
                'trigger': bool,
                'fix_type': str,
                'target_chapters': List[int]
            }
        """
        window_config = self.config.get('sliding_window_config', {})
        auto_fix_config = window_config.get('auto_fix_trigger', {})
        
        scores = [m.tomato_score for m in self.metrics_history]
        
        # 触发条件1：单章得分过低
        single_threshold = auto_fix_config.get('single_chapter_score_below', 60)
        for m in self.metrics_history:
            if m.tomato_score < single_threshold:
                return {
                    'trigger': True,
                    'fix_type': 'rewrite_chapter',
                    'target_chapters': [m.chapter_num],
                    'reason': f'第{m.chapter_num}章得分{m.tomato_score:.1f}低于阈值{single_threshold}'
                }
        
        # 触发条件2：窗口平均分过低
        window_threshold = auto_fix_config.get('window_avg_score_below', 65)
        if len(scores) >= 3:
            avg = sum(scores) / len(scores)
            if avg < window_threshold:
                return {
                    'trigger': True,
                    'fix_type': 'adjust_next_batch',
                    'target_chapters': [m.chapter_num for m in self.metrics_history],
                    'reason': f'窗口平均分{avg:.1f}低于阈值{window_threshold}'
                }
        
        # 触发条件3：连续压抑
        max_consecutive = auto_fix_config.get('consecutive_depressing', 2)
        emotions = [m.planned_emotion for m in self.metrics_history]
        consecutive = self._count_consecutive_emotions(emotions, ['压抑', '紧张'])
        if consecutive >= max_consecutive:
            return {
                'trigger': True,
                'fix_type': 'force_satisfaction',
                'target_chapters': [],
                'reason': f'连续{consecutive}章压抑情绪',
                'next_emotion': '大爽'
            }
        
        return {'trigger': False}
    
    def clear_window(self):
        """清空窗口"""
        self.metrics_history.clear()
        logger.info("[SlidingWindowMonitor] 窗口已清空")
