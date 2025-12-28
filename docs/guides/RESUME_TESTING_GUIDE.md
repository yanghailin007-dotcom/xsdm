# 恢复生成功能 - 测试和调试指南

## 🧪 如何测试恢复功能

### 方法1：使用测试脚本（推荐）

运行测试脚本创建一个模拟检查点：

```bash
python tools/create_test_checkpoint.py "修仙：我是一柄魔剑，专治各种不服"
```

这会创建一个测试检查点，然后你可以在网页上测试恢复功能。

### 方法2：手动创建检查点

检查点文件位置：
```
小说项目/{小说标题}/.generation/checkpoint.json
```

检查点数据格式：
```json
{
  "novel_title": "修仙：我是一柄魔剑，专治各种不服",
  "phase": "phase_one",
  "current_step": "development_stage_plan",
  "timestamp": "2025-12-28T11:00:00.000Z",
  "data": {
    "generation_params": {...},
    "generated_data": {...}
  }
}
```

## 🔍 调试步骤

### 1. 检查文件是否存在

```bash
# 查看检查点目录
ls -la "小说项目/{小说标题}/.generation/"

# 查看检查点内容
cat "小说项目/{小说标题}/.generation/checkpoint.json"
```

### 2. 测试API接口

```bash
# 获取所有可恢复任务
curl http://localhost:5000/api/resumable-tasks

# 获取特定任务的恢复信息
curl http://localhost:5000/api/resumable-tasks/{小说标题}
```

### 3. 检查浏览器控制台

打开浏览器开发者工具（F12），查看控制台日志：

**预期看到的日志：**
```
✅ 检测到可恢复任务：修仙：我是一柄魔剑 (37.5%)
```

**如果没有看到日志，检查：**
1. [`resume-generation.js`](web/static/js/resume-generation.js) 是否正确加载
2. API路由是否已注册
3. 是否有JavaScript错误

### 4. 检查网络请求

在开发者工具的"网络"标签页中：

**查找请求：**
```
GET /api/resumable-tasks/{小说标题}
```

**检查响应：**
- 状态码应该是 200
- 响应内容应该包含 `resume_info`

## 🐛 常见问题排查

### 问题1：恢复模式选项不显示

**可能原因：**
1. 检查点文件不存在
2. API未注册
3. 小说标题不匹配
4. JavaScript未加载

**排查步骤：**

1. **检查检查点文件：**
   ```bash
   # 查看是否存在
   ls "小说项目/{标题}/.generation/checkpoint.json"
   
   # 查看内容
   cat "小说项目/{标题}/.generation/checkpoint.json"
   ```

2. **检查API是否注册：**
   - 在服务器日志中查找：`已注册的恢复生成API路由`
   - 访问：`http://localhost:5000/api/resumable-tasks`

3. **检查浏览器控制台：**
   - 打开F12开发者工具
   - 查看是否有JavaScript错误
   - 查看是否有"检测到可恢复任务"的日志

4. **检查标题匹配：**
   - 检查点文件中的 `novel_title`
   - 创意库中的标题
   - 表单中的标题
   - 三者必须完全一致

### 问题2：API返回404

**解决方案：**
1. 确认API已注册：`register_resume_routes(app)`
2. 检查服务器启动日志
3. 确认端口正确

### 问题3：标题匹配问题

**标题规范化：**
```python
# 在 generation_checkpoint.py 中
def _sanitize_filename(self, filename: str) -> str:
    """清理文件名，移除非法字符"""
    safe = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', ':', '：', '（', '）', '(', ')', '[', ']')).rstrip()
    return safe.replace(' ', '_')
```

**注意：** 文件名和API中的标题需要匹配。

## 🧪 完整测试流程

### 步骤1：创建测试检查点

```bash
python tools/create_test_checkpoint.py "修仙：我是一柄魔剑，专治各种不服"
```

### 步骤2：启动Web服务器

```bash
python web/web_server_refactored.py
```

### 步骤3：打开浏览器

1. 访问 `http://localhost:5000`
2. 登录（如果需要）
3. 进入生成页面

### 步骤4：加载创意库

1. 点击"🔄 加载创意库"
2. 在下拉框中选择"修仙：我是一柄魔剑，专治各种不服"
3. 查看"生成模式"下拉框

**预期结果：**
```
生成模式
├─ 仅第一阶段（生成设定后暂停）
├─ 完整两阶段（继续生成章节）
└─ 🔄 恢复模式（继续未完成的生成 - 37.5%）  ← 应该显示这个
```

### 步骤5：测试恢复

1. 选择"恢复模式"
2. 点击"开始生成设定"
3. 应该弹出确认对话框

## 📊 日志和监控

### 服务器日志

**查找关键日志：**
```
[CheckpointRecoveryManager] 查找可恢复任务
[CheckpointRecoveryManager] 找到检查点
[RESUME_API] 获取恢复信息
```

### 浏览器日志

**打开控制台（F12）：**
```
✅ 检测到可恢复任务：标题 (进度%)
发现可恢复的检查点: {...}
```

### 网络请求

**在"网络"标签页：**
```
GET /api/resumable-tasks/修仙：我是一柄魔剑，专治各种不服
Status: 200 OK
Response: {"success": true, "resume_info": {...}}
```

## 🎯 验证清单

- [ ] 检查点文件已创建
- [ ] API路由已注册
- [ ] 浏览器控制台无错误
- [ ] 网络请求成功（200 OK）
- [ ] 恢复模式选项显示
- [ ] 选择恢复模式后能正确提示
- [ ] 点击开始后能正确跳转

## 🔧 调试技巧

### 1. 强制刷新浏览器

```
Ctrl + Shift + R (Windows/Linux)
Cmd + Shift + R (Mac)
```

### 2. 清除浏览器缓存

1. F12 打开开发者工具
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

### 3. 查看检查点文件

```bash
# Windows
type "小说项目\{标题}\.generation\checkpoint.json"

# Linux/Mac
cat "小说项目/{标题}/.generation/checkpoint.json"
```

### 4. 测试API直接调用

```bash
# 使用curl
curl http://localhost:5000/api/resumable-tasks

# 使用Python
import requests
response = requests.get('http://localhost:5000/api/resumable-tasks')
print(response.json())
```

## 📝 测试检查点创建脚本

使用 [`tools/create_test_checkpoint.py`](tools/create_test_checkpoint.py)：

```bash
# 使用默认标题
python tools/create_test_checkpoint.py

# 使用自定义标题
python tools/create_test_checkpoint.py "你的小说标题"
```

## 🚨 故障排除决策树

```
恢复模式不显示
│
├─ 检查点文件存在？
│  ├─ 否 → 创建测试检查点
│  └─ 是 → 继续
│
├─ API已注册？
│  ├─ 否 → 检查服务器启动日志
│  └─ 是 → 继续
│
├─ 浏览器控制台有错误？
│  ├─ 是 → 修复JavaScript错误
│  └─ 否 → 继续
│
├─ 标题匹配？
│  ├─ 否 → 检查标题格式
│  └─ 是 → 继续
│
└─ 网络请求成功？
   ├─ 否 → 检查API端点
   └─ 是 → 检查响应数据格式
```

## 💡 快速诊断命令

```bash
# 一键检查所有
echo "=== 检查点文件 ==="
ls -la "小说项目"/*/.generation/ 2>/dev/null || echo "未找到检查点目录"

echo -e "\n=== API测试 ==="
curl -s http://localhost:5000/api/resumable-tasks | python -m json.tool || echo "API未响应"

echo -e "\n=== 服务器日志 ==="
tail -n 20 logs/*.log 2>/dev/null || echo "未找到日志文件"
```

## 总结

测试恢复功能的关键点：

1. ✅ **创建测试检查点** - 使用提供的脚本
2. ✅ **检查API注册** - 查看服务器启动日志
3. ✅ **验证文件存在** - 检查 `.generation` 目录
4. ✅ **查看浏览器日志** - F12控制台
5. ✅ **测试网络请求** - 开发者工具网络标签

按照本指南逐步排查，应该能快速定位问题！