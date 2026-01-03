# 角色名称验证修复

## 问题描述

从日志中观察到以下角色名称被拒绝添加到角色发展表：
- ❌ "林苟 (第一任宿主)"
- ❌ "江清雪 (第二任宿主/女帝)"
- ✅ "主宰 (本体无名，自命代号)" (这个通过了)

这些是带有角色类型说明的有效角色名称，应该被允许通过验证。

## 根本原因

在 [`WorldStateManager._is_valid_character_name()`](../src/managers/WorldStateManager.py:1373) 方法中，验证逻辑没有优先处理带括号的角色类型说明格式。代码会先进行一系列检查（包括检查是否包含无效词汇），而此时还没有检查括号内容是否为合理的角色类型说明。

## 解决方案

修改验证逻辑的顺序，**优先检查带括号的角色类型说明**：

### 修改前
```python
# 🔥 重大修复：主角和特殊存在直接通过验证
protagonist_indicators = ['主角', '宿主', '第一任', '第二任', ...]
is_protagonist = any(indicator in name for indicator in protagonist_indicators)

# ... 然后才提取括号前的纯中文名
```

### 修改后
```python
# 🔥 优先检查：直接通过带角色类型说明的名称
if '(' in name or '（' in name:
    # 1. 提取纯中文名部分和括号内容
    pure_chinese_name = name.split('(')[0].strip()
    bracket_content = name[name.find('(')+1:name.rfind(')')].strip()
    
    # 2. 检查括号内容是否包含角色类型关键词
    role_type_keywords = [
        '主角', '宿主', '第一任', '第二任', '第三任', 
        '女帝', '魔尊', '剑圣', '法王', '本体', '真身', ...
    ]
    
    # 3. 如果纯中文名长度合理(2-6字符)且包含角色类型说明，直接通过
    if 2 <= len(pure_chinese_name) <= 6 and has_role_type:
        return True
```

## 关键改进

1. **优先处理括号格式**：在所有其他检查之前，先处理带括号的名称格式
2. **智能提取**：从完整名称中提取纯中文名部分进行验证
3. **角色类型关键词**：检查括号内容是否包含合理的角色类型说明
4. **放宽长度限制**：允许完整名称最长20个字符（包含英文翻译等）

## 测试用例

现在以下格式的角色名称都应该通过验证：

| 角色名称 | 纯中文名 | 括号内容 | 预期结果 |
|---------|---------|---------|---------|
| 林苟 (第一任宿主) | 林苟 | 第一任宿主 | ✅ 通过 |
| 江清雪 (第二任宿主/女帝) | 江清雪 | 第二任宿主/女帝 | ✅ 通过 |
| 主宰 (本体无名，自命代号) | 主宰 | 本体无名，自命代号 | ✅ 通过 |
| 张三 | 张三 | - | ✅ 通过 |
| 李四 | 李四 | - | ✅ 通过 |

## 影响范围

- 文件：`src/managers/WorldStateManager.py`
- 方法：`_is_valid_character_name()`
- 影响：所有涉及角色添加的场景（角色设计、章节生成等）

## 相关文件

- [`src/managers/WorldStateManager.py`](../src/managers/WorldStateManager.py) - 主要修改文件
- [`src/core/QualityAssessor.py`](../src/core/QualityAssessor.py) - 调用验证逻辑的类