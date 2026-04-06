# 续写、重新规划与重写功能对比分析

## 一、功能概述

### 1. 续写 (Continue Chapters)
```
用途：在已有内容基础上继续生成后续章节
触发：用户已生成部分章节，需要继续写下去
API: POST /api/market-driven/{title}/continue-chapters
```

**特点：**
- ✅ 保留所有已有章节
- ✅ 不改变任何设定（世界观、角色、金手指）
- ✅ 基于现有 blueprint 继续生成
- ✅ 生成指定范围的新章节

**适用场景：**
- 写到第50章，需要继续生成第51-60章
- 保持原有故事线和人物设定不变

---

### 2. 重新规划 (Replan)
```
用途：基于新设定重新生成创作方案，但不删除已有章节
触发：想要调整后续故事方向，但保留已有内容
API: POST /api/market-driven/{title}/replan
```

**特点：**
- ✅ 保留所有已有章节（不删除）
- ✅ 基于新设定重新生成 blueprint
- ✅ 后续新生成的章节会使用新设定
- ⚠️ 可能造成前后设定不一致

**适用场景：**
- 发现后续方向需要调整，但不想重写已有内容
- 想要改变主角的发展路线或金手指升级方式
- 测试不同的故事走向

---

### 3. 重写 (Rewrite)
```
用途：彻底重新开始，删除所有已有章节，基于新设定重新生成
触发：对现有内容不满意，想要完全重新开始
API: POST /api/market-driven/{title}/rewrite
```

**特点：**
- ❌ 删除所有已有章节（清空 chapters 目录）
- ❌ 清空项目章节索引
- ✅ 基于新设定重新生成完整方案
- ✅ 从第1章开始重新生成

**适用场景：**
- 对整体方向完全不满意
- 想要彻底改变题材或核心设定
- 从头开始重新创作

---

## 二、核心差异对比表

| 维度 | 续写 | 重新规划 | 重写 |
|------|------|----------|------|
| **已有章节** | 保留 | 保留 | ❌ 删除 |
| **已有设定** | 保留 | ❌ 更新 | ❌ 更新 |
| **blueprint** | 使用现有 | 重新生成 | 重新生成 |
| **起点** | 从 last_chapter+1 开始 | 保持当前进度 | 从第1章开始 |
| **一致性** | 完全一致 | 可能断裂 | 完全一致（新） |
| **点数消耗** | 10点/章 | 50点 | 100点 |
| **风险** | 低 | ⚠️ 中（设定冲突） | 高（丢失已有内容） |

---

## 三、数据流对比

### 续写流程
```
用户已有: chapters 1-50 + blueprint_v1
           ↓
调用 continue-chapters(start=51, end=60)
           ↓
使用 blueprint_v1 继续生成
           ↓
结果: chapters 1-60 + blueprint_v1 (不变)
```

### 重新规划流程
```
用户已有: chapters 1-50 + blueprint_v1
           ↓
调用 replan(new_settings)
           ↓
生成 blueprint_v2 (基于新设定)
           ↓
结果: chapters 1-50 + blueprint_v2
      ⚠️ 第51章起使用 blueprint_v2 生成
      ⚠️ 可能出现设定冲突
```

### 重写流程
```
用户已有: chapters 1-50 + blueprint_v1
           ↓
调用 rewrite(new_settings)
           ↓
❌ 删除 chapters 1-50
❌ 清空章节索引
生成 blueprint_v2
从第1章开始重新生成
           ↓
结果: chapters 1-60 (新) + blueprint_v2
```

---

## 四、潜在问题与风险

### 1. 续写功能的潜在问题

#### 问题1: Blueprint 格式兼容性
```python
# 续写时使用的 blueprint 可能来自不同生成路径
# - 市场导向模式生成的 blueprint
# - 自由创意模式生成的 blueprint  
# - 手动创建的 blueprint

# 如果 blueprint 缺少关键字段，可能导致生成失败
缺失字段风险:
- tropes (套路数据)
- stage_goals (阶段目标)
- emotion_curve (情绪曲线)
- character_design (角色设计)
```

#### 问题2: 上下文断层
```
问题：续写时如何获取前N章的内容作为上下文？

当前实现：从 blueprint 获取设定
潜在问题：
- 如果不读取实际章节内容，模型不知道前面具体写了什么
- 可能导致人物对话风格不一致
- 剧情细节可能接不上

建议改进：
- 续写前读取 last_chapter, last_chapter-1, last_chapter-2 的内容
- 将前3章内容作为 context 传给生成器
```

#### 问题3: 批次间的连贯性
```
问题：续写大批量章节时（如51-100章），分多个批次生成

批次1: 生成 51-56 章
批次2: 生成 57-62 章（基于 blueprint，但不知道51-56的具体内容）

风险：
- 批次2不知道批次1的具体剧情发展
- 可能导致剧情跳跃或重复

建议改进：
- 每个新批次开始前，读取上一批次的最后几章作为上下文
```

### 2. 重新规划的风险

#### 风险1: 设定冲突
```
场景：
- 前50章：主角是普通人，通过努力变强
- replan 后：主角设定改为重生者，带着记忆

问题：
- 第51章提到"前世记忆"，但前50章完全没有铺垫
- 读者会感到突兀
- 前后逻辑不一致
```

#### 风险2: 角色性格突变
```
场景：
- 前50章：女主角温柔善良
- replan 后：改为高冷御姐

问题：
- 人物性格不连贯
- 读者难以代入
```

### 3. 重写的风险

#### 风险1: 数据丢失
```
- 删除操作不可逆
- 如果没有备份，原有内容永久丢失
- 用户可能误操作

建议：
- 重写前自动创建备份
- 添加确认对话框
- 保留最近3个版本的备份
```

---

## 五、改进建议

### 1. 续写功能改进

```python
# 改进1: 增强上下文获取
def _get_chapter_context(project_path, chapter_num, context_size=3):
    """获取前N章的内容作为上下文"""
    context_chapters = []
    for i in range(max(1, chapter_num - context_size), chapter_num):
        chapter_file = project_path / "chapters" / f"chapter_{i:03d}.json"
        if chapter_file.exists():
            with open(chapter_file, 'r', encoding='utf-8') as f:
                chapter_data = json.load(f)
                context_chapters.append({
                    'chapter_num': i,
                    'title': chapter_data.get('title', ''),
                    'content_preview': chapter_data.get('content', '')[:500] + '...'
                })
    return context_chapters

# 改进2: 批次间传递上下文
def generate_batch_with_context(...):
    # 如果不是第一批，读取上一批的最后几章
    if start_chapter > initial_start_chapter:
        previous_context = _get_last_batch_chapters(project_path, start_chapter - 1)
        novel_data['previous_batch_context'] = previous_context
```

### 2. 重新规划功能改进

```python
# 改进: 设定变更检测与警告
def detect_setting_conflicts(old_blueprint, new_blueprint):
    """检测设定变更可能导致的冲突"""
    conflicts = []
    
    # 检查主角设定变化
    old_protagonist = old_blueprint.get('protagonist', {})
    new_protagonist = new_blueprint.get('protagonist', {})
    if old_protagonist.get('name') != new_protagonist.get('name'):
        conflicts.append("主角姓名变更")
    if old_protagonist.get('identity') != new_protagonist.get('identity'):
        conflicts.append("主角身份变更")
    
    # 检查金手指变化
    old_gf = old_blueprint.get('golden_finger', {})
    new_gf = new_blueprint.get('golden_finger', {})
    if old_gf.get('type') != new_gf.get('type'):
        conflicts.append("金手指类型变更")
    
    return conflicts

# 在用户调用 replan 前显示警告
if conflicts:
    return {
        "warning": "检测到以下设定变更，可能导致前后不一致",
        "conflicts": conflicts,
        "suggestion": "建议使用'重写'功能，或仔细评估变更影响"
    }
```

### 3. 重写功能改进

```python
# 改进: 自动备份
def _create_backup_before_rewrite(project_path, title):
    """重写前自动创建备份"""
    backup_dir = project_path / "backups" / f"rewrite_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    backup_dir.mkdir(parents=True, exist_ok=True)
    
    # 备份 chapters 目录
    chapters_dir = project_path / "chapters"
    if chapters_dir.exists():
        import shutil
        shutil.copytree(chapters_dir, backup_dir / "chapters")
    
    # 备份 project_info.json
    project_info_file = project_path / "project_info.json"
    if project_info_file.exists():
        shutil.copy2(project_info_file, backup_dir / "project_info.json")
    
    # 备份 blueprint
    blueprint_paths = [
        project_path / "phase_one_products" / "完整方案.json",
        project_path / "blueprint.json"
    ]
    for bp_path in blueprint_paths:
        if bp_path.exists():
            shutil.copy2(bp_path, backup_dir / bp_path.name)
    
    return backup_dir
```

---

## 六、用户使用指南

### 什么时候用续写？
✅ 现有内容满意，只需要继续写下去  
✅ 保持原有设定和故事线  
✅ 自然地延续已有剧情

### 什么时候用重新规划？
⚠️ 想要微调后续故事走向  
⚠️ 可以接受轻微的不一致性  
⚠️ 不想丢失已有内容

### 什么时候用重写？
❌ 对整体方向完全不满意  
❌ 愿意放弃已有内容从头开始  
❌ 需要彻底改变题材或核心设定

---

## 七、总结

| 功能 | 一句话说明 | 主要风险 |
|------|------------|----------|
| **续写** | 继续写下去 | 上下文断层、批次间不连贯 |
| **重新规划** | 改设定但不重写 | 前后设定冲突、角色性格突变 |
| **重写** | 完全重新开始 | 数据丢失、投入成本浪费 |

**建议优先级**：续写 > 重新规划 > 重写  
**数据安全第一**：重写前务必确认已备份重要内容
