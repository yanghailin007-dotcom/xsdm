"""
风格匹配器
根据需求匹配最合适的文风
"""

import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from enum import Enum

from .database import StyleDatabase, StyleProfile, StyleFingerprint


class MatchType(Enum):
    """匹配类型"""
    EXACT = "exact"           # 精确匹配
    SIMILAR = "similar"       # 相似度匹配
    HYBRID = "hybrid"         # 混合匹配


@dataclass
class StyleRequirements:
    """风格需求"""
    
    # 基础需求
    genre: Optional[str] = None           # 题材
    tone_tags: List[str] = field(default_factory=list)  # 腔调标签
    pace: Optional[str] = None            # 节奏
    
    # 描述性需求（自然语言）
    description: str = ""                 # 如："快节奏打脸爽文，口语化"
    
    # 精确指标需求（可选）
    target_fingerprint: StyleFingerprint = None
    
    # 权重配置
    weights: Dict[str, float] = field(default_factory=lambda: {
        'genre': 0.3,
        'tone': 0.3,
        'fingerprint': 0.4,
    })


@dataclass
class StyleMatch:
    """匹配结果"""
    profile: StyleProfile
    match_score: float                    # 匹配分数 (0-100)
    match_type: MatchType
    details: Dict[str, float] = field(default_factory=dict)  # 各维度分数


class StyleMatcher:
    """风格匹配器"""
    
    def __init__(self, db: StyleDatabase):
        self.db = db
    
    def match(self, requirements: StyleRequirements, top_k: int = 3) -> List[StyleMatch]:
        """
        根据需求匹配最佳风格
        
        Args:
            requirements: 风格需求
            top_k: 返回前K个结果
            
        Returns:
            List[StyleMatch] 匹配结果列表
        """
        # 1. 获取候选集
        candidates = self._get_candidates(requirements)
        
        if not candidates:
            return []
        
        # 2. 计算匹配分数
        matches = []
        for profile in candidates:
            score, details = self._calculate_match_score(profile, requirements)
            matches.append(StyleMatch(
                profile=profile,
                match_score=score,
                match_type=MatchType.SIMILAR,
                details=details
            ))
        
        # 3. 排序并返回Top-K
        matches.sort(key=lambda x: x.match_score, reverse=True)
        return matches[:top_k]
    
    def match_by_description(self, description: str, genre: str = None, top_k: int = 3) -> List[StyleMatch]:
        """
        根据自然语言描述匹配
        
        示例描述：
        - "像上门龙婿那种快节奏打脸"
        - "道诡异仙的诡异悬疑感"
        - "轻松幽默的都市脑洞风"
        """
        # 解析描述提取需求
        req = self._parse_description(description, genre)
        return self.match(req, top_k)
    
    def find_similar(self, profile_id: int, top_k: int = 3) -> List[StyleMatch]:
        """
        查找与指定风格相似的其他风格
        """
        source = self.db.get_profile(profile_id)
        if not source:
            return []
        
        # 构建需求
        req = StyleRequirements(
            genre=source.genre,
            tone_tags=source.tone_tags,
            target_fingerprint=source.fingerprint
        )
        
        matches = self.match(req, top_k + 1)
        
        # 排除自己
        return [m for m in matches if m.profile.id != profile_id][:top_k]
    
    def mix_styles(self, style_mixes: List[Tuple[int, float]]) -> StyleFingerprint:
        """
        混合多种风格
        
        Args:
            style_mixes: [(profile_id, weight), ...]
            
        Returns:
            混合后的风格指纹
            
        示例：
            mix_styles([(1, 0.7), (2, 0.3)])  # 70%风格1 + 30%风格2
        """
        fingerprints = []
        weights = []
        
        for profile_id, weight in style_mixes:
            profile = self.db.get_profile(profile_id)
            if profile and profile.fingerprint:
                fingerprints.append(profile.fingerprint)
                weights.append(weight)
        
        if not fingerprints:
            return StyleFingerprint()
        
        # 归一化权重
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        # 加权平均
        mixed = StyleFingerprint()
        
        mixed.avg_sentence_length = sum(f.avg_sentence_length * w for f, w in zip(fingerprints, weights))
        mixed.sentence_variance = sum(f.sentence_variance * w for f, w in zip(fingerprints, weights))
        mixed.short_sentence_ratio = sum(f.short_sentence_ratio * w for f, w in zip(fingerprints, weights))
        mixed.long_sentence_ratio = sum(f.long_sentence_ratio * w for f, w in zip(fingerprints, weights))
        mixed.fragment_ratio = sum(f.fragment_ratio * w for f, w in zip(fingerprints, weights))
        mixed.question_ratio = sum(f.question_ratio * w for f, w in zip(fingerprints, weights))
        mixed.exclamation_ratio = sum(f.exclamation_ratio * w for f, w in zip(fingerprints, weights))
        mixed.colloquialism_density = sum(f.colloquialism_density * w for f, w in zip(fingerprints, weights))
        mixed.filler_word_density = sum(f.filler_word_density * w for f, w in zip(fingerprints, weights))
        mixed.repetition_ratio = sum(f.repetition_ratio * w for f, w in zip(fingerprints, weights))
        mixed.unique_word_ratio = sum(f.unique_word_ratio * w for f, w in zip(fingerprints, weights))
        mixed.dialogue_ratio = sum(f.dialogue_ratio * w for f, w in zip(fingerprints, weights))
        mixed.paragraph_avg_length = sum(f.paragraph_avg_length * w for f, w in zip(fingerprints, weights))
        mixed.transition_word_ratio = sum(f.transition_word_ratio * w for f, w in zip(fingerprints, weights))
        mixed.hard_cut_ratio = sum(f.hard_cut_ratio * w for f, w in zip(fingerprints, weights))
        mixed.sensory_density = sum(f.sensory_density * w for f, w in zip(fingerprints, weights))
        mixed.emotion_word_density = sum(f.emotion_word_density * w for f, w in zip(fingerprints, weights))
        mixed.showing_ratio = sum(f.showing_ratio * w for f, w in zip(fingerprints, weights))
        
        mixed.full_vector = mixed.to_vector()
        
        return mixed
    
    def _get_candidates(self, req: StyleRequirements) -> List[StyleProfile]:
        """获取候选风格"""
        # 先按题材筛选
        if req.genre:
            candidates = self.db.list_profiles(genre=req.genre)
        else:
            candidates = self.db.list_profiles()
        
        # 再按腔调筛选
        if req.tone_tags:
            candidates = [c for c in candidates 
                         if any(t in c.tone_tags for t in req.tone_tags)]
        
        return candidates
    
    def _calculate_match_score(self, profile: StyleProfile, req: StyleRequirements) -> Tuple[float, Dict]:
        """计算匹配分数"""
        scores = {}
        weights = req.weights
        
        # 1. 题材匹配
        if req.genre:
            scores['genre'] = 100.0 if profile.genre == req.genre else 0.0
        else:
            scores['genre'] = 50.0  # 无要求时给中等分
        
        # 2. 腔调匹配
        if req.tone_tags:
            matched = len(set(profile.tone_tags) & set(req.tone_tags))
            total = len(set(profile.tone_tags) | set(req.tone_tags))
            scores['tone'] = (matched / total * 100) if total > 0 else 0.0
        else:
            scores['tone'] = 50.0
        
        # 3. 指纹相似度
        if req.target_fingerprint and profile.fingerprint:
            vec1 = np.array(req.target_fingerprint.full_vector)
            vec2 = np.array(profile.fingerprint.full_vector)
            
            # 余弦相似度
            similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-8)
            scores['fingerprint'] = max(0, similarity * 100)
        else:
            scores['fingerprint'] = 50.0
        
        # 加权总分
        total_score = sum(scores[k] * weights.get(k, 0.33) for k in scores)
        
        return total_score, scores
    
    def _parse_description(self, description: str, genre: str = None) -> StyleRequirements:
        """
        解析自然语言描述
        
        简单实现：关键词匹配
        未来可接入LLM进行语义理解
        """
        desc = description.lower()
        
        # 提取腔调标签
        tone_keywords = {
            '热血': ['热血', '燃', '爽', '霸气', '强势'],
            '幽默': ['幽默', '搞笑', '轻松', '吐槽', '逗'],
            '悬疑': ['悬疑', '诡异', '恐怖', '紧张', '压抑'],
            '甜宠': ['甜', '宠', '温馨', '暖', '治愈'],
            '严肃': ['严肃', '沉重', '正经', '写实'],
        }
        
        tone_tags = []
        for tone, keywords in tone_keywords.items():
            if any(kw in desc for kw in keywords):
                tone_tags.append(tone)
        
        # 提取节奏
        pace = None
        if any(kw in desc for kw in ['快', '紧凑', '爽', '打脸']):
            pace = '快节奏'
        elif any(kw in desc for kw in ['慢', '细腻', '温馨', '种田']):
            pace = '慢节奏'
        
        # 检查是否提到具体书名
        # 这里可以查询数据库匹配书名
        
        return StyleRequirements(
            genre=genre,
            tone_tags=tone_tags,
            pace=pace,
            description=description
        )
