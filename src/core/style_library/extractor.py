"""
文风特征提取器
从文本中提取可量化的风格特征
"""

import re
import statistics
from typing import List, Dict, Set
from collections import Counter

from .database import StyleFingerprint


class StyleExtractor:
    """风格特征提取器"""
    
    # 口语化词汇
    COLLOQUIAL_WORDS = {
        '啊', '呢', '吧', '吗', '嘛', '呗', '哈', '哟', '嘿', '哎',
        '喂', '哼', '嗯', '哦', '呃', '唉', '哇', '啦', '喽', '呦',
        '啥', '咋', '咱', '自个儿', '玩意儿', '家伙', '小子',
        '卧槽', '我去', '特么', ' goddamn', ' freaking'
    }
    
    # 语气词
    FILLER_WORDS = {'啊', '呢', '吧', '吗', '嘛', '呗', '哈', '哟', '啦', '喽', '哦', '嗯'}
    
    # 过渡词
    TRANSITION_WORDS = {
        '然后', '接着', '随后', '紧接着', '之后', '后来', '接着',
        '首先', '其次', '最后', '总之', '综上所述', '总而言之',
        '突然', '忽然', '猛然', '蓦地', '陡然', '骤然'
    }
    
    # 感官词
    SENSORY_WORDS = {
        'visual': ['看', '见', '望', '瞧', '盯', '瞥', '扫', '视', '瞅',
                   '红', '绿', '蓝', '白', '黑', '亮', '暗', '光', '影',
                   '大', '小', '高', '矮', '长', '短', '圆', '方'],
        'auditory': ['听', '闻', '响', '声', '音', '叫', '喊', '说', '吵',
                     '闹', '静', '寂', '嗡', '哗', '咚', '啪'],
        'tactile': ['摸', '触', '碰', '感', '冷', '热', '凉', '暖', '烫',
                    '软', '硬', '滑', '糙', '湿', '干', '疼', '痛'],
        'olfactory': ['闻', '嗅', '香', '臭', '味', '气', '腥', '臊'],
        'gustatory': ['尝', '吃', '喝', '品', '甜', '酸', '苦', '辣', '咸']
    }
    
    # 情绪词
    EMOTION_WORDS = {
        '愤怒': ['怒', '恨', '怒', '愤', '恼', '气', '暴怒', '愤怒', '恼火'],
        '喜悦': ['喜', '乐', '笑', '高兴', '开心', '愉快', '兴奋', '激动'],
        '悲伤': ['悲', '哀', '哭', '伤心', '难过', '痛苦', '绝望'],
        '恐惧': ['怕', '惧', '恐', '害怕', '恐惧', '惊恐', '战栗'],
        '惊讶': ['惊', '讶', '惊讶', '震惊', '意外', '吃惊', '愣住'],
    }
    
    # 讲述型词汇（vs展示型）
    TELLING_WORDS = {
        '感到', '觉得', '认为', '想到', '意识到', '明白', '知道',
        '感觉', '发觉', '发现', '觉得', '心想', '暗想'
    }
    
    def extract(self, text: str) -> StyleFingerprint:
        """
        从文本提取风格指纹
        
        Args:
            text: 章节文本
            
        Returns:
            StyleFingerprint 风格指纹对象
        """
        if not text or len(text) < 100:
            return StyleFingerprint()
        
        fingerprint = StyleFingerprint()
        
        # 提取各维度特征
        self._extract_sentence_features(text, fingerprint)
        self._extract_vocabulary_features(text, fingerprint)
        self._extract_rhythm_features(text, fingerprint)
        self._extract_emotion_features(text, fingerprint)
        
        # 重新计算完整向量
        fingerprint.full_vector = fingerprint.to_vector()
        
        return fingerprint
    
    def _extract_sentence_features(self, text: str, fp: StyleFingerprint):
        """提取句式特征"""
        # 分句
        sentences = re.split(r'[。！？…]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        
        if not sentences:
            return
        
        # 基本统计
        lengths = [len(s) for s in sentences]
        fp.avg_sentence_length = statistics.mean(lengths)
        
        if len(lengths) > 1:
            fp.sentence_variance = statistics.variance(lengths)
        
        # 短句/长句比例
        short_count = sum(1 for l in lengths if l < 10)
        long_count = sum(1 for l in lengths if l > 50)
        fp.short_sentence_ratio = short_count / len(lengths)
        fp.long_sentence_ratio = long_count / len(lengths)
        
        # 破碎句（<5字）
        fragment_count = sum(1 for l in lengths if l < 5)
        fp.fragment_ratio = fragment_count / len(lengths)
        
        # 问句/感叹句比例
        fp.question_ratio = text.count('？') / len(sentences)
        fp.exclamation_ratio = text.count('！') / len(sentences)
    
    def _extract_vocabulary_features(self, text: str, fp: StyleFingerprint):
        """提取词汇特征"""
        total_chars = len(text)
        if total_chars == 0:
            return
        
        # 口语化密度
        colloquial_count = sum(text.count(w) for w in self.COLLOQUIAL_WORDS)
        fp.colloquialism_density = colloquial_count / total_chars
        
        # 语气词密度
        filler_count = sum(text.count(w) for w in self.FILLER_WORDS)
        fp.filler_word_density = filler_count / total_chars
        
        # 词汇丰富度（简单近似：不同4字词 / 总词数）
        words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
        if words:
            fp.unique_word_ratio = len(set(words)) / len(words)
        
        # 重复率（出现3次以上的词占比）
        word_counts = Counter(words)
        repeated = sum(1 for w, c in word_counts.items() if c > 2)
        if word_counts:
            fp.repetition_ratio = repeated / len(word_counts)
    
    def _extract_rhythm_features(self, text: str, fp: StyleFingerprint):
        """提取节奏特征"""
        # 对话占比（引号内内容）
        dialogues = re.findall(r'["""]([^"""]+)["""]', text)
        dialogue_text = ''.join(dialogues)
        fp.dialogue_ratio = len(dialogue_text) / len(text) if text else 0
        
        # 段落长度
        paragraphs = [p.strip() for p in text.split('\n') if p.strip()]
        if paragraphs:
            fp.paragraph_avg_length = statistics.mean([len(p) for p in paragraphs])
        
        # 过渡词比例
        transition_count = sum(text.count(w) for w in self.TRANSITION_WORDS)
        fp.transition_word_ratio = transition_count / len(text) if text else 0
        
        # 硬切比例（段落间无过渡）
        if len(paragraphs) > 1:
            hard_cuts = 0
            for i in range(len(paragraphs) - 1):
                if not any(w in paragraphs[i][-20:] for w in self.TRANSITION_WORDS):
                    if not any(w in paragraphs[i+1][:20] for w in self.TRANSITION_WORDS):
                        hard_cuts += 1
            fp.hard_cut_ratio = hard_cuts / (len(paragraphs) - 1)
    
    def _extract_emotion_features(self, text: str, fp: StyleFingerprint):
        """提取情感特征"""
        total_chars = len(text)
        if total_chars == 0:
            return
        
        # 感官描写密度
        sensory_count = 0
        for sense_words in self.SENSORY_WORDS.values():
            sensory_count += sum(text.count(w) for w in sense_words)
        fp.sensory_density = sensory_count / total_chars
        
        # 情绪词密度
        emotion_count = 0
        for emotion_words in self.EMOTION_WORDS.values():
            emotion_count += sum(text.count(w) for w in emotion_words)
        fp.emotion_word_density = emotion_count / total_chars
        
        # 展示vs讲述（简单近似：讲述词比例越低越好）
        telling_count = sum(text.count(w) for w in self.TELLING_WORDS)
        fp.showing_ratio = 1 - (telling_count / total_chars if total_chars else 0)
    
    def extract_batch(self, texts: List[str]) -> StyleFingerprint:
        """
        批量提取，返回平均指纹
        
        用于：一本小说的多个章节 → 综合风格指纹
        """
        fingerprints = [self.extract(t) for t in texts if t and len(t) > 100]
        
        if not fingerprints:
            return StyleFingerprint()
        
        # 计算平均值
        n = len(fingerprints)
        
        avg_fp = StyleFingerprint()
        avg_fp.avg_sentence_length = sum(f.avg_sentence_length for f in fingerprints) / n
        avg_fp.sentence_variance = sum(f.sentence_variance for f in fingerprints) / n
        avg_fp.short_sentence_ratio = sum(f.short_sentence_ratio for f in fingerprints) / n
        avg_fp.long_sentence_ratio = sum(f.long_sentence_ratio for f in fingerprints) / n
        avg_fp.fragment_ratio = sum(f.fragment_ratio for f in fingerprints) / n
        avg_fp.question_ratio = sum(f.question_ratio for f in fingerprints) / n
        avg_fp.exclamation_ratio = sum(f.exclamation_ratio for f in fingerprints) / n
        avg_fp.colloquialism_density = sum(f.colloquialism_density for f in fingerprints) / n
        avg_fp.filler_word_density = sum(f.filler_word_density for f in fingerprints) / n
        avg_fp.repetition_ratio = sum(f.repetition_ratio for f in fingerprints) / n
        avg_fp.unique_word_ratio = sum(f.unique_word_ratio for f in fingerprints) / n
        avg_fp.dialogue_ratio = sum(f.dialogue_ratio for f in fingerprints) / n
        avg_fp.paragraph_avg_length = sum(f.paragraph_avg_length for f in fingerprints) / n
        avg_fp.transition_word_ratio = sum(f.transition_word_ratio for f in fingerprints) / n
        avg_fp.hard_cut_ratio = sum(f.hard_cut_ratio for f in fingerprints) / n
        avg_fp.sensory_density = sum(f.sensory_density for f in fingerprints) / n
        avg_fp.emotion_word_density = sum(f.emotion_word_density for f in fingerprints) / n
        avg_fp.showing_ratio = sum(f.showing_ratio for f in fingerprints) / n
        
        avg_fp.full_vector = avg_fp.to_vector()
        
        return avg_fp
