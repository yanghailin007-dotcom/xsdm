"""
荣誉墙数据库模型
使用SQLite存储作品分享信息
"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from web.web_config import logger, BASE_DIR


class HonorWallModel:
    """荣誉墙数据模型"""
    
    # 支持的平台配置
    PLATFORMS = {
        'fanqie': {'name': '番茄小说', 'domains': ['fanqienovel.com', 'fanqie.com']},
        'qidian': {'name': '起点读书', 'domains': ['qidian.com', 'book.qidian.com']},
        'qq_read': {'name': 'QQ阅读', 'domains': ['yuewen.com', 'read.qq.com']},
        'jinjiang': {'name': '晋江文学', 'domains': ['jjwxc.net', 'jjwxc.cn']}
    }
    
    def __init__(self, db_path=None):
        """初始化数据库连接"""
        if db_path is None:
            db_path = BASE_DIR / "data" / "users.db"
        elif isinstance(db_path, str):
            db_path = Path(db_path)
        
        self.db_path = str(db_path)
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表结构"""
        with self._get_connection() as conn:
            # 荣誉墙作品表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS honor_wall_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    user_name TEXT NOT NULL,
                    book_title TEXT NOT NULL,
                    book_intro TEXT,
                    platform TEXT NOT NULL,
                    platform_url TEXT NOT NULL,
                    word_count INTEGER DEFAULT 0,
                    likes INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'approved',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id),
                    UNIQUE(user_id, book_title)
                )
            """)
            
            # 点赞记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS honor_wall_likes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (entry_id) REFERENCES honor_wall_entries(id) ON DELETE CASCADE,
                    UNIQUE(entry_id, user_id)
                )
            """)
            
            # 用户分享计数表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_share_counts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER UNIQUE NOT NULL,
                    share_count INTEGER DEFAULT 0,
                    max_shares INTEGER DEFAULT 3,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            conn.commit()
    
    def get_entry(self, entry_id: int) -> Optional[Dict]:
        """获取单条作品信息"""
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM honor_wall_entries WHERE id = ?",
                (entry_id,)
            ).fetchone()
            
            if row:
                return dict(row)
            return None
    
    def list_entries(self, platform: str = 'all', sort_by: str = 'likes', 
                     page: int = 1, per_page: int = 10, search: str = '') -> Dict:
        """获取作品列表"""
        with self._get_connection() as conn:
            # 构建查询条件
            where_clauses = ["status = 'approved'"]
            params = []
            
            if platform != 'all':
                where_clauses.append("platform = ?")
                params.append(platform)
            
            if search:
                where_clauses.append("(book_title LIKE ? OR user_name LIKE ?)")
                params.extend([f'%{search}%', f'%{search}%'])
            
            where_sql = " AND ".join(where_clauses)
            
            # 排序
            sort_map = {
                'likes': 'likes DESC',
                'newest': 'created_at DESC',
                'word_count': 'word_count DESC'
            }
            order_by = sort_map.get(sort_by, 'likes DESC')
            
            # 查询总数
            count_sql = f"SELECT COUNT(*) FROM honor_wall_entries WHERE {where_sql}"
            total = conn.execute(count_sql, params).fetchone()[0]
            
            # 分页查询
            offset = (page - 1) * per_page
            sql = f"""
                SELECT * FROM honor_wall_entries 
                WHERE {where_sql}
                ORDER BY {order_by}
                LIMIT ? OFFSET ?
            """
            params.extend([per_page, offset])
            
            rows = conn.execute(sql, params).fetchall()
            entries = [dict(row) for row in rows]
            
            return {
                'entries': entries,
                'total': total,
                'page': page,
                'pages': (total + per_page - 1) // per_page
            }
    
    def create_entry(self, user_id: int, user_name: str, book_title: str,
                     platform: str, platform_url: str, book_intro: str = '',
                     word_count: int = 0) -> Dict:
        """创建作品分享"""
        with self._get_connection() as conn:
            # 检查是否已分享过
            existing = conn.execute(
                "SELECT id FROM honor_wall_entries WHERE user_id = ? AND book_title = ?",
                (user_id, book_title)
            ).fetchone()
            
            if existing:
                return {'success': False, 'error': '您已分享过这本书'}
            
            # 检查分享次数限制
            share_count = self._get_or_create_share_count(conn, user_id)
            if share_count['share_count'] >= share_count['max_shares']:
                return {
                    'success': False, 
                    'error': f"每人最多分享 {share_count['max_shares']} 本作品"
                }
            
            # 创建条目
            cursor = conn.execute("""
                INSERT INTO honor_wall_entries 
                (user_id, user_name, book_title, book_intro, platform, platform_url, word_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, user_name, book_title, book_intro, platform, platform_url, word_count))
            
            entry_id = cursor.lastrowid
            
            # 更新分享计数
            conn.execute("""
                UPDATE user_share_counts 
                SET share_count = share_count + 1, updated_at = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            conn.commit()
            
            return {
                'success': True,
                'entry_id': entry_id,
                'remaining_shares': share_count['max_shares'] - share_count['share_count'] - 1
            }
    
    def delete_entry(self, entry_id: int, user_id: int) -> Dict:
        """删除作品分享"""
        with self._get_connection() as conn:
            # 验证所有权
            entry = conn.execute(
                "SELECT user_id FROM honor_wall_entries WHERE id = ?",
                (entry_id,)
            ).fetchone()
            
            if not entry:
                return {'success': False, 'error': '作品不存在'}
            
            if entry['user_id'] != user_id:
                return {'success': False, 'error': '无权限删除'}
            
            # 删除条目
            conn.execute("DELETE FROM honor_wall_entries WHERE id = ?", (entry_id,))
            
            # 更新分享计数
            conn.execute("""
                UPDATE user_share_counts 
                SET share_count = MAX(0, share_count - 1), updated_at = ?
                WHERE user_id = ?
            """, (datetime.now().isoformat(), user_id))
            
            conn.commit()
            
            return {'success': True}
    
    def toggle_like(self, entry_id: int, user_id: int) -> Dict:
        """切换点赞状态"""
        with self._get_connection() as conn:
            # 检查是否已点赞
            existing = conn.execute(
                "SELECT id FROM honor_wall_likes WHERE entry_id = ? AND user_id = ?",
                (entry_id, user_id)
            ).fetchone()
            
            if existing:
                # 取消点赞
                conn.execute(
                    "DELETE FROM honor_wall_likes WHERE entry_id = ? AND user_id = ?",
                    (entry_id, user_id)
                )
                conn.execute(
                    "UPDATE honor_wall_entries SET likes = MAX(0, likes - 1) WHERE id = ?",
                    (entry_id,)
                )
                is_liked = False
            else:
                # 添加点赞
                conn.execute(
                    "INSERT INTO honor_wall_likes (entry_id, user_id) VALUES (?, ?)",
                    (entry_id, user_id)
                )
                conn.execute(
                    "UPDATE honor_wall_entries SET likes = likes + 1 WHERE id = ?",
                    (entry_id,)
                )
                is_liked = True
            
            conn.commit()
            
            # 获取更新后的点赞数
            likes = conn.execute(
                "SELECT likes FROM honor_wall_entries WHERE id = ?",
                (entry_id,)
            ).fetchone()[0]
            
            return {'success': True, 'is_liked': is_liked, 'likes': likes}
    
    def is_liked(self, entry_id: int, user_id: int) -> bool:
        """检查用户是否已点赞"""
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT id FROM honor_wall_likes WHERE entry_id = ? AND user_id = ?",
                (entry_id, user_id)
            ).fetchone()
            return result is not None
    
    def get_my_shares(self, user_id: int) -> Dict:
        """获取我的分享列表"""
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM honor_wall_entries WHERE user_id = ? ORDER BY created_at DESC",
                (user_id,)
            ).fetchall()
            
            entries = [dict(row) for row in rows]
            
            share_count = self._get_or_create_share_count(conn, user_id)
            
            return {
                'entries': entries,
                'used': share_count['share_count'],
                'max': share_count['max_shares'],
                'remaining': share_count['max_shares'] - share_count['share_count']
            }
    
    def get_stats(self) -> Dict:
        """获取统计数据"""
        with self._get_connection() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM honor_wall_entries WHERE status = 'approved'"
            ).fetchone()[0]
            
            total_likes = conn.execute(
                "SELECT COALESCE(SUM(likes), 0) FROM honor_wall_entries WHERE status = 'approved'"
            ).fetchone()[0]
            
            total_authors = conn.execute(
                "SELECT COUNT(DISTINCT user_id) FROM honor_wall_entries WHERE status = 'approved'"
            ).fetchone()[0]
            
            return {
                'total': total,
                'total_likes': total_likes,
                'total_authors': total_authors
            }
    
    def _get_or_create_share_count(self, conn: sqlite3.Connection, user_id: int) -> Dict:
        """获取或创建用户分享计数"""
        row = conn.execute(
            "SELECT * FROM user_share_counts WHERE user_id = ?",
            (user_id,)
        ).fetchone()
        
        if row:
            return dict(row)
        
        conn.execute(
            "INSERT INTO user_share_counts (user_id, share_count, max_shares) VALUES (?, 0, 3)",
            (user_id,)
        )
        conn.commit()
        
        return {'user_id': user_id, 'share_count': 0, 'max_shares': 3}
    
    def validate_platform_url(self, platform: str, url: str) -> bool:
        """验证平台链接格式"""
        if platform not in self.PLATFORMS:
            return False
        
        domains = self.PLATFORMS[platform]['domains']
        return any(domain in url for domain in domains)


# 全局实例
honor_wall_model = HonorWallModel()
