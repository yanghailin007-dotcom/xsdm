#!/usr/bin/env python3
"""
数据库迁移脚本：将 users.phone 字段从 NOT NULL 改为 NULLABLE
用于支持无需手机号的注册功能

执行方式:
    python tools/migrate_phone_nullable.py
    
或者使用嵌入式Python:
    .\python-embed\python.exe tools/migrate_phone_nullable.py

安全保证:
    1. 自动备份原数据库
    2. 保留所有已有用户数据
    3. 已绑定的手机号保持不变
    4. 支持回滚（使用备份文件）
"""

import sqlite3
import shutil
import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from web.web_config import logger, BASE_DIR


def check_migration_needed(db_path: Path) -> bool:
    """检查是否需要进行迁移"""
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('PRAGMA table_info(users)')
    columns = {row[1]: row[3] for row in cursor}  # name: notnull
    conn.close()
    
    # phone 字段的 notnull=1 表示需要迁移
    return columns.get('phone') == 1


def migrate_database():
    """执行数据库迁移"""
    db_path = BASE_DIR / "data" / "users.db"
    
    if not db_path.exists():
        print("❌ 数据库文件不存在，无需迁移")
        return True
    
    # 检查是否需要迁移
    if not check_migration_needed(db_path):
        print("✅ 数据库结构已是最新，无需迁移")
        return True
    
    # 创建备份
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = db_path.parent / f"users_backup_{timestamp}.db"
    
    try:
        print(f"📦 正在备份数据库到: {backup_path}")
        shutil.copy(str(db_path), str(backup_path))
        print(f"✅ 备份完成")
        
        # 执行迁移
        print("🔄 正在修改表结构...")
        conn = sqlite3.connect(db_path)
        
        # 获取现有数据
        cursor = conn.execute('SELECT * FROM users')
        users_data = cursor.fetchall()
        columns = [desc[0] for desc in cursor.description]
        
        print(f"   发现 {len(users_data)} 个已注册用户，准备迁移...")
        
        # 1. 创建新表（phone 允许 NULL）
        conn.execute('''
            CREATE TABLE users_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                phone TEXT UNIQUE,
                email TEXT,
                is_active INTEGER DEFAULT 1,
                is_admin INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP
            )
        ''')
        
        # 2. 迁移用户数据
        placeholders = ','.join(['?' for _ in columns])
        col_names = ','.join(columns)
        sql = f'INSERT INTO users_new ({col_names}) VALUES ({placeholders})'
        for user in users_data:
            conn.execute(sql, user)
        
        # 3. 获取验证码和登录日志数据（如果存在）
        try:
            cursor = conn.execute('SELECT * FROM verification_codes')
            codes_data = cursor.fetchall()
            codes_columns = [desc[0] for desc in cursor.description]
        except sqlite3.OperationalError:
            codes_data = []
            codes_columns = []
        
        try:
            cursor = conn.execute('SELECT * FROM login_logs')
            logs_data = cursor.fetchall()
            logs_columns = [desc[0] for desc in cursor.description]
        except sqlite3.OperationalError:
            logs_data = []
            logs_columns = []
        
        # 4. 删除旧表
        conn.execute('DROP TABLE users')
        conn.execute('ALTER TABLE users_new RENAME TO users')
        
        # 5. 重建其他表
        if codes_columns:
            conn.execute('''
                CREATE TABLE verification_codes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    phone TEXT NOT NULL,
                    code TEXT NOT NULL,
                    type TEXT NOT NULL,
                    expires_at TIMESTAMP NOT NULL,
                    used INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address TEXT
                )
            ''')
            placeholders = ','.join(['?' for _ in codes_columns])
            col_names = ','.join(codes_columns)
            sql = f'INSERT INTO verification_codes ({col_names}) VALUES ({placeholders})'
            for code in codes_data:
                conn.execute(sql, code)
        
        if logs_columns:
            conn.execute('''
                CREATE TABLE login_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    action TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    success INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users(id)
                )
            ''')
            placeholders = ','.join(['?' for _ in logs_columns])
            col_names = ','.join(logs_columns)
            sql = f'INSERT INTO login_logs ({col_names}) VALUES ({placeholders})'
            for log in logs_data:
                conn.execute(sql, log)
        
        conn.commit()
        conn.close()
        
        print("✅ 数据库迁移完成！")
        print(f"\n📊 迁移统计:")
        print(f"   - 已注册用户: {len(users_data)}")
        print(f"   - 验证码记录: {len(codes_data)}")
        print(f"   - 登录日志: {len(logs_data)}")
        print(f"\n💾 备份文件: {backup_path}")
        print(f"   如需回滚，请将备份文件复制回 {db_path}")
        
        return True
        
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        # 如果备份已创建，提示用户
        if backup_path.exists():
            print(f"\n⚠️  备份文件位于: {backup_path}")
        return False


def verify_migration():
    """验证迁移结果"""
    db_path = BASE_DIR / "data" / "users.db"
    conn = sqlite3.connect(db_path)
    cursor = conn.execute('PRAGMA table_info(users)')
    
    print("\n🔍 验证表结构:")
    for row in cursor:
        col_name = row[1]
        not_null = "NOT NULL" if row[3] else "NULL"
        default = f"DEFAULT {row[4]}" if row[4] else ""
        if col_name == 'phone':
            print(f"   ✅ phone: {not_null} {default}")
        else:
            print(f"   • {col_name}: {not_null}")
    
    conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("  数据库迁移工具: 支持无手机号注册")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    if success:
        verify_migration()
        print("\n✨ 迁移成功！现在可以支持无需手机号的注册功能了。")
        sys.exit(0)
    else:
        print("\n❌ 迁移失败，请检查错误信息。")
        sys.exit(1)
