"""
头部作品样本数据库
用于存储和管理番茄头部作品的样本数据
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
class ChapterSample:
    """章节样本"""
    id: Optional[int] = None
    novel_id: int = 0
    chapter_number: int = 0
    title: str = ""
    content: str = ""
    word_count: int = 0
    
    # 人味特征指标
    metrics: Dict[str, Any] = None
    
    # 原始文本特征
    sentence_count: int = 0
    avg_sentence_length: float = 0.0
    sentence_variance: float = 0.0
    
    created_at: str = ""
    
    def __post_init__(self):
        if self.metrics is None:
            self.metrics = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


@dataclass
class NovelSample:
    """小说样本"""
    id: Optional[int] = None
    
    # 基本信息
    title: str = ""  # 书名
    author: str = ""  # 作者
    genre: str = ""  # 题材类型
    platform: str = "番茄"  # 平台
    
    # 表现数据（可选）
    total_chapters: int = 0
    total_words: int = 0
    rating: float = 0.0  # 评分
    read_count: int = 0  # 阅读量
    
    # 样本信息
    sample_reason: str = ""  # 为什么选这本作为样本
    style_tags: List[str] = None  # 风格标签
    
    # 分析结果
    overall_metrics: Dict[str, Any] = None  # 整体指标
    
    created_at: str = ""
    
    def __post_init__(self):
        if self.style_tags is None:
            self.style_tags = []
        if self.overall_metrics is None:
            self.overall_metrics = {}
        if not self.created_at:
            self.created_at = datetime.now().isoformat()


class SampleDatabase:
    """头部作品样本数据库"""
    
    def __init__(self, db_path: str = None):
        """
        初始化数据库
        
        Args:
            db_path: 数据库文件路径，默认 data/human_touch_samples/samples.db
        """
        if db_path is None:
            db_path = Path(__file__).parent.parent.parent.parent / "data" / "human_touch_samples" / "samples.db"
        else:
            db_path = Path(db_path)
            
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_db()
        logger.info(f"[SampleDatabase] 数据库初始化完成: {self.db_path}")
    
    def _init_db(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # 小说表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS novels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    author TEXT,
                    genre TEXT,
                    platform TEXT DEFAULT '番茄',
                    total_chapters INTEGER,
                    total_words INTEGER,
                    rating REAL,
                    read_count INTEGER,
                    sample_reason TEXT,
                    style_tags TEXT,  -- JSON数组
                    overall_metrics TEXT,  -- JSON对象
                    created_at TEXT
                )
            ''')
            
            # 章节表
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS chapters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    novel_id INTEGER NOT NULL,
                    chapter_number INTEGER NOT NULL,
                    title TEXT,
                    content TEXT,
                    word_count INTEGER,
                    metrics TEXT,  -- JSON对象
                    sentence_count INTEGER,
                    avg_sentence_length REAL,
                    sentence_variance REAL,
                    created_at TEXT,
                    FOREIGN KEY (novel_id) REFERENCES novels(id)
                )
            ''')
            
            conn.commit()
    
    def add_novel(self, novel: NovelSample) -> int:
        """
        添加小说样本
        
        Returns:
            小说ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO novels 
                (title, author, genre, platform, total_chapters, total_words, 
                 rating, read_count, sample_reason, style_tags, overall_metrics, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                novel.title,
                novel.author,
                novel.genre,
                novel.platform,
                novel.total_chapters,
                novel.total_words,
                novel.rating,
                novel.read_count,
                novel.sample_reason,
                json.dumps(novel.style_tags, ensure_ascii=False),
                json.dumps(novel.overall_metrics, ensure_ascii=False),
                novel.created_at
            ))
            conn.commit()
            return cursor.lastrowid
    
    def add_chapter(self, chapter: ChapterSample) -> int:
        """
        添加章节样本
        
        Returns:
            章节ID
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO chapters
                (novel_id, chapter_number, title, content, word_count, metrics,
                 sentence_count, avg_sentence_length, sentence_variance, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                chapter.novel_id,
                chapter.chapter_number,
                chapter.title,
                chapter.content,
                chapter.word_count,
                json.dumps(chapter.metrics, ensure_ascii=False),
                chapter.sentence_count,
                chapter.avg_sentence_length,
                chapter.sentence_variance,
                chapter.created_at
            ))
            conn.commit()
            return cursor.lastrowid
    
    def get_novel(self, novel_id: int) -> Optional[NovelSample]:
        """获取小说样本"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM novels WHERE id = ?', (novel_id,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_novel(row)
            return None
    
    def get_novel_by_title(self, title: str) -> Optional[NovelSample]:
        """根据书名获取小说样本"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM novels WHERE title = ?', (title,))
            row = cursor.fetchone()
            
            if row:
                return self._row_to_novel(row)
            return None
    
    def get_all_novels(self, genre: str = None) -> List[NovelSample]:
        """
        获取所有小说样本
        
        Args:
            genre: 按题材筛选，None表示全部
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            if genre:
                cursor.execute('SELECT * FROM novels WHERE genre = ? ORDER BY id', (genre,))
            else:
                cursor.execute('SELECT * FROM novels ORDER BY id')
            
            rows = cursor.fetchall()
            return [self._row_to_novel(row) for row in rows]
    
    def get_chapters(self, novel_id: int) -> List[ChapterSample]:
        """获取小说的所有章节样本"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM chapters WHERE novel_id = ? ORDER BY chapter_number', (novel_id,))
            rows = cursor.fetchall()
            return [self._row_to_chapter(row) for row in rows]
    
    def get_genres(self) -> List[str]:
        """获取所有题材类型"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT genre FROM novels WHERE genre IS NOT NULL')
            return [row[0] for row in cursor.fetchall()]
    
    def update_novel_metrics(self, novel_id: int, metrics: Dict[str, Any]):
        """更新小说的整体指标"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE novels SET overall_metrics = ? WHERE id = ?',
                (json.dumps(metrics, ensure_ascii=False), novel_id)
            )
            conn.commit()
    
    def delete_novel(self, novel_id: int):
        """删除小说及其所有章节"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM chapters WHERE novel_id = ?', (novel_id,))
            cursor.execute('DELETE FROM novels WHERE id = ?', (novel_id,))
            conn.commit()
    
    def _row_to_novel(self, row) -> NovelSample:
        """将数据库行转换为NovelSample"""
        return NovelSample(
            id=row['id'],
            title=row['title'],
            author=row['author'],
            genre=row['genre'],
            platform=row['platform'],
            total_chapters=row['total_chapters'],
            total_words=row['total_words'],
            rating=row['rating'],
            read_count=row['read_count'],
            sample_reason=row['sample_reason'],
            style_tags=json.loads(row['style_tags']) if row['style_tags'] else [],
            overall_metrics=json.loads(row['overall_metrics']) if row['overall_metrics'] else {},
            created_at=row['created_at']
        )
    
    def _row_to_chapter(self, row) -> ChapterSample:
        """将数据库行转换为ChapterSample"""
        return ChapterSample(
            id=row['id'],
            novel_id=row['novel_id'],
            chapter_number=row['chapter_number'],
            title=row['title'],
            content=row['content'],
            word_count=row['word_count'],
            metrics=json.loads(row['metrics']) if row['metrics'] else {},
            sentence_count=row['sentence_count'],
            avg_sentence_length=row['avg_sentence_length'],
            sentence_variance=row['sentence_variance'],
            created_at=row['created_at']
        )
    
    def export_to_json(self, output_path: str, genre: str = None):
        """
        导出数据库到JSON
        
        Args:
            output_path: 输出文件路径
            genre: 按题材筛选导出
        """
        novels = self.get_all_novels(genre)
        data = []
        
        for novel in novels:
            novel_dict = asdict(novel)
            novel_dict['chapters'] = [asdict(c) for c in self.get_chapters(novel.id)]
            data.append(novel_dict)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[SampleDatabase] 已导出 {len(data)} 本小说到 {output_path}")
    
    def import_from_json(self, input_path: str):
        """
        从JSON导入样本数据
        
        Args:
            input_path: JSON文件路径
        """
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        count = 0
        for novel_dict in data:
            chapters = novel_dict.pop('chapters', [])
            novel = NovelSample(**novel_dict)
            novel_id = self.add_novel(novel)
            
            for chapter_dict in chapters:
                chapter_dict['novel_id'] = novel_id
                chapter = ChapterSample(**chapter_dict)
                self.add_chapter(chapter)
            
            count += 1
        
        logger.info(f"[SampleDatabase] 已从 {input_path} 导入 {count} 本小说")
