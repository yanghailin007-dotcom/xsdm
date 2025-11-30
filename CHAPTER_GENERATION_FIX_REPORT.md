# 章节生成失败问题修复报告

## 问题描述

用户报告章节生成出现失败，日志显示：
```
[2025-11-28 08:20:24] [ContentGenerator] [ERROR] [E] ❌ 第2章在第 5 次尝试中出现严重异常: 'GenerationContext' object has no attribute 'get'
```

## 错误原因

在 `src/core/ContentGenerator.py` 的第 1286 行，`_generate_unique_chapter_title` 方法中，代码错误地假设 `novel_data['_current_generation_context']` 是一个字典对象，并尝试调用 `.get()` 方法：

```python
# 错误代码
event_context = novel_data.get('_current_generation_context', {}).get('event_context', {})
```

但实际上，`_current_generation_context` 存储的是 `GenerationContext` 类的实例对象，该对象没有 `.get()` 方法。

## 修复方案

修改了 `ContentGenerator.py` 中的 `_generate_unique_chapter_title` 方法，添加了对 `GenerationContext` 对象的正确处理：

```python
# 修复后的代码
# 获取当前章节的主要事件信息
# 修复：处理 _current_generation_context 可能是 GenerationContext 对象的情况
context_obj = novel_data.get('_current_generation_context')
if hasattr(context_obj, 'event_context'):
    event_context = context_obj.event_context
elif isinstance(context_obj, dict):
    event_context = context_obj.get('event_context', {})
else:
    event_context = {}
```

## 额外修复

同时修复了日志输出的 Unicode 编码问题，在 `src/utils/logger.py` 中改进了错误处理：

```python
try:
    # 使用更安全的编码方式
    safe_line = log_line.encode('utf-8', errors='ignore').decode('utf-8')
    if safe_line.strip():  # 只有当清理后还有内容时才打印
        print(safe_line, file=output_stream)
except (UnicodeEncodeError, OSError):
    # 进一步回退: 使用ASCII
    try:
        safe_line = log_line.encode('ascii', 'ignore').decode('ascii')
        if safe_line.strip():
            print(safe_line, file=output_stream)
    except OSError:
        # 如果仍然失败，尝试最基本的输出
        try:
            print(f"[{self.module}] LOG: Output failed", file=output_stream)
        except OSError:
            pass  # 静默忽略
```

## 测试验证

创建了测试文件 `test_chapter_title_fix.py` 验证修复效果：

1. ✅ GenerationContext 对象创建成功
2. ✅ event_context 访问成功
3. ✅ active_events 获取成功
4. ✅ 事件信息提取正常

## 影响

- 修复了章节生成过程中因类型错误导致的失败问题
- 改善了日志系统对 Unicode 字符的处理能力
- 提高了系统的稳定性和容错能力

## 第二个问题：llm_config 属性不存在

### 错误信息
```
[2025-11-28 09:43:29] [ContentGenerator] [INFO] [I] 生成新标题失败: 'ContentGenerator' object has no attribute 'llm_config'
```

### 错误原因
在 `ContentGenerator.py` 的第 1329 行，代码尝试访问不存在的 `self.llm_config` 属性：

```python
# 错误代码
model=self.llm_config.get("api_model", "deepseek-chat")
```

同时，`generate_content_with_retry` 方法的调用参数也不正确，该方法不接受 `model`、`max_tokens`、`parser` 等参数。

### 修复方案

1. **修正 API 调用参数**：使用正确的 `generate_content_with_retry` 方法签名
2. **添加缺失的 prompt**：在 `WritingPrompts.py` 中添加 `chapter_title_generation` prompt

```python
# 修复后的代码
new_title = self.api_client.generate_content_with_retry(
    content_type="chapter_title_generation",
    user_prompt=title_prompt,
    temperature=0.7,
    purpose="生成章节标题"
)
```

在 `WritingPrompts.py` 中添加：
```python
"chapter_title_generation": """
你是一位专业的网络小说编辑，擅长创作吸引人的章节标题。

请根据用户提供的要求，生成一个简洁、吸引人的章节标题。

要求：
1. 标题要简洁有力，能够吸引读者点击
2. 标题要与章节内容相关
3. 标题长度控制在6-14字之间
4. 避免使用过于俗套的表达
5. 可以适当使用悬念、冲突等元素

请直接返回标题文本，不要包含任何额外的解释或格式标记。
"""
```

## 完整修复列表

### 修复位置汇总

1. **`_generate_unique_chapter_title` 方法** (line 1286-1293)
   - 修复了对 `GenerationContext.event_context` 的访问

2. **`_generate_event_related_title` 方法** (line 1351-1359)
   - 修复了对 `GenerationContext.event_context` 的访问

3. **`_save_chapter_failure` 方法** (line 2672-2686)
   - 修复了对 `GenerationContext` 所有属性的访问
   - 添加了完整的错误处理

4. **API 调用修复** (line 1327-1333)
   - 修正了 `generate_content_with_retry` 的调用参数
   - 移除了不存在的 `self.llm_config` 引用

5. **添加缺失的 Prompt** (`WritingPrompts.py`)
   - 添加了 `chapter_title_generation` prompt

## 测试验证

创建了全面的测试文件 `test_all_context_fixes.py`，验证了：
- ✅ `_generate_unique_chapter_title` 中的 event_context 访问
- ✅ `_generate_event_related_title` 中的 event_context 访问
- ✅ `_save_chapter_failure` 中的上下文摘要提取
- ✅ 所有属性访问的类型检查和错误处理

## 相关文件

- `src/core/ContentGenerator.py` (line 1286-1293, 1327-1333, 1351-1359, 2672-2686)
- `src/utils/logger.py` (line 143-161)
- `src/core/Contexts.py` (GenerationContext 类定义)
- `src/prompts/WritingPrompts.py` (添加 chapter_title_generation prompt)