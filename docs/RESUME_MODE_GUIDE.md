# 恢复模式功能说明

## 功能概述

恢复模式允许用户在生成过程中断后，从上次的检查点继续生成，而不是从头开始。

## 工作原理

### 1. 检查点机制

当生成任务启动时，系统会在以下目录创建检查点文件：

```
小说项目/{项目标题}/.generation/checkpoint.json
```

检查点文件包含：
- 项目标题
- 当前阶段（phase_one 或 phase_two）
- 当前步骤
- 时间戳
- 生成参数数据

### 2. 恢复模式选项显示

恢复模式选项在**生成模式**下拉框中默认隐藏：

```html
<option value="resume_mode" id="resume-mode-option" style="display: none;">
    🔄 恢复模式（继续未完成的生成）
</option>
```

只有当满足以下条件时才会显示：
1. 用户输入了项目标题
2. 系统检测到该标题有可用的检查点文件

### 3. 检测逻辑

[`resume-generation.js`](web/static/js/resume-generation.js) 提供了三种检测方式：

#### 方式一：标题输入框监听
当用户在标题输入框中输入内容时，系统会自动检查是否有检查点：

```javascript
titleInput.addEventListener('input', function() {
    // 延迟500ms后检查
    debounceTimer = setTimeout(async () => {
        const title = this.value.trim();
        const resumeInfo = await checkTaskResumeStatus(title);
        if (resumeInfo) {
            showResumeOption(resumeInfo);
        }
    }, 500);
});
```

#### 方式二：创意库选择
当用户从创意库中选择创意时，系统会检查该创意对应的检查点：

```javascript
ideaSelect.addEventListener('change', async function() {
    const title = selectedOption.text.replace(/^📚\s*/, '').trim();
    const resumeInfo = await checkTaskResumeStatus(title);
    if (resumeInfo) {
        showResumeOption(resumeInfo);
    }
});
```

#### 方式三：页面加载时检查
页面加载时，如果标题输入框已有内容，系统会自动检查：

```javascript
document.addEventListener('DOMContentLoaded', function() {
    const titleInput = document.getElementById('novel-title');
    if (titleInput && titleInput.value) {
        const resumeInfo = await checkTaskResumeStatus(titleInput.value);
        if (resumeInfo) {
            showResumeOption(resumeInfo);
        }
    }
});
```

## API 端点

### 获取恢复信息

```
GET /api/resumable-tasks/{title}
```

返回示例：

```json
{
    "success": true,
    "resume_info": {
        "novel_title": "测试项目_恢复模式",
        "phase": "phase_one",
        "phase_name": "第一阶段设定生成",
        "current_step": "character_generation",
        "current_step_index": 1,
        "total_steps": 8,
        "completed_steps": 1,
        "remaining_steps": 7,
        "progress_percentage": 12.5,
        "timestamp": "2025-12-29T14:00:00",
        "data": {
            "generation_params": {...},
            "status": "in_progress"
        }
    }
}
```

### 启动恢复生成

```
POST /api/generation/resume
```

请求体：

```json
{
    "title": "测试项目_恢复模式"
}
```

## 测试步骤

### 1. 创建测试检查点

运行测试脚本：

```bash
python test_resume_mode.py
```

这会在 `小说项目/测试项目_恢复模式/.generation/` 创建检查点文件。

### 2. 测试恢复模式显示

**方法A：使用标题输入框**
1. 打开浏览器，访问第一阶段设置页面
2. 在"小说标题"输入框中输入：`测试项目_恢复模式`
3. 等待500ms（防抖延迟）
4. "生成模式"下拉框应该显示恢复模式选项

**方法B：使用创意库**
1. 打开创意库
2. 添加一个标题为 `测试项目_恢复模式` 的创意
3. 选择该创意
4. "生成模式"下拉框应该显示恢复模式选项

### 3. 验证调试日志

打开浏览器控制台（F12），您应该看到以下日志：

```
🔍 [RESUME] 检查任务恢复状态: 测试项目_恢复模式
✅ [RESUME] 发现可恢复的检查点: {...}
🎯 [RESUME] 显示恢复选项: {...}
✅ [RESUME] 恢复模式选项已显示
```

## 恢复模式的生成步骤

第一阶段包含以下步骤：

1. `worldview_generation` - 世界观生成
2. `character_generation` - 角色生成
3. `opening_stage_plan` - 开篇阶段计划
4. `development_stage_plan` - 发展阶段计划
5. `climax_stage_plan` - 高潮阶段计划
6. `ending_stage_plan` - 结局阶段计划
7. `quality_assessment` - 质量评估
8. `finalization` - 最终整理

如果检查点显示当前步骤是 `character_generation`，恢复模式将从下一步 `opening_stage_plan` 继续。

## 常见问题

### Q1: 为什么恢复模式选项没有显示？

**可能原因：**
1. 没有检查点文件存在
2. 项目标题不匹配（区分大小写）
3. API未正确注册
4. JavaScript有错误

**解决方法：**
1. 检查浏览器控制台是否有错误
2. 验证检查点文件是否存在
3. 确认标题完全匹配
4. 查看网络请求是否成功

### Q2: 如何删除检查点？

检查点会在以下情况下自动删除：
- 任务成功完成
- 用户开始新的生成任务（会覆盖旧检查点）

手动删除：
```python
from pathlib import Path
import shutil

checkpoint_dir = Path("小说项目/测试项目_恢复模式/.generation")
if checkpoint_dir.exists():
    shutil.rmtree(checkpoint_dir)
```

### Q3: 恢复模式可以跳过某些步骤吗？

不行，恢复模式会严格按照检查点中记录的步骤顺序继续。这是为了确保生成过程的完整性和一致性。

## 相关文件

- **前端JavaScript**: [`web/static/js/resume-generation.js`](web/static/js/resume-generation.js)
- **后端API**: [`web/api/resume_generation_api.py`](web/api/resume_generation_api.py)
- **检查点管理器**: [`src/managers/stage_plan/generation_checkpoint.py`](src/managers/stage_plan/generation_checkpoint.py)
- **恢复管理器**: [`web/managers/resumable_novel_manager.py`](web/managers/resumable_novel_manager.py)
- **表单组件**: [`web/templates/components/generation-form.html`](web/templates/components/generation-form.html)