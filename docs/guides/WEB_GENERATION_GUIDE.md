# 📖 网页版小说生成完整指南

## 系统概述

完整重构的网页版小说生成系统，支持从网页端完整流程生成正本小说。

### 核心特性

✅ **真实集成**：与 NovelGenerator 完全集成，不再使用 Mock 数据
✅ **后台任务**：支持后台异步生成，不阻塞前端
✅ **实时进度**：动态显示生成进度和任务状态
✅ **完整流程**：支持完整的从创意到章节生成的全流程
✅ **项目管理**：保存和管理多个小说项目
✅ **数据导出**：支持 JSON 和文本格式导出

---

## 使用流程

### 1️⃣ 启动 Web 服务

```bash
python web_server.py
```

访问：http://localhost:5000

### 2️⃣ 创建新项目（首页）

1. 进入 **首页** (`/`)
2. 填写表单：
   - **小说标题**：你的小说名称
   - **小说简介**：简要内容描述
   - **核心设定**：故事的背景世界观
   - **总章节数**：计划生成的总章节数（1-200）
   - **本次生成章节数**：本次一口气生成多少章

3. 点击 **🚀 开始生成** 按钮
4. 系统会显示**生成进度**和**状态更新**

### 3️⃣ 监控生成进度

系统会自动显示以下阶段：

| 阶段 | 说明 |
|------|------|
| 初始化生成环境 | 准备生成器和配置 |
| 生成器已准备就绪 | NovelGenerator 初始化完成 |
| 创意种子准备完成 | 创意数据已处理 |
| 正在生成小说 | 实际生成中（显示进度%) |
| 生成完成！ | 任务完成，2秒后自动跳转到阅读页面 |

### 4️⃣ 阅读生成的小说（阅读页 `/novel`）

**三栏布局**：

```
┌─────────────────────────────────────────────────┐
│              📖 小说生成系统                      │
├─────────┬──────────────────────┬────────────────┤
│ 左侧    │   中间正文内容       │ 右侧            │
│         │                      │                 │
│ 📚小说  │ 【第N章】标题         │ ⭐ 质量评分     │
│   信息  │                      │                 │
│         │ 长篇小说正文内容...   │ ✓ 优点          │
│ ⚙️ 核心  │                      │                 │
│   设定  │ ← 上一章 | 下一章 →  │ 💡 改进建议     │
│         │                      │                 │
│ 📄章节  │                      │ 📊 详情数据     │
│   导航  │                      │   - 字数        │
│         │                      │   - 生成时间    │
└─────────┴──────────────────────┴────────────────┘
```

**操作方式**：
- 点击左侧章节导航快速切换
- 使用下方 **← 上一章 / 下一章 →** 按钮
- 支持键盘快捷键：
  - **← 或 ↑**：上一章
  - **→ 或 ↓**：下一章

### 5️⃣ 导出和管理

#### 导出为 JSON
```javascript
// 在阅读页点击 "导出 JSON" 按钮
// 自动下载完整的小说数据（JSON 格式）
```

#### API 导出
```bash
# JSON 格式
GET http://localhost:5000/api/project/{小说标题}/export?format=json

# 文本格式
GET http://localhost:5000/api/project/{小说标题}/export?format=text
```

### 6️⃣ 查看仪表板（统计页 `/dashboard`）

实时查看：
- 📊 生成统计数据
- 📈 进度条
- 📚 章节详情表
- ⭐ 评分分布图
- 📊 各种统计信息

---

## API 文档

### 生成任务相关

#### 1. 启动生成任务
```http
POST /api/start-generation
Content-Type: application/json

{
  "title": "小说标题",
  "synopsis": "小说简介",
  "core_setting": "核心设定",
  "core_selling_points": ["卖点1", "卖点2"],
  "total_chapters": 50,
  "chapters_count": 5
}

Response:
{
  "success": true,
  "task_id": "uuid-string",
  "message": "小说生成任务已启动，正在后台处理",
  "status": "started"
}
```

#### 2. 获取任务状态
```http
GET /api/task/{task_id}/status

Response:
{
  "task_id": "uuid",
  "title": "小说标题",
  "status": "generating|completed|failed",
  "progress": 45,
  "chapters_generated": [1, 2, 3, 4, 5],
  "error": null,
  "created_at": "ISO 8601",
  "updated_at": "ISO 8601"
}
```

#### 3. 获取任务进度
```http
GET /api/task/{task_id}/progress

Response:
{
  "status": "generating",
  "progress": 50,
  "timestamp": "ISO 8601"
}
```

#### 4. 获取所有任务
```http
GET /api/tasks

Response: [
  { ... task1 ... },
  { ... task2 ... }
]
```

### 项目管理 API

#### 获取所有项目
```http
GET /api/projects

Response: [
  {
    "title": "小说标题",
    "total_chapters": 50,
    "completed_chapters": 10,
    "created_at": "ISO 8601",
    "last_updated": "ISO 8601"
  }
]
```

#### 获取项目详情
```http
GET /api/project/{title}

Response: { ... 完整的小说数据 ... }
```

#### 获取章节详情
```http
GET /api/project/{title}/chapter/{chapter_num}

Response: { ... 章节数据 ... }
```

#### 导出项目
```http
GET /api/project/{title}/export?format=json|text

# JSON 返回完整项目数据
# TEXT 返回可读的文本格式
```

---

## 系统状态监控

### 任务状态流转

```
initializing
    ↓
generator_ready
    ↓
creative_ready
    ↓
generating → generating → generating (进度 0-100%)
    ↓
completed / failed
```

### 后台进程管理

系统自动管理后台线程：
- 每个任务在独立线程中运行
- 支持多任务并行生成
- 任务完成后自动清理资源
- 断开连接自动保存进度

---

## 故障排除

### 问题 1：生成任务一直卡在初始化
**原因**：API 密钥未配置或无效
**解决**：检查 `config.py` 中的 API 密钥配置

### 问题 2：404 错误 - 任务不存在
**原因**：使用了错误的 task_id
**解决**：从 `/api/tasks` 获取正确的任务 ID

### 问题 3：导出失败
**原因**：项目未完成或不存在
**解决**：等待项目完成或使用有效的项目标题

### 问题 4：网页响应缓慢
**原因**：大量章节加载
**解决**：
- 减少一次生成的章节数
- 使用分页加载
- 刷新页面清理缓存

---

## 配置说明

### `config.py` 相关配置

```python
CONFIG = {
    "api_keys": {
        "doubao": "YOUR_API_KEY",  # 豆包 API
        "claude": "YOUR_API_KEY"   # Claude API
    },
    "defaults": {
        "total_chapters": 50,      # 默认总章节数
        "chapter_length": 2000,    # 默认章节长度
    }
}
```

### Web 服务器配置

修改 `web_server.py` 末尾：

```python
app.run(
    host='0.0.0.0',  # 监听所有 IP
    port=5000,       # 端口号
    debug=True,      # 调试模式
    use_reloader=False  # 禁用自动重载
)
```

---

## 高级用法

### 1. 检查进行中的任务

```bash
curl http://localhost:5000/api/tasks | python -m json.tool
```

### 2. 导出完整项目

```bash
# 获取项目详情
curl http://localhost:5000/api/project/"小说标题" > novel.json

# 或使用文本格式
curl "http://localhost:5000/api/project/小说标题/export?format=text" > novel.txt
```

### 3. 同时生成多个项目

前端会自动分配不同的任务 ID，支持并行处理

```javascript
// 同时启动 2 个生成任务
fetch('/api/start-generation', { /* 项目1 */ })
fetch('/api/start-generation', { /* 项目2 */ })

// 分别监控各自的进度
```

---

## 常见问题 FAQ

**Q: 生成一部 50 章小说需要多长时间？**
A: 取决于 API 响应速度，通常需要 5-15 分钟

**Q: 能否暂停和恢复生成？**
A: 目前不支持，但生成中断后数据会自动保存

**Q: 生成的小说会保存在哪里？**
A: 内存中，关闭应用后需要使用导出功能保存数据

**Q: 支持多人同时生成吗？**
A: 是的，每个用户独立的任务 ID

**Q: 如何修改已生成的章节？**
A: 导出为 JSON，修改后重新上传（功能待实现）

---

## 总结

完整重构的网页版系统提供：

1. ✅ **完整流程**：从创意到阅读的完整体验
2. ✅ **后台处理**：不影响用户界面流畅度
3. ✅ **实时反馈**：动态进度显示
4. ✅ **数据管理**：多项目管理和导出
5. ✅ **易用界面**：三栏布局，直观清晰

开始使用：`python web_server.py` 然后访问 http://localhost:5000！
