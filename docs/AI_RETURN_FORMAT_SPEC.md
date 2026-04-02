# AI 返回格式规范说明书

> 本文档描述 XSDM 系统中所有章节生成相关功能对 AI 返回格式的要求
> 最后更新：2026-04-02

---

## 一、概述

所有**章节生成**相关的 AI 调用，统一要求返回 **JSON 格式**，包含两个核心字段：

```json
{
  "title": "章节标题（8-14字，不含'第X章'前缀）",
  "content": "章节正文内容（2000-2500字）"
}
```

### 关键原则

1. **title 字段**：只放纯标题文本，**绝对禁止**包含 "第X章" 前缀
2. **content 字段**：只放正文，**绝对禁止**在开头写 "第X章：XXX" 标题行
3. **禁止字段**：`chapter_number` 字段不允许出现
4. **自检报告**：AI 可以在 JSON 后附加自检报告，但会被系统提取并丢弃

---

## 二、各生成路径详细规范

### 1. 正常章节生成（对话模式）

**文件**：`chapter_conversation_generator.py`

**调用点**：`_generate_single_chapter_in_session()`

**提示词要求**：
```
## 【强制输出格式 - JSON】
必须返回以下JSON格式，不要返回纯文本：

```json
{
  "title": "章节标题（8-14字，不含'第X章'前缀）",
  "content": "章节正文内容（2000-2500字，正文开头不要写标题）"
}
```
```

**响应处理**：
- 使用 `_parse_response()` 解析
- 支持 Markdown 代码块包裹的 JSON（自动去除 ```json 标记）
- 自动清理 content 中的标题行（正则匹配 `第X章：XXX`）

---

### 2. 重试生成（质检失败时）

**文件**：`chapter_conversation_generator.py`

**调用点**：`_generate_single_chapter_in_session()` 中的 retry 逻辑

**触发条件**：当 AI 返回只包含自检报告而没有正文时

**简化提示词**：
```
请生成第{X}章，约2000-2500字。
要求：快节奏爽文，强情绪流，章章有钩子。

## 【强制输出格式 - JSON】
必须返回以下JSON格式，不要返回纯文本：
```json
{
  "title": "章节标题（8-14字，不要'第X章'前缀）",
  "content": "章节正文（2000-2500字，直接从场景开始，禁止在正文开头写'第X章'标题）"
}
```

⚠️ 警告：
- content字段必须直接以正文开头，绝对禁止以"第X章：XXX"开头
- 标题只放在title字段，不要重复放在content里
- 不需要自检报告，只返回JSON
```

**特殊处理**：
- 重试时明确要求 **不需要自检报告**
- 如果重试后仍只返回自检报告，抛出异常

---

### 3. 扩写生成（字数不足时）

**文件**：`chapter_conversation_generator.py`

**调用点**：`_expand_chapter()`

**提示词要求**：
```
## 【强制输出格式 - JSON】
必须返回以下JSON格式：

```json
{
  "content": "扩写后的完整章节内容（{目标字数}字以上）"
}
```

⚠️ **重要**：只需要返回content字段，包含扩写后的完整章节内容即可。
```

**注意**：扩写时只需要 `content` 字段，不需要 `title`（保留原标题）

---

### 4. 滑动窗口修复（Stage Review）

**文件**：`stage_review_optimizer.py`

**调用点**：`_optimize_window_conversational()` / `_render_fix_prompt()`

**提示词要求**：
```
## 【强制输出格式 - JSON】
必须返回以下JSON格式，不要返回纯文本或Markdown代码块：

```json
{
  "chapter_number": {章号},
  "title": "章节标题（8-14字，不要'第X章'前缀）",
  "content": "完整的修改后章节内容（直接从正文开始，绝对禁止在开头写'第X章'标题）"
}
```

⚠️ **重要警告**：
- `content`字段必须直接以正文开头，绝对禁止以"第X章：XXX"开头
- `title`字段只放标题文本，不要加"第X章"前缀
- 标题只放在`title`字段，不要重复放在`content`里
- 必须返回合法的JSON格式，title和content字段都不能省略
```

**特殊字段**：允许包含 `chapter_number`（用于校验）

---

### 5. 单章修复（单问题修复）

**文件**：`stage_review_optimizer.py`

**调用点**：`_fix_single_chapter()`

**提示词要求**：
```
## 【强制输出格式 - JSON】
必须返回以下JSON格式，不要返回纯文本：

```json
{
  "title": "章节标题（8-14字，不要'第X章'前缀）",
  "content": "修复后的完整章节内容（2000-2500字）"
}
```

⚠️ **重要警告**：
- 必须返回合法的JSON格式
- `title`字段只放标题文本，不要加"第X章"前缀
- `content`字段只放正文，不要包含标题行
```

---

### 6. 批次生成（Batch Generator）

**文件**：`batch_chapter_generator.py`

**调用点**：`_generate_single_chapter()`

**提示词要求**：
```
## 【强制输出格式 - JSON】
必须返回以下JSON格式，不要返回纯文本：

```json
{
  "title": "章节标题（8-14字，不要'第X章'前缀）",
  "content": "第{X}章正文（2000-2500字，直接从场景开始，禁止在正文开头写'第X章'标题）"
}
```

⚠️ **重要警告**：
- 必须返回合法的JSON格式
- `title`字段只放标题文本，不要加"第X章"前缀
- `content`字段只放正文，不要包含标题行"第X章：XXX"
- 禁止在正文中包含 `---正文结束---` 等分隔符
```

---

### 7. 阶段生成（Stage Generator）

**文件**：`stage_chapter_generator.py`

**调用点**：`_generate_chapter_in_session()`

**提示词要求**：与批次生成相同

---

### 8. 黄金三章生成

**文件**：`chapter_prompt_optimizer_v3.py`

**调用点**：`_render_golden_chapter_X_from_config()` (X=1,2,3)

**特殊之处**：
- 黄金三章的提示词通过 JSON 配置渲染
- 输出格式通过 `_render_output_format_from_config()` 统一渲染
- 包含详细的自检报告模板

**输出格式要求**：
```
## 【🚨 强制输出格式 - 必须严格遵守】

### 标题规范（番茄爆款标准）
- 字数：8-14字（**不含**"第X章"前缀）
- 内容：概括本章核心爽点/悬念
- 风格：简洁有力，有冲击力

### JSON输出格式（唯一允许的格式）
**你必须且只能返回一个符合以下结构的JSON对象：**

```json
{
  "title": "章节标题（8-14字，不含'第X章'）",
  "content": "章节正文内容（2000-2500字，正文开头不要写标题）"
}
```

### 🚨 强制规则
- title字段只放标题文本，不要加"第X章"前缀
- content字段只放正文，绝对禁止在正文开头写"第X章 XXX"
- chapter_number字段绝对禁止出现！
- 禁止在正文中包含 `---正文结束---` 等分隔符！
```

**自检报告要求**（黄金三章特有）：
```
----
【AI自检报告 - 第X章】
总字数：XXXX字

🚨【三大问题修复检查】
情绪密度：X个/千字（目标≥2.0）| 情绪词列表：XXX、XXX、XXX...
章尾钩子：有/无 | 钩子类型：XXX | 最后50字："..."
爽点密度：X个/千字（目标≥1.5）| 爽点时刻：X个

番茄算法：前300字冲突（是/否），500字系统（是/否）
微创新检查：时间（创新/套路），系统激活（创新/套路），反派（有智商/脸谱化）
情绪曲线：X次转变（列出）
自检结论：【通过/需优化】
问题与优化：列出发现的问题
----
```

---

## 三、标准章节生成

**文件**：`chapter_prompt_optimizer_v3.py`

**调用点**：`_render_standard_chapter_from_config()`

**输出格式**：与黄金三章相同，通过 `_render_output_format_from_config()` 渲染

---

## 四、响应解析处理

### 4.1 统一解析方法

所有路径使用类似的 `_parse_response()` 方法：

```python
def _parse_response(self, response) -> Dict:
    """
    解析响应
    返回包含 title 和 content 的字典
    支持处理 Markdown 代码块包裹的 JSON
    """
    result = {'title': '', 'content': ''}
    
    if isinstance(response, dict):
        # 已经是字典
        result['title'] = response.get('title', '')
        result['content'] = response.get('content', str(response))
    elif isinstance(response, str):
        cleaned = response.strip()
        
        # 移除 Markdown 代码块标记
        if cleaned.startswith('```'):
            first_newline = cleaned.find('\n')
            if first_newline != -1:
                cleaned = cleaned[first_newline:].strip()
            if cleaned.endswith('```'):
                cleaned = cleaned[:-3].strip()
        
        # 尝试解析 JSON
        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                result['title'] = parsed.get('title', '')
                result['content'] = parsed.get('content', cleaned)
        except:
            # JSON 解析失败，使用清理后的内容
            result['content'] = cleaned
    
    # 清理 content 中的标题行
    if result['content']:
        title_patterns = [
            r'^第[一二三四五六七八九十百千万零\d]+章[：:\s]*[^\n]*\n*',
            r'^Chapter\s*\d+[：:\s]*[^\n]*\n*',
        ]
        for pattern in title_patterns:
            result['content'] = re.sub(pattern, '', result['content'], flags=re.IGNORECASE)
        result['content'] = result['content'].lstrip('\n')
    
    return result
```

### 4.2 正文提取（处理自检报告）

**分隔符列表**：
- `---正文结束---`
- `【AI自检报告】`
- `自检报告：`
- `【自检报告】`

**提取逻辑**：
```python
def _extract_main_content(self, content: str, chapter_num: int) -> str:
    # 1. 查找分隔符，提取前面部分
    for sep in separators:
        if sep in content:
            return content.split(sep)[0].strip()
    
    # 2. 特殊处理：如果内容以 "---" 开头（自检报告分隔符）
    if content.strip().startswith('---'):
        # 跳过自检报告，找到正文开始位置
        ...
    
    return content.strip()
```

---

## 五、自检报告机制

### 5.1 自检报告用途

- AI 在生成章节后进行自我检查
- 检查字数、情绪密度、爽点、钩子、番茄算法指标等
- **不会被保存到数据库**，仅用于开发和调试

### 5.2 自检报告格式

```
----
【AI自检报告 - 第X章】
总字数：XXXX字

🚨【三大问题修复检查】
情绪密度：X个/千字（目标≥2.0）
章尾钩子：有/无 | 钩子类型：XXX
爽点密度：X个/千字（目标≥1.5）

番茄算法：前300字冲突（是/否），500字系统（是/否）
自检结论：【通过/需优化】
----
```

### 5.3 只返回自检报告的检测

```python
def _is_only_self_check_report(self, content: str) -> bool:
    """检查内容是否只包含自检报告而没有正文"""
    if not content or len(content) < 300:
        return True
    
    # 如果只包含自检报告标记
    if content.startswith("【AI自检报告") and "第" not in content[:50]:
        return True
    
    # 检查是否只有自检报告部分
    report_lines = [l for l in lines if l.startswith("【AI自检报告") 
                    or l.startswith("总字数：") 
                    or l.startswith("番茄算法：")]
    if len(report_lines) >= 3 and len(content) < 500:
        return True
    
    return False
```

---

## 六、错误示例与正确示例

### ❌ 错误示例 1：content 包含标题行

```json
{
  "content": "第5章：九幽冥蛇现，震惊全场\n\n暗紫色的雾气从山谷中升起..."
}
```
**错误原因**：content 字段包含 "第X章" 标题行！

### ❌ 错误示例 2：返回纯文本

```
第5章：九幽冥蛇现，震惊全场

暗紫色的雾气从山谷中升起...
```
**错误原因**：没有返回 JSON 格式！

### ❌ 错误示例 3：包含 chapter_number

```json
{
  "chapter_number": 5,
  "title": "九幽冥蛇现，震惊全场",
  "content": "暗紫色的雾气..."
}
```
**错误原因**：chapter_number 字段绝对禁止出现！

### ✅ 正确示例

```json
{
  "title": "九幽冥蛇现，震惊全场",
  "content": "暗紫色的雾气从山谷中升起..."
}
```

---

## 七、总结

| 生成类型 | 必需字段 | 可选字段 | 自检报告 | 特殊说明 |
|---------|---------|---------|---------|---------|
| 正常章节 | title, content | - | 允许附加 | 标准格式 |
| 重试生成 | title, content | - | **禁止** | 简化提示词 |
| 扩写生成 | content | - | - | 不需要 title |
| 滑动窗口修复 | title, content | chapter_number | 允许 | 修复模式 |
| 单章修复 | title, content | - | 允许 | 独立调用 |
| 批次生成 | title, content | - | 允许 | 标准格式 |
| 阶段生成 | title, content | - | 允许 | 标准格式 |
| 黄金三章 | title, content | - | **必须** | 详细自检 |

---

## 八、相关文件

- `chapter_conversation_generator.py` - 主对话生成器
- `chapter_prompt_optimizer_v3.py` - V3 提示词优化器（含黄金三章）
- `stage_review_optimizer.py` - 滑动窗口修复
- `batch_chapter_generator.py` - 批次生成器
- `stage_chapter_generator.py` - 阶段生成器
