# Short Drama Studio 重构计划

## 📊 当前状态分析

**文件**: `static/js/short-drama-studio.js`
- **行数**: ~11,600 行
- **类**: ShortDramaStudio (单一大类)
- **依赖**: video-generation.js (已独立)

## 🎯 重构目标

1. **提高可维护性**: 将大文件拆分为功能模块
2. **降低耦合度**: 明确模块间依赖关系
3. **保持兼容性**: 不破坏现有功能
4. **便于测试**: 每个模块可独立测试

## 📁 目标结构

```
static/js/
├── short-drama-studio/
│   ├── modules/
│   │   ├── ProjectManager.js      # 项目管理
│   │   ├── EpisodeSelector.js     # 第1步：选集
│   │   ├── VisualAssets.js        # 第2步：视觉资产库
│   │   ├── StoryBeats.js          # 第3步：故事节拍
│   │   ├── Storyboard.js          # 第4步：分镜生成
│   │   ├── Dubbing.js             # 第6步：配音制作
│   │   ├── Export.js              # 第7步：导出
│   │   └── Utils.js               # 工具函数
│   └── ShortDramaStudio.js        # 主类（整合模块）
├── video-generation.js            # 第5步：视频生成（已独立）
└── short-drama-studio-legacy.js  # 备份原文件
```

## 🔧 重构策略

### 方案选择：**Mixin 模式**

使用 JavaScript Mixin 模式，将功能模块作为 mixin 混入主类：

```javascript
// 示例：ProjectManager.js
const ProjectManagerMixin = {
    async loadProjects() { ... },
    async createProject() { ... },
    async saveProject() { ... }
};

// ShortDramaStudio.js
class ShortDramaStudio {
    constructor() { ... }
}

// 混入模块
Object.assign(ShortDramaStudio.prototype, ProjectManagerMixin);
Object.assign(ShortDramaStudio.prototype, EpisodeSelectorMixin);
// ...
```

**优点**:
- 保持向后兼容（全局 `shortDramaStudio` 对象不变）
- 渐进式重构（一次一个模块）
- 不需要修改 HTML 中的事件绑定

## 📝 实施步骤

### Phase 1: 准备阶段
- [x] 创建目录结构
- [ ] 备份原文件
- [ ] 创建测试清单

### Phase 2: 提取工具模块（低风险）
- [ ] Utils.js - 纯工具函数
- [ ] Export.js - 导出功能（占位符）

### Phase 3: 提取独立步骤（中风险）
- [ ] Dubbing.js - 配音制作
- [ ] StoryBeats.js - 故事节拍
- [ ] EpisodeSelector.js - 选集功能

### Phase 4: 提取复杂模块（高风险）
- [ ] VisualAssets.js - 视觉资产库（含 Konva）
- [ ] Storyboard.js - 分镜生成
- [ ] ProjectManager.js - 项目管理

### Phase 5: 整合与优化
- [ ] 创建主类文件
- [ ] 优化模块加载顺序
- [ ] 更新 HTML 引用

## ✅ 测试清单

每个模块提取后必须测试：

### 基础功能测试
- [ ] 页面加载正常
- [ ] 项目列表显示
- [ ] 创建新项目
- [ ] 打开现有项目

### 7步工作流测试
- [ ] 第1步：选集功能
- [ ] 第2步：视觉资产库加载和编辑
- [ ] 第3步：故事节拍显示
- [ ] 第4步：分镜生成
- [ ] 第5步：视频生成
- [ ] 第6步：配音制作
- [ ] 第7步：导出

### 特殊功能测试
- [ ] Konva 画布渲染
- [ ] 图片上传和预览
- [ ] 九宫格生成
- [ ] 步骤依赖检查
- [ ] Toast 通知显示

### 兼容性测试
- [ ] 全局对象 `shortDramaStudio` 可访问
- [ ] HTML 中的 `onclick` 事件正常
- [ ] 浏览器控制台无错误

## ⚠️ 风险评估

### 高风险区域
1. **Konva 画布**: 视觉资产库使用 Konva.js，状态管理复杂
2. **事件绑定**: 大量 HTML 内联事件（`onclick="shortDramaStudio.xxx()"`）
3. **状态共享**: 模块间共享 `this.shots`, `this.currentProject` 等状态

### 缓解措施
1. **渐进式重构**: 一次只提取一个模块
2. **保留备份**: 保留原文件作为 legacy 版本
3. **充分测试**: 每个模块提取后完整测试
4. **回滚机制**: 如果出现问题，立即回滚

## 📅 时间估算

- Phase 1: 30分钟
- Phase 2: 1-2小时
- Phase 3: 3-4小时
- Phase 4: 4-6小时
- Phase 5: 2-3小时
- **总计**: 10-15小时

## 🚀 开始实施？

**建议**: 先完成 Phase 1 和 Phase 2（低风险），测试通过后再继续。

**问题**:
1. 是否现在开始实施？
2. 是否需要先看一个模块的示例代码？
3. 是否有特定的模块优先级？
