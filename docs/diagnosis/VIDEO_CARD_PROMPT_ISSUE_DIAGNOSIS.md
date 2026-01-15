# 视频卡片提示词丢失问题诊断报告

## 问题描述
视频卡片显示"无提示词"，即使视频已经生成完成。

## 问题症状
```html
<div class="video-card" data-video-id="veo_cb9eb817f0a9" data-status="completed">
    <p class="video-prompt" title="无提示词">无提示词</p>
    <span class="video-progress">0%</span>
</div>
```

## 完整数据流程分析

### 1️⃣ 前端请求数据
**文件**: `web/static/js/video-studio.js`
```javascript
// 第277行
const response = await fetch('/api/veo/tasks?limit=50&order=desc');
const data = await response.json();
this.videoLibrary = data.data;  // 存储视频列表
```

### 2️⃣ 后端API处理
**文件**: `web/api/veo_video_api.py`
```python
# 第272-316行
@veo_video_api.route('/api/veo/tasks', methods=['GET'])
def list_generations():
    manager = get_veo_video_manager()
    generations = manager.list_generations(
        limit=limit,
        status=status,
        order=order
    )
    return jsonify({
        "data": [g.to_dict() for g in generations],  # 🔥 转换为字典
        "total": len(generations)
    })
```

### 3️⃣ 管理器加载任务（🐛 问题源头）
**文件**: `src/managers/VeOVideoManager.py`
```python
# 第182-251行 _load_tasks()
def _load_tasks(self):
    for task_file in self.storage_dir.glob("*.json"):
        task_data = json.load(f)
        
        # ❌ 原代码：创建空内容的占位请求
        placeholder_request = VeOVideoRequest(
            model=task_data.get("model", "veo_3_1-fast"),
            messages=[{"role": "user", "content": []}]  # ⚠️ 空的content！
        )
        
        task = VeOVideoGenerationTask(placeholder_request, placeholder_config)
```

**问题**: 
- 从磁盘加载任务时，创建了**空内容的请求对象**
- 没有从保存的JSON中读取 `prompt` 字段

### 4️⃣ 转换为响应对象
**文件**: `src/managers/VeOVideoManager.py`
```python
# 第102-143行 to_response()
def to_response(self) -> VeOGenerationResponse:
    # 尝试从messages中提取prompt
    prompt = ""
    if self.request.messages:
        content = self.request.messages[0].get("content", [])  # 空列表 []
        for item in content:  # 循环不执行（列表为空）
            if item.get("type") == "text":
                prompt = item.get("text", "")  # 永远不会执行
                break
```

**问题**: 
- 由于 `content` 是空列表，循环不会执行
- `prompt` 保持为空字符串 `""`

### 5️⃣ 序列化为JSON
**文件**: `src/models/veo_models.py`
```python
# 第389-439行 to_dict()
def to_dict(self) -> Dict[str, Any]:
    result = {
        "id": self.id,
        "prompt": self.prompt,  # 🔥 空字符串
        "created": self.created,
        ...
    }
```

### 6️⃣ 前端渲染
**文件**: `web/static/js/video-studio.js`
```javascript
// 第357-419行 renderVideoCard()
renderVideoCard(video) {
    const prompt = video.prompt || '无提示词';  // 显示"无提示词"
    const truncatedPrompt = prompt.length > 100 ? prompt.substring(0, 100) + '...' : prompt;
    
    return `
        <p class="video-prompt" title="${this.escapeHtml(prompt)}">${this.escapeHtml(truncatedPrompt)}</p>
        ...
    `;
}
```

## 根本原因

### 数据保存流程 ✅
```python
# VeOVideoManager.py:102-143 to_response()
# 保存时：prompt 被正确提取和保存
def to_response(self) -> VeOGenerationResponse:
    prompt = ""
    if self.request.messages:
        content = self.request.messages[0].get("content", [])
        for item in content:
            if item.get("type") == "text":
                prompt = item.get("text", "")  # ✅ 正确提取
                break
    
    response = VeOGenerationResponse(
        ...
        prompt=prompt,  # ✅ 保存到响应对象
        ...
    )
```

**保存的JSON格式**:
```json
{
  "id": "veo_cb9eb817f0a9",
  "prompt": "一位仙风道骨的剑仙...",  // ✅ prompt被保存
  "status": "completed",
  ...
}
```

### 数据加载流程 ❌
```python
# VeOVideoManager.py:182-251 _load_tasks()
# 加载时：没有从JSON中读取prompt
def _load_tasks(self):
    task_data = json.load(f)
    
    # ❌ 创建空内容的请求
    placeholder_request = VeOVideoRequest(
        model=task_data.get("model", "veo_3_1-fast"),
        messages=[{"role": "user", "content": []}]  # ❌ 空content
    )
```

**加载后的请求对象**:
```python
VeOVideoRequest(
    model="veo_3_1-fast",
    messages=[{"role": "user", "content": []}]  # ❌ 空列表
)
```

### 重新提取流程 ❌
```python
# to_response() 试图从空messages中提取prompt
prompt = ""  # 永远是空字符串
content = []  # 空列表
for item in content:  # 不执行
    prompt = item.get("text", "")
```

## 解决方案

### 修复代码
**文件**: `src/managers/VeOVideoManager.py`

```python
def _load_tasks(self):
    """从磁盘加载任务"""
    try:
        for task_file in self.storage_dir.glob("*.json"):
            task_data = json.load(f)
            task_id = task_file.stem
            
            # 🔥 关键修复：从保存的JSON中读取prompt
            saved_prompt = task_data.get("prompt", "")
            model_name = task_data.get("model", "veo_3_1-fast")
            
            # 🔥 创建包含prompt的请求对象
            placeholder_request = VeOVideoRequest(
                model=model_name,
                messages=[{
                    "role": "user", 
                    "content": [
                        {"type": "text", "text": saved_prompt}  # ✅ 恢复prompt
                    ]
                }]
            )
            
            placeholder_config = VeOGenerationConfig()
            task = VeOVideoGenerationTask(placeholder_request, placeholder_config)
            task.id = task_id
            
            # 🔥 额外修复：恢复进度和阶段信息
            if task_data.get("progress") is not None:
                task._current_progress = task_data["progress"]
            if task_data.get("stage"):
                task._current_stage = task_data["stage"]
            
            # 设置其他属性...
            task.status = VideoStatus(task_data.get("status", "pending"))
            task.created_at = task_data.get("created", int(time.time()))
            
            self.tasks[task_id] = task
```

## 测试验证

### 修复前
```javascript
// API返回
{
  "id": "veo_cb9eb817f0a9",
  "prompt": "",  // ❌ 空字符串
  "status": "completed"
}

// 前端显示
<p class="video-prompt">无提示词</p>  // ❌
<span class="video-progress">0%</span>  // ❌
```

### 修复后
```javascript
// API返回
{
  "id": "veo_cb9eb817f0a9",
  "prompt": "一位仙风道骨的剑仙在云端修行的场景...",  // ✅
  "status": "completed",
  "progress": 100  // ✅
}

// 前端显示
<p class="video-prompt">一位仙风道骨的剑仙在云端修行的场景...</p>  // ✅
<span class="video-progress">100%</span>  // ✅
```

## 相关文件

### 核心文件
1. `src/managers/VeOVideoManager.py` - 视频生成管理器（已修复）
2. `src/models/veo_models.py` - 数据模型
3. `web/api/veo_video_api.py` - API路由
4. `web/static/js/video-studio.js` - 前端JavaScript

### 数据流程图
```
保存流程:
创建任务 → to_response() → 保存prompt → JSON文件 ✅

加载流程:
JSON文件 → _load_tasks() → 空messages ❌ → to_response() → 空prompt ❌

修复后加载流程:
JSON文件 → _load_tasks() → 恢复prompt ✅ → to_response() → 正确prompt ✅
```

## 总结

### 问题本质
**数据保存和加载的不一致性**：
- 保存时：`prompt` 被正确保存到JSON
- 加载时：没有从JSON恢复 `prompt`，而是创建了空内容的请求对象
- 提取时：试图从空对象中提取 `prompt`，得到空字符串

### 修复策略
1. 从保存的JSON中直接读取 `prompt` 字段
2. 在创建占位请求时，将 `prompt` 放入 `messages` 结构中
3. 额外恢复 `progress` 和 `stage` 信息

### 防止类似问题
1. **保持数据结构一致性**：保存和加载使用相同的数据结构
2. **完整恢复对象**：加载时恢复所有必要的属性
3. **添加日志验证**：记录加载过程中的关键数据

## 修复时间
2026-01-15 08:59:00 UTC

## 修复验证状态
✅ 代码已修复
⏳ 等待服务器重启验证
⏳ 等待前端刷新测试