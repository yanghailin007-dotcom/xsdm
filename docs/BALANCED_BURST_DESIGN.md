# 番茄爆款仿写系统（平衡版）

## 核心原则

```
基础一致性（必须100%准确）
    ↓
动态状态（每章更新）
    ↓
情绪节奏（指导写作）
```

---

## 一、三层数据结构

### Layer 1: 核心设定（一成不变）
```python
CORE_IDENTITY = {
    # 主角（绝对不能变）
    "protagonist": {
        "name": "李明",                    # 姓名
        "age": 28,                         # 年龄
        "initial_identity": "外卖员",      # 初始身份
        "core_personality": ["隐忍", "护短", "不圣母"],  # 核心性格
        "appearance_tags": ["平凡长相", "坚毅眼神", "外卖服"]  # 外貌标签
    },
    
    # 重要配角（姓名+核心关系不变）
    "core_npcs": {
        "林雪": {
            "role": "女主",                # 身份
            "initial_relation": "陌生",     # 初始关系
            "core_trait": ["高冷", "善良"]  # 核心性格
        },
        "张少": {
            "role": "初期反派", 
            "identity": "富二代",
            "fate": "被反复打脸后下线"
        },
        "王管家": {
            "role": "管家", 
            "identity": "首富家忠仆",
            "relation_to_mc": "未来效忠"
        }
    },
    
    # 世界观锚点（不变）
    "world_anchors": {
        "current_year": 2024,
        "main_city": "东海市",
        "power_system": "金钱+地位",        # 神豪文
        "key_locations": ["城中村", "帝豪酒店", "拍卖行"]
    }
}
```

### Layer 2: 动态状态（每章准确更新）
```python
DYNAMIC_STATE = {
    "current_chapter": 25,
    
    # 主角当前状态（会变，但不能倒退）
    "protagonist_current": {
        "cultivation_level": "炼气期三层",  # 只能升不能降
        "current_wealth": 5000000,          # 只能增不能减
        "current_job": "待业→创业",         # 职业变化轨迹
        "current_location": "东海市→京城",   # 位置变化
        "known_identity": "隐藏",            # 身份暴露程度
        "love_interest_progress": 30         # 感情线进度
    },
    
    # NPC动态状态
    "npc_states": {
        "林雪": {
            "current_relation": "好感",       # 关系变化
            "current_location": "学校",
            "knows_mc_secret": False          # 是否知道主角秘密
        },
        "张少": {
            "status": "被击败住院",           # 当前状态
            "shame_level": 100,               # 羞耻值
            "revenge_plan": "找帮手"          # 后续行动
        }
    },
    
    # 关键数字（精确管理）
    "key_numbers": {
        "system_level": 3,
        "revenge_count": 5,                  # 打脸次数
        "shock_events": 3,                   # 震惊事件数
        "current_company": "李明集团"        # 当前势力
    },
    
    # 进行中事件
    "active_events": [
        {"name": "全国商业大赛", "progress": "初赛", "deadline_ch": 30},
        {"name": "身份揭秘危机", "progress": "酝酿", "deadline_ch": 35}
    ]
}
```

### Layer 3: 情绪节奏（写作指导）
```python
EMOTION_RHYTHM = {
    # 已发生的情绪轨迹
    "emotion_history": [
        {"ch": 1, "emotion": "压抑→希望", "intensity": 8},
        {"ch": 3, "emotion": "铺垫→打脸→爽", "intensity": 6},
        {"ch": 8, "emotion": "期待→震惊", "intensity": 8},
        {"ch": 15, "emotion": "铺垫→大高潮", "intensity": 9},
    ],
    
    # 下3章情绪规划
    "next_3_chapters": [
        {"ch": 26, "type": "收获", "target_emotion": "满足+期待"},
        {"ch": 27, "type": "铺垫", "target_emotion": "好奇+紧张"},
        {"ch": 28, "type": "打脸", "target_emotion": "爽快", "intensity": 8}
    ],
    
    # 爽点规划
    "slap_schedule": {
        28: {"target": "张少表哥", "intensity": 8, "scene": "拍卖会"},
        35: {"target": "商业对手", "intensity": 9, "scene": "全国直播"}
    }
}
```

---

## 二、System Prompt 设计（三层叠加）

```python
BALANCED_SYSTEM_PROMPT = """【番茄爆款作家 - 系统模式】

=== 第一层：核心设定（绝对准确）===
【主角】
- 姓名：{CORE_IDENTITY[protagonist][name]}
- 年龄：{CORE_IDENTITY[protagonist][age]}
- 外貌：{', '.join(CORE_IDENTITY[protagonist][appearance_tags])}
- 性格：{', '.join(CORE_IDENTITY[protagonist][core_personality])}
  ⚠️ 性格不能崩！不能圣母！不能怂！

【重要人物】（姓名、身份、关系不能错）
{format_core_npcs(CORE_IDENTITY[core_npcs])}

【世界观锚点】
- 时间：{CORE_IDENTITY[world_anchors][current_year]}
- 主舞台：{CORE_IDENTITY[world_anchors][main_city]}
- 力量体系：{CORE_IDENTITY[world_anchors][power_system]}

=== 第二层：当前状态（精准延续）===
【主角当前】（必须从这个状态开始写）
- 实力：{DYNAMIC_STATE[protagonist_current][cultivation_level]}
- 资产：{DYNAMIC_STATE[protagonist_current][current_wealth]:,}元
- 位置：{DYNAMIC_STATE[protagonist_current][current_location]}
- 身份暴露度：{DYNAMIC_STATE[protagonist_current][known_identity]}

【NPC当前状态】
{format_npc_states(DYNAMIC_STATE[npc_states])}

【关键数字】（不能错）
- 系统等级：Lv{DYNAMIC_STATE[key_numbers][system_level]}
- 打脸次数：{DYNAMIC_STATE[key_numbers][revenge_count]}次
- 震惊事件：{DYNAMIC_STATE[key_numbers][shock_events]}次

【进行中事件】（必须推进）
{format_active_events(DYNAMIC_STATE[active_events])}

=== 第三层：本章情绪目标 ===
【情绪定位】
- 本章类型：{EMOTION_RHYTHM[next_3_chapters][0][type]}
- 目标情绪：{EMOTION_RHYTHM[next_3_chapters][0][target_emotion]}
- 强度要求：{EMOTION_RHYTHM[next_3_chapters][0].get('intensity', '中等')}

【节奏要求】
- 铺垫：不能超过20%篇幅
- 冲突/高潮：60%篇幅，必须详细
- 钩子：章尾必须留悬念或期待

【爽点检查】
{format_slap_check(EMOTION_RHYTHM[next_3_chapters][0])}

=== 输出要求 ===
1. 主角名字必须是"{CORE_IDENTITY[protagonist][name]}"，不能变
2. 人物关系必须符合"第二层"的当前状态
3. 所有数字必须符合"第二层"，不能倒退
4. 情绪必须符合"第三层"的目标
5. 章尾必须有钩子

=== 输出JSON ===
{{
  "consistency_check": {{  // 一致性自检
    "protagonist_name_correct": true,
    "npc_names_correct": true,
    "numbers_consistent": true,
    "relations_correct": true
  }},
  "chapter_title": "第X章 标题",
  "content": "正文",
  "state_updates": {{       // 本章后的新状态
    "protagonist": {{...}},
    "npcs": {{...}},
    "key_numbers": {{...}}
  }},
  "emotion_result": {{      // 实际达成的情绪
    "actual_emotion": "...",
    "intensity": 8,
    "hook": "章尾钩子内容"
  }}
}}
"""
```

---

## 三、会话切换策略（保持连续性）

### 切换时保留的信息
```python
def build_session_switch_context(novel_title: str, next_chapter: int) -> Dict:
    """构建会话切换时的上下文"""
    
    # 1. 核心设定（完整加载）
    core = load_core_identity(novel_title)
    
    # 2. 最新动态状态（完整加载）
    dynamic = load_dynamic_state(novel_title)
    
    # 3. 最近2章摘要（快速回顾）
    recent_summaries = get_recent_summaries(novel_title, count=2)
    
    # 4. 下3章情绪规划（指导写作）
    rhythm = get_emotion_rhythm(novel_title)
    
    return {
        "core_identity": core,           # 完整核心设定
        "dynamic_state": dynamic,        # 完整当前状态
        "recent_summaries": recent_summaries,  # 最近2章发生了什么
        "emotion_plan": rhythm["next_3_chapters"]  # 接下来怎么写
    }
```

### 切换后的System Prompt
```python
SESSION_SWITCH_PROMPT = """【会话切换 - 上下文恢复】

【你正在续写长篇小说，上一会话已满，这是新的会话】

=== 绝对不能变的信息 ===
主角姓名：{core_identity[protagonist][name]}
重要人物：{format_npc_list(core_identity[core_npcs])}
世界观：{core_identity[world_anchors][main_city]}, {core_identity[world_anchors][current_year]}

=== 当前准确状态（从上一章结束开始写）===
主角：{dynamic_state[protagonist_current][cultivation_level]}, 
      资产{dynamic_state[protagonist_current][current_wealth]},
      在{dynamic_state[protagonist_current][current_location]}

NPC状态：
{format_npc_states(dynamic_state[npc_states])}

=== 最近发生了什么 ===
{format_summaries(recent_summaries)}

=== 接下来要写什么 ===
第{next_chapter}章规划：
- 类型：{emotion_plan[0][type]}
- 情绪目标：{emotion_plan[0][target_emotion]}
- 如果是打脸章，目标：{emotion_plan[0].get('target', '无')}

【重要】
1. 人物姓名绝对不能错
2. 主角状态必须从"当前准确状态"开始
3. 按照"接下来要写什么"的节奏写
"""
```

---

## 四、状态更新机制（每章后）

### 自动更新流程
```python
async def update_after_chapter(chapter_data: Dict, novel_title: str):
    """每章生成后更新状态"""
    
    state_updates = chapter_data.get('state_updates', {})
    
    # 1. 验证更新合法性（不能倒退）
    validation = validate_state_updates(state_updates, current_state)
    if not validation['valid']:
        raise ValueError(f"状态更新非法: {validation['errors']}")
    
    # 2. 更新主角状态
    update_protagonist_state(state_updates.get('protagonist', {}))
    
    # 3. 更新NPC状态
    update_npc_states(state_updates.get('npcs', {}))
    
    # 4. 更新关键数字
    update_key_numbers(state_updates.get('key_numbers', {}))
    
    # 5. 更新情绪历史
    record_emotion_result(chapter_data['emotion_result'])
    
    # 6. 保存状态
    save_dynamic_state(novel_title)
    
    # 7. 保存章节（含快照）
    save_chapter_with_snapshot(chapter_data, novel_title)
```

### 验证规则
```python
def validate_state_updates(updates: Dict, current: Dict) -> Dict:
    """验证状态更新是否合法"""
    errors = []
    
    # 规则1：系统等级只能升不能降
    if updates.get('system_level', current['system_level']) < current['system_level']:
        errors.append("系统等级不能下降")
    
    # 规则2：资产只能增不能减（除非有特殊剧情）
    if updates.get('current_wealth', current['current_wealth']) < current['current_wealth']:
        errors.append("主角资产不能无故减少")
    
    # 规则3：姓名不能变
    if updates.get('name') and updates['name'] != current['name']:
        errors.append("主角姓名不能改变")
    
    # 规则4：已死NPC不能复活
    for npc_name, npc_state in updates.get('npcs', {}).items():
        if current['npcs'].get(npc_name, {}).get('status') == '死亡' \
           and npc_state.get('status') != '死亡':
            errors.append(f"NPC {npc_name} 已死亡，不能复活")
    
    return {"valid": len(errors) == 0, "errors": errors}
```

---

## 五、存储结构

```
小说项目/
└── {novel_title}/
    ├── core_identity.json           # 核心设定（不变）
    ├── dynamic_state.json           # 动态状态（每章更新）
    ├── emotion_rhythm.json          # 情绪节奏规划
    ├── chapters/
    │   ├── chapter_001.json
    │   │   ├── content              # 正文
    │   │   ├── state_snapshot       # 该章结束后的状态
    │   │   └── summary              # 摘要
    │   └── ...
    └── sessions/                    # 会话历史
        └── session_001_final_state.json
```

---

## 六、关键检查点（每章必检）

### 一致性检查
- [ ] 主角姓名正确
- [ ] 重要配角姓名正确
- [ ] 人物关系符合当前状态
- [ ] 数字不倒退（等级、资产等）

### 节奏检查
- [ ] 章尾有钩子
- [ ] 爽点章强度达标
- [ ] 情绪符合规划
- [ ] 铺垫不过长

### 逻辑检查
- [ ] 已死NPC没复活
- [ ] 已知秘密的人没失忆
- [ ] 主角性格没崩

这个方案的核心：**基础设定100%准，动态状态精确管，情绪节奏灵活调**。
