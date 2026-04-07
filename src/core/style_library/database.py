"""
文风库数据库
存储头部作品的风格特征
"""

import json
import sqlite3
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


@dataclass
class StyleFingerprint:
    """文风指纹 - 可量化的风格特征"""
    
    # 句式维度
    avg_sentence_length: float = 0.0      # 平均句长
    sentence_variance: float = 0.0        # 句长方差（重要）
    short_sentence_ratio: float = 0.0     # 短句比例(<10字)
    long_sentence_ratio: float = 0.0      # 长句比例(>50字)
    fragment_ratio: float = 0.0           # 破碎句比例
    question_ratio: float = 0.0           # 问句比例
    exclamation_ratio: float = 0.0        # 感叹句比例
    
    # 词汇维度
    colloquialism_density: float = 0.0    # 口语词密度
    filler_word_density: float = 0.0      # 语气词密度
    repetition_ratio: float = 0.0         # 重复率
    unique_word_ratio: float = 0.0        # 词汇丰富度
    
    # 节奏维度
    dialogue_ratio: float = 0.0           # 对话占比
    paragraph_avg_length: float = 0.0     # 平均段长
    transition_word_ratio: float = 0.0    # 过渡词比例
    hard_cut_ratio: float = 0.0           # 硬切比例
    
    # 情感维度
    sensory_density: float = 0.0          # 感官描写密度
    emotion_word_density: float = 0.0     # 情绪词密度
    showing_ratio: float = 0.0            # 展示vs讲述
    
    # 完整向量（用于相似度计算）
    full_vector: List[float] = None
    
    def __post_init__(self):
        if self.full_vector is None:
            self.full_vector = self.to_vector()
    
    def to_vector(self) -> List[float]:
        """转换为特征向量"""
        return [
            self.avg_sentence_length / 50.0,  # 归一化
            min(self.sentence_variance / 50.0, 1.0),
            self.short_sentence_ratio,
            self.long_sentence_ratio,
            self.fragment_ratio,
            self.question_ratio,
            self.exclamation_ratio,
            self.colloquialism_density * 10,  # 放大
            self.filler_word_density * 10,
            1 - self.repetition_ratio,  # 重复率越低越好
            self.unique_word_ratio,
            self.dialogue_ratio,
            self.paragraph_avg_length / 200.0,
            1 - self.transition_word_ratio,  # 过渡词越少越好
            self.hard_cut_ratio,
            self.sensory_density * 20,
            self.emotion_word_density * 10,
            self.showing_ratio,
        ]
    
    def to_dict(self) -> Dict:
        return {
            'avg_sentence_length': self.avg_sentence_length,
            'sentence_variance': self.sentence_variance,
            'short_sentence_ratio': self.short_sentence_ratio,
            'long_sentence_ratio': self.long_sentence_ratio,
            'fragment_ratio': self.fragment_ratio,
            'question_ratio': self.question_ratio,
            'exclamation_ratio': self.exclamation_ratio,
            'colloquialism_density': self.colloquialism_density,
            'filler_word_density': self.filler_word_density,
            'repetition_ratio': self.repetition_ratio,
            'unique_word_ratio': self.unique_word_ratio,
            'dialogue_ratio': self.dialogue_ratio,
            'paragraph_avg_length': self.paragraph_avg_length,
            'transition_word_ratio': self.transition_word_ratio,
            'hard_cut_ratio': self.hard_cut_ratio,
            'sensory_density': self.sensory_density,
            'emotion_word_density': self.emotion_word_density,
            'showing_ratio': self.showing_ratio,
            'full_vector': self.full_vector,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'StyleFingerprint':
        return cls(
            avg_sentence_length=data.get('avg_sentence_length', 0),
            sentence_variance=data.get('sentence_variance', 0),
            short_sentence_ratio=data.get('short_sentence_ratio', 0),
            long_sentence_ratio=data.get('long_sentence_ratio', 0),
            fragment_ratio=data.get('fragment_ratio', 0),
            question_ratio=data.get('question_ratio', 0),
            exclamation_ratio=data.get('exclamation_ratio', 0),
            colloquialism_density=data.get('colloquialism_density', 0),
            filler_word_density=data.get('filler_word_density', 0),
            repetition_ratio=data.get('repetition_ratio', 0),
            unique_word_ratio=data.get('unique_word_ratio', 0),
            dialogue_ratio=data.get('dialogue_ratio', 0),
            paragraph_avg_length=data.get('paragraph_avg_length', 0),
            transition_word_ratio=data.get('transition_word_ratio', 0),
            hard_cut_ratio=data.get('hard_cut_ratio', 0),
            sensory_density=data.get('sensory_density', 0),
            emotion_word_density=data.get('emotion_word_density', 0),
            showing_ratio=data.get('showing_ratio', 0),
            full_vector=data.get('full_vector'),
        )


@dataclass
class StyleProfile:
    """风格档案 - 一本小说的整体风格"""
    
    id: Optional[int] = None
    
    # 基本信息
    title: str = ""                    # 书名
    author: str = ""                   # 作者
    genre: str = ""                    # 题材
    sub_genre: str = ""                # 子题材
    
    # 风格标签（人工标注）
    tone_tags: List[str] = None        # 腔调标签 [热血,幽默,悬疑,甜宠,压抑...]
    pace: str = ""                     # 节奏 [快节奏,慢节奏,张弛有度]
    
    # 风格描述
    description: str = ""              # 风格描述
    key_features: List[str] = None     # 关键特征
    
    # 风格特征
    fingerprint: StyleFingerprint = None  # 风格指纹
    
    # 样本信息
    chapter_count: int = 0             # 样本章节数
    total_sample_words: int = 0        # 总样本字数
    
    # 使用统计
    usage_count: int = 0               # 被使用次数
    rating: float = 0.0                # 用户评分
    
    created_at: str = ""
    updated_at: str = ""
    
    def __post_init__(self):
        if self.tone_tags is None:
            self.tone_tags = []
        if self.key_features is None:
            self.key_features = []
        if self.fingerprint is None:
            self.fingerprint = StyleFingerprint()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


@dataclass
class ChapterSample:
    """章节样本"""
    
    id: Optional[int] = None
    profile_id: int = 0
    
    chapter_number: int = 0
    title: str = ""
    content: str = ""                  # 原文（可选存储）
    word_count: int = 0
    
    fingerprint: StyleFingerprint = None  # 该章的风格指纹
    
    created_at: str = ""
    
    def __post_init__(self):
        if self.fingerprint is None:
            self.fingerprint = StyleFingerprint()
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class StyleDatabase:
    """文风库数据库"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "style_library" / "styles.db"
        else:
            db_path = Path(db_path)
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        logger.info(f"[StyleDatabase] 数据库初始化: {self.db_path}")
    
    def _init_db(self):
        """初始化表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 风格档案表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS style_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    genre TEXT,
                    sub_genre TEXT,
                    tone_tags TEXT,           -- JSON ["热血","快节奏"]
                    pace TEXT,
                    description TEXT,
                    key_features TEXT,        -- JSON
                    fingerprint TEXT,         -- JSON
                    chapter_count INTEGER DEFAULT 0,
                    total_sample_words INTEGER DEFAULT 0,
                    usage_count INTEGER DEFAULT 0,
                    rating REAL DEFAULT 0,
                    created_at TEXT,
                    updated_at TEXT
                )
            ''')
            
            # 章节样本表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chapter_samples (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    profile_id INTEGER NOT NULL,
                    chapter_number INTEGER,
                    title TEXT,
                    content TEXT,
                    word_count INTEGER,
                    fingerprint TEXT,         -- JSON
                    created_at TEXT,
                    FOREIGN KEY (profile_id) REFERENCES style_profiles(id)
                )
            ''')
            
            # 风格混合表（记录用户创建的混合风格）
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS style_mixes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    components TEXT,          -- JSON [{profile_id, weight}, ...]
                    fingerprint TEXT,         -- JSON
                    usage_count INTEGER DEFAULT 0,
                    created_at TEXT
                )
            ''')
            
            conn.commit()
    
    def add_profile(self, profile: StyleProfile) -> int:
        """添加风格档案"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO style_profiles
                (title, author, genre, sub_genre, tone_tags, pace, description,
                 key_features, fingerprint, chapter_count, total_sample_words,
                 usage_count, rating, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                profile.title,
                profile.author,
                profile.genre,
                profile.sub_genre,
                json.dumps(profile.tone_tags, ensure_ascii=False),
                profile.pace,
                profile.description,
                json.dumps(profile.key_features, ensure_ascii=False),
                json.dumps(profile.fingerprint.to_dict(), ensure_ascii=False),
                profile.chapter_count,
                profile.total_sample_words,
                profile.usage_count,
                profile.rating,
                profile.created_at,
                profile.updated_at
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_profile(self, profile_id: int) -> Optional[StyleProfile]:
        """获取风格档案"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM style_profiles WHERE id = ?', (profile_id,))
            row = cursor.fetchone()
            return self._row_to_profile(row) if row else None
    
    def get_profile_by_title(self, title: str) -> Optional[StyleProfile]:
        """根据书名获取"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM style_profiles WHERE title = ?', (title,))
            row = cursor.fetchone()
            return self._row_to_profile(row) if row else None
    
    def list_profiles(self, genre: str = None, tone: str = None) -> List[StyleProfile]:
        """列出风格档案"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if genre and tone:
                cursor.execute('''
                    SELECT * FROM style_profiles 
                    WHERE genre = ? AND tone_tags LIKE ?
                    ORDER BY usage_count DESC, rating DESC
                ''', (genre, f'%"{tone}"%'))
            elif genre:
                cursor.execute('''
                    SELECT * FROM style_profiles WHERE genre = ?
                    ORDER BY usage_count DESC, rating DESC
                ''', (genre,))
            elif tone:
                cursor.execute('''
                    SELECT * FROM style_profiles WHERE tone_tags LIKE ?
                    ORDER BY usage_count DESC, rating DESC
                ''', (f'%"{tone}"%',))
            else:
                cursor.execute('''
                    SELECT * FROM style_profiles 
                    ORDER BY usage_count DESC, rating DESC
                ''')
            
            rows = cursor.fetchall()
            return [self._row_to_profile(row) for row in rows]
    
    def add_chapter(self, chapter: ChapterSample) -> int:
        """添加章节样本"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chapter_samples
                (profile_id, chapter_number, title, content, word_count, fingerprint, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                chapter.profile_id,
                chapter.chapter_number,
                chapter.title,
                chapter.content,
                chapter.word_count,
                json.dumps(chapter.fingerprint.to_dict(), ensure_ascii=False),
                chapter.created_at
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_chapters(self, profile_id: int) -> List[ChapterSample]:
        """获取风格的所有章节样本"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM chapter_samples WHERE profile_id = ?
                ORDER BY chapter_number
            ''', (profile_id,))
            return [self._row_to_chapter(row) for row in cursor.fetchall()]
    
    def update_profile_fingerprint(self, profile_id: int):
        """重新计算风格档案的指纹（基于所有章节）"""
        chapters = self.get_chapters(profile_id)
        if not chapters:
            return
        
        # 计算平均指纹
        avg_fingerprint = self._compute_average_fingerprint([c.fingerprint for c in chapters])
        
        # 更新
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE style_profiles 
                SET fingerprint = ?, chapter_count = ?, updated_at = ?
                WHERE id = ?
            ''', (
                json.dumps(avg_fingerprint.to_dict(), ensure_ascii=False),
                len(chapters),
                datetime.now().isoformat(),
                profile_id
            ))
            conn.commit()
    
    def increment_usage(self, profile_id: int):
        """增加使用计数"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE style_profiles SET usage_count = usage_count + 1 WHERE id = ?
            ''', (profile_id,))
            conn.commit()
    
    def get_genres(self) -> List[str]:
        """获取所有题材"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT genre FROM style_profiles WHERE genre IS NOT NULL')
            return [row[0] for row in cursor.fetchall()]
    
    def get_tone_tags(self) -> List[str]:
        """获取所有腔调标签"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT tone_tags FROM style_profiles')
            all_tags = set()
            for row in cursor.fetchall():
                if row[0]:
                    tags = json.loads(row[0])
                    all_tags.update(tags)
            return sorted(list(all_tags))
    
    def _row_to_profile(self, row) -> StyleProfile:
        """数据库行转对象"""
        return StyleProfile(
            id=row['id'],
            title=row['title'],
            author=row['author'],
            genre=row['genre'],
            sub_genre=row['sub_genre'],
            tone_tags=json.loads(row['tone_tags']) if row['tone_tags'] else [],
            pace=row['pace'],
            description=row['description'],
            key_features=json.loads(row['key_features']) if row['key_features'] else [],
            fingerprint=StyleFingerprint.from_dict(json.loads(row['fingerprint'])) if row['fingerprint'] else StyleFingerprint(),
            chapter_count=row['chapter_count'],
            total_sample_words=row['total_sample_words'],
            usage_count=row['usage_count'],
            rating=row['rating'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def _row_to_chapter(self, row) -> ChapterSample:
        """数据库行转对象"""
        return ChapterSample(
            id=row['id'],
            profile_id=row['profile_id'],
            chapter_number=row['chapter_number'],
            title=row['title'],
            content=row['content'],
            word_count=row['word_count'],
            fingerprint=StyleFingerprint.from_dict(json.loads(row['fingerprint'])) if row['fingerprint'] else StyleFingerprint(),
            created_at=row['created_at']
        )
    
    def _compute_average_fingerprint(self, fingerprints: List[StyleFingerprint]) -> StyleFingerprint:
        """计算平均指纹"""
        if not fingerprints:
            return StyleFingerprint()
        
        n = len(fingerprints)
        
        def avg(values):
            return sum(values) / len(values) if values else 0
        
        return StyleFingerprint(
            avg_sentence_length=avg([f.avg_sentence_length for f in fingerprints]),
            sentence_variance=avg([f.sentence_variance for f in fingerprints]),
            short_sentence_ratio=avg([f.short_sentence_ratio for f in fingerprints]),
            long_sentence_ratio=avg([f.long_sentence_ratio for f in fingerprints]),
            fragment_ratio=avg([f.fragment_ratio for f in fingerprints]),
            question_ratio=avg([f.question_ratio for f in fingerprints]),
            exclamation_ratio=avg([f.exclamation_ratio for f in fingerprints]),
            colloquialism_density=avg([f.colloquialism_density for f in fingerprints]),
            filler_word_density=avg([f.filler_word_density for f in fingerprints]),
            repetition_ratio=avg([f.repetition_ratio for f in fingerprints]),
            unique_word_ratio=avg([f.unique_word_ratio for f in fingerprints]),
            dialogue_ratio=avg([f.dialogue_ratio for f in fingerprints]),
            paragraph_avg_length=avg([f.paragraph_avg_length for f in fingerprints]),
            transition_word_ratio=avg([f.transition_word_ratio for f in fingerprints]),
            hard_cut_ratio=avg([f.hard_cut_ratio for f in fingerprints]),
            sensory_density=avg([f.sensory_density for f in fingerprints]),
            emotion_word_density=avg([f.emotion_word_density for f in fingerprints]),
            showing_ratio=avg([f.showing_ratio for f in fingerprints]),
        )
