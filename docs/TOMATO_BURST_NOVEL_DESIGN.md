# 番茄爆款仿写系统设计方案

## 核心认知：什么是番茄爆款？

### 爆款公式（可复制的）
```
第1章：绝望开局 + 系统觉醒（压抑到极致→希望）
第2章：初试锋芒 + 小爽点（快速验证系统）
第3章：第一次打脸 + 震惊（小高潮）
第4-5章：收获 + 新期待
第6-10章：节奏循环（压制→打脸→收获→新目标）
...
每30章：一个大高潮（身份升级/大场面）
```

### 情绪节奏（必须精确控制）
```
章1：压抑(90%) → 震惊(10%)
章2：好奇(30%) → 爽快(70%)
章3：铺垫(20%) → 打脸(50%) → 震惊(30%)
章4：收获(40%) → 新目标(60%)
章尾：必须留下钩子（悬念/期待）
```

---

## 一、重新定义"上下文"

### 传统思路（错误）
记录所有细节：主角有什么、在哪、什么关系...
→ 信息爆炸，AI抓不住重点

### 爆款思路（正确）
只记录**影响下一章情绪节奏**的关键信息：

```python
BURST_CONTEXT = {
    # 1. 当前情绪位置（最重要！）
    "emotion_position": {
        "current_chapter": 5,
        "phase": "第一波打脸后",  # 情绪阶段
        "reader_emotion": "爽但不够满足",  # 读者当前情绪
        "next_need": "更大场面",  # 下一章需要给读者什么
    },
    
    # 2. 装逼打脸进度（核心驱动力）
    "face_slap_progress": {
        "last_slap_chapter": 3,  # 上次打脸在哪章
        "slap_intensity": 5,     # 上次强度1-10
        "next_slap_plan": {      # 下次打脸规划
            "chapter": 8,
            "target": "富二代张三",
            "scene": "高档餐厅",
            "intensity": 8,        # 必须比上次强
            "shock_level": "全市震惊"  # 震惊范围
        }
    },
    
    # 3. 收获进度（让读者有获得感）
    "reward_progress": {
        "last_reward_chapter": 5,
        "reward_type": "金钱+地位",
        "next_reward_plan": {
            "chapter": 10,
            "type": "身份升级",
            "detail": "被首富认作干儿子"
        }
    },
    
    # 4. 期待感管理（让读者追更）
    "expectations": [
        {"type": "身份揭秘", "target_chapter": 15, "hint": "主角到底是什么身份？"},
        {"type": "复仇", "target_chapter": 20, "hint": "前女友后悔的场面"},
        {"type": "大场面", "target_chapter": 30, "hint": "全国直播的神豪场面"}
    ],
    
    # 5. 关键数字（必须记住）
    "key_numbers": {
        "current_money": 5000000,    # 当前资产
        "system_level": 3,            # 系统等级
        "revenge_count": 1,           # 已打脸次数
        "shock_count": 2              # 已震惊次数
    }
}
```

---

## 二、章节生成Prompt（围绕情绪设计）

### System Prompt 结构
```python
BURST_SYSTEM_PROMPT = """【番茄爆款作家模式】

=== 目标 ===
写出让读者欲罢不能、疯狂追更的爆款网文。
核心指标：每章读完率>90%，章章有钩子。

=== 节奏铁律（必须遵守）===
【情绪曲线】
- 单章结构：铺垫(20%) → 冲突/高潮(60%) → 钩子(20%)
- 章间关系：上一章钩子 → 本章回应 → 新钩子
- 不能连续2章平淡，必须有爽点或期待

【爽点设计】
- 频率：每3-5章一次打脸
- 强度：必须递增（5→6→8→9→10）
- 范围：个人→周围→全场→全网→全国
- 公式：反派嘲讽 → 主角反击 → 身份曝光 → 众人震惊 → 反派后悔

【钩子类型】
1. 悬念钩子：主角的秘密即将暴露？
2. 期待钩子：更大的场面即将到来
3. 情绪钩子：读者想知道主角怎么反击
4. 收获钩子：主角即将获得什么

=== 当前状态 ===
【情绪位置】
- 上一章情绪：{last_emotion}
- 读者现在：{reader_state}
- 下一章需要：{next_need}

【打脸进度】
- 上次打脸：第{last_slap_chapter}章
- 强度：{last_intensity}/10
- 下次计划：第{next_slap_chapter}章，目标{next_slap_target}

【收获进度】
- 上次收获：{last_reward}
- 下次收获：第{next_reward_chapter}章，{next_reward_detail}

【关键数字】
- 主角当前：{protagonist_state}
- 系统等级：{system_level}
- 资产：{current_money}

【待回收期待】
{expectations}

=== 生成规则 ===
1. 【情绪连续】必须从"{last_emotion}"的状态开始
2. 【钩子回应】必须回应上一章的钩子（如果有）
3. 【新钩子】必须在章尾留下更强的钩子
4. 【爽点检查】如果本章是打脸章，强度必须达到{required_intensity}
5. 【数字准确】所有数字必须与当前状态一致，不能倒退
6. 【标签化】人物性格必须标签化（冷血/护短/霸气），不要复杂

=== 输出格式 ===
{format_json}
"""
```

### 输出JSON格式
```json
{
  "chapter_analysis": {
    "emotion_target": "让读者感到爽快但期待更大",  // 本章情绪目标
    "hook_response": "回应了上一章的XX悬念",      // 如何回应上一章钩子
    "new_hook": "主角即将参加拍卖会，会有多大手笔？", // 新钩子
    "slap_intensity": 6                              // 如果有打脸，强度多少
  },
  
  "chapter_title": "第X章 标题要有冲击力",
  "content": "正文内容...",
  
  "state_updates": {
    "emotion_position": {
      "phase": "第一波收获后",
      "reader_emotion": "满足但好奇",
      "next_need": "更大场面"
    },
    "key_numbers_updates": {
      "current_money": 10000000,  // 从500万变1000万
      "shock_count": 3
    }
  },
  
  "quality_check": {
    "has_slap": true,           // 是否有打脸
    "has_reward": true,         // 是否有收获
    "has_hook": true,           // 是否有钩子
    "intensity_reached": 6,     // 实际达到的强度
    "estimated_satisfaction": 8 // 预估读者满意度1-10
  }
}
```

---

## 三、会话管理策略（围绕情绪不断裂）

### 核心问题
会话切换时最大的风险：**情绪断裂**
→ 新会话不知道现在读者是什么情绪，可能写成平淡章

### 解决方案：情绪上下文优先

```python
class BurstContextManager:
    """爆款上下文管理器 - 情绪优先"""
    
    def build_context_for_session(self, chapter_num: int) -> str:
        """为新会话构建上下文（精简但关键）"""
        
        # 只取最近3章的情绪轨迹
        recent_emotions = self.get_recent_emotions(count=3)
        
        # 当前情绪位置
        current_emotion = self.get_current_emotion()
        
        # 下次爽点规划
        next_slap = self.get_next_face_slap_plan()
        
        # 关键数字（不能错）
        key_numbers = self.get_key_numbers()
        
        context = f"""【爆款节奏状态】

=== 情绪轨迹（最近3章）===
{format_emotion_trajectory(recent_emotions)}

=== 当前状态 ===
- 读者情绪：{current_emotion['reader_state']}
- 期待程度：{current_emotion['expectation_level']}/10
- 需要：{current_emotion['next_need']}

=== 下次爽点规划 ===
- 章节：第{next_slap['chapter']}章
- 目标：{next_slap['target']}
- 强度：{next_slap['intensity']}/10
- 震惊范围：{next_slap['shock_level']}

=== 关键数字（不能错）===
{format_key_numbers(key_numbers)}

=== 本章要求 ===
- 目标情绪：{self.get_target_emotion_for_chapter(chapter_num)}
- 是否爽点章：{"是" if next_slap['chapter'] == chapter_num else "否，铺垫"}
"""
        return context
```

### 会话切换流程
```python
async def switch_session_for_burst(self, next_chapter: int):
    """为爆款写作切换会话"""
    
    # 1. 加载静态产物
    static = self.load_static_products()
    
    # 2. 构建情绪上下文（关键！）
    burst_context = self.build_context_for_session(next_chapter)
    
    # 3. 构建System Prompt
    system_prompt = BURST_SYSTEM_PROMPT.format(
        writing_style=static['writing_style'],
        worldview=static['worldview'],
        burst_context=burst_context
    )
    
    # 4. 创建新会话
    session = self.api_client.create_conversation(
        system_prompt=system_prompt
    )
    
    # 5. 【可选】给1-2章示例（让AI理解节奏）
    recent_chapters = self.get_recent_chapters(count=2)
    for ch in recent_chapters:
        # 告诉AI：这是示例，学习节奏
        session.add_message("user", f"示例第{ch['num']}章：{ch['summary']}")
        session.add_message("assistant", f"明白了，本章节奏：{ch['emotion_curve']}")
    
    return session
```

---

## 四、质量控制检查点

### 每章生成后的自动检查
```python
def check_burst_quality(chapter_data: Dict, context: Dict) -> Dict:
    """检查是否符合爆款标准"""
    
    issues = []
    
    # 1. 情绪检查
    if not chapter_data['chapter_analysis']['has_hook']:
        issues.append("缺少钩子，读者不会追更")
    
    # 2. 爽点强度检查
    if context['next_chapter_is_slap']:
        actual = chapter_data['quality_check']['intensity_reached']
        required = context['required_intensity']
        if actual < required:
            issues.append(f"爽点强度不足：{actual} < {required}")
    
    # 3. 数字一致性检查
    if chapter_data['state_updates']['key_numbers']['current_money'] < context['current_money']:
        issues.append("主角资产倒退，违反逻辑")
    
    # 4. 平淡章检查
    if not chapter_data['quality_check']['has_slap'] and \
       not chapter_data['quality_check']['has_reward'] and \
       not chapter_data['quality_check']['has_hook']:
        issues.append("平淡章！必须有爽点、收获或钩子之一")
    
    # 5. 满意度预估
    if chapter_data['quality_check']['estimated_satisfaction'] < 6:
        issues.append("预估满意度低于6，需要优化")
    
    return {
        "passed": len(issues) == 0,
        "issues": issues,
        "score": calculate_burst_score(chapter_data)
    }
```

---

## 五、实施优先级

### P0（必须做）
1. **情绪轨迹追踪** - 记录每章的情绪变化
2. **爽点规划** - 提前规划3-5章后的打脸
3. **强度递增** - 确保打脸强度递增

### P1（重要）
4. **钩子检查** - 确保章章有钩子
5. **数字管理** - 主角状态不倒退
6. **期待感管理** - 埋伏笔和回收

### P2（优化）
7. **自动优化** - 质量低时自动重生成
8. **A/B测试** - 对比不同节奏的效果

---

## 六、关键Prompt技巧

### 让AI理解"爽感"
```
不要写："主角很生气"
要写："主角眼神冰冷，嘴角却勾起一抹弧度。熟悉他的人都知道，这是他暴怒前的征兆。"

不要写："大家都震惊了"
要写："全场死寂。下一秒，此起彼伏的抽气声如同海啸般席卷整个大厅。"
```

### 让AI理解"节奏"
```
铺垫不超过20%，快速进入冲突
打脸过程要详细（60%），读者爱看
震惊反应要写足（20%），爽感来源
```

---

这个方案的核心是：**忘掉复杂的设定管理，专注情绪节奏管理**。

番茄读者不在乎主角有多少技能，只在乎：
1. 这章爽不爽？
2. 下章期待吗？

所有设计围绕这两个问题。
