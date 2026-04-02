# 提示词备份机制清理报告

## 已清理的高优先级文件

| 文件 | 修改内容 | 状态 |
|------|----------|------|
| `trope_prompt_builder.py` | 删除所有硬编码备用，强制使用JSON配置 | ✅ |
| `tactical_planner.py` | 删除 system_prompt_template 硬编码 | ✅ |
| `stage_review_optimizer.py` | 删除多处硬编码默认值（_get_default_fix_prompt, _get_default_word_count_constraints, _get_default_self_check_list, _get_retry_warning） | ✅ |
| `chapter_prompt_optimizer_v3.py` | 删除黄金三章/标准章节/通用组件加载的硬编码fallback，删除_system_prompt构建的硬编码fallback | ✅ |
| `stage_chapter_generator.py` | 删除 _build_chapter_prompt_builtin 方法，强制使用模板 | ✅ |
| `market_driven_conversation.py` | 删除 _build_default_setting_prompt 硬编码 | ✅ |
| `chapter_conversation_generator.py` | 删除 _load_ending_template 硬编码 | ✅ |

## 修改模式

**之前：**
```python
if template:
    return template
# 降级：硬编码
logger.warning("使用硬编码")
return f"硬编码提示词..."
```

**现在：**
```python
if not template:
    raise ValueError("配置未找到，请检查 xxx.json")
return template
```

## 结果

- ✅ 单一数据源：所有提示词强制从 JSON 配置加载
- ✅ 快速失败：配置缺失时立即报错，不会静默使用错误提示词
- ✅ 易于维护：修改只需改 JSON 文件，无需改动代码
