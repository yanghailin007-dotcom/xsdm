"""
点数系统数据库模型
管理用户点数余额、交易记录和配置
"""
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple
from web.web_config import logger, BASE_DIR


class PointModel:
    """点数系统模型"""
    
    # 默认配置
    DEFAULT_CONFIG = {
        # 点数获取
        'register_bonus': 88,        # 新用户注册赠送
        'daily_checkin': 10,         # 每日签到
        'checkin_streak_bonus': 5,   # 连续签到额外奖励
        
        # 第一阶段消耗
        'phase1_planning': 1,        # 规划阶段
        'phase1_worldview': 3,       # 世界观生成
        'phase1_characters': 2,      # 角色设计(每个)
        'phase1_outline': 1,         # 大纲(每10章)
        'phase1_validation': 1,      # 质量评估
        
        # 第二阶段消耗
        'phase2_chapter_batch': 2,   # 批量模式(每章) = 生成1点 + 质量检查1点
        'phase2_chapter_refined': 3, # 精修模式(每章) = 生成1点 + 质量检查1点 + 精修1点
        'phase2_regenerate': 1,      # 单章重生成
        
        # 其他功能
        'cover_generation': 5,       # 封面生成
        'fanqie_upload': 2,          # 番茄上传
        'contract_assist': 3,        # 签约辅助
    }
    
    def __init__(self, db_path=None):
        """初始化数据库连接"""
        if db_path is None:
            db_path = BASE_DIR / "data" / "users.db"
        elif isinstance(db_path, str):
            db_path = Path(db_path)
        
        self.db_path = str(db_path)
        self._init_db()
        self._init_default_config()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            # 用户点数表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    balance INTEGER DEFAULT 0,
                    total_earned INTEGER DEFAULT 0,
                    total_spent INTEGER DEFAULT 0,
                    last_checkin_date TEXT,
                    checkin_streak INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 点数交易记录表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS point_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('earn', 'spend', 'rollback')),
                    amount INTEGER NOT NULL,
                    balance_after INTEGER NOT NULL,
                    source TEXT NOT NULL,
                    description TEXT,
                    related_id TEXT,
                    status TEXT DEFAULT 'success' CHECK(status IN ('success', 'failed', 'pending')),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 点数配置表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS point_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    config_key TEXT NOT NULL UNIQUE,
                    config_value INTEGER NOT NULL,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_by INTEGER
                )
            """)
            
            # 支付订单表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS payment_orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id TEXT NOT NULL UNIQUE,
                    user_id INTEGER NOT NULL,
                    amount REAL NOT NULL,
                    bonus INTEGER DEFAULT 0,
                    total_points INTEGER NOT NULL,
                    status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'completed', 'failed', 'cancelled')),
                    trade_no TEXT,
                    paid_at INTEGER,
                    created_at INTEGER NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            conn.commit()
            logger.info("✅ 点数系统数据库表初始化完成")
    
    def _init_default_config(self):
        """初始化默认配置"""
        with self._get_connection() as conn:
            for key, value in self.DEFAULT_CONFIG.items():
                conn.execute("""
                    INSERT OR IGNORE INTO point_config (config_key, config_value, description)
                    VALUES (?, ?, ?)
                """, (key, value, f"默认配置: {key}"))
            conn.commit()
    
    # ==================== 用户点数操作 ====================
    
    def get_user_points(self, user_id: int) -> Dict[str, Any]:
        """获取用户点数信息"""
        with self._get_connection() as conn:
            points = conn.execute(
                "SELECT * FROM user_points WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if points:
                return dict(points)
            
            # 如果不存在，创建新记录
            conn.execute(
                "INSERT INTO user_points (user_id, balance) VALUES (?, 0)",
                (user_id,)
            )
            conn.commit()
            
            return {
                'user_id': user_id,
                'balance': 0,
                'total_earned': 0,
                'total_spent': 0,
                'last_checkin_date': None,
                'checkin_streak': 0
            }
    
    def add_points(self, user_id: int, amount: int, source: str, 
                   description: str = "", related_id: str = None) -> Dict[str, Any]:
        """
        给用户增加点数
        
        Returns:
            {success, balance, message}
        """
        try:
            with self._get_connection() as conn:
                # 获取当前余额
                current = conn.execute(
                    "SELECT balance, total_earned FROM user_points WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
                
                if not current:
                    # 创建新记录
                    conn.execute(
                        """INSERT INTO user_points 
                            (user_id, balance, total_earned) VALUES (?, ?, ?)""",
                        (user_id, amount, amount)
                    )
                    new_balance = amount
                    new_total = amount
                else:
                    new_balance = current['balance'] + amount
                    new_total = current['total_earned'] + amount
                    
                    conn.execute(
                        """UPDATE user_points 
                            SET balance = ?, total_earned = ?, updated_at = ?
                            WHERE user_id = ?""",
                        (new_balance, new_total, datetime.now().isoformat(), user_id)
                    )
                
                # 记录交易
                conn.execute(
                    """INSERT INTO point_transactions 
                        (user_id, type, amount, balance_after, source, description, related_id)
                        VALUES (?, 'earn', ?, ?, ?, ?, ?)""",
                    (user_id, amount, new_balance, source, description, related_id)
                )
                
                conn.commit()
                
                logger.info(f"✅ 给用户{user_id}增加{amount}点，来源: {source}")
                return {
                    'success': True,
                    'balance': new_balance,
                    'amount': amount,
                    'message': f'成功获得{amount}点'
                }
                
        except Exception as e:
            logger.error(f"❌ 增加点数失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def spend_points(self, user_id: int, amount: int, source: str,
                     description: str = "", related_id: str = None) -> Dict[str, Any]:
        """
        扣除用户点数
        
        Returns:
            {success, balance, transaction_id, error}
        """
        try:
            with self._get_connection() as conn:
                # 检查余额
                current = conn.execute(
                    "SELECT balance, total_spent FROM user_points WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
                
                if not current:
                    return {'success': False, 'error': '用户不存在'}
                
                if current['balance'] < amount:
                    return {
                        'success': False, 
                        'error': '点数不足',
                        'required': amount,
                        'current': current['balance']
                    }
                
                new_balance = current['balance'] - amount
                new_total_spent = current['total_spent'] + amount
                
                # 更新余额
                conn.execute(
                    """UPDATE user_points 
                        SET balance = ?, total_spent = ?, updated_at = ?
                        WHERE user_id = ?""",
                    (new_balance, new_total_spent, datetime.now().isoformat(), user_id)
                )
                
                # 记录交易
                cursor = conn.execute(
                    """INSERT INTO point_transactions 
                        (user_id, type, amount, balance_after, source, description, related_id)
                        VALUES (?, 'spend', ?, ?, ?, ?, ?)""",
                    (user_id, amount, new_balance, source, description, related_id)
                )
                
                conn.commit()
                
                logger.info(f"✅ 扣除用户{user_id}的{amount}点，余额: {new_balance}")
                return {
                    'success': True,
                    'balance': new_balance,
                    'amount': amount,
                    'transaction_id': cursor.lastrowid
                }
                
        except Exception as e:
            logger.error(f"❌ 扣除点数失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def rollback_points(self, user_id: int, related_id: str, 
                        reason: str = "") -> Dict[str, Any]:
        """
        回滚点数（AI调用失败等场景）
        """
        try:
            with self._get_connection() as conn:
                # 查找对应的消费记录
                transaction = conn.execute(
                    """SELECT * FROM point_transactions 
                        WHERE user_id = ? AND related_id = ? AND type = 'spend'
                        ORDER BY created_at DESC LIMIT 1""",
                    (user_id, related_id)
                ).fetchone()
                
                if not transaction:
                    return {'success': False, 'error': '未找到对应的消费记录'}
                
                # 检查是否已经回滚
                existing_rollback = conn.execute(
                    """SELECT id FROM point_transactions 
                        WHERE user_id = ? AND related_id = ? AND type = 'rollback'""",
                    (user_id, related_id)
                ).fetchone()
                
                if existing_rollback:
                    return {'success': False, 'error': '已经回滚过了'}
                
                amount = transaction['amount']
                
                # 获取当前余额
                current = conn.execute(
                    "SELECT balance FROM user_points WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
                
                new_balance = current['balance'] + amount
                
                # 更新余额
                conn.execute(
                    """UPDATE user_points 
                        SET balance = ?, updated_at = ?
                        WHERE user_id = ?""",
                    (new_balance, datetime.now().isoformat(), user_id)
                )
                
                # 记录回滚
                conn.execute(
                    """INSERT INTO point_transactions 
                        (user_id, type, amount, balance_after, source, description, related_id)
                        VALUES (?, 'rollback', ?, ?, 'rollback', ?, ?)""",
                    (user_id, amount, new_balance, 
                     f"回滚: {reason}" if reason else "操作失败回滚", related_id)
                )
                
                conn.commit()
                
                logger.info(f"✅ 回滚用户{user_id}的{amount}点")
                return {
                    'success': True,
                    'balance': new_balance,
                    'amount': amount
                }
                
        except Exception as e:
            logger.error(f"❌ 回滚点数失败: {e}")
            return {'success': False, 'error': str(e)}
    
    # ==================== 签到功能 ====================
    
    def daily_checkin(self, user_id: int) -> Dict[str, Any]:
        """
        每日签到
        
        Returns:
            {success, earned, balance, streak, message}
        """
        try:
            today = datetime.now().date().isoformat()
            yesterday = (datetime.now().date() - timedelta(days=1)).isoformat()
            
            with self._get_connection() as conn:
                # 获取用户点数信息
                user_points = conn.execute(
                    "SELECT * FROM user_points WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
                
                if not user_points:
                    # 创建新记录
                    conn.execute(
                        "INSERT INTO user_points (user_id) VALUES (?)",
                        (user_id,)
                    )
                    conn.commit()
                    user_points = {'last_checkin_date': None, 'checkin_streak': 0}
                
                # 检查今天是否已签到
                if user_points['last_checkin_date'] == today:
                    return {
                        'success': False,
                        'error': '今天已经签到过了',
                        'already_checked': True
                    }
                
                # 计算连续签到
                if user_points['last_checkin_date'] == yesterday:
                    streak = user_points['checkin_streak'] + 1
                else:
                    streak = 1
                
                # 获取配置
                base_reward = self.get_config('daily_checkin', 10)
                streak_bonus = self.get_config('checkin_streak_bonus', 5) if streak >= 7 else 0
                total_reward = base_reward + streak_bonus
                
                # 更新签到信息
                conn.execute(
                    """UPDATE user_points 
                        SET last_checkin_date = ?, checkin_streak = ?, updated_at = ?
                        WHERE user_id = ?""",
                    (today, streak, datetime.now().isoformat(), user_id)
                )
                
                conn.commit()
                
                # 发放点数
                result = self.add_points(
                    user_id, total_reward, 'daily_checkin',
                    f'每日签到奖励，连续{streak}天'
                )
                
                message = f'签到成功！获得{base_reward}点'
                if streak_bonus > 0:
                    message += f'，连续签到奖励{streak_bonus}点'
                
                return {
                    'success': True,
                    'earned': total_reward,
                    'balance': result['balance'],
                    'streak': streak,
                    'message': message
                }
                
        except Exception as e:
            logger.error(f"❌ 签到失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_checkin_status(self, user_id: int) -> Dict[str, Any]:
        """获取签到状态"""
        with self._get_connection() as conn:
            user_points = conn.execute(
                "SELECT last_checkin_date, checkin_streak FROM user_points WHERE user_id = ?",
                (user_id,)
            ).fetchone()
            
            if not user_points:
                return {'can_checkin': True, 'streak': 0}
            
            today = datetime.now().date().isoformat()
            can_checkin = user_points['last_checkin_date'] != today
            
            return {
                'can_checkin': can_checkin,
                'last_checkin': user_points['last_checkin_date'],
                'streak': user_points['checkin_streak']
            }
    
    # ==================== 交易记录 ====================
    
    def get_transactions(self, user_id: int, page: int = 1, 
                         limit: int = 20) -> Dict[str, Any]:
        """获取交易记录"""
        offset = (page - 1) * limit
        
        with self._get_connection() as conn:
            # 获取记录
            transactions = conn.execute(
                """SELECT * FROM point_transactions 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?""",
                (user_id, limit, offset)
            ).fetchall()
            
            # 获取总数
            total = conn.execute(
                "SELECT COUNT(*) as count FROM point_transactions WHERE user_id = ?",
                (user_id,)
            ).fetchone()['count']
            
            return {
                'transactions': [dict(t) for t in transactions],
                'pagination': {
                    'total': total,
                    'page': page,
                    'limit': limit,
                    'pages': (total + limit - 1) // limit
                }
            }
    
    # ==================== 配置管理 ====================
    
    def get_config(self, key: str, default: int = None) -> int:
        """获取配置值"""
        with self._get_connection() as conn:
            result = conn.execute(
                "SELECT config_value FROM point_config WHERE config_key = ? AND is_active = 1",
                (key,)
            ).fetchone()
            
            if result:
                return result['config_value']
            
            return default if default is not None else self.DEFAULT_CONFIG.get(key, 0)
    
    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        with self._get_connection() as conn:
            configs = conn.execute(
                "SELECT config_key, config_value FROM point_config WHERE is_active = 1 ORDER BY config_key"
            ).fetchall()
            
            result = {
                'earning': {},
                'spending': {}
            }
            
            for row in configs:
                key = row['config_key']
                value = row['config_value']
                
                # 根据key前缀分类
                if key in ['register_bonus', 'daily_checkin', 'checkin_streak_bonus']:
                    result['earning'][key] = value
                else:
                    result['spending'][key] = value
            
            return result
    
    def update_config(self, key: str, value: int, updated_by: int = None) -> bool:
        """更新配置"""
        try:
            with self._get_connection() as conn:
                conn.execute(
                    """UPDATE point_config 
                        SET config_value = ?, updated_at = ?, updated_by = ?
                        WHERE config_key = ?""",
                    (value, datetime.now().isoformat(), updated_by, key)
                )
                conn.commit()
                logger.info(f"✅ 更新点数配置: {key} = {value}")
                return True
        except Exception as e:
            logger.error(f"❌ 更新配置失败: {e}")
            return False
    
    # ==================== 消耗计算 ====================
    
    def calculate_phase1_cost(self, total_chapters: int = 200, 
                              estimated_characters: int = 4) -> Dict[str, Any]:
        """
        计算第一阶段消耗（基于实际 API 调用次数估算）
        
        实际流程分析：
        - 基础流程：创意精炼(1) + 方案生成循环(4轮×2次) + 风格指南(1) + 市场分析(3次) + 世界观(3次) + 势力系统(1) = 19次
        - 角色设计：核心角色(1) + 配角补充(1) = 2次
        - 情绪蓝图：1次
        - 成长规划：1次
        - 阶段计划：按阶段计算，每阶段约 10-15 次 API 调用
        """
        total_chapters = int(total_chapters) if total_chapters else 200
        
        # 基础流程固定消耗（与章节数无关）
        base_cost = 25  # 创意精炼 + 方案循环(8次) + 风格指南 + 市场分析(3次) + 世界观(3次) + 势力系统 + 角色设计(2次) + 情绪蓝图 + 成长规划
        
        # 阶段相关消耗（每阶段约 12 次 API 调用）
        # 阶段数 = 总章节数 / 每阶段章节数(约30章)
        estimated_stages = max(3, total_chapters // 30)  # 至少3个阶段
        stage_cost = estimated_stages * 12  # 每阶段约12次调用
        
        # 质量评估和验证
        validation_cost = estimated_stages * 2  # 每个阶段的质量评估
        
        breakdown = {
            'base_flow': base_cost,
            'stage_planning': stage_cost,
            'validation': validation_cost,
            'buffer': 10  # 预留缓冲（实际可能有额外调用）
        }
        
        total = sum(breakdown.values())
        
        return {
            'total': total,
            'breakdown': breakdown,
            'note': f'预估基于 {estimated_stages} 个阶段，实际消耗可能因生成复杂度而异'
        }
    
    def calculate_phase2_cost(self, chapter_count: int, 
                              mode: str = 'batch') -> Dict[str, Any]:
        """计算第二阶段消耗"""
        if mode == 'batch':
            cost_per = self.get_config('phase2_chapter_batch', 1)
        else:
            cost_per = self.get_config('phase2_chapter_refined', 2)
        
        return {
            'total': chapter_count * cost_per,
            'chapter_count': chapter_count,
            'mode': mode,
            'cost_per_chapter': cost_per
        }


# 创建全局实例
point_model = PointModel()
