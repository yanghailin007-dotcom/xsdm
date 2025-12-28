# 恢复生成功能 - 快速集成指南

## 功能说明

当生成过程中断（网络问题、API超时、浏览器关闭等）后，恢复功能允许从上次中断的步骤继续生成，而不是从头开始，大幅节省API成本和时间。

## 快速启用

### 1. 在HTML中引入脚本

在生成表单页面添加：

```html
<script src="/static/js/resume-generation.js"></script>
```

### 2. 注册API路由

在 `web/web_server_refactored.py` 或主服务器文件中添加：

```python
from web.api.resume_generation_api import register_resume_routes

# 在app初始化后注册
register_resume_routes(app)
```

### 3. 修改表单提交

将表单的 `onsubmit` 改为使用恢复版本：

```html
<!-- 原来 -->
<form onsubmit="startPhaseOneGeneration(event)">

<!-- 改为 -->
<form onsubmit="startPhaseOneGenerationWithResume(event)">
```

## 使用流程

### 用户操作流程

1. **选择创意**：从创意库选择一个创意
2. **自动检测**：系统自动检查该创意是否有未完成的任务
3. **显示选项**：如果有，在"生成模式"下拉框中显示"🔄 恢复模式"选项
4. **选择模式**：用户可以选择"恢复模式"继续生成，或选择其他模式重新开始
5. **开始生成**：点击"开始生成设定"按钮，从上次中断的步骤继续

### 界面示例

```
生成模式
├─ 仅第一阶段（生成设定后暂停）
├─ 完整两阶段（继续生成章节）
└─ 🔄 恢复模式（继续未完成的生成 - 37.5%）  ← 新增选项
```

## 检查点保存时机

需要在生成流程的关键步骤保存检查点：

```python
from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint

# 创建检查点管理器
checkpoint_mgr = GenerationCheckpoint(
    novel_title=title,
    workspace_dir=Path.cwd()
)

# 在每个步骤完成后保存
checkpoint_mgr.create_checkpoint(
    phase='phase_one',
    step='worldview_generation',  # 当前步骤名称
    data={
        'worldview': generated_worldview,
        'status': 'completed'
    }
)

# 任务完成后删除
checkpoint_mgr.delete_checkpoint()
```

## 可用的生成步骤

### 第一阶段 (phase_one)
- `worldview_generation` - 世界观生成
- `character_generation` - 角色生成  
- `opening_stage_plan` - 开篇阶段计划
- `development_stage_plan` - 发展阶段计划
- `climax_stage_plan` - 高潮阶段计划
- `ending_stage_plan` - 结局阶段计划
- `quality_assessment` - 质量评估
- `finalization` - 最终整理

### 第二阶段 (phase_two)
- `chapter_1_10` - 第1-10章
- `chapter_11_20` - 第11-20章
- ... (动态生成)

## 检查点文件位置

```
小说项目/
└── {小说标题}/
    └── .generation/
        ├── checkpoint.json         # 当前检查点
        └── checkpoint_backup.json  # 备份检查点
```

## API端点

```bash
# 获取所有可恢复任务
GET /api/resumable-tasks

# 获取特定任务的恢复信息
GET /api/resumable-tasks/{title}

# 恢复生成
POST /api/generation/resume
Body: {"title": "小说标题"}

# 删除检查点
POST /api/generation/checkpoint/delete
Body: {"title": "小说标题"}

# 启动生成（带恢复选项）
POST /api/generation/start-with-resume-option
Body: {"title": "...", "resume_if_available": true}
```

## 注意事项

1. **自动检测**：选中创意后自动检测，无需额外操作
2. **可选恢复**：用户可以选择恢复或重新开始
3. **进度显示**：显示上次中断的位置和完成百分比
4. **安全备份**：检查点有备份机制，防止数据丢失
5. **完成清理**：任务完成后自动删除检查点

## 故障排查

### 问题：恢复模式选项未显示

**可能原因：**
- 脚本未加载
- API未注册
- 创意标题不匹配

**解决方案：**
1. 检查浏览器控制台是否有错误
2. 确认API路由已注册
3. 验证创意标题格式一致

### 问题：恢复后数据不完整

**可能原因：**
- 检查点保存不完整
- 步骤定义不匹配

**解决方案：**
1. 确保每个步骤保存必要的数据
2. 检查步骤名称是否一致
3. 查看日志了解详细错误

### 问题：检查点文件不存在

**可能原因：**
- 目录权限不足
- 文件路径包含非法字符

**解决方案：**
1. 检查 `.generation` 目录是否可写
2. 使用安全的文件名处理
3. 查看日志了解详细错误

## 扩展功能

如需更多高级功能，参考完整文档：
- [恢复生成功能完整指南](./RESUME_GENERATION_GUIDE.md)

## 总结

恢复生成功能通过3个简单步骤即可启用：

1. ✅ 引入脚本
2. ✅ 注册API  
3. ✅ 修改表单提交

功能特点：
- 🎯 **自动检测** - 无需手动操作
- 💾 **安全保存** - 原子写入+备份
- 🔄 **智能恢复** - 从断点继续
- 📊 **进度显示** - 清晰展示完成度
- 🎨 **简洁UI** - 集成到现有表单

启用后，用户在生成过程中断时可以轻松恢复，大幅提升使用体验！