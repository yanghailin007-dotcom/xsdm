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
    
    # 最小余额单位
    MIN_DECIMAL_PLACES = 2  # 精确到0.01
    
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
        self._init_default_model_pricing()
    
    @staticmethod
    def round_amount(amount: float) -> float:
        """
        四舍五入金额到最小单位（0.01）
        
        Args:
            amount: 原始金额
            
        Returns:
            四舍五入后的金额
        """
        return round(amount, PointModel.MIN_DECIMAL_PLACES)
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            # 用户点数表 - 使用 REAL 支持小数（最小0.01）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_points (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    balance REAL DEFAULT 0,
                    total_earned REAL DEFAULT 0,
                    total_spent REAL DEFAULT 0,
                    last_checkin_date TEXT,
                    checkin_streak INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            """)
            
            # 点数交易记录表 - 使用 REAL 支持小数（最小0.01）
            conn.execute("""
                CREATE TABLE IF NOT EXISTS point_transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    type TEXT NOT NULL CHECK(type IN ('earn', 'spend', 'rollback')),
                    amount REAL NOT NULL,
                    balance_after REAL NOT NULL,
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
            
            
            # 模型定价表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_pricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    model_display_name TEXT,
                    input_price_per_1m REAL NOT NULL DEFAULT 0,
                    output_price_per_1m REAL NOT NULL DEFAULT 0,
                    currency TEXT DEFAULT 'CNY',
                    is_active INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(provider, model_name)
                )
            """)
            
            # Token使用日志表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS token_usage_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    provider TEXT NOT NULL,
                    model_name TEXT NOT NULL,
                    prompt_tokens INTEGER DEFAULT 0,
                    completion_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    input_cost REAL DEFAULT 0,
                    output_cost REAL DEFAULT 0,
                    total_cost REAL DEFAULT 0,
                    purpose TEXT,
                    source TEXT,
                    related_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    
    def _init_default_model_pricing(self):
        """初始化默认模型定价（官方价格+20%，单位：点数/百万token）"""
        # 1元 = 10创造点，官方价格上浮20%
        defaults = [
            # (provider, model_name, display_name, input_price_per_1m, output_price_per_1m)
            # 1元 = 10创造点，官方价格上浮20%
            ('deepseek', 'deepseek-reasoner', 'DeepSeek Reasoner', 48.0, 192.0),
            ('deepseek', 'deepseek-chat', 'DeepSeek V3', 12.0, 24.0),
            ('deepseek', 'deepseek-v4-flash', 'DeepSeek V4 Flash', 12.0, 24.0),
            ('deepseek', 'deepseek-v4-pro', 'DeepSeek V4 Pro', 144.0, 288.0),
            ('kimi', 'kimi-k2.5', 'Kimi K2.5', 96.0, 384.0),
            ('doubao', 'doubao-seed-2-0-pro-260215', '豆包 Seed 2.0 Pro', 60.0, 108.0),
            ('gemini', 'gemini-3-flash-preview-thinking', 'Gemini 3 Flash', 8.4, 25.2),
            ('gemini', 'gemini-3-flash', 'Gemini 3 Flash', 8.4, 25.2),
            ('gemini', 'gemini-2.5-flash', 'Gemini 2.5 Flash', 8.4, 25.2),
        ]
        try:
            with self._get_connection() as conn:
                for provider, model_name, display_name, input_p, output_p in defaults:
                    conn.execute("""
                        INSERT OR IGNORE INTO model_pricing 
                        (provider, model_name, model_display_name, input_price_per_1m, output_price_per_1m)
                        VALUES (?, ?, ?, ?, ?)
                    """, (provider, model_name, display_name, input_p, output_p))
                conn.commit()
        except Exception as e:
            logger.warning(f"初始化默认模型定价失败: {e}")
    
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
    
    def add_points(self, user_id: int, amount: float, source: str, 
                   description: str = "", related_id: str = None) -> Dict[str, Any]:
        """
        给用户增加点数（自动四舍五入到0.01）
        
        Returns:
            {success, balance, message}
        """
        # 四舍五入金额
        amount = self.round_amount(amount)
        
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
                    new_balance = self.round_amount(current['balance'] + amount)
                    new_total = self.round_amount(current['total_earned'] + amount)
                    
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
    
    def spend_points(self, user_id: int, amount: float, source: str,
                     description: str = "", related_id: str = None) -> Dict[str, Any]:
        """
        扣除用户点数（自动四舍五入到0.01）
        
        Returns:
            {success, balance, transaction_id, error}
        """
        # 四舍五入金额
        amount = self.round_amount(amount)
        
        try:
            with self._get_connection() as conn:
                # 检查余额
                current = conn.execute(
                    "SELECT balance, total_spent FROM user_points WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
                
                if not current:
                    return {'success': False, 'error': '用户不存在'}
                
                # 四舍五入当前余额进行比较
                current_balance = self.round_amount(current['balance'])
                
                if current_balance < amount:
                    return {
                        'success': False, 
                        'error': '点数不足',
                        'required': amount,
                        'current': current_balance
                    }
                
                new_balance = self.round_amount(current_balance - amount)
                new_total_spent = self.round_amount(current['total_spent'] + amount)
                
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
                
                amount = self.round_amount(transaction['amount'])
                
                # 获取当前余额
                current = conn.execute(
                    "SELECT balance FROM user_points WHERE user_id = ?",
                    (user_id,)
                ).fetchone()
                
                new_balance = self.round_amount(current['balance'] + amount)
                
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
        计算第一阶段消耗（设定生成）
        
        一阶段是整体生成，固定消耗，与章节数无关。
        包含：创意精炼、方案生成、风格指南、市场分析、世界观、势力系统、
              角色设计、情绪蓝图、成长规划、阶段计划、质量评估
        """
        # 一阶段固定消耗：75点（不随章节数变化）
        fixed_cost = 75
        
        return {
            'total': fixed_cost,
            'breakdown': {
                'base_flow': 25,      # 创意精炼 + 方案循环 + 风格指南 + 市场分析
                'worldview': 15,      # 世界观 + 势力系统
                'characters': 10,     # 角色设计
                'planning': 15,       # 情绪蓝图 + 成长规划 + 阶段计划
                'validation': 5,      # 质量评估
                'buffer': 5           # 预留缓冲
            },
            'note': '一阶段设定生成为固定消耗，与章节数无关'
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
    
    # ==================== Token计费系统 ====================
    
    def get_model_pricing(self, provider: str, model_name: str) -> Optional[Dict[str, Any]]:
        """获取模型定价信息"""
        with self._get_connection() as conn:
            row = conn.execute(
                """SELECT * FROM model_pricing 
                    WHERE provider = ? AND model_name = ? AND is_active = 1""",
                (provider, model_name)
            ).fetchone()
            return dict(row) if row else None
    
    def get_all_model_pricing(self) -> List[Dict[str, Any]]:
        """获取所有模型定价"""
        with self._get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM model_pricing ORDER BY provider, model_name"""
            ).fetchall()
            return [dict(r) for r in rows]
    
    def set_model_pricing(self, provider: str, model_name: str,
                          model_display_name: str, input_price_per_1m: float,
                          output_price_per_1m: float, is_active: int = 1) -> Dict[str, Any]:
        """设置/更新模型定价"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO model_pricing 
                        (provider, model_name, model_display_name, 
                         input_price_per_1m, output_price_per_1m, is_active, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(provider, model_name) DO UPDATE SET
                        model_display_name = excluded.model_display_name,
                        input_price_per_1m = excluded.input_price_per_1m,
                        output_price_per_1m = excluded.output_price_per_1m,
                        is_active = excluded.is_active,
                        updated_at = excluded.updated_at
                """, (provider, model_name, model_display_name,
                      input_price_per_1m, output_price_per_1m, is_active,
                      datetime.now().isoformat()))
                conn.commit()
                return {'success': True, 'message': f'{provider}/{model_name} 定价已更新'}
        except Exception as e:
            logger.error(f"❌ 更新模型定价失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def delete_model_pricing(self, pricing_id: int) -> Dict[str, Any]:
        """删除模型定价"""
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM model_pricing WHERE id = ?", (pricing_id,))
                conn.commit()
                return {'success': True, 'message': '定价已删除'}
        except Exception as e:
            logger.error(f"❌ 删除模型定价失败: {e}")
            return {'success': False, 'error': str(e)}
    
    def calculate_token_cost(self, provider: str, model_name: str,
                             prompt_tokens: int, completion_tokens: int) -> Optional[Dict[str, Any]]:
        """计算Token费用，返回None表示该模型未配置价格（应回退到按次计费）"""
        pricing = self.get_model_pricing(provider, model_name)
        if not pricing:
            return None
        
        input_cost = (prompt_tokens / 1_000_000) * pricing['input_price_per_1m']
        output_cost = (completion_tokens / 1_000_000) * pricing['output_price_per_1m']
        total_cost = self.round_amount(input_cost + output_cost)
        
        return {
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': prompt_tokens + completion_tokens,
            'input_cost': self.round_amount(input_cost),
            'output_cost': self.round_amount(output_cost),
            'total_cost': total_cost,
            'pricing': pricing
        }
    
    def deduct_by_tokens(self, user_id: int, provider: str, model_name: str,
                         prompt_tokens: int, completion_tokens: int,
                         purpose: str = "", source: str = "token_billing",
                         related_id: str = None) -> Dict[str, Any]:
        """按Token使用量扣费，无价格配置时返回None让调用方回退到按次计费"""
        cost_info = self.calculate_token_cost(provider, model_name, prompt_tokens, completion_tokens)
        if cost_info is None:
            return None  # 回退信号
        
        total_cost = cost_info['total_cost']
        
        # 检查余额
        points_info = self.get_user_points(user_id)
        if points_info['balance'] < total_cost:
            return {
                'success': False,
                'error': '点数不足',
                'required': total_cost,
                'current': points_info['balance']
            }
        
        # 执行扣费
        spend_result = self.spend_points(
            user_id=user_id,
            amount=total_cost,
            source=source,
            description=f"{provider}/{model_name}: {prompt_tokens}+{completion_tokens} tokens = {total_cost}点",
            related_id=related_id
        )
        
        if spend_result.get('success'):
            # 记录Token使用日志
            self.log_token_usage(
                user_id=user_id,
                provider=provider,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=cost_info['total_tokens'],
                input_cost=cost_info['input_cost'],
                output_cost=cost_info['output_cost'],
                total_cost=total_cost,
                purpose=purpose,
                source=source,
                related_id=related_id
            )
        
        return spend_result
    
    def log_token_usage(self, user_id: int, provider: str, model_name: str,
                        prompt_tokens: int, completion_tokens: int, total_tokens: int,
                        input_cost: float, output_cost: float, total_cost: float,
                        purpose: str = "", source: str = "", related_id: str = None):
        """记录Token使用日志"""
        try:
            with self._get_connection() as conn:
                conn.execute("""
                    INSERT INTO token_usage_logs
                        (user_id, provider, model_name, prompt_tokens, completion_tokens,
                         total_tokens, input_cost, output_cost, total_cost, purpose, source, related_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, provider, model_name, prompt_tokens, completion_tokens,
                      total_tokens, input_cost, output_cost, total_cost, purpose, source, related_id))
                conn.commit()
        except Exception as e:
            logger.error(f"❌ 记录Token使用日志失败: {e}")
    
    def get_token_usage_stats(self, user_id: int, days: int = 30) -> Dict[str, Any]:
        """获取用户Token使用统计"""
        with self._get_connection() as conn:
            # 总消耗
            total = conn.execute("""
                SELECT SUM(total_tokens) as tokens, SUM(total_cost) as cost, COUNT(*) as calls
                FROM token_usage_logs WHERE user_id = ? 
                AND created_at >= datetime('now', '-{} days')
            """.format(days), (user_id,)).fetchone()
            
            # 按模型统计
            by_model = conn.execute("""
                SELECT provider, model_name, 
                       SUM(prompt_tokens) as prompt_tokens,
                       SUM(completion_tokens) as completion_tokens,
                       SUM(total_tokens) as total_tokens,
                       SUM(total_cost) as total_cost,
                       COUNT(*) as call_count
                FROM token_usage_logs WHERE user_id = ?
                AND created_at >= datetime('now', '-{} days')
                GROUP BY provider, model_name
                ORDER BY total_cost DESC
            """.format(days), (user_id,)).fetchall()
            
            return {
                'total_tokens': total['tokens'] or 0,
                'total_cost': total['cost'] or 0,
                'total_calls': total['calls'] or 0,
                'by_model': [dict(r) for r in by_model]
            }


# 创建全局实例
point_model = PointModel()
