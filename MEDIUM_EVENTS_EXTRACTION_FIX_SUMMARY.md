# 中级事件提取修复总结

## 问题描述

从日志可以看到:
```
[LongSeriesStrategy] 分配完成：0 集（覆盖约200章）
```

**根本原因**: LongSeriesStrategy从重大事件中提取中级事件时,获取的`medium_events`为空数组,导致无法生成任何分集。

## 问题分析

### 1. 阶段名称不统一

系统中存在两种叙事阶段命名格式:
- **新格式**: `起因`、`发展`、`高潮`、`结局`
- **旧格式**: `起`、`承`、`转`、`合`

### 2. 代码中的不一致

#### EventExtractor ([`src/managers/EventExtractor.py:182`](src/managers/EventExtractor.py:182))
- 只支持新格式: `["起因", "发展", "高潮", "结局"]`
- **问题**: 无法提取旧格式的中级事件

#### LongSeriesStrategy ([`src/managers/VideoAdapterManager.py:364`](src/managers/VideoAdapterManager.py:364))
- 只支持新格式: `["起因", "发展", "高潮", "结局"]`
- **问题**: 无法提取旧格式的中级事件

#### LongSeriesStrategy.stage_config ([`src/managers/VideoAdapterManager.py:263`](src/managers/VideoAdapterManager.py:263))
- 只定义了新格式的配置
- **问题**: 遇到旧格式阶段名称时会抛出 KeyError

#### video_generation_api.py ([`web/api/video_generation_api.py:250`](web/api/video_generation_api.py:250))
- 获取事件列表时使用: `["起", "承", "转", "合"]`
- 展开中级事件时使用: `["起因", "发展", "高潮", "结局"]`
- **问题**: 不一致导致无法正确展开中级事件

## 修复方案

### 1. 统一使用 EventExtractor 的 extract_medium_events 方法

**修复位置**: 
- [`video_generation_api.py:388-397`](web/api/video_generation_api.py:388)
- [`video_generation_api.py:448-459`](web/api/video_generation_api.py:448)
- [`video_generation_api.py:465-476`](web/api/video_generation_api.py:465)

**修复方式**: 将硬编码的阶段名称改为调用 `event_extractor.extract_medium_events(major_event)`

```python
# 修复前
for stage in ["起因", "发展", "高潮", "结局"]:
    medium_events = composition.get(stage, [])
    ...

# 修复后
medium_events_from_extractor = event_extractor.extract_medium_events(major_event)
for medium_event in medium_events_from_extractor:
    ...
```

### 2. 增强 EventExtractor.extract_medium_events

**修复位置**: [`src/managers/EventExtractor.py:182-230`](src/managers/EventExtractor.py:182)

**修复内容**:
```python
# 支持两种格式
new_stage_order = ["起因", "发展", "高潮", "结局"]
old_stage_order = ["起", "承", "转", "合"]

# 检测使用哪种格式
has_new_format = any(composition.get(stage) for stage in new_stage_order)
has_old_format = any(composition.get(stage) for stage in old_stage_order)

if has_new_format:
    stage_order = new_stage_order
elif has_old_format:
    stage_order = old_stage_order
else:
    # 动态检测所有非空键
    stage_order = list(composition.keys())
```

### 3. 增强 LongSeriesStrategy._extract_medium_events

**修复位置**: [`src/managers/VideoAdapterManager.py:364-430`](src/managers/VideoAdapterManager.py:364)

**修复内容**: 
- 支持新旧两种格式
- 添加详细的调试日志
- 增加类型检查和容错处理

### 4. 扩展 LongSeriesStrategy.stage_config

**修复位置**: [`src/managers/VideoAdapterManager.py:259-330`](src/managers/VideoAdapterManager.py:259)

**修复内容**: 同时支持两种阶段名称
```python
self.stage_config = {
    # 新格式
    "起因": { ... },
    "发展": { ... },
    "高潮": { ... },
    "结局": { ... },
    # 旧格式
    "起": { ... },
    "承": { ... },
    "转": { ... },
    "合": { ... }
}
```

### 5. 修复 _generate_audio_design 逻辑错误

**修复位置**: [`src/managers/VideoAdapterManager.py:664-725`](src/managers/VideoAdapterManager.py:664)

**问题**: `_generate_audio_prompt` 试图访问 `shot["audio_design"]`,但此时 audio_design 还没生成

**修复**: 先生成各个组件,再传给 `_generate_audio_prompt`

### 6. 增强 EventExtractor.extract_all_major_events

**修复位置**: [`src/managers/EventExtractor.py:21-79`](src/managers/EventExtractor.py:21)

**修复内容**: 添加对 `stage_writing_plans` 格式的支持(介于新旧格式之间的中间格式)

## 测试验证

### 测试脚本
创建了 [`test_medium_events_fix.py`](test_medium_events_fix.py) 进行全面测试

### 测试结果
```
[PASS] 通过 - EventExtractor
[PASS] 通过 - LongSeriesStrategy
[PASS] 通过 - VideoAdapterManager

[SUCCESS] 所有测试通过！中级事件提取修复成功！
```

### 测试覆盖
- ✅ 旧格式(起承转合)的中级事件提取
- ✅ 新格式(起因发展高潮结局)的中级事件提取
- ✅ LongSeriesStrategy 的完整转换流程
- ✅ 镜头序列生成(包含音频设计)

## 影响范围

### 修改的文件
1. [`src/managers/EventExtractor.py`](src/managers/EventExtractor.py)
   - `extract_medium_events()` 方法
   - `extract_all_major_events()` 方法

2. [`src/managers/VideoAdapterManager.py`](src/managers/VideoAdapterManager.py)
   - `LongSeriesStrategy._extract_medium_events()` 方法
   - `LongSeriesStrategy.stage_config` 属性
   - `LongSeriesStrategy._generate_audio_design()` 方法
   - `LongSeriesStrategy._generate_audio_prompt()` 方法

3. [`web/api/video_generation_api.py`](web/api/video_generation_api.py)
   - `generate_prompt()` 函数中的3处中级事件展开逻辑

### 向后兼容性
✅ 完全向后兼容
- 支持新格式(起因发展高潮结局)
- 支持旧格式(起承转合)
- 自动检测并使用正确的格式

## 关键改进

1. **统一性**: 所有模块都使用 `EventExtractor.extract_medium_events()` 方法,确保行为一致
2. **容错性**: 增加了类型检查和错误处理,避免因数据格式问题导致崩溃
3. **可维护性**: 修改集中在 EventExtractor 中,其他模块只需调用即可
4. **可扩展性**: 如果未来出现新的格式,只需在 EventExtractor 中添加支持即可

## 建议

1. **逐步迁移**: 建议逐步将旧格式数据迁移到新格式,减少维护成本
2. **文档更新**: 更新相关文档,明确标注支持的数据格式
3. **单元测试**: 为这些核心方法添加更全面的单元测试

## 验证步骤

### 验证旧格式支持
```bash
python test_medium_events_fix.py
```

### 验证实际项目
1. 打开视频生成页面
2. 选择一个小说项目
3. 选择"长篇剧集"模式
4. 检查是否能正确提取并显示中级事件
5. 验证生成的分集数量是否正确

## 预期效果

修复后,日志应该显示:
```
[LongSeriesStrategy] 分配完成：XX 集（覆盖约200章）
```

其中 XX 应该大于 0,表示成功提取到中级事件并生成了分集。