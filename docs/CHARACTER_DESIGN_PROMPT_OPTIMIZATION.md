# 角色设计提示词优化分析

## 问题诊断

### 当前状况
根据日志显示：
- **提示词长度记录**: 2 字符（明显错误，记录的是变量占位符而非实际内容）
- **实际请求载荷**: 57442 字符（约 56KB）
- **API响应时间**: 10.18 秒

### 问题根源

提示词过长的主要原因：

1. **提示词模板本身过长**（约2000+字符）
   - 详细的说明文字和教学性内容
   - 完整的JSON结构定义
   - 大量的示例和注意事项

2. **数据载荷过大**
   - `EXISTING_CHARACTERS`: 包含所有已有角色的完整JSON数据
   - `STAGE_REQUIREMENTS`: 包含阶段信息的完整JSON数据
   - 都是使用 `indent=2` 格式化的（多空格缩进）

3. **冗余的JSON结构定义**
   - 提示词中重复定义了完整的JSON Schema
   - 字段说明过于详细

## 设计不合理之处

### 1. 提示词过载
```
当前：~2000字符的模板 + ~55000字符的数据 = ~57000字符总计
建议：~500字符的模板 + ~15000字符的数据 = ~15500字符总计
```

### 2. 教学式提示词
- 当前提示词像是"教AI如何设计角色"
- 应该改为"直接指令式"
- AI已经知道基本的角色设计原则

### 3. 过度说明
```json
// 当前：
"initial_state": {
    "description": "string // 对该角色登场时状态的简要描述",
    "cultivation_level": "string // 登场时的修为境界",
    ...
}

// 优化后：
"initial_state": {
    "description": "简要描述",
    "cultivation_level": "修为境界",
    ...
}
```

## 优化方案

### 方案A: 压缩提示词（推荐）

#### 1. 简化提示词模板
```python
"character_design_supplementary": """
基于现有角色和阶段需求，设计新配角。
输出JSON：
{
    "newly_added_characters": [{
        "name": "姓名",
        "role": "定位",
        "initial_state": {
            "description": "状态描述",
            "cultivation_level": "修为",
            "location": "地点",
            "faction": "势力",
            "identity": "身份"
        },
        "soul_matrix": [{
            "core_trait": "核心特质",
            "behavioral_manifestations": ["行为表现"]
        }],
        "living_characteristics": {
            "physical_presence": "外貌气场",
            "distinctive_traits": "鲜明特点",
            "communication_style": "交流方式"
        },
        "dialogue_style_example": "台词",
        "faction_affiliation": {
            "current_faction": "势力",
            "position": "地位",
            "loyalty_level": "忠诚度"
        },
        "faction_relationships": {
            "allies_in_faction": [],
            "rivals_in_faction": []
        },
        "relationship_with_protagonist": {
            "initial_friction_or_hook": "初次接触点"
        },
        "narrative_purpose": "剧情作用",
        "reader_impression": "读者印象"
    }]
}
只输出JSON，无其他内容。
"""
```

**效果**: 从 ~2000字符 压缩到 ~500字符（减少75%）

#### 2. 压缩数据载荷
```python
# 修改 plan_generator.py 第256行
# 当前：
prompt_context_str = json.dumps(prompt_context, ensure_ascii=False, indent=2)

# 优化后：
prompt_context_str = json.dumps(prompt_context, ensure_ascii=False, separators=(',', ':'))
```

**效果**: 从 ~55000字符 压缩到 ~15000字符（减少70%）

#### 3. 精简传输数据
```python
# 只传输必要的信息，而非完整的角色JSON
def _build_minimal_character_context(self, existing_characters):
    """构建最小化的角色上下文"""
    minimal = {
        "main_character": {
            "name": existing_characters.get("main_character", {}).get("name"),
            "faction": existing_characters.get("main_character", {}).get("faction_affiliation", {}).get("current_faction")
        },
        "important_characters": [
            {
                "name": char.get("name"),
                "role": char.get("role"),
                "faction": char.get("faction_affiliation", {}).get("current_faction")
            }
            for char in existing_characters.get("important_characters", [])
        ]
    }
    return minimal
```

**效果**: 再减少50%的数据传输

### 方案B: 分步设计（备选）

将角色设计分成多个步骤：
1. **基础信息生成**：只生成姓名、定位、势力
2. **详细设计生成**：基于第一步生成详细信息

优点：每次请求更小、更快
缺点：需要多次API调用，可能增加总时间

## 预期效果对比

| 指标 | 当前 | 优化后（方案A） | 改善 |
|------|------|----------------|------|
| 提示词模板 | ~2000字符 | ~500字符 | -75% |
| 数据载荷 | ~55000字符 | ~15000字符 | -73% |
| 总载荷 | ~57000字符 | ~15500字符 | -73% |
| 响应时间 | ~10秒 | ~3-5秒 | -50-70% |
| 成本 | 高 | 低 | -73% |

## 实施建议

### 优先级1（立即实施）
1. 修改 `plan_generator.py` 第256行，使用紧凑的JSON格式
2. 移除提示词中的教学性内容，保留核心指令

### 优先级2（后续优化）
1. 实施最小化数据传输
2. 考虑分步设计模式

### 优先级3（长期优化）
1. 建立提示词模板库
2. 实施提示词A/B测试
3. 监控不同提示词长度对质量和速度的影响

## 结论

**当前设计不合理**，主要问题：
1. ❌ 提示词过长（包含大量教学性内容）
2. ❌ 数据传输冗余（完整JSON + 格式化缩进）
3. ❌ 成本高昂（57KB的载荷）
4. ❌ 响应慢（10秒+）

**推荐优化**：
1. ✅ 压缩提示词模板至核心指令
2. ✅ 使用紧凑的JSON格式
3. ✅ 只传输必要信息
4. ✅ 预期减少73%的载荷和50-70%的响应时间

## 验证方法

实施优化后，对比以下指标：
- API请求载荷大小
- API响应时间
- 生成质量（是否下降）
- Token消耗量