# 番茄自动签约功能使用指南

## 功能概述

番茄自动签约模块新增了以下功能：

1. **获取启用用户配置列表** - 获取所有配置中启用的用户信息
2. **获取可签约小说列表** - 获取当前页面所有连载中且未签约的小说
3. **自动签约** - 根据小说标题和用户配置自动执行签约流程
4. **作者名匹配验证** - 在签约前验证当前登录作者名是否与配置的用户名一致

## 配置说明

在 `Chrome/config/automation_config.yaml` 中配置多个签约用户：

```yaml
contract:
  auto_sign: true  # 是否自动签约
  current_user: "user1"  # 当前使用的用户ID
  
  # 多用户签约信息配置
  users:
    user1:
      name: "用户1"  # 作者名（用于匹配验证）
      enabled: true  # 是否启用此用户
      contact_info:
        phone: "13760125919"
        email: "405625365@qq.com"
        qq: "405625365"
        bank_account: "6214857812704759"
        bank_branch: "招商银行深圳愉康支行"
        address:
          province: "广东省"
          city: "深圳市"
          detail: "宝安区"
    
    user2:
      name: "北莽王庭的达延"
      enabled: true
      contact_info:
        phone: "15286302700"
        email: "1078943007@qq.com"
        qq: "1078943007"
        bank_account: "6217007150009196817"
        bank_branch: "中国建设银行股份有限公司凯里北京路支行"
        address:
          province: "贵州省"
          city: "凯里市"
          detail: "北京路"
```

## API接口

### 1. 获取启用的用户配置

**端点**: `GET /api/contract/users/enabled`

**响应示例**:
```json
{
  "success": true,
  "users": [
    {
      "user_id": "user1",
      "name": "用户1",
      "contact_info": {
        "phone": "13760125919",
        "email": "405625365@qq.com",
        ...
      }
    },
    {
      "user_id": "user2",
      "name": "北莽王庭的达延",
      "contact_info": {
        ...
      }
    }
  ],
  "count": 2,
  "timestamp": "2025-12-24T09:00:00.000Z"
}
```

### 2. 获取可签约小说列表

**端点**: `GET /api/contract/novels/contractable`

**响应示例**:
```json
{
  "success": true,
  "task_id": "task_123456",
  "message": "正在获取可签约小说列表...",
  "timestamp": "2025-12-24T09:00:00.000Z"
}
```

**实际结果** (通过查询任务状态获取):
```json
{
  "success": true,
  "task_id": "task_123456",
  "status": "completed",
  "result": {
    "current_author_name": "北莽王庭的达延",
    "novels": [
      {
        "title": "凡人：我在落云宗种田",
        "status": "连载中",
        "can_sign": true
      }
    ],
    "count": 1
  }
}
```

### 3. 自动签约小说

**端点**: `POST /api/contract/sign/auto`

**请求参数**:
```json
{
  "novel_title": "凡人：我在落云宗种田",
  "user_id": "user2"
}
```

**响应示例**:
```json
{
  "success": true,
  "task_id": "task_789012",
  "message": "自动签约任务已提交: 《凡人：我在落云宗种田》使用用户 user2",
  "task_type": "auto_sign",
  "novel_title": "凡人：我在落云宗种田",
  "user_id": "user2",
  "timestamp": "2025-12-24T09:00:00.000Z"
}
```

**签约失败示例** (作者名不匹配):
```json
{
  "success": false,
  "task_id": "task_789013",
  "error": "作者名不匹配！当前作者: 用户1, 配置作者: 北莽王庭的达延",
  "current_author_name": "用户1",
  "expected_author_name": "北莽王庭的达延"
}
```

## 使用流程

### 方式一: 使用Python脚本

```bash
# 运行示例脚本
python Chrome/scripts/auto_sign_example.py
```

按照提示选择操作：
1. 获取启用的用户配置 - 查看所有可用的签约用户
2. 获取可签约的小说列表 - 查看当前页面哪些小说可以签约
3. 自动签约小说 - 为指定小说使用指定用户进行签约

### 方式二: 直接调用API

```python
from Chrome.automation.api.contract_api import contract_api

# 1. 获取启用的用户
users_result = contract_api.get_enabled_users()
print(users_result)

# 2. 获取可签约小说列表
novels_result = contract_api.get_contractable_novels()
task_id = novels_result['task_id']

# 3. 查询任务结果
status = contract_api.get_task_status(task_id)
print(status)

# 4. 执行自动签约
sign_result = contract_api.submit_auto_sign_task(
    novel_title="凡人：我在落云宗种田",
    user_id="user2"
)
print(sign_result)
```

## 重要说明

### 作者名匹配验证

自动签约功能会验证当前登录的作者名是否与配置的用户名一致。这是为了确保使用正确的账号进行签约。

- 从页面获取的作者名：通过选择器 `div.slogin-user-avatar__info__name` 获取
- 配置的作者名：从 `automation_config.yaml` 中 `users.{user_id}.name` 获取

如果两者不匹配，签约将失败并返回错误信息。

### 签约流程

1. 验证当前作者名是否与配置的用户名一致
2. 切换到指定的用户配置（用于填写联系信息）
3. 导航到小说管理页面
4. 查找目标小说
5. 点击"签约管理"按钮
6. 填写签约表单（使用配置的联系信息）
7. 提交签约

### 安全提示

- 请确保在配置文件中正确填写用户的真实信息
- 签约前请仔细检查作者名是否匹配
- 建议先在测试环境验证流程
- 建议定期检查签约状态

## 文件结构

```
Chrome/automation/
├── api/
│   └── contract_api.py              # API接口
├── services/
│   ├── contract_service.py          # 基础签约服务
│   └── enhanced_contract_service.py # 增强版签约服务（包含自动签约功能）
├── managers/
│   └── contract_manager.py          # 签约管理器
├── utils/
│   ├── config_loader.py             # 配置加载器
│   └── ui_helper.py                 # UI辅助工具
└── config/
    └── automation_config.yaml       # 配置文件

Chrome/scripts/
└── auto_sign_example.py             # 使用示例脚本
```

## 常见问题

### Q1: 为什么签约失败？

可能的原因：
1. 作者名不匹配 - 检查当前登录的作者名是否与配置一致
2. 用户未启用 - 检查配置文件中该用户的 `enabled` 是否为 `true`
3. 小说已签约或不符合签约条件
4. 浏览器连接失败

### Q2: 如何添加新的签约用户？

在 `automation_config.yaml` 中的 `contract.users` 下添加新用户配置：

```yaml
users:
  user3:
    name: "新作者名"
    enabled: true
    contact_info:
      phone: "手机号"
      email: "邮箱"
      ...
```

### Q3: 可以同时签约多个小说吗？

可以。您可以为每本小说提交一个签约任务，系统会按顺序处理。

## 更新日志

### 2025-12-24
- 新增获取启用用户配置列表功能
- 新增获取可签约小说列表功能
- 新增自动签约功能
- 新增作者名匹配验证
- 修复配置文件YAML语法错误