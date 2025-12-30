# 用户注册系统部署指南

本文档介绍如何部署和配置用户注册系统，包括手机验证码功能。

## 目录

- [系统架构](#系统架构)
- [功能特性](#功能特性)
- [快速开始](#快速开始)
- [配置说明](#配置说明)
- [短信服务配置](#短信服务配置)
- [数据库结构](#数据库结构)
- [API接口文档](#api接口文档)
- [安全建议](#安全建议)
- [故障排查](#故障排查)

---

## 系统架构

### 核心组件

```
┌─────────────────┐      ┌──────────────────┐
│   注册页面      │─────▶│   注册API        │
│  register.html  │      │ register_api.py  │
└─────────────────┘      └────────┬─────────┘
                                  │
                                  ▼
                         ┌──────────────────┐
                         │   验证码服务     │
                         │  sms_service.py  │
                         └────────┬─────────┘
                                  │
                    ┌─────────────┴─────────────┐
                    ▼                           ▼
            ┌───────────────┐          ┌───────────────┐
            │   用户模型    │          │  短信服务商   │
            │ user_model.py │          │ (阿里/腾讯)   │
            └───────┬───────┘          └───────────────┘
                    │
                    ▼
            ┌───────────────┐
            │ SQLite数据库  │
            │  users.db     │
            └───────────────┘
```

### 文件结构

```
web/
├── models/
│   ├── __init__.py
│   └── user_model.py           # 用户数据模型
├── services/
│   ├── __init__.py
│   └── sms_service.py          # 短信服务
├── api/
│   └── register_api.py         # 注册API路由
├── routes/
│   └── auth_routes.py          # 认证路由（已更新）
├── templates/
│   ├── register.html           # 注册页面
│   └── login.html              # 登录页面（已更新）
└── web_server_refactored.py    # Web服务器（已更新）
```

---

## 功能特性

### 1. 用户注册

- ✅ 用户名唯一性验证
- ✅ 密码强度检查
- ✅ 手机号格式验证
- ✅ 手机验证码验证
- ✅ 可选邮箱字段
- ✅ 防重复注册

### 2. 手机验证码

- ✅ 支持3个主流短信服务商（阿里云、腾讯云、聚合数据）
- ✅ 开发模式支持模拟发送
- ✅ 验证码5分钟有效期
- ✅ 频率限制（1小时最多3次）
- ✅ 自动清理过期验证码

### 3. 安全特性

- ✅ 密码哈希存储（SHA256）
- ✅ 验证码一次性使用
- ✅ 频率限制防刷
- ✅ Session管理
- ✅ 登录日志记录

---

## 快速开始

### 1. 启动开发服务器

开发模式使用模拟短信服务，验证码会直接显示在服务器日志中。

```bash
# 确保已安装依赖
pip install -r requirements.txt

# 设置环境变量（可选，默认使用mock模式）
export SMS_PROVIDER=mock

# 启动服务器
python web/web_server_refactored.py
```

### 2. 访问注册页面

```bash
# 在浏览器中打开
http://localhost:5000/register
```

### 3. 测试注册流程

1. 填写用户名（3-20个字符，字母数字下划线）
2. 填写密码（至少6个字符）
3. 确认密码
4. 填写手机号（11位，1开头）
5. 点击"发送验证码"按钮
6. 开发模式会在服务器日志和页面提示中显示验证码
7. 输入验证码
8. 点击"注册"按钮
9. 注册成功后自动跳转到登录页面

---

## 配置说明

### 环境变量配置

在 `.env` 文件或系统环境变量中配置：

```bash
# 短信服务商选择
# 可选值：mock（开发模式）、aliyun（阿里云）、tencent（腾讯云）
SMS_PROVIDER=mock

# 数据库路径（可选，默认为 data/users.db）
# USER_DB_PATH=data/users.db
```

### 验证码配置

在 `web/services/sms_service.py` 中可调整：

```python
# 频率限制
max_requests=3          # 时间窗口内最大请求次数
window_seconds=3600     # 时间窗口（秒）

# 验证码有效期
expiry_minutes=5        # 验证码有效期（分钟）
```

---

## 短信服务配置

### 开发模式（mock）

无需配置，验证码直接显示在日志中。

```bash
SMS_PROVIDER=mock
```

### 阿里云短信

1. **注册阿里云并开通短信服务**

   访问：https://www.aliyun.com/product/sms

2. **获取AccessKey**

   - 进入控制台
   - 创建AccessKey
   - 记录 AccessKey ID 和 AccessKey Secret

3. **配置短信签名和模板**

   - 申请短信签名（如：小说生成系统）
   - 申请短信模板（如：您的验证码是${code}，5分钟内有效。）

4. **配置环境变量**

```bash
SMS_PROVIDER=aliyun
ALIYUN_ACCESS_KEY_ID=your_access_key_id
ALIYUN_ACCESS_KEY_SECRET=your_access_key_secret
ALIYUN_SMS_SIGN_NAME=小说生成系统
ALIYUN_SMS_TEMPLATE_CODE=SMS_123456789
```

### 腾讯云短信

1. **注册腾讯云并开通短信服务**

   访问：https://cloud.tencent.com/product/sms

2. **获取API密钥**

   - 进入控制台
   - 创建密钥
   - 记录 SecretId 和 SecretKey

3. **配置短信应用**

   - 创建短信应用
   - 配置签名和模板

4. **配置环境变量**

```bash
SMS_PROVIDER=tencent
TENCENT_SMS_SECRET_ID=your_secret_id
TENCENT_SMS_SECRET_KEY=your_secret_key
TENCENT_SMS_APP_ID=12345678
TENCENT_SMS_SIGN_NAME=小说生成系统
TENCENT_SMS_TEMPLATE_ID=12345
```

---

## 数据库结构

### users 表

```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,           -- 用户名
    password_hash TEXT NOT NULL,             -- 密码哈希
    phone TEXT UNIQUE NOT NULL,              -- 手机号
    email TEXT,                              -- 邮箱（可选）
    is_active INTEGER DEFAULT 1,             -- 账户状态
    is_admin INTEGER DEFAULT 0,              -- 管理员标识
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login_at TIMESTAMP                  -- 最后登录时间
);
```

### verification_codes 表

```sql
CREATE TABLE verification_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT NOT NULL,                     -- 手机号
    code TEXT NOT NULL,                      -- 验证码
    type TEXT NOT NULL,                      -- 类型（register/login/reset）
    expires_at TIMESTAMP NOT NULL,           -- 过期时间
    used INTEGER DEFAULT 0,                  -- 是否已使用
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ip_address TEXT                          -- 请求IP
);
```

### login_logs 表

```sql
CREATE TABLE login_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,                         -- 用户ID
    username TEXT,                           -- 用户名
    action TEXT NOT NULL,                    -- 动作
    ip_address TEXT,                         -- IP地址
    user_agent TEXT,                         -- 用户代理
    success INTEGER DEFAULT 1,               -- 是否成功
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

---

## API接口文档

### 1. 发送验证码

**接口：** `POST /api/register/send-code`

**请求体：**
```json
{
    "phone": "13800138000"
}
```

**响应：**
```json
{
    "success": true,
    "message": "验证码已发送",
    "expires_in": 300,
    "code": "123456",  // 仅开发模式
    "dev_mode": true   // 仅开发模式
}
```

### 2. 验证验证码

**接口：** `POST /api/register/verify-code`

**请求体：**
```json
{
    "phone": "13800138000",
    "code": "123456"
}
```

**响应：**
```json
{
    "success": true,
    "message": "验证成功"
}
```

### 3. 用户注册

**接口：** `POST /api/register`

**请求体：**
```json
{
    "username": "testuser",
    "password": "password123",
    "phone": "13800138000",
    "code": "123456",
    "email": "optional@email.com"
}
```

**响应：**
```json
{
    "success": true,
    "message": "注册成功",
    "user_id": 1
}
```

### 4. 检查用户名

**接口：** `POST /api/register/check-username`

**请求体：**
```json
{
    "username": "testuser"
}
```

**响应：**
```json
{
    "success": true,
    "available": true
}
```

---

## 安全建议

### 生产环境部署

1. **使用更强的密码哈希算法**

   当前使用SHA256，建议升级为bcrypt：

```python
# 安装bcrypt
pip install bcrypt

# 修改 web/models/user_model.py
import bcrypt

def _hash_password(self, password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(self, password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

2. **启用HTTPS**

   生产环境必须使用HTTPS保护传输数据。

3. **配置CORS**

   限制跨域访问来源。

4. **配置Session密钥**

```python
app.secret_key = 'your-random-secret-key-32-chars'
```

5. **数据库备份**

   定期备份 `data/users.db` 数据库。

### 防护措施

- ✅ 频率限制防刷
- ✅ 验证码有效期限制
- ✅ 密码强度要求
- ✅ 用户名格式验证
- ✅ 手机号格式验证

---

## 故障排查

### 1. 数据库初始化失败

**问题：** 启动时数据库初始化报错

**解决方案：**
```bash
# 手动创建数据目录
mkdir -p data

# 检查权限
chmod 755 data
```

### 2. 短信发送失败

**问题：** 验证码发送失败

**解决方案：**
1. 检查环境变量是否正确配置
2. 检查短信服务商账户余额
3. 检查签名和模板是否通过审核
4. 查看服务器日志获取详细错误信息

### 3. 验证码验证失败

**问题：** 输入正确验证码但验证失败

**解决方案：**
1. 检查验证码是否过期（5分钟有效期）
2. 检查验证码是否已被使用
3. 清除浏览器缓存和Cookie
4. 重新获取验证码

### 4. 注册后无法登录

**问题：** 注册成功但登录失败

**解决方案：**
1. 检查用户认证逻辑是否正确
2. 查看数据库中用户记录是否正确创建
3. 检查Session配置
4. 查看服务器日志

---

## 开发调试

### 查看日志

```bash
# 实时查看日志
tail -f logs/novel_generator.log

# 搜索注册相关日志
grep "注册" logs/novel_generator.log
```

### 数据库查询

```bash
# 使用sqlite3查询数据库
sqlite3 data/users.db

# 查询所有用户
SELECT * FROM users;

# 查询最近的验证码
SELECT * FROM verification_codes ORDER BY created_at DESC LIMIT 10;
```

### 测试API

```bash
# 测试发送验证码
curl -X POST http://localhost:5000/api/register/send-code \
  -H "Content-Type: application/json" \
  -d '{"phone":"13800138000"}'

# 测试注册
curl -X POST http://localhost:5000/api/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"password123","phone":"13800138000","code":"123456"}'
```

---

## 常见问题

### Q: 如何切换到生产短信服务？

A: 修改 `config/config.py` 文件中的 `sms.provider` 变量，并配置对应的短信服务商信息。

### Q: 验证码有效期可以调整吗？

A: 可以。在 `config/config.py` 中修改 `sms.expiry_minutes` 参数。

### Q: 验证码有效期可以调整吗？

A: 可以。在 `web/api/register_api.py` 中修改 `expiry_minutes` 参数。

### Q: 如何禁用注册功能？

A: 在 `web/routes/auth_routes.py` 中注释掉注册路由即可。

### Q: 支持其他国家的手机号吗？

A: 当前仅支持中国手机号格式（1开头的11位数字）。如需支持其他国家，需修改验证逻辑。

---

## 更新日志

### v1.0.0 (2024-12-30)

- ✅ 实现用户注册功能
- ✅ 集成手机验证码
- ✅ 支持多个短信服务商
- ✅ 开发模式模拟发送
- ✅ 频率限制防刷
- ✅ 用户数据持久化

---

## 技术支持

如有问题，请查看：
1. 服务器日志：`logs/novel_generator.log`
2. 数据库文件：`data/users.db`
3. 环境配置：`.env`

---

## 许可证

本注册系统集成在小说生成系统中，遵循项目整体许可证。