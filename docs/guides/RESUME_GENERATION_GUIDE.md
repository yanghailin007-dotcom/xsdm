# 恢复生成功能使用指南

## 功能概述

恢复生成功能允许在生成过程中断后，从上次中断的步骤继续生成，而不是从头开始。这样可以大幅节省API成本和时间。

## 核心特性

### 1. 自动检查点保存
- 系统会在每个生成步骤完成后自动保存检查点
- 检查点包含当前步骤、已生成数据、进度信息等
- 采用原子写入，确保数据安全

### 2. 智能恢复提示
- 选中创意后，如果该创意有未完成的任务，会自动显示恢复选项
- 用户可以选择继续之前的生成或重新开始

### 3. 简洁的UI设计
- 不使用复杂的卡片列表
- 只在表单顶部显示一个简单的复选框选项
- 清晰显示上次中断的位置和完成进度

## 文件结构

```
src/managers/stage_plan/
├── generation_checkpoint.py          # 检查点管理器（核心）
└── plan_persistence.py               # 计划持久化

web/managers/
└── resumable_novel_manager.py        # 可恢复生成管理器

web/api/
└── resume_generation_api.py          # 恢复生成API接口

web/static/js/
└── resume-generation.js              # 前端恢复功能脚本
```

## 使用方法

### 前端使用

1. **引入恢复功能脚本**
   ```html
   <script src="/static/js/resume-generation.js"></script>
   ```

2. **修改表单提交函数**
   ```javascript
   // 将原有的 onsubmit="startPhaseOneGeneration(event)"
   // 改为 onsubmit="startPhaseOneGenerationWithResume(event)"
   ```

3. **用户体验流程**
   - 用户从创意库中选择一个创意
   - 如果该创意有未完成的任务，表单顶部会显示恢复选项
   - 用户勾选"继续之前的生成"复选框
   - 点击"开始生成设定"按钮
   - 系统从上次中断的步骤继续生成

### 后端集成

1. **注册API路由**
   ```python
   from web.api.resume_generation_api import register_resume_routes
   
   # 在web服务器初始化时注册
   register_resume_routes(app)
   ```

2. **在生成流程中创建检查点**
   ```python
   from src.managers.stage_plan.generation_checkpoint import GenerationCheckpoint
   
   # 创建检查点管理器
   checkpoint_mgr = GenerationCheckpoint(
       novel_title=title,
       workspace_dir=Path.cwd()
   )
   
   # 在每个步骤完成后保存检查点
   checkpoint_mgr.create_checkpoint(
       phase='phase_one',
       step='worldview_generation',
       data={
           'worldview_data': generated_worldview,
           'status': 'completed'
       }
   )
   ```

3. **任务完成后删除检查点**
   ```python
   checkpoint_mgr.delete_checkpoint()
   ```

## API接口

### 1. 获取可恢复任务列表
```
GET /api/resumable-tasks
```

**响应示例：**
```json
{
  "success": true,
  "tasks": [
    {
      "novel_title": "凡人修仙同人·观战者",
      "phase": "phase_one",
      "phase_name": "第一阶段设定生成",
      "current_step": "development_stage_plan",
      "current_step_index": 3,
      "total_steps": 8,
      "completed_steps": 3,
      "remaining_steps": 5,
      "progress_percentage": 37.5,
      "timestamp": "2025-12-28T11:00:00"
    }
  ],
  "total": 1
}
```

### 2. 获取特定任务的恢复信息
```
GET /api/resumable-tasks/{title}
```

**响应示例：**
```json
{
  "success": true,
  "resume_info": {
    "novel_title": "凡人修仙同人·观战者",
    "phase": "phase_one",
    "phase_name": "第一阶段设定生成",
    "current_step": "development_stage_plan",
    "progress_percentage": 37.5,
    "timestamp": "2025-12-28T11:00:00"
  }
}
```

### 3. 恢复生成
```
POST /api/generation/resume

{
  "title": "凡人修仙同人·观战者"
}
```

**响应示例：**
```json
{
  "success": true,
  "task_id": "resume_凡人修仙同人·观战者_development_stage_plan",
  "message": "生成任务已恢复",
  "resume_info": {
    "phase": "phase_one",
    "current_step": "development_stage_plan"
  }
}
```

### 4. 删除检查点
```
POST /api/generation/checkpoint/delete

{
  "title": "凡人修仙同人·观战者"
}
```

### 5. 启动生成（带恢复选项）
```
POST /api/generation/start-with-resume-option

{
  "title": "凡人修仙同人·观战者",
  "resume_if_available": true,
  "synopsis": "...",
  "core_setting": "...",
  ...
}
```

## 检查点数据结构

### 检查点文件位置
```
小说项目/{小说标题}/.generation/checkpoint.json
```

### 检查点数据格式
```json
{
  "novel_title": "凡人修仙同人·观战者",
  "phase": "phase_one",
  "current_step": "development_stage_plan",
  "timestamp": "2025-12-28T11:00:00.000Z",
  "data": {
    "generation_params": {
      "title": "...",
      "synopsis": "...",
      "core_setting": "..."
    },
    "generated_data": {
      "worldview": {...},
      "characters": {...}
    },
    "resume_count": 0,
    "status": "in_progress"
  }
}
```

## 生成阶段定义

### 第一阶段（phase_one）
1. `worldview_generation` - 世界观生成
2. `character_generation` - 角色生成
3. `opening_stage_plan` - 开篇阶段计划
4. `development_stage_plan` - 发展阶段计划
5. `climax_stage_plan` - 高潮阶段计划
6. `ending_stage_plan` - 结局阶段计划
7. `quality_assessment` - 质量评估
8. `finalization` - 最终整理

### 第二阶段（phase_two）
1. `chapter_1_10` - 第1-10章
2. `chapter_11_20` - 第11-20章
3. `chapter_21_30` - 第21-30章
... （根据总章节数动态生成）

## 最佳实践

### 1. 何时保存检查点
- 在每个耗时的AI调用完成后
- 在生成重要数据结构后
- 在阶段切换前

### 2. 何时删除检查点
- 整个生成任务成功完成后
- 用户明确选择重新开始时
- 检查点数据已过时（如创意内容已修改）

### 3. 数据安全
- 使用原子写入（临时文件+重命名）
- 保留备份文件（checkpoint_backup.json）
- 加载时优先尝试备份

### 4. 用户体验
- 清晰显示恢复选项和进度
- 提供取消恢复的选项
- 恢复失败时优雅降级到正常生成

## 故障排查

### 问题1：检查点未保存
**可能原因：**
- 目录权限不足
- 磁盘空间不足
- 文件路径包含非法字符

**解决方案：**
- 检查日志中的错误信息
- 确保 `.generation` 目录可写
- 使用安全的文件名处理

### 问题2：恢复时数据丢失
**可能原因：**
- 检查点数据不完整
- 步骤定义不匹配

**解决方案：**
- 检查检查点文件内容
- 确保每个步骤保存必要的数据
- 使用备份恢复

### 问题3：前端未显示恢复选项
**可能原因：**
- API未正确注册
- 脚本未加载
- 创意标题不匹配

**解决方案：**
- 检查浏览器控制台错误
- 确认API路由已注册
- 验证创意标题格式

## 性能优化

### 1. 减少检查点大小
- 只保存必要的数据
- 避免保存大量重复内容
- 使用引用而非复制

### 2. 异步保存
- 在后台线程保存检查点
- 不阻塞主生成流程

### 3. 定期清理
- 自动删除过期的检查点
- 提供清理工具

## 扩展功能

### 1. 检查点版本控制
- 保存多个历史版本
- 允许回滚到任意版本

### 2. 分布式检查点
- 使用云端存储
- 支持多设备同步

### 3. 检查点分析
- 统计常见中断点
- 优化生成流程

## 总结

恢复生成功能通过以下方式提升用户体验：

1. **节省成本** - 避免重复生成已完成的内容
2. **提高可靠性** - 中断后可快速恢复
3. **简化操作** - 自动检测和提示恢复选项
4. **数据安全** - 原子写入和备份机制

该功能设计简洁，易于集成，对现有生成流程的影响最小。