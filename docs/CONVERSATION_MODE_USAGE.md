# 对话模式使用指南

## 快速开始

### 1. 启用对话模式

在配置文件中添加：

```python
config = {
    # 启用第一阶段对话模式
    "use_phase_one_conversation_mode": True,
    
    # 配置各 Session 的执行模式
    "session_fallback": {
        "foundation_planning": {"mode": "auto"},      # 自动选择
        "character_narrative": {"mode": "auto"},      # 自动选择
        "expectation_system": {"mode": "auto"}        # 自动选择
    }
}
```

### 2. 模式说明

**auto** (推荐): 优先尝试对话模式，失败时自动回退到传统模式

**conversation**: 强制使用对话模式，失败时报错

**traditional**: 强制使用传统模式

### 3. 查看执行结果

在日志中可以看到使用的模式：

```
基础规划使用模式: conversation
角色设计使用模式: conversation
期待感系统使用模式: traditional
```

## 高级配置

### 配置超时时间

```python
config = {
    "session_fallback": {
        "foundation_planning": {
            "mode": "auto",
            "timeout_seconds": 900  # 15分钟
        }
    }
}
```

### 禁用对话模式

如果对话模式出现问题，可以一键禁用：

```python
config = {
    "use_phase_one_conversation_mode": False
}
```

## 常见问题

### Q: 对话模式和传统模式有什么区别？

**传统模式**: 每个步骤独立调用 API，产物可能缺乏连贯性

**对话模式**: 在同一会话中多轮对话，产物更连贯一致

### Q: 对话模式会失败吗？

默认配置（auto 模式）下，如果对话模式失败会自动回退到传统模式，不会影响整体流程。

### Q: 需要更多 API 调用吗？

是的。对话模式使用多轮对话，API 调用次数会增加，但产物质量更高。

### Q: 如何验证产物格式？

系统会自动验证产物格式，如果不符合要求会回退到传统模式。

## 故障排查

### 问题: 对话模式总是失败

**解决方案**:
1. 检查 API 密钥和连接
2. 查看日志中的错误信息
3. 临时切换到传统模式

### 问题: 产物格式不符合预期

**解决方案**:
1. 运行验证测试: `python -m tests.test_full_integration`
2. 检查 Session 配置
3. 查看对比报告

### 问题: 进度显示不正确

**解决方案**:
这是正常现象，因为对话模式的进度计算方式不同。最终产物不受影响。

## 性能对比

| 指标 | 传统模式 | 对话模式 |
|------|---------|---------|
| API 调用次数 | 较少 | 较多 |
| 生成时间 | 较快 | 稍慢 |
| 产物连贯性 | 一般 | 更好 |
| 失败回退 | 无 | 自动 |

## 建议

1. **生产环境**: 使用 auto 模式，确保稳定性
2. **测试环境**: 可以尝试 conversation 模式，体验更好质量
3. **问题排查**: 保留传统模式作为备用方案
