"""
人味特征分析器
分析文本的"人味"特征，对比AI文和真人写作的差异
"""

import re
import statistics
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class HumanTouchMetrics:
    """人味特征指标"""
    
    # 句式特征
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    sentence_variance: float = 0.0  # 句长方差 - 重要人味指标
    short_sentence_ratio: float = 0.0  # 短句比例(<10字)
    long_sentence_ratio: float = 0.0  # 长句比例(>50字)
    fragment_ratio: float = 0.0  # 破碎句比例
    
    # 段落特征
    paragraph_count: int = 0
    avg_paragraph_length: float = 0.0
    paragraph_variance: float = 0.0
    
    # 感官描写密度
    visual_density: float = 0.0  # 视觉
    auditory_density: float = 0.0  # 听觉
    tactile_density: float = 0.0  # 触觉
    olfactory_density: float = 0.0  # 嗅觉
    gustatory_density: float = 0.0  # 味觉
    
    # 对话特征
    dialogue_ratio: float = 0.0  # 对话占比
    colloquialism_ratio: float = 0.0  # 口语化比例
    filler_words_count: int = 0  # 语气词数量
    
    # 叙事特征
    transition_word_ratio: float = 0.0  # 过渡词比例
    hard_cut_ratio: float = 0.0  # 硬切比例
    showing_ratio: float = 0.0  # 展示vs讲述比例
    
    # 词汇多样性
    unique_word_ratio: float = 0.0  # 词汇丰富度
    repetition_ratio: float = 0.0  # 重复率
    
    # 整体人味分数
    overall_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'sentence': {
                'count': self.sentence_count,
                'avg_length': round(self.avg_sentence_length, 2),
                'variance': round(self.sentence_variance, 2),
                'short_ratio': round(self.short_sentence_ratio, 2),
                'long_ratio': round(self.long_sentence_ratio, 2),
                'fragment_ratio': round(self.fragment_ratio, 2),
            },
            'paragraph': {
                'count': self.paragraph_count,
                'avg_length': round(self.avg_paragraph_length, 2),
                'variance': round(self.paragraph_variance, 2),
            },
            'sensory': {
                'visual': round(self.visual_density, 3),
                'auditory': round(self.auditory_density, 3),
                'tactile': round(self.tactile_density, 3),
                'olfactory': round(self.olfactory_density, 3),
                'gustatory': round(self.gustatory_density, 3),
            },
            'dialogue': {
                'ratio': round(self.dialogue_ratio, 2),
                'colloquialism_ratio': round(self.colloquialism_ratio, 2),
                'filler_words': self.filler_words_count,
            },
            'narrative': {
                'transition_ratio': round(self.transition_word_ratio, 2),
                'hard_cut_ratio': round(self.hard_cut_ratio, 2),
                'showing_ratio': round(self.showing_ratio, 2),
            },
            'vocabulary': {
                'unique_ratio': round(self.unique_word_ratio, 3),
                'repetition_ratio': round(self.repetition_ratio, 3),
            },
            'overall_score': round(self.overall_score, 2),
        }


class HumanTouchAnalyzer:
    """人味特征分析器"""
    
    # 感官词汇库
    SENSORY_WORDS = {
        'visual': ['看', '见', '望', '瞧', '盯', '瞥', '扫', '视', '观', '瞅', 
                   '红', '绿', '蓝', '白', '黑', '亮', '暗', '光', '影', '色',
                   '大', '小', '高', '矮', '长', '短', '圆', '方'],
        'auditory': ['听', '闻', '响', '声', '音', '叫', '喊', '说', '话', '语',
                     '吵', '闹', '静', '寂', '嗡', '哗', '咚', '啪', '咔'],
        'tactile': ['摸', '触', '碰', '感', '觉', '冷', '热', '凉', '暖', '烫',
                    '软', '硬', '滑', '糙', '湿', '干', '疼', '痛', '痒', '麻'],
        'olfactory': ['闻', '嗅', '香', '臭', '味', '气', '腥', '臊', '膻', '芳'],
        'gustatory': ['尝', '吃', '喝', '品', '甜', '酸', '苦', '辣', '咸', '鲜'],
    }
    
    # 口语化标记
    COLLOQUIAL_MARKERS = ['啊', '呢', '吧', '吗', '嘛', '呗', '哈', '哟', '嘿', '哎',
                          '喂', '哼', '嗯', '哦', '呃', '唉', '哟', '哇', '啦', '喽']
    
    # 语气词
    FILLER_WORDS = ['啊', '呢', '吧', '嘛', '呗', '哈', '哟', '嘿', '哎', '喂',
                    '哼', '嗯', '哦', '呃', '唉', '哇', '啦', '喽', '着', '了']
    
    # 过渡词（过度使用会显得机械）
    TRANSITION_WORDS = ['然后', '接着', '随后', '紧接着', '之后', '后来',
                        '首先', '其次', '最后', '总之', '综上所述',
                        '突然', '忽然', '猛然', '蓦地', '陡然']
    
    # 讲述型词汇（vs展示型）
    TELLING_WORDS = ['感到', '觉得', '认为', '想到', '意识到', '明白', '知道',
                     '非常', '特别', '十分', '极其', '格外', '相当']
    
    def analyze(self, text: str) -> HumanTouchMetrics:
        """
        分析文本的人味特征
        
        Args:
            text: 要分析的文本
            
        Returns:
            HumanTouchMetrics 指标对象
        """
        metrics = HumanTouchMetrics()
        
        if not text or len(text) < 100:
            logger.warning("[HumanTouchAnalyzer] 文本太短，无法分析")
            return metrics
        
        # 基础统计
        self._analyze_sentences(text, metrics)
        self._analyze_paragraphs(text, metrics)
        
        # 内容特征
        self._analyze_sensory(text, metrics)
        self._analyze_dialogue(text, metrics)
        self._analyze_narrative(text, metrics)
        self._analyze_vocabulary(text, metrics)
        
        # 计算整体人味分数
        metrics.overall_score = self._calculate_overall_score(metrics)
        
        return metrics
    
    def _analyze_sentences(self, text: str, metrics: HumanTouchMetrics):
        """分析句式特征"""
        # 分句（按句号、感叹号、问号、省略号）
        sentences = re.split(r'[。！？…]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return
        
        metrics.sentence_count = len(sentences)
        
        # 句长统计
        lengths = [len(s) for s in sentences]
        metrics.avg_sentence_length = statistics.mean(lengths)
        
        if len(lengths) > 1:
            metrics.sentence_variance = statistics.variance(lengths)
        
        # 短句和长句比例
        short_count = sum(1 for l in lengths if l < 10)
        long_count = sum(1 for l in lengths if l > 50)
        metrics.short_sentence_ratio = short_count / len(lengths)
        metrics.long_sentence_ratio = long_count / len(lengths)
        
        # 破碎句（极短句，通常是情绪表达）
        fragment_count = sum(1 for l in lengths if l < 5)
        metrics.fragment_ratio = fragment_count / len(lengths)
    
    def _analyze_paragraphs(self, text: str, metrics: HumanTouchMetrics):
        """分析段落特征"""
        paragraphs = text.split('\n')
        paragraphs = [p.strip() for p in paragraphs if p.strip()]
        
        if not paragraphs:
            return
        
        metrics.paragraph_count = len(paragraphs)
        
        lengths = [len(p) for p in paragraphs]
        metrics.avg_paragraph_length = statistics.mean(lengths)
        
        if len(lengths) > 1:
            metrics.paragraph_variance = statistics.variance(lengths)
    
    def _analyze_sensory(self, text: str, metrics: HumanTouchMetrics):
        """分析感官描写密度"""
        total_chars = len(text)
        if total_chars == 0:
            return
        
        for sense, words in self.SENSORY_WORDS.items():
            count = sum(text.count(w) for w in words)
            density = count / total_chars
            
            if sense == 'visual':
                metrics.visual_density = density
            elif sense == 'auditory':
                metrics.auditory_density = density
            elif sense == 'tactile':
                metrics.tactile_density = density
            elif sense == 'olfactory':
                metrics.olfactory_density = density
            elif sense == 'gustatory':
                metrics.gustatory_density = density
    
    def _analyze_dialogue(self, text: str, metrics: HumanTouchMetrics):
        """分析对话特征"""
        # 提取对话内容（引号内）
        dialogues = re.findall(r'["""]([^"""]+)["""]', text)
        dialogue_text = ''.join(dialogues)
        
        if len(text) > 0:
            metrics.dialogue_ratio = len(dialogue_text) / len(text)
        
        # 口语化程度
        colloquial_count = sum(dialogue_text.count(w) for w in self.COLLOQUIAL_MARKERS)
        if len(dialogue_text) > 0:
            metrics.colloquialism_ratio = colloquial_count / len(dialogue_text)
        
        # 语气词
        metrics.filler_words_count = sum(text.count(w) for w in self.FILLER_WORDS)
    
    def _analyze_narrative(self, text: str, metrics: HumanTouchMetrics):
        """分析叙事特征"""
        # 过渡词比例
        transition_count = sum(text.count(w) for w in self.TRANSITION_WORDS)
        metrics.transition_word_ratio = transition_count / len(text) if len(text) > 0 else 0
        
        # 硬切检测（段落间缺少过渡词的情况）
        paragraphs = text.split('\n')
        hard_cuts = 0
        for i in range(len(paragraphs) - 1):
            if not any(w in paragraphs[i][-20:] for w in self.TRANSITION_WORDS):
                if not any(w in paragraphs[i+1][:20] for w in self.TRANSITION_WORDS):
                    hard_cuts += 1
        
        if len(paragraphs) > 1:
            metrics.hard_cut_ratio = hard_cuts / (len(paragraphs) - 1)
        
        # 展示vs讲述（简单近似）
        telling_count = sum(text.count(w) for w in self.TELLING_WORDS)
        if len(text) > 0:
            # 讲述比例越低越好（展示更多）
            metrics.showing_ratio = 1 - (telling_count / len(text))
    
    def _analyze_vocabulary(self, text: str, metrics: HumanTouchMetrics):
        """分析词汇特征"""
        # 简单分词（按字和常见词）
        words = re.findall(r'[\u4e00-\u9fa5]{1,4}', text)
        
        if not words:
            return
        
        unique_words = set(words)
        metrics.unique_word_ratio = len(unique_words) / len(words)
        
        # 重复率（出现次数>2的词占比）
        from collections import Counter
        word_counts = Counter(words)
        repeated = sum(1 for w, c in word_counts.items() if c > 2)
        metrics.repetition_ratio = repeated / len(unique_words) if unique_words else 0
    
    def _calculate_overall_score(self, metrics: HumanTouchMetrics) -> float:
        """
        计算整体人味分数
        
        基于多个指标的加权平均
        """
        scores = []
        weights = []
        
        # 句长方差（最重要）
        if metrics.sentence_variance > 0:
            # 方差20-30为佳，超过50可能太混乱
            variance_score = min(metrics.sentence_variance / 25, 1.0)
            scores.append(variance_score)
            weights.append(0.25)
        
        # 破碎句比例
        if metrics.fragment_ratio > 0:
            # 0.1-0.2为佳
            fragment_score = 1 - abs(metrics.fragment_ratio - 0.15) / 0.15
            scores.append(max(0, fragment_score))
            weights.append(0.15)
        
        # 感官密度
        sensory_total = (metrics.visual_density + metrics.auditory_density + 
                        metrics.tactile_density + metrics.olfactory_density + 
                        metrics.gustatory_density)
        # 总密度0.02-0.05为佳
        sensory_score = min(sensory_total / 0.03, 1.0)
        scores.append(sensory_score)
        weights.append(0.20)
        
        # 口语化
        scores.append(min(metrics.colloquialism_ratio * 10, 1.0))
        weights.append(0.15)
        
        # 词汇多样性
        scores.append(metrics.unique_word_ratio)
        weights.append(0.15)
        
        # 展示比例
        scores.append(metrics.showing_ratio)
        weights.append(0.10)
        
        if not scores:
            return 0.0
        
        # 加权平均
        total_score = sum(s * w for s, w in zip(scores, weights))
        total_weight = sum(weights)
        
        return (total_score / total_weight) * 100
    
    def compare(self, text1: str, text2: str) -> Dict[str, Any]:
        """
        对比两段文本的人味特征
        
        Returns:
            对比报告
        """
        metrics1 = self.analyze(text1)
        metrics2 = self.analyze(text2)
        
        return {
            'text1': metrics1.to_dict(),
            'text2': metrics2.to_dict(),
            'comparison': {
                'score_diff': round(metrics2.overall_score - metrics1.overall_score, 2),
                'variance_diff': round(metrics2.sentence_variance - metrics1.sentence_variance, 2),
                'sensory_diff': round(
                    (metrics2.visual_density + metrics2.auditory_density) -
                    (metrics1.visual_density + metrics1.auditory_density), 3
                ),
            },
            'conclusion': 'text2更有人味' if metrics2.overall_score > metrics1.overall_score else 'text1更有人味'
        }
    
    def get_baseline(self, genre: str = None) -> Dict[str, float]:
        """
        获取头部作品的基准线指标
        
        这些值应该通过分析大量头部作品样本得到
        """
        # 默认值基于一般观察，实际应该从数据库统计
        baselines = {
            'default': {
                'sentence_variance': 25.0,
                'fragment_ratio': 0.15,
                'sensory_density': 0.04,
                'colloquialism_ratio': 0.05,
                'unique_word_ratio': 0.35,
                'overall_score': 70.0,
            },
            '赘婿': {
                'sentence_variance': 20.0,
                'fragment_ratio': 0.12,
                'sensory_density': 0.03,
                'colloquialism_ratio': 0.08,
                'unique_word_ratio': 0.30,
                'overall_score': 65.0,
            },
            '玄幻': {
                'sentence_variance': 30.0,
                'fragment_ratio': 0.18,
                'sensory_density': 0.05,
                'colloquialism_ratio': 0.04,
                'unique_word_ratio': 0.40,
                'overall_score': 75.0,
            },
        }
        
        return baselines.get(genre, baselines['default'])
