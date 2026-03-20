"""
本地上传任务模型
跟踪用户通过本地脚本上传的进度和状态
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path

# 数据库路径
DB_PATH = Path(__file__).parent.parent / 'data' / 'upload_tasks.db'


class UploadTaskModel:
    """上传任务数据模型"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self._init_db()
    
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 上传任务主表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS upload_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                novel_title TEXT NOT NULL,
                novel_id TEXT,
                total_chapters INTEGER DEFAULT 0,
                completed_chapters INTEGER DEFAULT 0,
                failed_chapters INTEGER DEFAULT 0,
                status TEXT DEFAULT 'pending',  -- pending, running, completed, failed
                platform TEXT DEFAULT 'fanqie',  -- fanqie, qidian, etc.
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                error_log TEXT,  -- JSON 格式存储错误信息
                client_info TEXT  -- 客户端环境信息
            )
        ''')
        
        # 章节上传详情表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS upload_chapters (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                chapter_number INTEGER NOT NULL,
                chapter_title TEXT,
                status TEXT DEFAULT 'pending',  -- pending, uploading, success, failed
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                uploaded_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (task_id) REFERENCES upload_tasks(task_id),
                UNIQUE(task_id, chapter_number)
            )
        ''')
        
        # 创建索引
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_user ON upload_tasks(user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_task_status ON upload_tasks(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_chapter_task ON upload_chapters(task_id)')
        
        conn.commit()
        conn.close()
    
    def create_task(self, task_id: str, user_id: int, novel_title: str, 
                    novel_id: str = None, total_chapters: int = 0,
                    platform: str = 'fanqie', client_info: str = None) -> bool:
        """创建上传任务"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO upload_tasks 
                (task_id, user_id, novel_title, novel_id, total_chapters, platform, client_info)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (task_id, user_id, novel_title, novel_id, total_chapters, platform, client_info))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[UploadTask] 创建任务失败: {e}")
            return False
    
    def create_chapters(self, task_id: str, chapters: List[Dict]) -> bool:
        """批量创建章节记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            for chapter in chapters:
                cursor.execute('''
                    INSERT OR IGNORE INTO upload_chapters 
                    (task_id, chapter_number, chapter_title, status)
                    VALUES (?, ?, ?, 'pending')
                ''', (task_id, chapter['number'], chapter.get('title', '')))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[UploadTask] 创建章节失败: {e}")
            return False
    
    def update_chapter_status(self, task_id: str, chapter_number: int, 
                              status: str, error_message: str = None) -> bool:
        """更新章节上传状态"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            if status == 'success':
                cursor.execute('''
                    UPDATE upload_chapters 
                    SET status = ?, uploaded_at = CURRENT_TIMESTAMP
                    WHERE task_id = ? AND chapter_number = ?
                ''', (status, task_id, chapter_number))
            elif status == 'failed':
                cursor.execute('''
                    UPDATE upload_chapters 
                    SET status = ?, error_message = ?, retry_count = retry_count + 1
                    WHERE task_id = ? AND chapter_number = ?
                ''', (status, error_message, task_id, chapter_number))
            else:
                cursor.execute('''
                    UPDATE upload_chapters 
                    SET status = ?
                    WHERE task_id = ? AND chapter_number = ?
                ''', (status, task_id, chapter_number))
            
            # 更新任务总体进度
            self._update_task_progress(cursor, task_id)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[UploadTask] 更新章节状态失败: {e}")
            return False
    
    def _update_task_progress(self, cursor, task_id: str):
        """更新任务进度统计"""
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as completed,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM upload_chapters
            WHERE task_id = ?
        ''', (task_id,))
        
        row = cursor.fetchone()
        if row:
            total, completed, failed = row
            
            # 确定任务状态
            if completed == total:
                task_status = 'completed'
                completed_at = 'CURRENT_TIMESTAMP'
            elif failed == total:
                task_status = 'failed'
                completed_at = 'CURRENT_TIMESTAMP'
            elif completed > 0 or failed > 0:
                task_status = 'running'
                completed_at = 'NULL'
            else:
                task_status = 'pending'
                completed_at = 'NULL'
            
            if completed_at == 'CURRENT_TIMESTAMP':
                cursor.execute('''
                    UPDATE upload_tasks 
                    SET completed_chapters = ?, failed_chapters = ?, status = ?, 
                        updated_at = CURRENT_TIMESTAMP, completed_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (completed, failed, task_status, task_id))
            else:
                cursor.execute('''
                    UPDATE upload_tasks 
                    SET completed_chapters = ?, failed_chapters = ?, status = ?, 
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                ''', (completed, failed, task_status, task_id))
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """获取任务详情"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM upload_tasks WHERE task_id = ?', (task_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return dict(row)
        return None
    
    def get_task_chapters(self, task_id: str) -> List[Dict]:
        """获取任务的所有章节"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM upload_chapters 
            WHERE task_id = ? 
            ORDER BY chapter_number
        ''', (task_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_user_tasks(self, user_id: int, limit: int = 20) -> List[Dict]:
        """获取用户的任务列表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM upload_tasks 
            WHERE user_id = ? 
            ORDER BY created_at DESC
            LIMIT ?
        ''', (user_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def get_failed_chapters(self, task_id: str) -> List[Dict]:
        """获取上传失败的章节（用于重试）"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM upload_chapters 
            WHERE task_id = ? AND status = 'failed'
            ORDER BY chapter_number
        ''', (task_id,))
        
        rows = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in rows]
    
    def add_error_log(self, task_id: str, error_info: Dict) -> bool:
        """添加错误日志"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # 获取现有错误日志
            cursor.execute('SELECT error_log FROM upload_tasks WHERE task_id = ?', (task_id,))
            row = cursor.fetchone()
            
            error_logs = []
            if row and row[0]:
                error_logs = json.loads(row[0])
            
            error_logs.append({
                'timestamp': datetime.now().isoformat(),
                **error_info
            })
            
            cursor.execute('''
                UPDATE upload_tasks 
                SET error_log = ?, updated_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            ''', (json.dumps(error_logs, ensure_ascii=False), task_id))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[UploadTask] 添加错误日志失败: {e}")
            return False
    
    def delete_task(self, task_id: str) -> bool:
        """删除任务及其章节"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM upload_chapters WHERE task_id = ?', (task_id,))
            cursor.execute('DELETE FROM upload_tasks WHERE task_id = ?', (task_id,))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"[UploadTask] 删除任务失败: {e}")
            return False
