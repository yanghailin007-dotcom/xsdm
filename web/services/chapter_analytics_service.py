# -*- coding: utf-8 -*-
"""
章节分析服务 - 量化分析单章质量，对标番茄头部标准
"""
import json
import re
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class ChapterMetrics:
    """单章质量指标"""
    chapter_num: int
    title: str
    word_count: int
    
    # 番茄算法核心指标
    dialogue_ratio: float  # 对话比例
    shuang_density: float  # 爽点密度（次/千字）
    emotion_density: float  # 情绪词密度
    has_cliffhanger: bool  # 章末是否有钩子
    paragraph_count: int  # 段落数
    long_paragraph_ratio: float  # 长段落(>100字)占比
    
    # 情绪分布
    emotion_breakdown: Dict[str, int]  # 各情绪词出现次数
    
    # 评分
    tomato_score: float  # 番茄算法得分(0-100)
    
    def to_dict(self) -> Dict:
        return asdict(self)


class ChapterAnalyticsService:
    """章节分析服务"""
    
    # 番茄头部标准（国运类Top10均值）
    TOMATO_BENCHMARK = {
        'dialogue_ratio': 50.0,  # %
        'shuang_density': 1.5,   # 次/千字
        'emotion_density': 3.0,  # 次/千字
        'cliffhanger_rate': 100.0,  # %
        'avg_paragraph_length': 35,  # 字
    }
    
    # 爽点关键词
    SHUANG_KEYWORDS = [
        '震惊', '骇然', '不可思议', '不可能', '秒杀', '碾压', '逆天', 
        '恐怖', '妖孽', '怪物', '爽', '畅快', '解气', '打脸', '装逼',
        '牛逼', '卧槽', '天啊', '神了', '无敌', '恐怖如斯'
    ]
    
    # 情绪词分类
    EMOTION_WORDS = {
        '震惊': ['震惊', '骇然', '不可思议', '目瞪口呆', '哗然', '震撼'],
        '恐惧': ['恐惧', '害怕', '颤栗', '惊悚', '恐怖', '绝望', '窒息'],
        '兴奋': ['激动', '兴奋', '热血沸腾', '期待', '振奋', '欢呼'],
        '压抑': ['压抑', '沉重', '灰暗', '窒息', '绝望', '窒息'],
        '爽感': ['爽', '畅快', '解气', '舒服', '痛快', '满足'],
        '愤怒': ['愤怒', '怒火', '气愤', '暴怒', '愤恨', '怒骂']
    }
    
    # 钩子关键词
    CLIFFHANGER_KEYWORDS = ['?', '？', '！', '...', '……', '但是', '然而', 
                           '突然', '没想到', '危机', '危险', '警告', '紧急']
    
    def __init__(self, novel_path: str):
        self.novel_path = Path(novel_path)
        self.chapters_path = self.novel_path / 'chapters'
        self.metrics_cache: Dict[int, ChapterMetrics] = {}
    
    def analyze_chapter(self, chapter_num: int) -> Optional[ChapterMetrics]:
        """分析单章质量"""
        chapter_file = self.chapters_path / f'chapter_{chapter_num:03d}.json'
        
        if not chapter_file.exists():
            return None
        
        try:
            with open(chapter_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            title = data.get('title', f'第{chapter_num}章')
            content = data.get('content', '')
            
            return self._calculate_metrics(chapter_num, title, content)
            
        except Exception as e:
            print(f"[Analytics] 分析第{chapter_num}章失败: {e}")
            return None
    
    def _calculate_metrics(self, chapter_num: int, title: str, content: str) -> ChapterMetrics:
        """计算各项质量指标"""
        word_count = len(content)
        
        # 1. 对话比例
        dialogue_ratio = self._calc_dialogue_ratio(content)
        
        # 2. 爽点密度
        shuang_density = self._calc_shuang_density(content, word_count)
        
        # 3. 情绪词分析
        emotion_breakdown = self._calc_emotion_breakdown(content)
        total_emotion = sum(emotion_breakdown.values())
        emotion_density = (total_emotion / word_count * 1000) if word_count > 0 else 0
        
        # 4. 章末钩子
        has_cliffhanger = self._check_cliffhanger(content)
        
        # 5. 段落分析
        paragraph_count, long_para_ratio = self._analyze_paragraphs(content)
        
        # 6. 番茄算法得分
        tomato_score = self._calc_tomato_score(
            dialogue_ratio, shuang_density, emotion_density, 
            has_cliffhanger, long_para_ratio
        )
        
        return ChapterMetrics(
            chapter_num=chapter_num,
            title=title,
            word_count=word_count,
            dialogue_ratio=dialogue_ratio,
            shuang_density=shuang_density,
            emotion_density=emotion_density,
            has_cliffhanger=has_cliffhanger,
            paragraph_count=paragraph_count,
            long_paragraph_ratio=long_para_ratio,
            emotion_breakdown=emotion_breakdown,
            tomato_score=tomato_score
        )
    
    def _calc_dialogue_ratio(self, content: str) -> float:
        """计算对话比例"""
        # 匹配对话："..." 或 '...' 或 「...」
        # 使用简单的逐字符匹配来避免正则复杂性
        dialogue_len = 0
        in_quote = False
        quote_char = None
        current_dialogue = []
        
        for char in content:
            if char in '"""\'\'\'「」':
                if not in_quote:
                    in_quote = True
                    quote_char = char
                    current_dialogue = []
                elif char == quote_char or (quote_char == '"' and char in '"""') or (quote_char == "'" and char in "'''"):
                    in_quote = False
                    dialogue_len += len(current_dialogue)
                    current_dialogue = []
                else:
                    current_dialogue.append(char)
            elif in_quote:
                current_dialogue.append(char)
        
        return (dialogue_len / len(content) * 100) if content else 0
    
    def _calc_shuang_density(self, content: str, word_count: int) -> float:
        """计算爽点密度"""
        count = sum(content.count(kw) for kw in self.SHUANG_KEYWORDS)
        return (count / word_count * 1000) if word_count > 0 else 0
    
    def _calc_emotion_breakdown(self, content: str) -> Dict[str, int]:
        """计算各情绪词出现次数"""
        breakdown = {}
        for emotion, words in self.EMOTION_WORDS.items():
            count = sum(content.count(w) for w in words)
            breakdown[emotion] = count
        return breakdown
    
    def _check_cliffhanger(self, content: str) -> bool:
        """检查章末是否有钩子"""
        if not content:
            return False
        
        # 检查最后100字
        last_100 = content[-100:]
        return any(kw in last_100 for kw in self.CLIFFHANGER_KEYWORDS)
    
    def _analyze_paragraphs(self, content: str) -> Tuple[int, float]:
        """分析段落结构"""
        paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        if not paragraphs:
            return 0, 0
        
        long_paras = [p for p in paragraphs if len(p) > 100]
        long_ratio = len(long_paras) / len(paragraphs)
        
        return len(paragraphs), long_ratio
    
    def _calc_tomato_score(self, dialogue_ratio: float, shuang_density: float,
                          emotion_density: float, has_cliffhanger: bool,
                          long_para_ratio: float) -> float:
        """计算番茄算法得分"""
        score = 100.0
        
        # 对话比例扣分
        dialogue_gap = max(0, self.TOMATO_BENCHMARK['dialogue_ratio'] - dialogue_ratio)
        score -= dialogue_gap * 0.8
        
        # 爽点密度扣分
        shuang_gap = max(0, self.TOMATO_BENCHMARK['shuang_density'] - shuang_density)
        score -= shuang_gap * 10
        
        # 情绪密度扣分
        emotion_gap = max(0, self.TOMATO_BENCHMARK['emotion_density'] - emotion_density)
        score -= emotion_gap * 8
        
        # 无钩子扣分
        if not has_cliffhanger:
            score -= 15
        
        # 长段落过多扣分
        if long_para_ratio > 0.3:
            score -= (long_para_ratio - 0.3) * 30
        
        return max(0, min(100, score))
    
    def analyze_batch(self, start_chapter: int, end_chapter: int) -> List[ChapterMetrics]:
        """分析一个批次（如1-10章）"""
        results = []
        for num in range(start_chapter, end_chapter + 1):
            metrics = self.analyze_chapter(num)
            if metrics:
                results.append(metrics)
                self.metrics_cache[num] = metrics
        return results
    
    def get_batch_summary(self, metrics_list: List[ChapterMetrics]) -> Dict:
        """生成批次汇总数据"""
        if not metrics_list:
            return {}
        
        total_words = sum(m.word_count for m in metrics_list)
        avg_dialogue = sum(m.dialogue_ratio for m in metrics_list) / len(metrics_list)
        avg_shuang = sum(m.shuang_density for m in metrics_list) / len(metrics_list)
        avg_emotion = sum(m.emotion_density for m in metrics_list) / len(metrics_list)
        cliffhanger_rate = sum(1 for m in metrics_list if m.has_cliffhanger) / len(metrics_list) * 100
        avg_score = sum(m.tomato_score for m in metrics_list) / len(metrics_list)
        
        # 汇总情绪分布
        total_emotion = {}
        for m in metrics_list:
            for emotion, count in m.emotion_breakdown.items():
                total_emotion[emotion] = total_emotion.get(emotion, 0) + count
        
        # 找出问题章节
        problem_chapters = [
            {'num': m.chapter_num, 'title': m.title, 'score': m.tomato_score, 'issues': self._get_issues(m)}
            for m in metrics_list if m.tomato_score < 70
        ]
        
        return {
            'chapter_range': f"{metrics_list[0].chapter_num}-{metrics_list[-1].chapter_num}",
            'total_chapters': len(metrics_list),
            'total_words': total_words,
            'avg_word_count': total_words // len(metrics_list),
            'avg_dialogue_ratio': round(avg_dialogue, 1),
            'avg_shuang_density': round(avg_shuang, 2),
            'avg_emotion_density': round(avg_emotion, 2),
            'cliffhanger_rate': round(cliffhanger_rate, 1),
            'avg_tomato_score': round(avg_score, 1),
            'emotion_breakdown': total_emotion,
            'problem_chapters': problem_chapters,
            'benchmark_comparison': self._compare_to_benchmark(
                avg_dialogue, avg_shuang, avg_emotion, cliffhanger_rate
            )
        }
    
    def _get_issues(self, metrics: ChapterMetrics) -> List[str]:
        """获取章节问题列表"""
        issues = []
        if metrics.dialogue_ratio < 30:
            issues.append(f"对话比例过低({metrics.dialogue_ratio:.1f}%)")
        if metrics.shuang_density < 1.0:
            issues.append(f"爽点密度不足({metrics.shuang_density:.1f}/千字)")
        if not metrics.has_cliffhanger:
            issues.append("缺少章末钩子")
        if metrics.long_paragraph_ratio > 0.3:
            issues.append(f"长段落过多({metrics.long_paragraph_ratio:.1%})")
        return issues
    
    def _compare_to_benchmark(self, dialogue: float, shuang: float, 
                             emotion: float, cliffhanger: float) -> Dict:
        """与番茄标准对比"""
        return {
            'dialogue': {
                'current': round(dialogue, 1),
                'benchmark': self.TOMATO_BENCHMARK['dialogue_ratio'],
                'gap': round(dialogue - self.TOMATO_BENCHMARK['dialogue_ratio'], 1),
                'status': 'ok' if dialogue >= 45 else ('warning' if dialogue >= 30 else 'danger')
            },
            'shuang_density': {
                'current': round(shuang, 2),
                'benchmark': self.TOMATO_BENCHMARK['shuang_density'],
                'gap': round(shuang - self.TOMATO_BENCHMARK['shuang_density'], 2),
                'status': 'ok' if shuang >= 1.3 else ('warning' if shuang >= 0.8 else 'danger')
            },
            'emotion_density': {
                'current': round(emotion, 2),
                'benchmark': self.TOMATO_BENCHMARK['emotion_density'],
                'gap': round(emotion - self.TOMATO_BENCHMARK['emotion_density'], 2),
                'status': 'ok' if emotion >= 2.5 else ('warning' if emotion >= 1.5 else 'danger')
            },
            'cliffhanger_rate': {
                'current': round(cliffhanger, 1),
                'benchmark': self.TOMATO_BENCHMARK['cliffhanger_rate'],
                'gap': round(cliffhanger - self.TOMATO_BENCHMARK['cliffhanger_rate'], 1),
                'status': 'ok' if cliffhanger >= 90 else ('warning' if cliffhanger >= 70 else 'danger')
            }
        }
