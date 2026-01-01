# 视频生成系统 - 事件和角色选择改进

## 改进概述

针对视频生成系统中事件和角色选择流程进行了重大优化，解决了以下核心问题：

1. **事件层级展开**：重大事件现在可以展开/收起，显示其中级事件
2. **角色自动推导**：根据选中的事件自动推导需要的角色，无需手动选择

## 主要改进内容

### 1. API层改进 ([`web/api/video_generation_api.py`](web/api/video_generation_api.py))

#### 修改 [`get_novel_content()`](web/api/video_generation_api.py:203) 端点

**改进前**：
- 返回扁平化的事件列表，重大事件和中级事件混在一起
- 每个事件都是平级的，没有层级关系

**改进后**：
```python
# 返回层级结构
events.append({
    "id": f"major_event_{idx}",
    "title": event_name,
    "type": "major",  # 标记为重大事件
    "has_children": len(medium_events_list) > 0,
    "children_count": len(medium_events_list),
    "children": medium_events_list,  # 包含所有中级事件
    # ... 其他字段
})
```

**优势**：
- 清晰的层级结构：重大事件 → 中级事件
- 包含子事件数量信息
- 支持展开/收起操作

### 2. 前端UI改进 ([`web/static/js/video-generation.js`](web/static/js/video-generation.js))

#### 修改 [`renderEventsList()`](web/static/js/video-generation.js:360) 方法

**新增功能**：
1. **重大事件可展开/收起**
   - 添加展开按钮（▶ / ▼）
   - 显示子事件数量徽章
   - 点击展开按钮显示/隐藏中级事件列表

2. **事件选择逻辑**
   - 重大事件和中级事件都可以独立选择
   - 选中重大事件时，可以进一步选择其包含的中级事件
   - 视觉反馈：选中的事件高亮显示

**新增方法**：

1. **[`deriveCharactersFromEvents()`](web/static/js/video-generation.js:783)**
   - 从选中的事件中自动推导角色
   - 支持从重大事件和中级事件的 `characters` 字段提取
   - 如果没有推导出角色，返回前5个主要角色作为默认

2. **[`parseCharacterString()`](web/static/js/video-generation.js:817)**
   - 解析角色字符串（支持多种分隔符：`,，、;；`）
   - 从完整角色列表中查找详细信息

3. **[`findEventById()`](web/static/js/video-generation.js:835)**
   - 根据ID查找事件（支持重大事件和中级事件）

4. **[`renderDerivedCharacters()`](web/static/js/video-generation.js:855)**
   - 渲染推导的角色列表（只读，不可手动选择）
   - 显示"🔍 自动推导"标记
   - 禁用复选框，表示自动推导

5. **[`updateDerivedCharacters()`](web/static/js/video-generation.js:907)**
   - 当事件选择变化时更新推导的角色列表

#### 修改 [`updateSelectionStats()`](web/static/js/video-generation.js:743) 方法

**改进前**：
```javascript
const characterCount = this.selectedCharacters.size;
document.getElementById('selectedCharactersCount').textContent = `已选: ${characterCount}个角色`;
```

**改进后**：
```javascript
const derivedCharacters = this.deriveCharactersFromEvents();
const characterCount = derivedCharacters.length;
document.getElementById('selectedCharactersCount').textContent = `推导: ${characterCount}个角色`;
this.renderDerivedCharacters(derivedCharacters);
```

### 3. CSS样式改进 ([`web/static/css/video-generation.css`](web/static/css/video-generation.css))

#### 新增样式

1. **重大事件容器样式**
   - [`.major-event-item`](web/static/css/video-generation.css:1620) - 重大事件容器
   - [`.major-event-header`](web/static/css/video-generation.css:1629) - 重大事件头部
   - [`.expand-btn`](web/static/css/video-generation.css:1646) - 展开/收起按钮
   - [`.children-count-badge`](web/static/css/video-generation.css:1658) - 子事件数量徽章

2. **中级事件列表样式**
   - [`.medium-events-list`](web/static/css/video-generation.css:1668) - 中级事件列表容器
   - [`.medium-event-item`](web/static/css/video-generation.css:1675) - 中级事件项

3. **推导角色样式**
   - [`.derived-badge`](web/static/css/video-generation.css:1693) - 推导角色标记
   - [`.derived-character`](web/static/css/video-generation.css:1702) - 推导角色项（只读）

## 使用流程

### 事件选择流程

1. **选择小说和视频类型**后，进入事件选择界面
2. **重大事件默认显示**，每个重大事件显示：
   - 事件标题
   - 描述（如果有）
   - 章节范围
   - 子事件数量（例如："5个中级事件"）
   - 展开按钮（▶）

3. **点击展开按钮**查看中级事件：
   - 展开后显示所有中级事件
   - 每个中级事件显示：
     - 标题
     - 阶段标签（起因、发展、高潮、结局）
     - 描述
     - 参与角色、地点、情绪

4. **选择事件**：
   - 可以选择整个重大事件
   - 也可以只选择其中的某些中级事件
   - 选中的事件会高亮显示

### 角色自动推导

1. **选中事件后**，系统自动：
   - 从选中的事件中提取角色信息
   - 解析角色字符串（支持多种分隔符）
   - 从完整角色列表中查找角色详情

2. **角色列表显示**：
   - 只读显示，不可手动选择
   - 显示"🔍 自动推导"标记
   - 包含角色的详细信息（外貌、性格、背景等）

3. **如果没有推导出角色**：
   - 自动返回前5个主要角色作为默认

## 数据结构示例

### API返回的事件结构

```json
{
  "success": true,
  "events": [
    {
      "id": "major_event_0",
      "title": "锈剑苏醒，废物祭旗",
      "type": "major",
      "description": "重大事件描述",
      "chapter_range": "1-10",
      "has_children": true,
      "children_count": 4,
      "children": [
        {
          "id": "medium_event_0",
          "title": "主角获得锈剑",
          "stage": "起因",
          "description": "中级事件描述",
          "characters": "赤, 姜清歌",
          "location": "冷宫",
          "emotion": "惊讶"
        },
        // ... 更多中级事件
      ],
      "characters": "赤, 姜清歌, 叶无道"
    }
  ]
}
```

### 推导的角色列表

```javascript
[
  {
    "name": "赤",
    "role": "主角",
    "personality": "冷静、果断",
    "appearance": "身材修长，眼神锐利",
    "background": "神秘的剑灵化身"
  },
  // ... 更多角色
]
```

## 技术要点

### 1. 事件ID命名规则

- 重大事件：`major_event_{index}`
- 中级事件：`major_event_{index}_medium_event_{child_index}`

### 2. 角色推导逻辑

```javascript
// 1. 从选中事件中提取角色字符串
// 2. 分割字符名（支持：,，、;；）
// 3. 从完整角色列表中查找详细信息
// 4. 如果找不到，创建基本角色对象
// 5. 返回去重的角色列表
```

### 3. 状态同步

- 事件选择变化 → 自动更新推导的角色
- 角色列表自动更新统计信息
- 角色列表为只读，无法手动修改

## 后续优化建议

### 1. AI角色推导（未实现）

当逻辑推导失败时，可以调用AI接口生成角色列表：

```javascript
async deriveCharactersWithAI(events) {
    if (this.deriveCharactersFromEvents().length > 0) {
        return this.deriveCharactersFromEvents();
    }
    
    // 调用AI接口
    const response = await fetch('/api/video/derive-characters', {
        method: 'POST',
        body: JSON.stringify({ events })
    });
    
    return response.json().characters;
}
```

### 2. 角色关系图

- 可视化展示角色之间的关系
- 显示角色在事件中的参与度

### 3. 智能推荐

- 根据事件类型推荐主要角色
- 根据角色重要性排序

## 测试建议

1. **事件展开/收起功能**
   - 测试有子事件和无子事件的重大事件
   - 测试展开/收起动画流畅性

2. **角色推导功能**
   - 测试不同分隔符的角色字符串
   - 测试角色名称匹配
   - 测试默认角色返回

3. **边界情况**
   - 没有选中任何事件
   - 事件中没有角色信息
   - 角色列表为空

## 相关文件

- [`web/api/video_generation_api.py`](web/api/video_generation_api.py) - API接口
- [`web/static/js/video-generation.js`](web/static/js/video-generation.js) - 前端逻辑
- [`web/static/css/video-generation.css`](web/static/css/video-generation.css) - 样式定义
- [`src/managers/EventExtractor.py`](src/managers/EventExtractor.py) - 事件提取器

## 版本信息

- **改进日期**：2026-01-01
- **影响范围**：视频生成系统的事件和角色选择流程
- **向后兼容**：是（旧格式数据仍然支持）