# WorldStateManager 问题分析

## 发现的问题

### 1. 硬编码的"扮演度"概念

在 `build_constraint_prompt()` 方法中（第290-297行）：

```python
# 3. 系统规则（扮演度）
rules = self.state.system_rules
lines.append(f"\n系统规则(扮演度):")  # ❌ 硬编码！
lines.append(f"  - 当前扮演度: {rules.current_playing_degree}%")  # ❌ 硬编码！
lines.append(f"  - 历史最高: {rules.max_playing_degree}%")  # ❌ 硬编码！
lines.append(f"  - 已解锁技能: {', '.join(rules.unlocked_skills[-3:]) if rules.unlocked_skills else '基础技能'}")
if rules.special_states:
    lines.append(f"  - 特殊状态: {', '.join(rules.special_states)}")

# ...

lines.append("\n【约束规则】")
lines.append("1. 必须保持上述角色状态一致（伤势、能力、扮演度）")  # ❌ 硬编码！
```

### 2. 数据模型硬编码

```python
@dataclass
class SystemRule:
    """系统规则状态"""
    current_playing_degree: float = 0.0  # ❌ 硬编码为"扮演度"
    max_playing_degree: float = 0.0      # ❌ 硬编码为"扮演度"
    cooldown_end_chapter: int = 0
    special_states: List[str] = field(default_factory=list)
    unlocked_skills: List[str] = field(default_factory=list)
```

### 3. 导致的后果

即使我们修复了 `.world_state.json` 文件的内容，`build_constraint_prompt()` 仍然会生成包含"扮演度"的提示词：

```
【世界状态约束 - 必须遵循】

主角(沈浪)当前状态:
  - 健康: 健康
  - 已解锁能力: 基础能力

系统规则(扮演度):  ← 错误！应该是"弹幕干涉系统"
  - 当前扮演度: 0.0%  ← 错误！应该是"弹幕热度"或"互动槽点数"
  - 历史最高: 0.0%
  - 已解锁技能: 基础技能

【约束规则】
1. 必须保持上述角色状态一致（伤势、能力、扮演度）  ← 错误！
```

## 正确的架构应该是

### 方案：通用系统规则模型

```python
@dataclass
class SystemRule:
    """系统规则状态 - 通用模型"""
    system_name: str = ""                    # 系统名称（如"弹幕干涉系统"）
    system_type: str = ""                    # 系统类型（如"金手指"、"扮演系统"）
    current_level: str = "初始"              # 当前等级/阶段
    current_power: float = 0.0               # 当前能力值（通用）
    max_power: float = 0.0                   # 历史最高能力值
    unlocked_abilities: List[str] = field(default_factory=list)  # 已解锁能力
    special_states: List[str] = field(default_factory=list)      # 特殊状态
    
    # 保留旧字段用于兼容性
    current_playing_degree: float = 0.0      # 兼容旧数据
    max_playing_degree: float = 0.0          # 兼容旧数据
    unlocked_skills: List[str] = field(default_factory=list)     # 兼容旧数据
```

### 修改 build_constraint_prompt()

```python
def build_constraint_prompt(self, chapter_num: int) -> str:
    lines = ["\n【世界状态约束 - 必须遵循】\n"]
    
    # 1. 主角状态
    protag = self.state.protagonist
    lines.append(f"主角({protag.name})当前状态:")
    lines.append(f"  - 健康: {protag.health}")
    lines.append(f"  - 当前位置: {protag.current_location or '未知'}")
    if protag.abilities_unlocked:
        lines.append(f"  - 已解锁能力: {', '.join(protag.abilities_unlocked[-3:])}")
    
    # 2. 系统规则（使用实际的系统名称）
    rules = self.state.system_rules
    system_name = rules.system_name or "系统"
    lines.append(f"\n{system_name}状态:")  # ✅ 使用实际的系统名称
    lines.append(f"  - 当前等级: {rules.current_level}")
    lines.append(f"  - 当前能力值: {rules.current_power}")
    if rules.unlocked_abilities:
        lines.append(f"  - 已解锁能力: {', '.join(rules.unlocked_abilities[-3:])}")
    if rules.special_states:
        lines.append(f"  - 特殊状态: {', '.join(rules.special_states)}")
    
    # 3. 剧情线索...
    # ...
    
    lines.append("\n【约束规则】")
    lines.append(f"1. 必须保持上述角色状态与{system_name}状态一致")
    lines.append("2. 不能突然解锁未获得的能力")
    lines.append("3. 活跃的剧情线索需要在文中体现（至少提及）")
    lines.append("4. 能力变化需要有合理过渡，不能突变")
    
    return "\n".join(lines)
```

## 修复步骤

1. **修改数据模型**：`SystemRule` 添加通用字段
2. **修改提示词构建**：`build_constraint_prompt()` 使用通用字段
3. **修改初始化器**：`ProjectStateInitializer` 正确设置 `system_name`
4. **修改更新逻辑**：章节提取后更新 `unlocked_abilities` 而不是 `unlocked_skills`

## 结论

用户的理解是对的：
- 第1章：如果状态文件不存在 → 初始化
- 后续章节：读取状态文件 → 生成章节 → 更新状态文件

但问题是 `WorldStateManager` 的数据模型和提示词构建逻辑**硬编码了"扮演度"概念**，导致即使状态文件正确，生成的提示词仍然是错的。

需要修改 `world_state_manager.py` 来使用通用的系统规则模型。
