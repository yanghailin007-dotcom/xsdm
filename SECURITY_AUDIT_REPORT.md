# 大文娱系统数据安全审计报告

> 审计日期: 2026年3月5日  
> 系统版本: V2  
> 审计范围: 数据库、用户认证、API接口、文件操作、日志系统

---

## 🔴 严重级别 (Critical) - 必须立即修复

### 1. 硬编码密钥和敏感信息
**风险等级**: 🔴 Critical

**问题描述**:
- `web/web_config.py:61` - Flask SECRET_KEY 硬编码为 `'your-secret-key-here'`
- `web/api/points_api.py:185,225,260` - 内部API密钥硬编码为 `'your-internal-api-key'`
- `web/auth.py:14` - admin 默认密码硬编码为 `"admin"`

**潜在影响**:
- 攻击者可直接使用默认密钥伪造会话、篡改数据
- 内部API可被任意调用，导致点数被恶意操作

**修复建议**:
```python
# 1. 从环境变量读取 SECRET_KEY
import os
SECRET_KEY = os.environ.get('FLASK_SECRET_KEY') or os.urandom(32)

# 2. 内部API密钥从配置文件读取，并定期轮换
INTERNAL_API_KEY = os.environ.get('INTERNAL_API_KEY')

# 3. 强制首次登录修改默认密码
```

---

### 2. 测试用户任意密码登录
**风险等级**: 🔴 Critical

**问题描述**:
- `web/auth.py:52-54` - test用户允许任意密码登录
- `web/auth.py:32` - test用户默认密码为 `"test123"`

**潜在影响**:
- 任何人可使用 test 账号登录系统
- 生产环境若未删除，将导致未授权访问

**修复建议**:
```python
# 上线前必须删除或禁用以下代码
if username.lower() == 'test':
    return True  # ← 删除此行
```

---

### 3. 密码哈希算法不安全
**风险等级**: 🔴 Critical

**问题描述**:
- `web/models/user_model.py:88-90` - 使用 SHA256 单轮哈希，无盐值

```python
def _hash_password(self, password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
```

**潜在影响**:
- SHA256 可被 GPU/ASIC 快速破解
- 无盐值导致彩虹表攻击有效
- 相同密码产生相同哈希，易被批量破解

**修复建议**:
```python
import bcrypt

def _hash_password(self, password: str) -> str:
    # 使用 bcrypt，自动处理盐值
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(self, password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

---

## 🟠 高危级别 (High) - 建议48小时内修复

### 4. 日志记录敏感信息
**风险等级**: 🟠 High

**问题描述**:
- `web/routes/auth_routes.py:35,38` - 记录完整的登录请求数据
- `web/routes/auth_routes.py:43` - 记录密码长度信息

```python
logger.info(f"🔍 JSON数据: {data}")  # 可能包含密码
logger.info(f"🔍 Form数据: {dict(data)}")  # 可能包含密码
```

**潜在影响**:
- 日志文件泄露可导致密码泄露
- 合规审计无法通过（GDPR、等保）

**修复建议**:
```python
# 过滤敏感字段
def sanitize_log_data(data):
    if isinstance(data, dict):
        return {k: '***' if k in ['password', 'token', 'api_key'] else v 
                for k, v in data.items()}
    return data

logger.info(f"数据: {sanitize_log_data(data)}")
```

---

### 5. 会话管理不安全
**风险等级**: 🟠 High

**问题描述**:
- 未检查 `SESSION_COOKIE_SECURE` 设置
- 未设置 `SESSION_COOKIE_HTTPONLY` 
- 未设置 `SESSION_COOKIE_SAMESITE`
- 会话永久有效，无过期时间

**潜在影响**:
- XSS 攻击可窃取会话 Cookie
- 中间人攻击可劫持会话
- 长期有效的会话增加被盗风险

**修复建议**:
```python
# web_config.py
class FlaskConfig:
    SESSION_COOKIE_SECURE = True  # 仅HTTPS
    SESSION_COOKIE_HTTPONLY = True  # 禁止JS访问
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF防护
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)  # 24小时过期
```

---

### 6. API密钥明文存储和返回
**风险等级**: 🟠 High

**问题描述**:
- `web/api/tts_api.py:1455-1457` - 返回完整的 Gemini API Key 给前端

```python
'api_key': api_key,  # 返回完整key供前端填充
```

**潜在影响**:
- 任何登录用户可获取后端API密钥
- 密钥泄露导致第三方服务被滥用

**修复建议**:
```python
# 只返回前缀，用于识别
'api_key_configured': bool(api_key),
'key_prefix': api_key[:8] + '****' if api_key else None
```

---

## 🟡 中危级别 (Medium) - 建议1周内修复

### 7. 文件上传无类型验证
**风险等级**: 🟡 Medium

**问题描述**:
- 多处文件上传接口未验证文件类型和大小
- 可能存在目录遍历风险

**涉及的文件**:
- `cover_api.py` - 封面图片上传
- `still_image_api.py` - 剧照上传
- `creative_api.py` - 创意文件上传

**潜在影响**:
- 上传恶意文件（WebShell、病毒）
- 目录遍历导致任意文件写入

**修复建议**:
```python
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

def validate_file(file):
    # 验证扩展名
    ext = file.filename.rsplit('.', 1)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False
    
    # 验证MIME类型
    if file.mimetype not in ['image/png', 'image/jpeg', 'image/gif']:
        return False
    
    # 验证文件大小
    file.seek(0, 2)
    size = file.tell()
    file.seek(0)
    if size > MAX_FILE_SIZE:
        return False
    
    return True
```

---

### 8. 用户输入未充分过滤
**风险等级**: 🟡 Medium

**问题描述**:
- 部分接口直接拼接用户输入到文件路径
- 小说标题等字段未做严格过滤

**潜在影响**:
- 路径遍历攻击（../../../etc/passwd）
- 存储型XSS（虽然前端有转义，但存在风险）

**修复建议**:
```python
import re
from werkzeug.utils import secure_filename

def sanitize_filename(name):
    # 移除危险字符
    name = secure_filename(name)
    # 限制长度
    name = name[:100]
    return name
```

---

### 9. 支付回调验证不足
**风险等级**: 🟡 Medium

**问题描述**:
- `web/api/payment_api.py` - 支付回调仅验证签名，无订单金额二次确认
- 无支付结果主动查询机制

**潜在影响**:
- 回调被篡改导致点数发放错误
- 重复回调导致重复充值

**修复建议**:
```python
# 1. 验证订单金额一致性
if float(params.get('money')) != order['amount']:
    logger.error(f"订单金额不匹配: {order_id}")
    return 'fail'

# 2. 幂等性检查
if order['status'] == 'completed':
    return 'success'  # 已处理，直接返回

# 3. 主动查询支付状态（可选）
```

---

## 🟢 低危级别 (Low) - 建议优化

### 10. 数据库连接未加密
**风险等级**: 🟢 Low

**问题描述**:
- SQLite 数据库文件无加密
- 敏感数据（手机号、邮箱）明文存储

**潜在影响**:
- 数据库文件被复制后可读取所有数据

**修复建议**:
```python
# 方案1: 使用 SQLCipher 加密 SQLite
# 方案2: 敏感字段加密存储
from cryptography.fernet import Fernet

cipher = Fernet(os.environ.get('DB_ENCRYPTION_KEY'))
encrypted_phone = cipher.encrypt(phone.encode()).decode()
```

---

### 11. 缺乏速率限制
**风险等级**: 🟢 Low

**问题描述**:
- 登录接口无速率限制
- API调用无频率控制

**潜在影响**:
- 暴力破解密码
- API被恶意刷取

**修复建议**:
```python
from flask_limiter import Limiter

limiter = Limiter(
    app,
    key_func=lambda: request.remote_addr,
    default_limits=["200 per day", "50 per hour"]
)

@app.route('/login', methods=['POST'])
@limiter.limit("5 per minute")  # 登录限制
def login():
    ...
```

---

### 12. 错误信息泄露
**风险等级**: 🟢 Low

**问题描述**:
- 部分API返回详细的错误堆栈
- 调试模式可能开启

**修复建议**:
```python
# 生产环境关闭调试模式
DEBUG = False

# 统一错误响应
@app.errorhandler(Exception)
def handle_error(error):
    logger.error(f"Error: {error}", exc_info=True)
    return jsonify({
        'success': False,
        'error': '服务器内部错误'
    }), 500
```

---

## 📋 上线前检查清单

### 必须完成（Critical）
- [ ] 修改硬编码的 SECRET_KEY，使用环境变量
- [ ] 删除或禁用 test 用户的任意密码登录
- [ ] 将 SHA256 密码哈希迁移到 bcrypt
- [ ] 删除所有硬编码的内部 API 密钥

### 强烈建议（High）
- [ ] 清理日志中的敏感信息
- [ ] 配置安全的 Cookie 属性
- [ ] 修复 API 密钥明文返回问题
- [ ] 启用 HTTPS（生产环境）

### 建议完成（Medium/Low）
- [ ] 添加文件上传类型验证
- [ ] 添加速率限制
- [ ] 配置数据库加密
- [ ] 添加安全响应头

---

## 🔧 快速修复脚本

创建 `scripts/security_fixes.py`：

```python
#!/usr/bin/env python3
"""
安全修复脚本 - 上线前必须运行
"""
import os
import secrets
import bcrypt

def generate_secure_key():
    """生成安全的密钥"""
    return secrets.token_urlsafe(32)

def check_environment():
    """检查环境变量配置"""
    required_vars = [
        'FLASK_SECRET_KEY',
        'INTERNAL_API_KEY',
        'DB_ENCRYPTION_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if not os.environ.get(var):
            missing.append(var)
    
    if missing:
        print(f"❌ 缺少环境变量: {', '.join(missing)}")
        print("请设置以下环境变量:")
        for var in missing:
            print(f"  export {var}={generate_secure_key()}")
        return False
    
    print("✅ 环境变量检查通过")
    return True

def check_test_user():
    """检查test用户是否禁用"""
    print("⚠️ 请确认已禁用 test 用户的任意密码登录")
    print("   文件: web/auth.py, 行: 52-54")
    return True

if __name__ == '__main__':
    print("🔐 安全修复检查...")
    check_environment()
    check_test_user()
```

---

## 📞 后续建议

1. **定期安全审计**: 每季度进行一次安全审查
2. **渗透测试**: 上线前聘请专业团队进行渗透测试
3. **漏洞赏金计划**: 建立漏洞报告渠道
4. **安全培训**: 开发团队定期进行安全培训
5. **依赖更新**: 定期更新第三方库，修复已知漏洞

---

**报告生成时间**: 2026-03-05  
**下次审计时间**: 建议上线前再次审计
