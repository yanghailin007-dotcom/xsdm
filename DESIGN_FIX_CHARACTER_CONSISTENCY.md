# 角色一致性保障设计方案

## 问题根因

1. **会话隔离**：每批10章创建新的 `ChapterConversationGenerator`，`novel_data` 传递不完整
2. **缺乏强制约束**：System Prompt 中没有不可违背的角色设定
3. **无内容校验**：生成后没有检查主角名是否正确
4. **状态不持久**：批次间没有共享角色状态

---

## 解决方案（四层防护）

### 第一层：System Prompt 强制注入（不可违背）

```python
def _build_system_prompt(self, start_chapter: int) -> str:
    """构建系统提示词 - 强制角色设定"""
    
    # 获取主角名（多层回退）
    protagonist_name = self._get_enforced_protagonist_name()
    
    base_prompt = optimizer.build_system_prompt()
    
    # 添加不可违背的角色设定
    enforcement = f"""
【角色设定 - 绝对不可更改】
主角姓名：{protagonist_name}
注意：
1. 必须使用此名字，禁止编造其他名字
2. 禁止出现"林枫""林霄"等其他名字
3. 每章正文开头必须包含主角名字至少一次
4. 如果忘记主角名，请回顾本章提示词

【违反惩罚】
如果生成内容使用了错误的主角名，视为严重错误，必须重新生成。
"""
    
    return enforcement + "\n\n" + base_prompt
```

### 第二层：每章提示词重复提醒

```python
def _build_chapter_prompt(self, chapter_num, ...):
    """构建章节提示词 - 强化角色提醒"""
    
    protagonist_name = self._get_enforced_protagonist_name()
    
    # 在提示词开头强制提醒
    reminder = f"""
【重要提醒 - 第{chapter_num}章】
主角名：{protagonist_name}（严格使用此名字）
前文主角：{protagonist_name}
本章主角：{protagonist_name}
禁止使用的名字：林枫、林霄、XXX、主角、他

"""
    
    chapter_prompt = optimizer.build_chapter_prompt(...)
    return reminder + chapter_prompt
```

### 第三层：内容生成后校验（自动修正）

```python
def _validate_and_fix_content(self, content: str, chapter_num: int) -> str:
    """校验并修复内容中的角色名"""
    
    protagonist_name = self._get_enforced_protagonist_name()
    
    # 检测错误名字
    wrong_names = ['林枫', '林霄', '林雷', '陆风']  # 常见错误
    fixes = []
    
    for wrong_name in wrong_names:
        if wrong_name in content:
            count = content.count(wrong_name)
            content = content.replace(wrong_name, protagonist_name)
            fixes.append(f"{wrong_name}→{protagonist_name}({count}处)")
    
    if fixes:
        logger.warning(f"[第{chapter_num}章] 自动修复角色名: {', '.join(fixes)}")
    
    # 检测是否完全没有主角名（可能用了"他"或"主角"）
    if protagonist_name not in content:
        logger.error(f"[第{chapter_num}章] 严重错误：正文完全没有主角名'{protagonist_name}'！")
        raise ValueError(f"第{chapter_num}章缺少主角名，需要重新生成")
    
    return content
```

### 第四层：状态持久化（跨批次共享）

```python
class CharacterStateManager:
    """角色状态管理器 - 跨批次保持设定"""
    
    def __init__(self, project_path: str):
        self.state_file = Path(project_path) / ".character_state.json"
    
    def save_state(self, state: dict):
        """保存角色状态"""
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    
    def load_state(self) -> dict:
        """加载角色状态"""
        if self.state_file.exists():
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def get_protagonist_name(self) -> str:
        """获取持久化的主角名"""
        state = self.load_state()
        return state.get('protagonist_name', '')

# 在 BatchChapterGenerator 中使用
class BatchChapterGenerator:
    def __init__(self, ..., project_path: str = None):
        ...
        self.state_manager = CharacterStateManager(project_path) if project_path else None
    
    def generate_batch(self, ..., novel_data: Dict):
        # 从状态管理器恢复主角名
        if self.state_manager:
            saved_name = self.state_manager.get_protagonist_name()
            if saved_name:
                novel_data['user_choices'] = novel_data.get('user_choices', {})
                novel_data['user_choices']['protagonist_name'] = saved_name
                logger.info(f"[BatchGenerator] 从状态恢复主角名: {saved_name}")
            else:
                # 第一次生成，保存主角名
                current_name = novel_data.get('user_choices', {}).get('protagonist_name', '')
                if current_name:
                    self.state_manager.save_state({
                        'protagonist_name': current_name,
                        'saved_at': datetime.now().isoformat()
                    })
```

---

## 实施方案

### 立即实施（代码修复）

1. **修改 `chapter_conversation_generator.py`**
   - 添加 `_get_enforced_protagonist_name()` 方法
   - 修改 `_build_system_prompt()` 添加强制设定
   - 修改 `_build_chapter_prompt()` 添加每章提醒
   - 添加 `_validate_and_fix_content()` 校验

2. **修改 `batch_chapter_generator.py`**
   - 集成 `CharacterStateManager`
   - 批次间持久化角色状态

### 中期优化（流程改进）

3. **添加角色名冲突检测**
   ```python
   # 在生成前检查 character_design 和 user_choices 是否一致
   def validate_character_consistency(novel_data: dict) -> bool:
       char_design_name = novel_data.get('character_design', {}).get('protagonist', {}).get('name', '')
       user_choice_name = novel_data.get('user_choices', {}).get('protagonist_name', '')
       
       if char_design_name and user_choice_name and char_design_name != user_choice_name:
           logger.error(f"角色名不一致！character_design: {char_design_name}, user_choices: {user_choice_name}")
           return False
       return True
   ```

4. **AI自检增加角色名检查**
   ```
   【AI自检报告】
   ...
   角色名检查：主角名是否一致？是/否
   如果否，列出使用的错误名字
   ```

---

## 预期效果

| 问题 | 修复前 | 修复后 |
|------|--------|--------|
| 主角名混乱 | 每批可能不同 | 全篇统一 |
| 反派名混乱 | 随意编造 | 按设定使用 |
| 发现时机 | 生成后人工发现 | 自动生成时校验 |
| 修复成本 | 批量替换 | 实时纠正 |

---

## 已修复的文件总结

1. ✅ `market_driven_api.py` - 添加 `user_choices` 传递
2. ✅ `chapter_conversation_generator.py` - 添加主角设定提醒
3. ✅ `chapter_conversation_generator.py` - 添加自检报告检测
4. ✅ `batch_chapter_generator.py` - 减小批次（10→6章）
5. ✅ `fix_character_names.py` - 批量修复已有章节
