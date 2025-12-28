# 恢复生成功能 - 总览

## 🎯 功能简介

**问题：** 生成过程中断（网络问题、API超时、浏览器关闭等）后，需要从头开始生成，浪费大量API成本和时间。

**解决方案：** 恢复生成功能在每个步骤完成后自动保存检查点，中断后可以从上次中断的步骤继续生成。

**核心价值：**
- 💰 **节省成本** - 避免重复生成已完成的内容
- ⏱️ **节省时间** - 不需要重新开始整个生成流程
- 🔄 **智能恢复** - 自动检测并提示恢复选项
- 📊 **进度可见** - 清晰显示上次中断位置

## 📦 包含的文件

### 核心代码
```
src/managers/stage_plan/
└── generation_checkpoint.py          # 检查点管理器（核心）

web/managers/
└── resumable_novel_manager.py        # 可恢复生成管理器

web/api/
└── resume_generation_api.py          # API接口

web/static/js/
└── resume-generation.js              # 前端脚本

web/templates/components/
└── generation-form.html              # 表单模板（已修改）
```

### 文档
```
docs/
├── RESUME_GENERATION_README.md       # 本文档（总览）
├── RESUME_GENERATION_IMPLEMENTATION_SUMMARY.md  # 实施总结
└── guides/
    ├── RESUME_GENERATION_GUIDE.md    # 完整使用指南
    └── RESUME_QUICK_START.md         # 快速集成指南
```

## 🚀 快速开始（3步启用）

### 步骤1：引入前端脚本
```html
<script src="/static/js/resume-generation.js"></script>
```

### 步骤2：注册API路由
```python
from web.api.resume_generation_api import register_resume_routes

register_resume_routes(app)
```

### 步骤3：修改表单提交
```html
<!-- 原来 -->
<form onsubmit="startPhaseOneGeneration(event)">

<!-- 改为 -->
<form onsubmit="startPhaseOneGenerationWithResume(event)">
```

完成！🎉

## 📖 文档导航

### 快速集成
想要快速启用功能？→ **[快速集成指南](./guides/RESUME_QUICK_START.md)**

### 完整文档
需要详细了解？→ **[完整使用指南](./guides/RESUME_GENERATION_GUIDE.md)**

### 实施细节
了解技术实现？→ **[实施总结](./RESUME_GENERATION_IMPLEMENTATION_SUMMARY.md)**

## 💡 使用流程

### 用户视角
1. 选择创意
2. 系统自动检测是否有未完成的任务
3. 如果有，在"生成模式"下拉框显示"🔄 恢复模式"选项
4. 选择恢复模式，显示进度信息
5. 点击开始，从断点继续生成

### 开发者视角
```python
# 1. 创建检查点管理器
checkpoint_mgr = GenerationCheckpoint(title, Path.cwd())

# 2. 每完成一个步骤，保存检查点
checkpoint_mgr.create_checkpoint(
    phase='phase_one',
    step='worldview_generation',
    data={'worldview': generated_data}
)

# 3. 任务完成后，删除检查点
checkpoint_mgr.delete_checkpoint()
```

## 🎨 UI效果

### 生成模式下拉框
```
生成模式
├─ 仅第一阶段（生成设定后暂停）
├─ 完整两阶段（继续生成章节）
└─ 🔄 恢复模式（继续未完成的生成 - 37.5%）  ← 自动显示
```

## 🔌 API端点

```
GET  /api/resumable-tasks                    # 获取所有可恢复任务
GET  /api/resumable-tasks/{title}            # 获取特定任务信息
POST /api/generation/resume                  # 恢复生成
POST /api/generation/checkpoint/delete       # 删除检查点
```

## ✨ 核心特性

### 自动检查点保存
- 在每个步骤完成后自动保存
- 包含当前步骤、已生成数据、进度信息
- 原子写入确保数据安全

### 智能恢复检测
- 选中创意后自动检查
- 无需手动操作
- 支持多种检测方式

### 简洁UI设计
- 不使用复杂卡片列表
- 只在下拉框中添加一个选项
- 清晰显示进度

### 安全可靠
- 原子写入防止数据损坏
- 自动备份机制
- 完成后自动清理

## 📊 检查点数据

### 存储位置
```
小说项目/{小说标题}/.generation/
├── checkpoint.json         # 当前检查点
└── checkpoint_backup.json  # 备份
```

### 数据结构
```json
{
  "novel_title": "小说标题",
  "phase": "phase_one",
  "current_step": "development_stage_plan",
  "timestamp": "2025-12-28T11:00:00.000Z",
  "data": {
    "generation_params": {...},
    "generated_data": {...},
    "resume_count": 0,
    "status": "in_progress"
  }
}
```

## 🔧 可用的生成步骤

### 第一阶段 (phase_one)
1. `worldview_generation` - 世界观生成
2. `character_generation` - 角色生成
3. `opening_stage_plan` - 开篇阶段计划
4. `development_stage_plan` - 发展阶段计划
5. `climax_stage_plan` - 高潮阶段计划
6. `ending_stage_plan` - 结局阶段计划
7. `quality_assessment` - 质量评估
8. `finalization` - 最终整理

### 第二阶段 (phase_two)
- `chapter_1_10` - 第1-10章
- `chapter_11_20` - 第11-20章
- ... (根据总章节数动态生成)

## ❓ 常见问题

### Q1: 恢复模式选项没有显示？
**A:** 检查：
1. 脚本是否正确加载
2. API是否正确注册
3. 创意标题是否与检查点匹配
4. 浏览器控制台是否有错误

### Q2: 恢复后数据不完整？
**A:** 确保：
1. 每个步骤都保存了检查点
2. 步骤名称定义一致
3. 检查点数据包含必要信息

### Q3: 如何删除检查点？
**A:** 三种方式：
1. 任务完成后自动删除
2. 选择"重新开始"会覆盖旧检查点
3. 调用API `/api/generation/checkpoint/delete`

### Q4: 可以恢复到任意步骤吗？
**A:** 当前版本只支持从下一个步骤继续，不支持回滚。未来版本可能支持。

## 🎯 最佳实践

### 何时保存检查点
- 在每个耗时的AI调用完成后
- 在生成重要数据结构后
- 在阶段切换前

### 何时删除检查点
- 整个生成任务成功完成后
- 用户明确选择重新开始时
- 检查点数据已过时

### 数据安全
- 使用原子写入（临时文件+重命名）
- 保留备份文件
- 加载时优先尝试备份

## 📈 性能影响

### 检查点保存
- **频率**：每个步骤完成后一次
- **大小**：通常几KB到几百KB
- **时间**：通常<100ms
- **影响**：可忽略不计

### 检查点加载
- **频率**：选中创意时一次
- **时间**：通常<50ms
- **影响**：可忽略不计

## 🔍 测试建议

### 基本功能
- ✅ 创建新任务，检查检查点是否保存
- ✅ 中断生成，重新打开，检查恢复选项
- ✅ 选择恢复模式，验证从正确步骤继续
- ✅ 选择重新开始，验证检查点被覆盖

### 边界情况
- ✅ 删除检查点文件，验证系统行为
- ✅ 损坏检查点文件，验证备份恢复
- ✅ 多个可恢复任务，验证UI显示

## 🚧 未来改进

### 短期（可能实施）
- 检查点版本控制
- 部分恢复选项
- 检查点压缩

### 长期（考虑中）
- 分布式检查点（云端存储）
- 智能恢复策略
- 检查点分析和报告

## 💬 反馈与支持

如有问题或建议，请：
1. 查看完整文档：[完整使用指南](./guides/RESUME_GENERATION_GUIDE.md)
2. 查看实施总结：[实施总结](./RESUME_GENERATION_IMPLEMENTATION_SUMMARY.md)
3. 检查常见问题：上面的"常见问题"部分

## ✅ 总结

恢复生成功能通过以下方式提升体验：

1. **节省成本** - 避免重复生成
2. **提高可靠性** - 中断后可快速恢复
3. **简化操作** - 自动检测和提示
4. **数据安全** - 原子写入和备份
5. **易于集成** - 只需3步即可启用

**现在就开始使用吧！** 🚀