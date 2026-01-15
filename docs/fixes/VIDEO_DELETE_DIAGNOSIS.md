# VeO 视频删除功能问题诊断报告

## 问题现象
用户在 UI 中点击删除按钮时，后端提示"任务不存在"，但该任务明明显示在列表中。

## 根本原因分析

### 问题1：任务ID不匹配 🔴

#### 问题位置
`src/managers/VeOVideoManager.py` 的 `_load_tasks()` 方法

#### 问题描述
当从磁盘加载任务时，存在**双重ID来源不一致**的问题：

```python
# 第196-209行
task_id = task_data.get("id")  # ❌ 从JSON内容中读取ID
if task_id:
    self.tasks[task_id] = VeOVideoGenerationTask(...)  # 使用JSON中的ID作为key
    # 但是文件名是另一个ID！
```

#### 流程追踪

**保存时（创建任务）**:
```python
# VeOVideoGenerationTask.__init__ (第54行)
self.id = f"veo_{uuid.uuid4().hex[:12]}"  # 例如: veo_abc123def456

# _save_task (第222行)
task_file = self.storage_dir / f"{task.id}.json"  # 文件名: veo_abc123def456.json
```

**加载时（服务器启动）**:
```python
# _load_tasks (第189行)
for task_file in self.storage_dir.glob("*.json"):  # 例如: veo_cb3f543fa700.json
    with open(task_file, 'r', encoding='utf-8') as f:
        task_data = json.load(f)  # JSON内容中的id可能是另一个值
    
    task_id = task_data.get("id")  # ❌ 使用JSON内容中的ID
    self.tasks[task_id] = ...      # ❌ 用JSON中的ID作为内存字典的key
```

#### 问题场景
1. **服务器运行时创建任务**: `veo_abc123def456`
   - 保存到文件: `veo_abc123def456.json`
   - 内存字典key: `veo_abc123def456`
   - ✅ 一致

2. **服务器重启后加载任务**:
   - 读取文件: `veo_cb3f543fa700.json`
   - JSON内容中可能有其他ID或格式问题
   - 内存字典key: 使用JSON内容中的ID（可能与文件名不同）
   - ❌ 不一致！

3. **删除操作**:
   - UI发送: `DELETE /api/veo/tasks/veo_cb3f543fa700`（使用文件名中的ID）
   - 后端查找: `self.tasks.get("veo_cb3f543fa700")`
   - 结果: 找不到（因为内存字典key是JSON内容中的ID）
   - ❌ 删除失败

### 问题2：任务对象不完整 🟡

`_load_tasks()` 创建的是占位任务对象，缺少原始请求的完整信息：

```python
placeholder_request = VeOVideoRequest(
    model=task_data.get("model", "veo_3_1"),  # ❌ 可能不准确
    messages=[{"role": "user", "content": []}]  # ❌ 空内容
)
```

这导致：
- 任务对象无法正确序列化
- 某些字段可能丢失
- 后续操作可能失败

## 完整流程问题演示

### 正常流程（应该如此）
```
1. 创建任务 → veo_abc123
2. 保存文件 → veo_abc123.json (内容: {"id": "veo_abc123", ...})
3. 重启服务器
4. 加载文件 veo_abc123.json
5. 解析ID → veo_abc123
6. 内存字典 → {"veo_abc123": task_object}
7. UI请求删除 veo_abc123
8. 找到任务 → 删除成功 ✅
```

### 实际流程（当前bug）
```
1. 创建任务 → veo_abc123
2. 保存文件 → veo_abc123.json (内容: {"id": "veo_abc123", ...})
3. 重启服务器
4. 加载文件 veo_xyz789.json (可能是另一个任务)
5. 解析ID → 可能使用错误的字段或格式
6. 内存字典 → {"parsed_id": task_object} (与文件名不匹配)
7. UI请求删除 veo_xyz789 (使用文件名)
8. 查找字典 → 找不到（因为key是parsed_id）
9. 删除失败 ❌
```

## 解决方案

### 方案1：统一使用文件名作为ID（推荐）✅

**优点**:
- 文件系统作为真实来源
- 避免JSON解析错误
- 更可靠

**实现**:
```python
def _load_tasks(self):
    for task_file in self.storage_dir.glob("*.json"):
        # ✅ 从文件名提取ID（去掉.json后缀）
        task_id = task_file.stem  # 例如: veo_abc123
        
        with open(task_file, 'r', encoding='utf-8') as f:
            task_data = json.load(f)
        
        # 使用文件名中的ID
        self.tasks[task_id] = VeOVideoGenerationTask(...)
        self.tasks[task_id].id = task_id  # 确保ID一致
```

### 方案2：修复JSON内容ID与文件名的一致性

**实现**:
```python
def _save_task(self, task: VeOVideoGenerationTask):
    task_file = self.storage_dir / f"{task.id}.json"
    response = task.to_response()
    
    # ✅ 确保JSON内容中的ID与文件名一致
    response.id = task.id
    
    with open(task_file, 'w', encoding='utf-8') as f:
        json.dump(response.to_dict(), f, ensure_ascii=False, indent=2)
```

## 影响范围

### 受影响功能
1. ❌ 删除任务（DELETE /api/veo/tasks/{id}）
2. ❌ 查询任务状态（GET /api/veo/status/{id}）
3. ❌ 取消任务（POST /api/veo/cancel/{id}）
4. ⚠️ 列出任务（可能显示不正确的ID）

### 受影响场景
- 服务器重启后
- 任务持久化后的任何操作
- 长时间运行的服务器

## 建议修复优先级

1. **立即修复** 🔴: 使用文件名作为ID的唯一来源
2. **后续优化** 🟡: 增加ID一致性校验
3. **长期改进** 🟢: 重构任务加载机制，使用更可靠的状态管理

## 测试验证

修复后需要测试：
1. 创建任务
2. 服务器重启
3. 加载任务列表
4. 删除任务
5. 查询任务状态
6. 确保所有操作使用相同的ID