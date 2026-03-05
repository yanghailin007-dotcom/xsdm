# 大文娱系统部署指南

## 快速部署步骤

### 1. 克隆代码到服务器

```bash
git clone https://github.com/yanghailin007-dotcom/xsdm.git
cd xsdm
```

### 2. 创建虚拟环境并安装依赖

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
# 或 .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 3. 配置环境变量

复制模板文件并修改：

```bash
cp .env.example .env
nano .env  # 或用其他编辑器
```

**必须修改的配置项：**

```bash
# Flask 安全密钥（生成命令：openssl rand -base64 32）
FLASK_SECRET_KEY=your-random-secret-key-here

# 内部API密钥
INTERNAL_API_KEY=your-internal-api-key-here

# 易支付配置（用于充值功能）
YIPAY_MERCHANT_ID=your_merchant_id
YIPAY_MERCHANT_KEY=your_merchant_key
YIPAY_API_URL=https://your-pay-server.com
```

### 4. 初始化数据库

```bash
python scripts/create_payment_table.py
```

### 5. 启动服务

开发模式：
```bash
python start.py
```

生产模式（Linux）：
```bash
gunicorn -w 4 -b 0.0.0.0:5000 web.wsgi:app
```

---

## .env 文件说明

| 变量名 | 说明 | 是否必须 |
|--------|------|----------|
| `FLASK_SECRET_KEY` | Flask 会话加密密钥 | ✅ 必须 |
| `INTERNAL_API_KEY` | 内部API通信密钥 | ✅ 必须 |
| `DB_ENCRYPTION_KEY` | 数据库加密密钥 | ❌ 可选 |
| `FLASK_DEBUG` | 调试模式（生产环境设为false） | ✅ 建议 |
| `YIPAY_MERCHANT_ID` | 易支付商户ID | ❌ 充值功能需要 |
| `YIPAY_MERCHANT_KEY` | 易支付商户密钥 | ❌ 充值功能需要 |
| `YIPAY_API_URL` | 易支付接口地址 | ❌ 充值功能需要 |

### 生成安全密钥

```bash
# Linux/Mac
export FLASK_SECRET_KEY=$(openssl rand -base64 32)
export INTERNAL_API_KEY=$(openssl rand -base64 32)

# 查看生成的密钥
echo $FLASK_SECRET_KEY
echo $INTERNAL_API_KEY
```

---

## 重要安全提醒

⚠️ **.env 文件包含敏感信息，请勿提交到 Git！**

该文件已被 .gitignore 排除，但请确保：
1. 不要手动添加 .env 到 git
2. 服务器上的 .env 文件设置 600 权限：`chmod 600 .env`
3. 定期更换密钥
4. 生产环境使用强密码

---

## 目录结构

```
xsdm/
├── .env                  # 环境变量（不提交到git）
├── .env.example          # 环境变量模板
├── .gitignore           # git忽略规则
├── requirements.txt     # Python依赖
├── web/                 # 主应用代码
├── config/              # 配置文件
├── scripts/             # 工具脚本
└── DEPLOY.md           # 本文件
```

---

## 故障排查

### 问题：环境变量未加载

检查 .env 文件是否存在：
```bash
ls -la .env
```

检查 python-dotenv 是否安装：
```bash
pip show python-dotenv
```

### 问题：支付功能不工作

检查支付配置：
```bash
cat .env | grep YIPAY
```

查看支付日志：
```bash
tail -f logs/payment.log
```
