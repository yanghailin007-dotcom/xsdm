#!/usr/bin/env python3
"""
安全修复脚本 - 上线前必须运行
修复最严重的安全问题
"""
import os
import sys
import secrets
import re
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

def generate_secure_key():
    """生成安全的密钥"""
    return secrets.token_urlsafe(32)

def fix_hardcoded_secrets():
    """修复硬编码密钥"""
    print("\n🔧 检查硬编码密钥...")
    
    web_config_path = Path("web/web_config.py")
    if web_config_path.exists():
        content = web_config_path.read_text(encoding='utf-8')
        
        # 检查是否有硬编码的 SECRET_KEY
        if "your-secret-key-here" in content:
            print("⚠️  发现硬编码 SECRET_KEY，请手动修改为环境变量读取")
            print("   建议修改:")
            print("   SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or secrets.token_urlsafe(32)")
        else:
            print("✅ SECRET_KEY 检查通过")
    
    points_api_path = Path("web/api/points_api.py")
    if points_api_path.exists():
        content = points_api_path.read_text(encoding='utf-8')
        
        if "your-internal-api-key" in content:
            print("⚠️  发现硬编码内部API密钥，请手动修改")
            print("   文件: web/api/points_api.py")
        else:
            print("✅ 内部API密钥检查通过")

def fix_test_user():
    """检查test用户"""
    print("\n🔧 检查 test 用户...")
    
    auth_path = Path("web/auth.py")
    if auth_path.exists():
        content = auth_path.read_text(encoding='utf-8')
        
        # 检查是否有任意密码登录
        if "if username.lower() == 'test':" in content and "return True" in content:
            print("❌ 发现 test 用户任意密码登录漏洞！")
            print("   文件: web/auth.py, 约第52-54行")
            print("   必须删除或注释以下代码:")
            print("   ```")
            print("   if username.lower() == 'test':")
            print("       logger.info(f\"✅ 测试用户登录成功: {username}\")")
            print("       return True")
            print("   ```")
            print("   建议: 上线前完全删除 test 用户")
        else:
            print("✅ test 用户检查通过")

def fix_password_hash():
    """检查密码哈希算法"""
    print("\n🔧 检查密码哈希算法...")
    
    user_model_path = Path("web/models/user_model.py")
    if user_model_path.exists():
        content = user_model_path.read_text(encoding='utf-8')
        
        if "hashlib.sha256(password.encode())" in content:
            print("❌ 发现不安全的 SHA256 密码哈希！")
            print("   当前使用 SHA256，建议迁移到 bcrypt")
            print("   文件: web/models/user_model.py, 第88-90行")
        else:
            print("✅ 密码哈希算法检查通过")

def fix_logging_issues():
    """检查日志敏感信息"""
    print("\n🔧 检查日志敏感信息...")
    
    auth_routes_path = Path("web/routes/auth_routes.py")
    if auth_routes_path.exists():
        content = auth_routes_path.read_text(encoding='utf-8')
        
        issues = []
        if 'logger.info(f"🔍 JSON数据: {data}")' in content:
            issues.append("JSON数据可能被记录（含敏感信息）")
        if 'logger.info(f"🔍 Form数据: {dict(data)}")' in content:
            issues.append("Form数据可能被记录（含敏感信息）")
        
        if issues:
            print("⚠️  发现日志可能记录敏感信息:")
            for issue in issues:
                print(f"   - {issue}")
            print("   建议: 过滤 password, token, api_key 等字段")
        else:
            print("✅ 日志敏感信息检查通过")

def generate_env_template():
    """生成环境变量模板"""
    print("\n🔧 生成安全环境变量配置...")
    
    env_template = f"""# 大文娱系统环境变量配置
# 复制此文件为 .env 并填入实际值

# Flask 安全密钥（必须修改）
FLASK_SECRET_KEY={generate_secure_key()}

# 内部API密钥（必须修改）
INTERNAL_API_KEY={generate_secure_key()}

# 数据库加密密钥（可选）
DB_ENCRYPTION_KEY={generate_secure_key()}

# 支付宝/易支付配置
YIPAY_MERCHANT_ID=your_merchant_id
YIPAY_MERCHANT_KEY=your_merchant_key
YIPAY_API_URL=https://pay.example.com
"""
    
    env_path = Path(".env.example")
    env_path.write_text(env_template, encoding='utf-8')
    print(f"✅ 环境变量模板已生成: {env_path}")
    print("   请复制为 .env 文件并填入实际配置")

def check_database_encryption():
    """检查数据库加密"""
    print("\n🔧 检查数据库加密...")
    
    db_path = Path("data/users.db")
    if db_path.exists():
        import sqlite3
        try:
            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()
            
            # 检查是否使用了 SQLCipher
            cursor.execute("PRAGMA cipher_version;")
            result = cursor.fetchone()
            
            if result:
                print(f"✅ 数据库已加密 (SQLCipher {result[0]})")
            else:
                print("⚠️  数据库未加密")
                print("   建议: 使用 SQLCipher 加密 SQLite 数据库")
            
            conn.close()
        except Exception as e:
            print(f"⚠️  无法检查数据库加密: {e}")
    else:
        print("⚠️  数据库文件不存在")

def main():
    """主函数"""
    print("=" * 60)
    print("🔐 大文娱系统安全修复检查")
    print("=" * 60)
    
    fix_hardcoded_secrets()
    fix_test_user()
    fix_password_hash()
    fix_logging_issues()
    generate_env_template()
    check_database_encryption()
    
    print("\n" + "=" * 60)
    print("📋 上线前必须完成的安全检查:")
    print("=" * 60)
    print("""
1. [必须] 修改 web/web_config.py 中的 SECRET_KEY
2. [必须] 删除 web/auth.py 中 test 用户的任意密码登录
3. [必须] 将密码哈希从 SHA256 迁移到 bcrypt
4. [必须] 修改 web/api/points_api.py 中的内部API密钥
5. [建议] 清理日志中的敏感信息
6. [建议] 配置 HTTPS
7. [建议] 启用数据库加密

详细修复指南请参考: SECURITY_AUDIT_REPORT.md
""")
    
    # 等待用户确认
    input("\n按 Enter 键继续...")

if __name__ == '__main__':
    main()
