# 恢复生成功能 - 部署清单

## ✅ 已完成的修改

### 1. 核心功能文件
- [x] [`src/managers/stage_plan/generation_checkpoint.py`](src/managers/stage_plan/generation_checkpoint.py) - 检查点管理器
- [x] [`web/managers/resumable_novel_manager.py`](web/managers/resumable_novel_manager.py) - 可恢复生成管理器
- [x] [`web/api/resume_generation_api.py`](web/api/resume_generation_api.py) - API接口

### 2. 前端文件
- [x] [`web/static/js/resume-generation.js`](web/static/js/resume-generation.js) - 恢复功能脚本
- [x] [`web/templates/components/generation-form.html`](web/templates/components/generation-form.html) - 添加恢复选项
- [x] [`web/templates/phase-one-setup.html`](web/templates/phase-one-setup.html) - **已添加脚本引用**

### 3. UI清理
- [x] [`web/static/js/creative-library.js`](web/static/js/creative-library.js) - 移除卡片视图
- [x] [`web/templates/components/creative-library.html`](web/templates/components/creative-library.html) - 简化为列表视图

### 4. 文档
- [x] [`docs/RESUME_GENERATION_README.md`](docs/RESUME_GENERATION_README.md) - 总览
- [x] [`docs/guides/RESUME_QUICK_START.md`](docs/guides/RESUME_QUICK_START.md) - 快速开始
- [x] [`docs/guides/RESUME_GENERATION_GUIDE.md`](docs/guides/RESUME_GENERATION_GUIDE.md) - 完整指南
- [x] [`docs/guides/RESUME_TESTING_GUIDE.md`](docs/guides/RESUME_TESTING_GUIDE.md) - 测试指南

### 5. 测试工具
- [x] [`tools/create_test_checkpoint.py`](tools/create_test_checkpoint.py) - 创建测试检查点

## 🚀 启用步骤

### 步骤1：注册API路由

在 [`web/web_server_refactored.py`](web/web_server_refactored.py) 中添加：

```python
from web.api.resume_generation_api import register_resume_routes

# 在app初始化后注册
register_resume_routes(app)
```

### 步骤2：重启服务器

```bash
# 停止现有服务器
# 然后重新启动
python web/web_server_refactored.py
```

### 步骤3：验证API已注册

在服务器启动日志中查找：

```
📋 已注册的恢复生成API路由:
  - GET /api/resumable-tasks
  - GET /api/resumable-tasks/<title>
  - POST /api/generation/resume
  - POST /api/generation/checkpoint/delete
  - POST /api/generation/start-with-resume-option
```

### 步骤4：创建测试检查点

```bash
python tools/create_test_checkpoint.py "修仙：我是一柄魔剑，专治各种不服"
```

### 步骤5：在浏览器中测试

1. 打开浏览器（清除缓存：Ctrl+Shift+R）
2. 访问 `http://localhost:5000/phase-one-setup`
3. 点击"🔄 加载创意库"
4. 选择"修仙：我是一柄魔剑，专治各种不服"
5. 查看"生成模式"下拉框

**预期结果：**
```
生成模式
├─ 仅第一阶段（生成设定后暂停）
├─ 完整两阶段（继续生成章节）
└─ 🔄 恢复模式（继续未完成的生成 - 37.5%）  ← 应该显示
```

## 🔍 验证清单

### API端点测试

```bash
# 测试1：获取所有可恢复任务
curl http://localhost:5000/api/resumable-tasks

# 预期响应：
# {
#   "success": true,
#   "tasks": [...],
#   "total": 1
# }

# 测试2：获取特定任务信息
curl "http://localhost:5000/api/resumable-tasks/修仙：我是一柄魔剑，专治各种不服"

# 预期响应：
# {
#   "success": true,
#   "resume_info": {
#     "novel_title": "修仙：我是一柄魔剑，专治各种不服",
#     "progress_percentage": 37.5,
#     ...
#   }
# }
```

### 浏览器控制台测试

打开F12开发者工具，应该看到：

```
✅ 检测到可恢复任务：修仙：我是一柄魔剑 (37.5%)
发现可恢复的检查点: {novel_title: "...", progress_percentage: 37.5, ...}
```

### 文件系统验证

```bash
# 检查检查点文件
ls "小说项目/修仙：我是一柄魔剑，专治各种不服/.generation/"

# 应该看到：
# checkpoint.json
# checkpoint_backup.json
```

## 🐛 如果恢复模式还是不显示

### 检查1：脚本是否加载

在浏览器控制台输入：

```javascript
// 检查函数是否存在
typeof checkTaskResumeStatus
// 应该返回 "function"

// 检查监听器是否设置
typeof setupResumeModeListener
// 应该返回 "function"
```

### 检查2：API是否响应

```javascript
// 在控制台运行
fetch('/api/resumable-tasks')
  .then(r => r.json())
  .then(d => console.log('可恢复任务:', d))
```

### 检查3：检查点文件内容

```bash
cat "小说项目/修仙：我是一柄魔剑，专治各种不服/.generation/checkpoint.json"
```

确认 `novel_title` 字段与创意库中的标题完全一致。

## 📋 完整测试流程

```bash
# 1. 创建测试检查点
python tools/create_test_checkpoint.py

# 2. 启动服务器
python web/web_server_refactored.py

# 3. 在浏览器中
# - 访问 http://localhost:5000/phase-one-setup
# - 清除缓存 (Ctrl+Shift+R)
# - 打开F12控制台
# - 点击"加载创意库"
# - 选择创意
# - 查看"生成模式"下拉框
```

## 📝 已知问题

### 问题：标题匹配
检查点文件名和API请求中的标题必须完全一致。

**解决方案：** 使用测试脚本创建检查点，确保标题格式正确。

### 问题：浏览器缓存
修改后可能需要强制刷新浏览器。

**解决方案：** Ctrl+Shift+R (Windows) 或 Cmd+Shift+R (Mac)

## ✨ 完成确认

- [ ] API已注册并响应
- [ ] 测试检查点已创建
- [ ] 脚本已加载（控制台无错误）
- [ ] 恢复模式选项显示
- [ ] 能成功选择恢复模式
- [ ] 点击开始后正确跳转

全部勾选后，功能即可正常使用！