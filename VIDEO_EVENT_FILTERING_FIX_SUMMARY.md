# 视频生成事件过滤功能修复总结

## 问题描述

**原始问题：**
用户在视频生成界面选择特定事件后，系统仍然生成了所有89个中级事件的分镜头脚本，而不是只生成用户选中的事件。

**根本原因：**
1. API层：`/api/video/generate-storyboard` 接口没有接受 `selected_events` 参数
2. 适配器层：`VideoAdapterManager.convert_to_video()` 总是处理所有事件
3. 前端层：没有将选中的事件传递给API

## 解决方案

### 1. API层修改 (`web/api/video_generation_api.py`)

#### 新增 `_filter_selected_events()` 函数
```python
def _filter_selected_events(all_events: List[Dict], selected_event_ids: List[str], logger) -> List[Dict]:
    """
    过滤出用户选中的事件（支持重大事件和中级事件）
    
    功能：
    - 支持通过ID或名称选中重大事件
    - 支持通过复合ID选中特定的中级事件
    - 支持混合选择（完整事件+部分中级事件）
    """
```

**支持的ID格式：**
- 重大事件ID：`major_event_0`, `event_0`, 事件名称
- 中级事件ID：`major_event_0_event_0_0` (父事件_阶段索引_中级事件索引)

#### 修改 `generate_storyboard()` API
```python
@video_api.route('/video/generate-storyboard', methods=['POST'])
@login_required
def generate_storyboard():
    """
    请求参数：
    {
        "title": "小说标题",
        "video_type": "long_series",
        "selected_events": ["event_0", "event_1", ...]  # 新增：选中的事件ID列表
    }
    """
```

### 2. 适配器层修改 (`src/managers/VideoAdapterManager.py`)

#### 新增 `filtered_events` 参数
```python
def convert_to_video(
    self,
    novel_data: Dict,
    video_type: str,
    filtered_events: Optional[List[Dict]] = None,  # 新增
    **kwargs
) -> Dict:
```

**逻辑：**
- 如果提供了 `filtered_events`，直接使用过滤后的事件列表
- 如果未提供，则提取所有事件（保持向后兼容）

### 3. 前端层修改 (`web/static/js/video-generation.js`)

#### 传递选中事件到API
```javascript
const requestData = {
    title: this.selectedNovel,
    video_type: this.selectedType,
    selected_events: Array.from(this.selectedEvents)  // 新增
};
```

## 测试验证

创建了完整的测试套件 `test_video_event_filtering.py`，包含5个测试场景：

### 测试1：没有选中任何事件
✅ 返回空列表

### 测试2：选中整个重大事件
✅ 返回完整的重大事件及其所有中级事件

### 测试3：通过ID选中重大事件
✅ 支持多种ID格式（major_event_0, event_0）

### 测试4：选中部分中级事件
✅ 返回包含选中中级事件的部分重大事件

### 测试5：混合选择
✅ 支持同时选择完整事件和部分中级事件

## 使用说明

### 用户界面操作流程

1. **选择小说和视频类型**
   - 在欢迎屏幕选择小说
   - 选择视频类型（短片/长剧集/短视频）

2. **选择事件和角色**
   - 在事件列表中勾选想要生成的事件
   - 可以展开重大事件查看其中的中级事件
   - 支持选择整个重大事件或特定的中级事件

3. **生成分镜头脚本**
   - 点击"生成分镜头脚本"按钮
   - 系统只生成选中事件的分镜头

### API调用示例

```javascript
// 只选中特定事件
const response = await fetch('/api/video/generate-storyboard', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        title: "吞噬万界：从一把生锈铁剑开始",
        video_type: "long_series",
        selected_events: [
            "major_event_0",              // 整个第一个重大事件
            "major_event_1_event_2_0"     // 第二个重大事件的特定中级事件
        ]
    })
});
```

## 性能优化

**生成时间对比：**
- 修复前：生成89个中级事件 → 约890秒（10秒/事件）
- 修复后：假设选中5个中级事件 → 约50秒

**性能提升：**
- 选择性生成可节省大量时间
- 用户可以按需生成，避免不必要的等待

## 技术亮点

1. **灵活的事件过滤**
   - 支持多种ID格式
   - 支持混合选择模式
   - 保持向后兼容

2. **详细的日志记录**
   - 每个步骤都有清晰的日志
   - 便于调试和问题追踪

3. **完善的测试覆盖**
   - 5个测试场景覆盖所有使用情况
   - 确保功能稳定性

## 文件变更清单

1. `web/api/video_generation_api.py`
   - 新增 `_filter_selected_events()` 函数
   - 修改 `generate_storyboard()` 接受 `selected_events` 参数

2. `src/managers/VideoAdapterManager.py`
   - `convert_to_video()` 新增 `filtered_events` 参数

3. `web/static/js/video-generation.js`
   - `generateStoryboard()` 传递 `selected_events` 到API

4. `test_video_event_filtering.py` (新建)
   - 完整的测试套件

## 后续建议

1. **UI改进**
   - 添加"全选"和"清空"快捷按钮
   - 显示选中事件的预估生成时间
   - 支持保存和加载事件选择配置

2. **功能扩展**
   - 支持批量操作（如选择连续的多个事件）
   - 支持按章节范围筛选事件
   - 添加事件预览功能

3. **性能优化**
   - 考虑添加缓存机制
   - 支持后台生成和进度通知
   - 支持暂停和恢复生成

## 总结

✅ 问题已完全解决
✅ 所有测试通过
✅ 保持向后兼容
✅ 代码质量良好
✅ 准备投入使用

用户现在可以精确控制要生成哪些事件的视频内容，大大提升了系统的可用性和效率。