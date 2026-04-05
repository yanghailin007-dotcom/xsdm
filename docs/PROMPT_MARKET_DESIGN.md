# 提示词包市场 - 技术设计文档

**版本**: v1.0  
**日期**: 2026-04-05  
**状态**: 待开发

---

## 目录

1. [概述](#1-概述)
2. [系统架构](#2-系统架构)
3. [数据模型](#3-数据模型)
4. [加密与安全](#4-加密与安全)
5. [API接口](#5-api接口)
6. [核心流程](#6-核心流程)
7. [前端设计](#7-前端设计)
8. [支付与提现](#8-支付与提现)
9. [部署配置](#9-部署配置)

---

## 1. 概述

### 1.1 业务目标

构建一个创作者经济生态：
- **创作者**: 可创建加密提示词包，获得80%销售分成
- **用户**: 可购买/使用提示词包，提升创作效率
- **平台**: 20%抽成，通过会员、广告等多元变现

### 1.2 核心功能

| 模块 | 功能 |
|------|------|
| 创作者中心 | 创建包、设置价格、查看收益、提现 |
| 提示词市场 | 浏览、搜索、预览、购买 |
| 加密系统 | 内容加密、防破解、水印追踪 |
| 支付系统 | 微信支付、支付宝、余额支付 |
| 会员系统 | 月度/年度订阅、权益管理 |

### 1.3 技术栈

- **后端**: Python Flask + SQLAlchemy + Redis
- **数据库**: PostgreSQL (主) + Redis (缓存)
- **前端**: Vue3 + TypeScript + Element Plus
- **支付**: 微信支付JSAPI、支付宝当面付
- **存储**: 阿里云OSS (加密包存储)

---

## 2. 系统架构

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                         前端层 (Vue3)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   用户端      │  │   创作者端    │  │   管理后台    │          │
│  │  (购买/使用)  │  │ (创建/收益)   │  │  (审核/运营)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         API网关 (Nginx)                          │
│                     限流、鉴权、日志                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      业务服务 (Flask)                            │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │
│  │  用户服务   │ │  市场服务   │ │  支付服务   │ │  加密服务   │   │
│  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │
│  ┌────────────┐ ┌────────────┐ ┌────────────┐                 │
│  │  创作者服务 │ │  会员服务   │ │  消息服务   │                 │
│  └────────────┘ └────────────┘ └────────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      数据层                                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  PostgreSQL  │  │    Redis     │  │  阿里云OSS   │          │
│  │   (主数据)    │  │   (缓存)     │  │  (文件存储)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 服务拆分

```python
# 服务模块划分

services/
├── user_service/          # 用户服务
│   ├── auth.py           # 登录注册
│   ├── profile.py        # 用户资料
│   └── membership.py     # 会员权益

├── creator_service/       # 创作者服务
│   ├── creator.py        # 创作者认证
│   ├── package.py        # 包管理
│   ├── revenue.py        # 收益计算
│   └── withdrawal.py     # 提现

├── market_service/        # 市场服务
│   ├── browse.py         # 浏览/搜索
│   ├── purchase.py       # 购买
│   ├── review.py         # 评价
│   └── preview.py        # 预览

├── encryption_service/    # 加密服务
│   ├── encryptor.py      # 加密算法
│   ├── watermark.py      # 水印
│   └── anti_tamper.py    # 防破解

├── payment_service/       # 支付服务
│   ├── wechat_pay.py     # 微信支付
│   ├── alipay.py         # 支付宝
│   └── balance.py        # 余额

└── notification_service/  # 消息服务
    ├── sms.py            # 短信
    ├── email.py          # 邮件
    └── webhook.py        # 回调
```

---

## 3. 数据模型

### 3.1 ER图

```
┌──────────────────┐         ┌──────────────────┐
│     users        │         │    creators      │
├──────────────────┤         ├──────────────────┤
│ id (PK)          │◄───────►│ id (PK)          │
│ username         │   1:1   │ user_id (FK)     │
│ email            │         │ level            │
│ phone            │         │ revenue_share    │
│ balance          │         │ total_sales      │
│ membership_type  │         │ rating           │
│ created_at       │         │ followers        │
└──────────────────┘         └──────────────────┘
                                       │
                                       │ 1:N
                                       ▼
┌──────────────────┐         ┌──────────────────┐
│  purchases       │         │ prompt_packages  │
├──────────────────┤         ├──────────────────┤
│ id (PK)          │   N:1   │ id (PK)          │
│ user_id (FK)     │◄────────│ creator_id (FK)  │
│ package_id (FK)  │         │ name             │
│ price_paid       │         │ description      │
│ platform_fee     │         │ encrypted_data   │
│ creator_earning  │         │ price            │
│ status           │         │ is_free          │
│ created_at       │         │ sales_count      │
└──────────────────┘         │ rating           │
                             │ status           │
                             └──────────────────┘
                                       │
                                       │ 1:N
                                       ▼
                             ┌──────────────────┐
                             │ package_contents │
                             ├──────────────────┤
                             │ id (PK)          │
                             │ package_id (FK)  │
                             │ content_type     │
                             │ encrypted_chunk  │
                             │ chunk_order      │
                             └──────────────────┘
```

### 3.2 详细表结构

```sql
-- 用户表
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE,
    phone VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    avatar_url VARCHAR(500),
    balance DECIMAL(10,2) DEFAULT 0.00,
    membership_type VARCHAR(20) DEFAULT 'free', -- free/month/year
    membership_expire_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创作者表
CREATE TABLE creators (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    level VARCHAR(20) DEFAULT 'trainee', -- trainee/certified/premium/star/partner
    revenue_share_rate DECIMAL(3,2) DEFAULT 0.60,
    total_sales DECIMAL(12,2) DEFAULT 0.00,
    total_withdrawal DECIMAL(12,2) DEFAULT 0.00,
    rating DECIMAL(2,1) DEFAULT 5.0,
    follower_count INTEGER DEFAULT 0,
    bio TEXT,
    wechat_qr VARCHAR(500), -- 加密存储
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_creator_level (level),
    INDEX idx_creator_rating (rating DESC)
);

-- 提示词包表
CREATE TABLE prompt_packages (
    id BIGSERIAL PRIMARY KEY,
    creator_id BIGINT REFERENCES creators(id) ON DELETE CASCADE,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    short_desc VARCHAR(200), -- 卡片展示用
    cover_image VARCHAR(500),
    
    -- 加密相关
    encryption_version VARCHAR(10) DEFAULT 'v2.0',
    encrypted_data JSONB NOT NULL, -- 加密后的提示词
    watermark_config JSONB, -- 水印配置
    
    -- 价格
    price DECIMAL(10,2) DEFAULT 0.00,
    original_price DECIMAL(10,2), -- 划线价
    is_free BOOLEAN DEFAULT FALSE,
    
    -- 统计
    sales_count INTEGER DEFAULT 0,
    view_count INTEGER DEFAULT 0,
    rating DECIMAL(2,1) DEFAULT 5.0,
    review_count INTEGER DEFAULT 0,
    
    -- 分类
    genre VARCHAR(50), -- 题材：国运/神豪/奶爸
    tags VARCHAR(50)[], -- 标签数组
    difficulty VARCHAR(20), -- 难度：beginner/intermediate/advanced
    
    -- 状态
    status VARCHAR(20) DEFAULT 'draft', -- draft/pending/approved/rejected/banned
    admin_note TEXT, -- 审核备注
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_package_status (status),
    INDEX idx_package_genre (genre),
    INDEX idx_package_price (price),
    INDEX idx_package_sales (sales_count DESC),
    INDEX idx_package_rating (rating DESC),
    FULLTEXT INDEX idx_package_search (name, description)  -- 全文搜索
);

-- 包内容分块表（用于大提示词分块加密）
CREATE TABLE package_contents (
    id BIGSERIAL PRIMARY KEY,
    package_id BIGINT REFERENCES prompt_packages(id) ON DELETE CASCADE,
    chunk_order INTEGER NOT NULL,
    content_type VARCHAR(50), -- header/instruction/example/output
    encrypted_chunk TEXT NOT NULL,
    checksum VARCHAR(64), -- SHA256校验
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (package_id, chunk_order)
);

-- 购买记录表
CREATE TABLE purchases (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    package_id BIGINT REFERENCES prompt_packages(id),
    order_no VARCHAR(64) UNIQUE NOT NULL,
    
    -- 金额
    price_paid DECIMAL(10,2) NOT NULL,
    platform_fee DECIMAL(10,2) NOT NULL,
    creator_earning DECIMAL(10,2) NOT NULL,
    
    -- 支付
    payment_method VARCHAR(20), -- wechat/alipay/balance
    payment_status VARCHAR(20) DEFAULT 'pending', -- pending/paid/failed/refunded
    paid_at TIMESTAMP,
    
    -- 使用限制
    daily_calls_limit INTEGER DEFAULT 100,
    monthly_calls_limit INTEGER DEFAULT 3000,
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_purchase_user (user_id),
    INDEX idx_purchase_order (order_no),
    INDEX idx_purchase_status (payment_status)
);

-- 使用记录表（用于限流和统计）
CREATE TABLE usage_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    package_id BIGINT REFERENCES prompt_packages(id),
    purchase_id BIGINT REFERENCES purchases(id),
    call_type VARCHAR(20), -- preview/full/custom
    tokens_used INTEGER,
    input_preview TEXT, -- 输入前100字符
    output_preview TEXT, -- 输出前100字符
    ip_address VARCHAR(45),
    user_agent TEXT,
    risk_score INTEGER DEFAULT 0, -- 风险评分
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_usage_user_package (user_id, package_id),
    INDEX idx_usage_created (created_at)
);

-- 评价表
CREATE TABLE reviews (
    id BIGSERIAL PRIMARY KEY,
    package_id BIGINT REFERENCES prompt_packages(id),
    user_id BIGINT REFERENCES users(id),
    purchase_id BIGINT REFERENCES purchases(id),
    rating INTEGER CHECK (rating >= 1 AND rating <= 5),
    content TEXT,
    is_anonymous BOOLEAN DEFAULT FALSE,
    helpful_count INTEGER DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active', -- active/hidden
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_review_package (package_id),
    INDEX idx_review_rating (rating DESC)
);

-- 创作者提现表
CREATE TABLE withdrawals (
    id BIGSERIAL PRIMARY KEY,
    creator_id BIGINT REFERENCES creators(id),
    amount DECIMAL(10,2) NOT NULL,
    status VARCHAR(20) DEFAULT 'pending', -- pending/processing/completed/failed
    withdrawal_method VARCHAR(20), -- wechat/alipay/bank
    account_info VARCHAR(255), -- 加密存储
    processed_at TIMESTAMP,
    admin_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_withdrawal_creator (creator_id),
    INDEX idx_withdrawal_status (status)
);

-- 会员订阅表
CREATE TABLE subscriptions (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id),
    plan_type VARCHAR(20), -- month/year
    price DECIMAL(10,2),
    started_at TIMESTAMP,
    expires_at TIMESTAMP,
    auto_renew BOOLEAN DEFAULT TRUE,
    status VARCHAR(20) DEFAULT 'active', -- active/cancelled/expired
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 邀请关系表
CREATE TABLE referrals (
    id BIGSERIAL PRIMARY KEY,
    inviter_id BIGINT REFERENCES users(id),
    invitee_id BIGINT REFERENCES users(id),
    referral_code VARCHAR(20),
    reward_claimed BOOLEAN DEFAULT FALSE,
    reward_amount DECIMAL(10,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (inviter_id, invitee_id)
);

-- 系统配置表
CREATE TABLE system_configs (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认配置
INSERT INTO system_configs (key, value, description) VALUES
('revenue_share', '{"platform": 0.20, "creator_trainee": 0.60, "creator_certified": 0.70, "creator_premium": 0.75, "creator_star": 0.80, "creator_partner": 0.85}', '分成比例配置'),
('membership_benefits', '{"month": {"discount": 0.90, "free_packages": ["basic"]}, "year": {"discount": 0.80, "free_packages": ["basic", "intermediate"]}}', '会员权益配置'),
('encryption_keys', '{"current_version": "v2.0", "key_rotation_date": "2026-04-01"}', '加密密钥配置');
```

---

## 4. 加密与安全

### 4.1 加密流程

```python
# web/services/encryption/prompt_encryptor.py

import json
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from typing import Dict, List
import secrets

class PromptEncryptor:
    """
    提示词加密器
    采用多层加密 + 混淆策略
    """
    
    # 密钥应从环境变量或KMS获取
    MASTER_KEY = None  # 在初始化时加载
    
    def __init__(self):
        self.master_key = self._load_master_key()
        self.obfuscation_map = self._generate_obfuscation_map()
    
    def encrypt_package(self, raw_prompts: Dict, author_id: str) -> Dict:
        """
        加密整个提示词包
        """
        # 1. 内容混淆
        obfuscated = self._obfuscate_content(raw_prompts)
        
        # 2. 结构分块
        chunks = self._split_into_chunks(obfuscated)
        
        # 3. 加密每个块
        encrypted_chunks = []
        for i, chunk in enumerate(chunks):
            encrypted = self._encrypt_chunk(chunk, author_id, i)
            encrypted_chunks.append({
                "order": i,
                "type": chunk["type"],
                "data": encrypted["ciphertext"],
                "iv": encrypted["iv"],
                "checksum": encrypted["checksum"]
            })
        
        # 4. 生成访问令牌
        access_token = self._generate_access_token(author_id)
        
        # 5. 嵌入水印
        watermark = self._generate_watermark(author_id)
        
        return {
            "version": "v2.0",
            "chunks": encrypted_chunks,
            "access_token": access_token,
            "watermark": watermark,
            "chunk_order": self._shuffle_order(len(chunks)),
            "metadata": {
                "total_chunks": len(chunks),
                "author_id": self._hash_author_id(author_id),
                "created_at": datetime.now().isoformat()
            }
        }
    
    def _obfuscate_content(self, prompts: Dict) -> Dict:
        """
        内容混淆：保留功能，隐藏实现
        """
        # 预定义的混淆映射（可定期更新）
        keyword_map = {
            # 角色混淆
            "你是一位网文专家": "[[角色]]_1",
            "你是一名资深编辑": "[[角色]]_2",
            "你是番茄小说编辑": "[[角色]]_3",
            
            # 概念混淆
            "爆款": "[[热门]]",
            "套路": "[[模式]]",
            "爽点": "[[亮点]]",
            "金手指": "[[能力]]",
            "装逼": "[[展示]]",
            "打脸": "[[反击]]",
            
            # 指令混淆
            "请写": "[[执行]]",
            "生成": "[[创建]]",
            "创作": "[[产出]]",
            "prompt": "[[P]]",
            "指令": "[[CMD]]",
            
            # 输出格式混淆
            "JSON": "[[J]]",
            "Markdown": "[[M]]",
            "列表": "[[L]]",
        }
        
        def obfuscate_text(text: str) -> str:
            for key, value in keyword_map.items():
                text = text.replace(key, value)
            return text
        
        result = {}
        for key, value in prompts.items():
            if isinstance(value, str):
                result[key] = obfuscate_text(value)
            elif isinstance(value, dict):
                result[key] = self._obfuscate_content(value)
            elif isinstance(value, list):
                result[key] = [obfuscate_text(item) if isinstance(item, str) else item for item in value]
            else:
                result[key] = value
        
        return result
    
    def _split_into_chunks(self, prompts: Dict) -> List[Dict]:
        """
        将提示词拆分为逻辑块
        """
        chunks = []
        
        # 系统角色块
        if "system_role" in prompts:
            chunks.append({
                "type": "system",
                "content": prompts["system_role"]
            })
        
        # 上下文块
        if "context" in prompts:
            chunks.append({
                "type": "context",
                "content": prompts["context"]
            })
        
        # 指令块
        if "instructions" in prompts:
            for i, instruction in enumerate(prompts["instructions"]):
                chunks.append({
                    "type": f"instruction_{i}",
                    "content": instruction
                })
        
        # 示例块
        if "examples" in prompts:
            chunks.append({
                "type": "examples",
                "content": json.dumps(prompts["examples"], ensure_ascii=False)
            })
        
        # 输出格式块
        if "output_format" in prompts:
            chunks.append({
                "type": "output",
                "content": json.dumps(prompts["output_format"], ensure_ascii=False)
            })
        
        return chunks
    
    def _encrypt_chunk(self, chunk: Dict, author_id: str, chunk_index: int) -> Dict:
        """
        AES-256-GCM 加密单个块
        """
        # 派生密钥
        chunk_key = self._derive_key(author_id, chunk_index)
        
        # 准备数据
        plaintext = json.dumps(chunk, ensure_ascii=False).encode('utf-8')
        
        # AES-256-GCM 加密
        cipher = AES.new(chunk_key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(pad(plaintext, AES.block_size))
        
        # 计算校验和
        checksum = hashlib.sha256(plaintext).hexdigest()
        
        return {
            "ciphertext": base64.b64encode(ciphertext).decode('utf-8'),
            "iv": base64.b64encode(cipher.nonce).decode('utf-8'),
            "tag": base64.b64encode(tag).decode('utf-8'),
            "checksum": checksum
        }
    
    def _generate_watermark(self, author_id: str) -> str:
        """
        生成隐形水印（零宽字符）
        用于追踪泄露源
        """
        # 将 author_id 转换为二进制
        binary = ''.join(format(ord(c), '08b') for c in str(author_id))
        
        # 零宽字符映射
        zero_width_map = {
            '0': '\u200B',  # 零宽空格
            '1': '\u200C',  # 零宽非连接符
        }
        
        watermark = ''.join(zero_width_map[b] for b in binary)
        
        # 添加起始和结束标记
        start_marker = '\u200D'  # 零宽连接符
        end_marker = '\uFEFF'    # 零宽无断开空格
        
        return start_marker + watermark + end_marker
    
    def decrypt_for_execution(self, encrypted_package: Dict, user_id: str, 
                             purchase_id: str) -> Dict:
        """
        解密用于执行（仅服务端）
        """
        # 验证权限
        if not self._verify_access(encrypted_package, user_id, purchase_id):
            raise PermissionError("无权限访问此提示词包")
        
        # 验证令牌
        if not self._verify_token(encrypted_package["access_token"], user_id):
            raise PermissionError("访问令牌无效或已过期")
        
        # 解密块
        chunks = []
        chunk_order = encrypted_package["chunk_order"]
        
        for idx in chunk_order:
            chunk_data = encrypted_package["chunks"][idx]
            decrypted = self._decrypt_chunk(
                chunk_data, 
                encrypted_package["metadata"]["author_id"],
                idx
            )
            chunks.append(decrypted)
        
        # 重组
        reconstructed = self._reconstruct_prompts(chunks)
        
        # 反混淆
        deobfuscated = self._deobfuscate(reconstructed)
        
        # 嵌入水印（用于追踪）
        watermarked = self._embed_watermark_in_output(deobfuscated, user_id)
        
        return watermarked
    
    def _verify_access(self, package: Dict, user_id: str, purchase_id: str) -> bool:
        """
        验证用户是否有权限访问
        """
        # 检查购买记录
        # 检查是否在有效期内
        # 检查调用次数限制
        pass
```

### 4.2 防破解系统

```python
# web/services/encryption/anti_tamper.py

class AntiTamperSystem:
    """
    防破解检测系统
    """
    
    RISK_THRESHOLDS = {
        "low": 20,
        "medium": 50,
        "high": 80
    }
    
    def __init__(self, redis_client):
        self.redis = redis_client
        self.alert_handlers = []
    
    def check_request(self, user_id: str, package_id: str, 
                     request_data: Dict, context: Dict) -> Dict:
        """
        检查请求是否存在破解风险
        """
        risk_score = 0
        risk_factors = []
        
        # 1. 频率检测
        freq_risk = self._check_frequency(user_id, package_id)
        risk_score += freq_risk["score"]
        if freq_risk["score"] > 0:
            risk_factors.append(freq_risk["reason"])
        
        # 2. 行为模式检测
        behavior_risk = self._check_behavior_pattern(user_id, context)
        risk_score += behavior_risk["score"]
        if behavior_risk["score"] > 0:
            risk_factors.append(behavior_risk["reason"])
        
        # 3. 请求内容检测（尝试注入）
        content_risk = self._check_request_content(request_data)
        risk_score += content_risk["score"]
        if content_risk["score"] > 0:
            risk_factors.append(content_risk["reason"])
        
        # 4. 设备指纹检测
        device_risk = self._check_device_fingerprint(user_id, context)
        risk_score += device_risk["score"]
        if device_risk["score"] > 0:
            risk_factors.append(device_risk["reason"])
        
        # 风险评级
        level = self._calculate_risk_level(risk_score)
        
        result = {
            "risk_score": risk_score,
            "risk_level": level,
            "risk_factors": risk_factors,
            "action": self._determine_action(level)
        }
        
        # 高风险时记录并告警
        if level in ["high", "critical"]:
            self._log_suspicious_activity(user_id, package_id, result)
            self._trigger_alert(user_id, result)
        
        return result
    
    def _check_frequency(self, user_id: str, package_id: str) -> Dict:
        """
        检查调用频率是否异常
        """
        key = f"usage:{user_id}:{package_id}"
        
        # 获取最近1小时的调用次数
        hour_count = self.redis.zcount(key, time.time() - 3600, time.time())
        
        # 获取最近1天的调用次数
        day_count = self.redis.zcount(key, time.time() - 86400, time.time())
        
        if hour_count > 100:  # 1小时超过100次
            return {"score": 30, "reason": f"调用频率异常：1小时{hour_count}次"}
        
        if day_count > 1000:  # 1天超过1000次
            return {"score": 20, "reason": f"日调用量异常：{day_count}次"}
        
        return {"score": 0, "reason": ""}
    
    def _check_behavior_pattern(self, user_id: str, context: Dict) -> Dict:
        """
        检查行为模式是否异常
        """
        score = 0
        reasons = []
        
        # 检查是否总是请求最大输出长度
        if context.get("max_tokens_request", 0) > 10:
            score += 10
            reasons.append("频繁请求最大输出长度")
        
        # 检查输入是否总是很短（可能是在测试）
        avg_input_length = context.get("avg_input_length", 100)
        if avg_input_length < 20:
            score += 15
            reasons.append("输入长度过短，疑似测试行为")
        
        # 检查是否总是相同的输入（脚本攻击）
        if context.get("unique_input_ratio", 1.0) < 0.1:
            score += 40
            reasons.append("输入重复率过高，疑似脚本攻击")
        
        return {
            "score": score,
            "reason": "; ".join(reasons) if reasons else ""
        }
    
    def _determine_action(self, risk_level: str) -> str:
        """
        根据风险等级决定采取的措施
        """
        actions = {
            "low": "allow",      # 允许
            "medium": "captcha", # 要求验证码
            "high": "block_temp", # 临时封禁（30分钟）
            "critical": "block_perm" # 永久封禁
        }
        return actions.get(risk_level, "allow")
```

---

## 5. API接口

### 5.1 创作者API

```yaml
# 创作者认证
POST /api/v1/creators/apply
Request:
  {
    "real_name": "张三",
    "id_card": "310***********1234",  # 加密传输
    "phone": "138****1234",
    "bio": "10年网文编辑经验...",
    "sample_works": ["作品1链接", "作品2链接"]
  }
Response:
  {
    "success": true,
    "data": {
      "creator_id": "CRE-20260405-001",
      "status": "pending",  # 待审核
      "estimated_review_time": "3个工作日"
    }
  }

# 创建提示词包
POST /api/v1/creators/packages
Request:
  {
    "name": "国运文-直播流爆款生成器",
    "description": "详细描述...",
    "short_desc": "一句话简介",
    "genre": "国运文-直播类",
    "tags": ["国运", "直播", "震惊流"],
    "price": 99.00,
    "original_price": 199.00,
    "prompts": {
      "system_role": "你是一位...",
      "instructions": ["指令1", "指令2"],
      "examples": [{"input": "...", "output": "..."}],
      "output_format": {"type": "json", "schema": {...}}
    }
  }
Response:
  {
    "success": true,
    "data": {
      "package_id": "PKG-20260405-001",
      "encrypted_id": "enc_xxx",
      "status": "draft",
      "preview_url": "/preview/PKG-20260405-001"
    }
  }

# 获取创作者收益
GET /api/v1/creators/revenue?start_date=2026-03-01&end_date=2026-04-01
Response:
  {
    "success": true,
    "data": {
      "total_revenue": 12580.00,
      "total_sales": 156,
      "platform_fee": 2516.00,
      "net_earning": 10064.00,
      "pending_clearance": 2100.00,  # 待结算（7天保护期）
      "available_withdrawal": 7964.00,
      "daily_stats": [
        {"date": "2026-04-01", "sales": 5, "revenue": 495.00}
      ]
    }
  }

# 申请提现
POST /api/v1/creators/withdrawals
Request:
  {
    "amount": 5000.00,
    "method": "wechat",  # wechat/alipay/bank
    "account": "encrypted_xxx"  # 加密后的账号
  }
Response:
  {
    "success": true,
    "data": {
      "withdrawal_id": "WD-20260405-001",
      "status": "pending",
      "estimated_arrival": "3个工作日内"
    }
  }
```

### 5.2 市场API

```yaml
# 浏览提示词包
GET /api/v1/market/packages?genre=国运文&sort=sales&page=1&size=20
Response:
  {
    "success": true,
    "data": {
      "total": 156,
      "packages": [
        {
          "id": "PKG-001",
          "name": "国运文-直播流爆款生成器",
          "short_desc": "一句话简介",
          "cover_image": "https://...",
          "price": 99.00,
          "original_price": 199.00,
          "sales_count": 1200,
          "rating": 4.8,
          "review_count": 234,
          "creator": {
            "id": "CRE-001",
            "name": "猛哥",
            "avatar": "https://...",
            "level": "star"
          },
          "tags": ["国运", "直播"],
          "is_free": false
        }
      ]
    }
  }

# 预览效果
POST /api/v1/market/packages/{id}/preview
Request:
  {
    "test_input": "生成一个国运文开局..."
  }
Response:
  {
    "success": true,
    "data": {
      "output": "【预览效果】这是AI生成的内容...",
      "watermark": true,
      "truncated": true,  # 已截断
      "limitations": [
        "预览版限制500字输出",
        "完整版支持3000字"
      ],
      "tokens_used": 150
    }
  }

# 购买提示词包
POST /api/v1/market/packages/{id}/purchase
Request:
  {
    "payment_method": "wechat",
    "coupon_code": "xxx"  # 可选
  }
Response:
  {
    "success": true,
    "data": {
      "order_no": "ORD-20260405-001",
      "payment_url": "weixin://...",  # 微信支付URL
      "amount": 99.00,
      "expires_at": "2026-04-05T15:00:00"  # 支付超时时间
    }
  }

# 使用提示词包
POST /api/v1/market/packages/{id}/execute
Headers:
  Authorization: Bearer {token}
Request:
  {
    "input": "用户输入内容...",
    "parameters": {  # 可选参数
      "temperature": 0.7,
      "max_tokens": 2000
    }
  }
Response:
  {
    "success": true,
    "data": {
      "output": "AI生成的完整内容...",
      "tokens_used": 1250,
      "remaining_calls": 99,  # 今日剩余次数
      "watermark": "零宽字符水印"
    }
  }
```

### 5.3 会员API

```yaml
# 获取会员权益
GET /api/v1/membership/benefits
Response:
  {
    "success": true,
    "data": {
      "current_plan": "free",
      "benefits": {
        "month": {
          "price": 29.00,
          "discount": 0.90,
          "free_packages": ["basic_pack_1", "basic_pack_2"],
          "daily_calls": 100
        },
        "year": {
          "price": 199.00,
          "discount": 0.80,
          "free_packages": ["basic_pack_1", "basic_pack_2", "intermediate_pack_1"],
          "daily_calls": 300
        }
      }
    }
  }

# 订阅会员
POST /api/v1/membership/subscribe
Request:
  {
    "plan_type": "year",
    "payment_method": "alipay",
    "auto_renew": true
  }
Response:
  {
    "success": true,
    "data": {
      "subscription_id": "SUB-001",
      "status": "active",
      "expires_at": "2027-04-05T14:30:00"
    }
  }
```

---

## 6. 核心流程

### 6.1 购买流程

```
用户浏览市场
    ↓
选择提示词包
    ↓
预览效果（限制版）
    ↓
点击购买
    ↓
创建订单（待支付状态，15分钟超时）
    ↓
调起微信支付/支付宝
    ↓
支付成功回调
    ↓
创建购买记录（调用权限生效）
    ↓
通知创作者（有新订单）
    ↓
收益计算（平台20%，创作者80%）
    ↓
用户可使用完整功能
```

### 6.2 使用流程

```
用户选择已购买的包
    ↓
输入创作需求
    ↓
服务端验证权限（是否已购买、次数限制）
    ↓
解密提示词（服务端）
    ↓
组合完整Prompt
    ↓
调用AI模型（Kimi/OpenAI）
    ↓
嵌入水印到输出
    ↓
返回给用户
    ↓
记录使用日志（用于限流和统计）
```

### 6.3 提现流程

```
创作者申请提现（最低100元）
    ↓
系统验证可提现金额
    ↓
创建提现记录（pending状态）
    ↓
管理员审核（或自动审核）
    ↓
调用微信支付/支付宝转账接口
    ↓
更新提现状态（completed/failed）
    ↓
通知创作者
```

---

## 7. 前端设计

### 7.1 关键页面

```
pages/
├── market/                    # 提示词市场
│   ├── index.vue             # 市场首页（卡片网格）
│   ├── detail.vue            # 详情页（预览+购买）
│   └── search.vue            # 搜索结果

├── creator/                   # 创作者中心
│   ├── dashboard.vue         # 收益仪表盘
│   ├── packages/             # 我的包
│   │   ├── list.vue
│   │   ├── create.vue        # 创建/编辑
│   │   └── stats.vue         # 数据统计
│   ├── withdrawal.vue        # 提现
│   └── settings.vue          # 创作者设置

├── user/                      # 用户中心
│   ├── purchases.vue         # 已购买
│   ├── favorites.vue         # 收藏
│   └── membership.vue        # 会员中心

└── admin/                     # 管理后台
    ├── review.vue            # 审核
    ├── users.vue
    ├── creators.vue
    └── finance.vue           # 财务
```

### 7.2 关键组件

```vue
<!-- 提示词包卡片组件 -->
<template>
  <div class="package-card" @click="goToDetail">
    <div class="card-cover">
      <img :src="package.cover_image" />
      <span v-if="package.is_free" class="badge-free">免费</span>
      <span v-else-if="package.discount" class="badge-discount">-{{ discount }}%</span>
    </div>
    <div class="card-body">
      <h4 class="title">{{ package.name }}</h4>
      <p class="desc">{{ package.short_desc }}</p>
      <div class="meta">
        <span class="author">
          <img :src="package.creator.avatar" class="avatar" />
          {{ package.creator.name }}
        </span>
        <span class="rating">⭐ {{ package.rating }}</span>
        <span class="sales">已售 {{ formatNumber(package.sales_count) }}</span>
      </div>
    </div>
    <div class="card-footer">
      <span class="price">
        <span v-if="package.is_free" class="free">免费</span>
        <template v-else>
          <span class="current">¥{{ package.price }}</span>
          <span v-if="package.original_price" class="original">¥{{ package.original_price }}</span>
        </template>
      </span>
      <button class="btn-preview" @click.stop="preview">预览</button>
    </div>
  </div>
</template>

<!-- 预览模态框 -->
<template>
  <el-dialog v-model="visible" title="效果预览" width="800px">
    <div class="preview-container">
      <div class="input-section">
        <el-input 
          v-model="testInput" 
          type="textarea" 
          :rows="4"
          placeholder="输入测试内容，预览提示词效果..."
        />
        <el-button type="primary" @click="generatePreview" :loading="loading">
          生成预览
        </el-button>
      </div>
      
      <div v-if="result" class="output-section">
        <div class="output-header">
          <span>生成结果</span>
          <el-tag type="warning">预览版</el-tag>
        </div>
        <div class="output-content" v-html="formatOutput(result.output)" />
        <div class="output-footer">
          <p>💡 {{ result.watermark }}</p>
          <p v-for="limit in result.limitations" :key="limit">• {{ limit }}</p>
        </div>
      </div>
    </div>
  </el-dialog>
</template>
```

---

## 8. 支付与提现

### 8.1 微信支付集成

```python
# web/services/payment/wechat_pay.py

import requests
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime

class WechatPayService:
    """
    微信支付服务
    """
    
    def __init__(self):
        self.app_id = "wx..."  # 从配置读取
        self.mch_id = "16..."
        self.api_key = "..."
        self.notify_url = "https://api.example.com/webhook/wechat"
    
    def create_jsapi_order(self, order_no: str, amount: float, 
                          description: str, openid: str) -> Dict:
        """
        创建JSAPI支付订单
        """
        url = "https://api.mch.weixin.qq.com/pay/unifiedorder"
        
        params = {
            "appid": self.app_id,
            "mch_id": self.mch_id,
            "nonce_str": self._generate_nonce(),
            "body": description,
            "out_trade_no": order_no,
            "total_fee": int(amount * 100),  # 转为分
            "spbill_create_ip": "用户IP",
            "notify_url": self.notify_url,
            "trade_type": "JSAPI",
            "openid": openid
        }
        
        params["sign"] = self._generate_sign(params)
        
        xml_data = self._dict_to_xml(params)
        response = requests.post(url, data=xml_data)
        
        result = self._xml_to_dict(response.content)
        
        if result.get("return_code") == "SUCCESS" and result.get("result_code") == "SUCCESS":
            # 生成前端调起支付所需的参数
            prepay_id = result["prepay_id"]
            pay_params = {
                "appId": self.app_id,
                "timeStamp": str(int(datetime.now().timestamp())),
                "nonceStr": self._generate_nonce(),
                "package": f"prepay_id={prepay_id}",
                "signType": "RSA"  # 注意：v3版本使用RSA
            }
            pay_params["paySign"] = self._generate_rsa_sign(pay_params)
            
            return {
                "success": True,
                "payment_params": pay_params
            }
        
        return {
            "success": False,
            "error": result.get("err_code_des", "创建订单失败")
        }
    
    def transfer_to_user(self, openid: str, amount: float, 
                        desc: str, trade_no: str) -> Dict:
        """
        企业付款到零钱（提现）
        """
        url = "https://api.mch.weixin.qq.com/mmpaymkttransfers/promotion/transfers"
        
        params = {
            "mch_appid": self.app_id,
            "mchid": self.mch_id,
            "nonce_str": self._generate_nonce(),
            "partner_trade_no": trade_no,
            "openid": openid,
            "check_name": "NO_CHECK",
            "amount": int(amount * 100),
            "desc": desc,
            "spbill_create_ip": "服务器IP"
        }
        
        params["sign"] = self._generate_sign(params)
        
        # 需要证书
        response = requests.post(
            url, 
            data=self._dict_to_xml(params),
            cert=("apiclient_cert.pem", "apiclient_key.pem")
        )
        
        result = self._xml_to_dict(response.content)
        
        return {
            "success": result.get("return_code") == "SUCCESS",
            "payment_no": result.get("payment_no"),
            "payment_time": result.get("payment_time")
        }
```

---

## 9. 部署配置

### 9.1 环境变量

```bash
# .env.production

# 数据库
DATABASE_URL=postgresql://user:pass@localhost:5432/prompt_market
REDIS_URL=redis://localhost:6379/0

# 加密密钥（从KMS或安全服务获取）
PROMPT_ENCRYPTION_KEY=xxx
WATERMARK_SALT=xxx

# 微信支付
WECHAT_APP_ID=wx...
WECHAT_MCH_ID=16...
WECHAT_API_KEY=...
WECHAT_API_V3_KEY=...
WECHAT_CERT_PATH=/path/to/cert.pem
WECHAT_KEY_PATH=/path/to/key.pem

# 阿里云OSS
OSS_ACCESS_KEY_ID=...
OSS_ACCESS_KEY_SECRET=...
OSS_BUCKET=prompt-market
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com

# 其他
SECRET_KEY=flask-secret-key
JWT_SECRET_KEY=jwt-secret-key
LOG_LEVEL=INFO
```

### 9.2 Docker Compose

```yaml
# docker-compose.yml

version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/prompt_market
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs
      - ./certs:/app/certs

  db:
    image: postgres:15
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=prompt_market
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - app

volumes:
  postgres_data:
  redis_data:
```

---

## 10. 开发排期

| 阶段 | 时间 | 任务 |
|------|------|------|
| **Phase 1** | 2周 | 核心系统搭建（数据库、加密、基础API） |
| **Phase 2** | 2周 | 创作者中心（创建包、收益、提现） |
| **Phase 3** | 2周 | 提示词市场（浏览、搜索、购买） |
| **Phase 4** | 1周 | 会员系统、邀请系统 |
| **Phase 5** | 1周 | 支付对接、测试、优化 |
| **上线** | - | 内测 → 公测 |

**预估总工期**: 8周

---

## 附录

### A. 参考链接

- [星月写作创作者案例](http://mp.weixin.qq.com/s?__biz=...)
- [PromptBase模式分析](https://aitools.aiting.com/zh/ai/promptbase)
- [微信支付开发文档](https://pay.weixin.qq.com/wiki/doc/apiv3/index.shtml)

### B. 关键指标

| 指标 | 目标值 |
|------|--------|
| 加密破解难度 | > 3个月 |
| API响应时间 | < 200ms |
| 支付成功率 | > 95% |
| 创作者留存率 | > 60%（3个月） |

---

**文档结束**
