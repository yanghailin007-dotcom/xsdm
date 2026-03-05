#!/usr/bin/env python3
"""
创建支付订单表
"""
import sys
import os
import sqlite3
from pathlib import Path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from web.web_config import BASE_DIR

def get_db_connection():
    """获取数据库连接"""
    db_path = BASE_DIR / "data" / "users.db"
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    return conn

def create_payment_orders_table():
    """创建支付订单表"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建支付订单表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payment_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT UNIQUE NOT NULL,
            user_id INTEGER NOT NULL,
            amount INTEGER NOT NULL,
            bonus INTEGER DEFAULT 0,
            total_points INTEGER NOT NULL,
            status TEXT DEFAULT 'pending',
            trade_no TEXT,
            created_at INTEGER NOT NULL,
            paid_at INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    # 创建索引
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_payment_orders_user_id 
        ON payment_orders(user_id)
    ''')
    
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_payment_orders_status 
        ON payment_orders(status)
    ''')
    
    conn.commit()
    conn.close()
    
    print("✅ 支付订单表创建成功")

if __name__ == '__main__':
    create_payment_orders_table()
