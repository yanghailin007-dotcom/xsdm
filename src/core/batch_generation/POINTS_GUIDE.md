# 批量生成创造点消耗指南

## 核心规则

**1次API调用 = 1创造点**

批量生成的核心优势：无论生成多少章正文，**正文生成阶段只消耗1创造点**。

## 消耗明细

### 2章中型事件

| 阶段 | 逐章方案 | 批量方案 | 节省 |
|-----|---------|---------|-----|
| 场景生成 | 2点 | 1点 | 1点 |
| 正文生成 | 2点 | 1点 | **1点** |
| 质量评估 | 2点 | 1点 | 1点 |
| **总计** | **6点** | **3点** | **3点 (50%)** |

### 3章中型事件

| 阶段 | 逐章方案 | 批量方案 | 节省 |
|-----|---------|---------|-----|
| 场景生成 | 3点 | 1点 | 2点 |
| 正文生成 | 3点 | 1点 | **2点** |
| 质量评估 | 3点 | 1点 | 2点 |
| **总计** | **9点** | **3-4点** | **5-6点 (55%)** |

## 代码中如何统计

### BatchProcessResult 新增字段

```python
@dataclass
class BatchProcessResult:
    success: bool
    chapters: Dict[int, ChapterContent]
    api_calls_used: int      # API调用次数
    points_consumed: int     # 消耗的创造点（=api_calls_used）
    points_saved: int        # 节省的创造点
    ...
```

### 使用示例

```python
result = processor.process_medium_event(
    medium_event=event,
    chapter_range=(5, 7),  # 3章
    novel_data=novel_data
)

if result.success:
    print(f"✅ 生成成功")
    print(f"   消耗创造点: {result.points_consumed}点")
    print(f"   节省创造点: {result.points_saved}点")
    print(f"   节省比例: {result.points_saved / (result.points_consumed + result.points_saved):.1%}")
    
    # 3章事件示例输出:
    # 消耗创造点: 3点（或4点，如果触发Level 2评估）
    # 节省创造点: 6点（或5点）
    # 节省比例: 66.7%
```

## 自动扣费机制

批量生成使用现有的APIClient扣费回调机制：

```python
# 在NovelGenerator中设置扣费回调
self.api_client.set_api_call_callback(self._on_api_call_deduct_points)

def _on_api_call_deduct_points(self, purpose: str, attempt: int):
    """每次API调用成功扣除1创造点"""
    # 扣除用户1创造点
    # 记录消耗日志
    # 发布点数消耗事件
```

批量生成模块**无需额外处理扣费**，只需正确统计API调用次数。

## 回退场景的点数处理

当批量生成失败回退到逐章生成时：

```python
result = processor.process_medium_event(...)

if result.fallback_used:
    # 回退后逐章生成，消耗点数增加
    print(f"⚠️ 已回退到{result.fallback_level}")
    print(f"   实际消耗: {result.points_consumed}点")
    print(f"   节省点数: {result.points_saved}点（回退后为0）")
```

**注意**: 回退后逐章生成，`points_saved` 将为0或负数。

## 监控与告警

### 累计统计

```python
stats = processor.get_stats()

print(f"""
累计统计:
- 处理事件: {stats['total_events']}
- 成功事件: {stats['batch_success']}
- 回退次数: {stats['fallback_count']}
- 累计节省创造点: {stats['api_calls_saved']}点  <-- 重点监控
- 成功率: {stats['success_rate']:.1%}
""")
```

### 日志输出

批量生成会在日志中明确显示点数信息：

```
[MultiChapterGen] 调用API批量生成3章内容... (预计消耗1创造点，节省2点)
[MultiChapterGen] 批量生成成功: 3章, 消耗1创造点, 节省2点
[BatchProcessor] 中型事件处理完成: 韩立得掌天瓶 API调用:3(消耗3创造点), 节省:6点, 评估:L1
```

## 最佳实践

1. **监控节省率**: 如果 `points_saved` 经常为0，说明批量生成效果不好，检查API稳定性
2. **关注回退**: 回退会增加点数消耗，监控 `fallback_count`
3. **跳过评估**: 调试时可 `skip_assessment=True` 节省1点，但生产环境建议开启
4. **合理分批**: 4+章事件拆分为2+2批次，平衡成功率与节省率

## 常见问题

### Q: 批量生成失败会扣费吗？

A: 不会。点数在API调用**成功后**才扣除。

### Q: 回退到逐章生成会重复扣费吗？

A: 不会。每次API调用独立扣费，回退是新的调用。

### Q: 如何查看详细的点数消耗记录？

A: 查看APIClient的日志，每次调用都有 `[API调用 #N] 点数已扣除` 的记录。

### Q: 批量生成可以节省多少创造点？

A: 根据统计：
- 2章事件：节省3点（50%）
- 3章事件：节省5-6点（55-66%）
- 4章事件（2+2批次）：节省6-7点（50-58%）
