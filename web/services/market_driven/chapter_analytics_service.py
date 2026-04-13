# -*- coding: utf-8 -*-
"""
Chapter Analytics Service
章节分析服务 - 提供章节质量分析和数据统计

用于批次总结时的质量分析
"""

import json
import logging
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class ChapterAnalyticsService:
    """
    章节分析服务
    
    分析章节质量指标：
    - 情绪密度
    - 爽点密度  
    - 钩子质量
    - 字数统计
    """
    
    def __init__(self, novel_path: str):
        """
        初始化分析服务
        
        Args:
            novel_path: 小说项目路径
        """
        self.novel_path = Path(novel_path)
        self.chapters_dir = self.novel_path / "chapters"
        
    def analyze_chapter(self, chapter_num: int) -> Optional[Dict]:
        """
        分析单个章节
        
        Args:
            chapter_num: 章节号
            
        Returns:
            分析结果字典
        """
        try:
            chapter_file = self.chapters_dir / f"chapter_{chapter_num:03d}.json"
            if not chapter_file.exists():
                return None
                
            with open(chapter_file, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
            
            content = chapter_data.get('content', '')
            
            # 基础分析
            word_count = len(content)
            analysis = {
                "chapter_number": chapter_num,
                "word_count": word_count,
                "emotion_density": self._calculate_emotion_density(content),
                "appeal_density": self._calculate_appeal_density(content),
                "dialogue_ratio": self._calculate_dialogue_ratio(content),
                "shuang_density": self._calculate_appeal_density(content),  # 爽点密度
                "has_hook": self._check_has_hook(content),
                "has_cliffhanger": self._check_has_hook(content),
                "quality_score": chapter_data.get('quality_score', 8.0),
                "tomato_score": chapter_data.get('quality_score', 8.0) * 10  # 转换为百分制
            }
            
            return analysis
            
        except Exception as e:
            logger.error(f"[ChapterAnalytics] 分析章节{chapter_num}失败: {e}")
            return None
    
    def analyze_batch(self, start_ch: int, end_ch: int) -> List[Dict]:
        """
        分析一批章节
        
        Args:
            start_ch: 起始章节
            end_ch: 结束章节
            
        Returns:
            分析结果列表
        """
        results = []
        for ch_num in range(start_ch, end_ch + 1):
            analysis = self.analyze_chapter(ch_num)
            if analysis:
                results.append(analysis)
        return results
    
    def analyze_text(self, content: str) -> Dict:
        """
        分析任意文本的番茄指标（不依赖章节文件）
        
        Args:
            content: 正文内容
            
        Returns:
            分析结果字典
        """
        word_count = len(content)
        dialogue_ratio = self._calculate_dialogue_ratio(content)
        emotion_density = self._calculate_emotion_density(content)
        appeal_density = self._calculate_appeal_density(content)
        has_hook = self._check_has_hook(content)
        
        # 复用 stage_review_optimizer 的番茄评分公式（简化版）
        score = 5.0
        score += min(2.5, dialogue_ratio * 0.05)
        score += min(2.0, appeal_density * 1.0)
        score += min(1.5, emotion_density * 0.5)
        score += 0.5 if has_hook else 0.0
        score += 0.5 if 2000 <= word_count <= 2500 else 0.0
        score -= 1.0 if word_count > 2800 or word_count < 1800 else 0.0
        quality_score = round(max(1.0, min(10.0, score)), 1)
        
        return {
            "word_count": word_count,
            "dialogue_ratio": dialogue_ratio,
            "emotion_density": emotion_density,
            "appeal_density": appeal_density,
            "shuang_density": appeal_density,
            "has_hook": has_hook,
            "quality_score": quality_score,
            "tomato_score": quality_score * 10
        }
    
    def _calculate_emotion_density(self, content: str) -> float:
        """计算情绪词密度"""
        emotion_words = [
            '暴怒', '狂怒', '杀意', '震撼', '骇然', '惊恐', '目瞪口呆', 
            '狂喜', '激动', '兴奋', '畅快', '绝望', '无力', '屈辱',
            '悲愤', '窒息', '错愕', '难以置信', '怀疑人生'
        ]
        
        if not content:
            return 0.0
            
        word_count = len(content)
        emotion_count = sum(1 for word in emotion_words if word in content)
        
        # 每千字的情绪词数
        density = (emotion_count / word_count) * 1000 if word_count > 0 else 0
        return round(density, 2)
    
    def _calculate_appeal_density(self, content: str) -> float:
        """计算爽点密度"""
        appeal_words = [
            '碾压', '横扫', '瞬杀', '秒杀', '摧枯拉朽', '全场死寂',
            '骇然失色', '暴涨', '飙升', '翻倍', '突破', '打脸',
            '反转', '跪服', '求饶', '后悔莫及'
        ]
        
        if not content:
            return 0.0
            
        word_count = len(content)
        appeal_count = sum(1 for word in appeal_words if word in content)
        
        # 每千字的爽点词数
        density = (appeal_count / word_count) * 1000 if word_count > 0 else 0
        return round(density, 2)
    
    def _calculate_dialogue_ratio(self, content: str) -> float:
        """计算对话比例（引号内容占比）"""
        if not content:
            return 0.0
        
        import re
        # 匹配引号内的内容（包括中文引号和英文引号）
        dialogue_patterns = [
            r'"[^"]*"',  # 中文双引号
            r'"[^"]*"',  # 英文双引号
            r'『[^』]*』',  # 中文书名号变体
            r'「[^」]*」',  # 日式引号
            r'【[^】]*】',  # 方括号（弹幕/系统提示）
        ]
        
        dialogue_chars = 0
        for pattern in dialogue_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                dialogue_chars += len(match)
        
        total_chars = len(content)
        ratio = (dialogue_chars / total_chars) * 100 if total_chars > 0 else 0
        return round(ratio, 1)
    
    def _check_has_hook(self, content: str) -> bool:
        """检查是否有章尾钩子"""
        if not content or len(content) < 100:
            return False
            
        # 检查最后100字
        ending = content[-100:]
        
        # 钩子特征
        hook_indicators = [
            '...', '？', '?', '！', '!', 
            '突然', '竟然', '居然', '没想到',
            '与此同时', '远处', '此刻', '下一秒'
        ]
        
        return any(indicator in ending for indicator in hook_indicators)
    
    def get_batch_summary(self, start_ch: int, end_ch: int) -> Dict:
        """
        获取批次总结统计
        
        Args:
            start_ch: 起始章节
            end_ch: 结束章节
            
        Returns:
            批次统计信息
        """
        analyses = self.analyze_batch(start_ch, end_ch)
        
        if not analyses:
            return {
                "total_chapters": 0,
                "avg_word_count": 0,
                "avg_emotion_density": 0,
                "avg_appeal_density": 0,
                "hook_compliance_rate": 0
            }
        
        total = len(analyses)
        
        return {
            "total_chapters": total,
            "avg_word_count": sum(a['word_count'] for a in analyses) / total,
            "avg_emotion_density": sum(a['emotion_density'] for a in analyses) / total,
            "avg_appeal_density": sum(a['appeal_density'] for a in analyses) / total,
            "hook_compliance_rate": sum(1 for a in analyses if a['has_hook']) / total * 100,
            "chapters": analyses
        }
