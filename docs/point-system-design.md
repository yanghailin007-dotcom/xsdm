# 大文娱系统 - 点数付费系统设计方案

## 一、系统概述

### 1.1 设计理念
- **创造点（Creative Points）**：用户通过创作行为获得和使用点数
- **免费起步**：新用户获得88点，足够体验完整功能
- **日活激励**：每日签到获得10点，鼓励持续使用
- **按量付费**：只消耗成功的AI调用，失败不扣点

### 1.2 核心流程
```
用户注册 → 获得88点 → 使用AI功能 → 按调用扣点 → 点数不足 → 签到/充值
```

---

## 二、数据库设计

### 2.1 用户点数表 (user_points)
```sql
CREATE TABLE user_points (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    balance INTEGER DEFAULT 0,           -- 当前余额
    total_earned INTEGER DEFAULT 0,      -- 累计获得
    total_spent INTEGER DEFAULT 0,       -- 累计消耗
    last_checkin_date DATE,              -- 最后签到日期
    checkin_streak INTEGER DEFAULT 0,    -- 连续签到天数
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 2.2 点数交易记录表 (point_transactions)
```sql
CREATE TABLE point_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    type VARCHAR(50) NOT NULL,           -- 类型: earn/spend
    amount INTEGER NOT NULL,             -- 数量(正数)
    balance_after INTEGER NOT NULL,      -- 交易后余额
    source VARCHAR(100),                 -- 来源: register/checkin/api_call/etc
    description TEXT,                    -- 描述
    related_id VARCHAR(100),             -- 关联ID(如task_id)
    status VARCHAR(20) DEFAULT 'success', -- success/failed/pending
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

### 2.3 点数配置表 (point_config)
```sql
CREATE TABLE point_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    config_key VARCHAR(100) NOT NULL UNIQUE,  -- 配置键
    config_value INTEGER NOT NULL,              -- 配置值
    description TEXT,                           -- 描述
    is_active BOOLEAN DEFAULT 1,                -- 是否启用
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_by INTEGER                          -- 更新者(管理员ID)
);
```

---

## 三、默认配置项

### 3.1 点数获取配置
| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `register_bonus` | 88 | 新用户注册赠送点数 |
| `daily_checkin` | 10 | 每日签到获得点数 |
| `checkin_streak_bonus` | 5 | 连续签到额外奖励 |

### 3.2 第一阶段 - 设定生成消耗
| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `phase1_planning` | 1 | 规划阶段 |
| `phase1_worldview` | 3 | 世界观生成 |
| `phase1_characters` | 2 | 角色设计(每个角色) |
| `phase1_outline` | 1 | 章节大纲(每10章) |
| `phase1_validation` | 1 | 质量评估 |

### 3.3 第二阶段 - 章节生成消耗
| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `phase2_chapter_batch` | 1 | 批量模式(每章) |
| `phase2_chapter_refined` | 2 | 精修模式(每章) |
| `phase2_regenerate` | 1 | 单章重生成 |

### 3.4 其他功能消耗
| 配置键 | 默认值 | 说明 |
|--------|--------|------|
| `cover_generation` | 5 | 封面生成(每张) |
| `fanqie_upload` | 2 | 番茄上传(每次) |
| `contract_assist` | 3 | 签约辅助(每次) |

---

## 四、API设计

### 4.1 用户端API

#### 获取当前点数
```
GET /api/points/balance
Response: { "balance": 88, "total_earned": 88, "total_spent": 0 }
```

#### 获取交易记录
```
GET /api/points/transactions?page=1&limit=20
Response: {
    "transactions": [...],
    "pagination": { "total": 100, "page": 1, "limit": 20 }
}
```

#### 每日签到
```
POST /api/points/checkin
Response: { 
    "success": true, 
    "earned": 10, 
    "balance": 98,
    "streak": 3,
    "message": "签到成功！连续3天，额外奖励5点"
}
```

#### 预估消耗（使用功能前调用）
```
POST /api/points/estimate
Body: { "action": "phase1", "params": { "total_chapters": 200 } }
Response: {
    "action": "phase1",
    "estimated_cost": 15,
    "breakdown": {
        "planning": 1,
        "worldview": 3,
        "characters": 6,  // 3个角色
        "outline": 4      // 200章/10*1
    },
    "current_balance": 88,
    "sufficient": true
}
```

### 4.2 服务端API（内部调用）

#### 扣除点数
```python
# 伪代码
result = point_service.spend_points(
    user_id=user.id,
    amount=estimated_cost,
    source="phase1_generation",
    description="第一阶段设定生成",
    related_id=task_id
)
if not result.success:
    return error("点数不足")
```

#### 失败回滚
```python
# AI调用失败时回滚点数
point_service.rollback_points(
    user_id=user.id,
    related_id=task_id,
    reason="AI调用失败"
)
```

### 4.3 管理员API

#### 获取配置
```
GET /api/admin/points/config
Response: {
    "earning": { "register_bonus": 88, "daily_checkin": 10 },
    "spending": { "phase1_worldview": 3, ... }
}
```

#### 更新配置
```
PUT /api/admin/points/config
Body: { "config_key": "phase1_worldview", "config_value": 5 }
Response: { "success": true }
```

#### 给用户加点数（人工补偿）
```
POST /api/admin/points/grant
Body: { "user_id": 123, "amount": 100, "reason": "活动奖励" }
```

---

## 五、前端界面设计

### 5.1 导航栏显示点数
```
[logo] 大文娱系统      [两阶段生成] [项目管理]...      💰 88点 [头像]
```

### 5.2 点数不足提示弹窗
```
┌─────────────────────────┐
│  ⚠️ 点数不足              │
│                          │
│  当前余额: 5点           │
│  预计需要: 15点          │
│                          │
│  [去签到 +10点] [充值]   │
│                          │
│  [取消]                  │
└─────────────────────────┘
```

### 5.3 消费确认弹窗
```
┌─────────────────────────┐
│  💰 确认使用点数          │
│                          │
│  操作: 第一阶段设定生成   │
│  预计消耗: 15点          │
│  当前余额: 88点          │
│  剩余: 73点              │
│                          │
│  [确认生成] [取消]       │
└─────────────────────────┘
```

### 5.4 管理后台界面
- 配置管理表格（可编辑各项消耗点数）
- 用户点数查询
- 交易记录查看
- 人工加减点数

---

## 六、核心业务逻辑

### 6.1 第一阶段消耗计算
```python
def calculate_phase1_cost(params):
    config = get_point_config()
    cost = 0
    
    # 规划阶段
    cost += config['phase1_planning']  # 1点
    
    # 世界观
    cost += config['phase1_worldview']  # 3点
    
    # 角色设计（预估3-5个角色）
    estimated_characters = 4
    cost += config['phase1_characters'] * estimated_characters  # 2*4=8点
    
    # 大纲（按章节数计算）
    total_chapters = params.get('total_chapters', 200)
    cost += (total_chapters // 10) * config['phase1_outline']  # 20*1=20点
    
    # 质量评估
    cost += config['phase1_validation']  # 1点
    
    return {
        'total': cost,
        'breakdown': {...}
    }
```

### 6.2 第二阶段消耗计算
```python
def calculate_phase2_cost(params):
    config = get_point_config()
    
    mode = params.get('mode', 'batch')  # batch 或 refined
    chapter_count = params.get('chapter_count', 5)
    
    if mode == 'batch':
        cost_per_chapter = config['phase2_chapter_batch']  # 1点
    else:
        cost_per_chapter = config['phase2_chapter_refined']  # 2点
    
    return chapter_count * cost_per_chapter
```

### 6.3 签到逻辑
```python
def daily_checkin(user_id):
    user_points = get_user_points(user_id)
    
    # 检查今天是否已签到
    if user_points.last_checkin_date == today():
        return error("今天已经签到过了")
    
    # 计算连续签到
    if user_points.last_checkin_date == yesterday():
        user_points.checkin_streak += 1
    else:
        user_points.checkin_streak = 1
    
    # 基础奖励
    base_reward = config['daily_checkin']  # 10点
    
    # 连续签到额外奖励
    streak_bonus = 0
    if user_points.checkin_streak >= 7:
        streak_bonus = config['checkin_streak_bonus']  # 5点
    
    total_reward = base_reward + streak_bonus
    
    # 发放点数
    add_points(user_id, total_reward, "daily_checkin", "每日签到")
    
    return {
        "earned": total_reward,
        "streak": user_points.checkin_streak
    }
```

---

## 七、安全与异常处理

### 7.1 并发控制
- 使用数据库事务处理点数扣除
- 乐观锁防止并发扣点导致负数

### 7.2 失败处理
- AI调用失败自动回滚点数
- 记录失败原因供排查

### 7.3 防刷机制
- 签到IP限制
- 短时间内重复调用限制
- 异常行为监控

---

## 八、后续扩展

### 8.1 充值系统（可选）
- 支付宝/微信支付接入
- 点数套餐设计

### 8.2 任务系统
- 完成任务获得点数
- 邀请好友奖励

### 8.3 VIP会员
- 月卡/年卡享受折扣
- 专属功能解锁

---

## 九、实现优先级

### P0 - 核心功能（必须先做）
1. 数据库表创建
2. 用户注册自动发放点数
3. 点数扣除/回滚逻辑
4. 第一阶段消耗计算
5. 点数余额显示

### P1 - 重要功能
1. 每日签到
2. 交易记录
3. 消费确认弹窗
4. 管理员配置界面

### P2 - 优化功能
1. 预估消耗API
2. 点数不足提示优化
3. 签到动画效果
4. 数据统计报表

---

## 十、文件结构

```
web/
├── api/
│   └── points_api.py          # 点数相关API
├── services/
│   └── point_service.py       # 点数业务逻辑
├── models/
│   └── point_models.py        # 数据模型
├── templates/
│   └── admin/
│       └── points-config.html # 管理员配置页面
└── static/
    └── js/
        └── points.js          # 前端点数相关逻辑
```
