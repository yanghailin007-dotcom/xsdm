#!/usr/bin/env python3
"""
创建管理员账户工具
"""
import sqlite3
import hashlib
from pathlib import Path
import sys

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))
from web.web_config import BASE_DIR

def create_admin():
    db_path = BASE_DIR / "data" / "users.db"
    
    if not db_path.exists():
        print("❌ 数据库不存在，请先启动一次服务")
        return False
    
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    
    # 检查是否已有管理员
    admin = conn.execute("SELECT id, username FROM users WHERE is_admin = 1").fetchone()
    if admin:
        print(f"✅ 已有管理员账户: {admin['username']} (ID: {admin['id']})")
        conn.close()
        return True
    
    # 创建默认管理员
    username = "admin"
    password = "admin123"
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    try:
        cursor = conn.execute(
            "INSERT INTO users (username, password_hash, phone, is_admin) VALUES (?, ?, ?, ?)",
            (username, password_hash, "admin@local", 1)
        )
        conn.commit()
        print("✅ 管理员账户创建成功")
        print(f"   用户名: {username}")
        print(f"   密码: {password}")
        print(f"   ID: {cursor.lastrowid}")
    except sqlite3.IntegrityError:
        # 如果admin用户已存在，将其设为管理员
        conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
        conn.commit()
        print(f"✅ 已将 {username} 设为管理员")
        print("   密码: admin123")
    
    conn.close()
    return True

if __name__ == "__main__":
    create_admin()
