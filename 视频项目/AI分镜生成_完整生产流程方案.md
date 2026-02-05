# AI分镜生成完整生产流程方案
## 从创意到Veo提示词的全流程设计

---

## 一、现状分析与优化目标

### 1.1 现有流程诊断

**你目前的流程**（推测）：
```
创意输入 → [Gemini单次调用] → 完整分镜JSON → Veo生成
```

**存在问题**：
| 问题 | 影响 | 优先级 |
|------|------|--------|
| 单次生成长JSON易出错 | 格式混乱、字段缺失 | 🔴 高 |
| Veo提示词含禁用词 | 生成质量差 | 🔴 高 |
| 无中间检查点 | 错误累积到后期难改 | 🟡 中 |
| 情绪曲线不可控 | 场景间跳跃突兀 | 🟡 中 |

### 1.2 优化目标

**核心原则**：
- **渐进式优化**：不推倒重来，在现有流程上增加质量控制
- **人机协作**：AI生成 + 人工审核关键节点
- **分层控制**：故事 → 场景 → 镜头，逐级细化

---

## 二、优化后的完整流程

### 2.1 流程总览

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           生产流程总览                                   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Step 0: 创意输入                                                        │
│  ├── 项目名称、总时长、风格标签                                          │
│  ├── 一句话故事、核心钩子                                                │
│  └── 角色设定（名称、身份、特征）                                        │
│                              ↓                                          │
│  Step 1: AI生成故事节拍 【Gemini调用 1】                                  │
│  ├── 输出：10个场景的叙事框架                                            │
│  ├── 包含：场景标题、叙事目的、情绪曲线、对白                            │
│  └── 不包含：具体镜头、Veo提示词                                         │
│                              ↓                                          │
│  Step 2: 人工审核场景设计 【关键控制点】                                  │
│  ├── 修改场景标题和叙事目的                                              │
│  ├── 调整情绪曲线和时长分配                                              │
│  └── 优化对白文案                                                        │
│                              ↓                                          │
│  Step 3: AI生成分镜细节 【Gemini调用 2】                                  │
│  ├── 按场景逐个生成（10次调用）                                          │
│  ├── 输出：具体镜头 + Veo提示词                                          │
│  └── 自动质检：禁用词检查、长度检查                                      │
│                              ↓                                          │
│  Step 4: 人工审核分镜                                                    │
│  ├── 编辑单个镜头的Veo提示词                                             │
│  ├── 重新生成不合格镜头                                                  │
│  └── 确认导出                                                            │
│                              ↓                                          │
│  Step 5: 导出与使用                                                      │
│  ├── 导出完整JSON                                                        │
│  ├── 导出Excel（供人工阅读）                                             │
│  └── 复制Veo提示词开始视频生成                                           │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.2 流程优化对比

| 维度 | 原流程 | 新流程 | 改进点 |
|------|--------|--------|--------|
| Gemini调用次数 | 1次 | 1次(节拍) + 10次(分镜) | 分层生成，质量更高 |
| 人工干预点 | 0个 | 2个(场景审核+分镜审核) | 关键节点可控 |
| 错误发现时机 | 生成后 | 生成中 | 早发现早修复 |
| Veo提示词质量 | 不稳定 | 结构化，稳定 | 禁用词检查 |

---

## 三、五步骤详细设计

### Step 0: 创意输入页面

**页面功能**：项目基础信息录入

**输入字段**：
```json
{
  "project_name": "凡人慕佩灵的修仙之路 第1集",
  "total_duration": 80,
  "style_tags": ["修仙", "女性向", "热血", "成长"],
  "concept": {
    "logline": "资质平庸的女修为了追上韩立，以命为赌注凝结金丹",
    "hook": "当所有人都说她不可能成功，她却用命赌一个奇迹",
    "theme": "平凡者的逆袭，不甘平庸的抗争"
  },
  "characters": [
    {
      "name": "慕佩灵",
      "role": "主角",
      "identity": "韩立名义道侣，结丹后期",
      "traits": ["坚韧", "不甘平庸", "深情", "责任感强"],
      "visual": "青色道袍，眼神坚定，气质温婉但内里刚强",
      "arc": "从被动承受者到主动守护者"
    },
    {
      "name": "程宣",
      "role": "配角",
      "identity": "韩立弟子",
      "traits": ["忠诚", "慌张", "年轻"],
      "function": "喜剧担当，衬托主角"
    }
  ]
}
```

**输出**：保存为 `project_config.json`

---

### Step 1: AI生成故事节拍

**调用方式**：Gemini API 单次调用

**Prompt模板**：
```markdown
你是一个专业的短剧编剧。请根据以下项目信息，生成{{TOTAL_DURATION}}秒的故事节拍(Story Beats)。

## 项目信息
项目名称：{{PROJECT_NAME}}
总时长：{{TOTAL_DURATION}}秒
风格：{{STYLE_TAGS}}
核心创意：{{CONCEPT_LOGLINE}}
主题：{{CONCEPT_THEME}}
角色设定：
{{CHARACTERS}}

## 生成要求

### 1. 三幕结构分配
- 第一幕「建立」(占30%)：约{{TOTAL_DURATION * 0.3}}秒
  - 任务：建立世界观、人物关系、核心矛盾
- 第二幕「对抗」(占40%)：约{{TOTAL_DURATION * 0.4}}秒
  - 任务：冲突升级、情感转折、内心挣扎
- 第三幕「高潮」(占30%)：约{{TOTAL_DURATION * 0.3}}秒
  - 任务：决战时刻、人物觉醒、悬念收尾

### 2. 每个节拍的字段
```json
{
  "scene_number": 1,
  "scene_title_cn": "中文场景标题",
  "scene_title_en": "English Scene Title",
  "story_beat_cn": "中文叙事目的",
  "story_beat_en": "English Story Purpose",
  "emotional_arc": "情绪曲线，如：决绝→紧张→痛苦→希望",
  "duration_seconds": 8,
  "key_moment": "关键瞬间描述",
  "dialogues": [
    {
      "timestamp": 0,
      "speaker": "角色名",
      "lines_cn": "中文台词",
      "lines_en": "English lines",
      "tone_cn": "语气描述",
      "tone_en": "Tone description"
    }
  ]
}
```

### 3. 规则约束
- 总时长必须严格等于{{TOTAL_DURATION}}秒
- 场景数量建议在8-12个之间
- 每个场景必须有对白
- 对白要体现角色性格
- 情绪曲线要有变化，避免平铺直叙

### 4. 禁止事项
- 不要生成镜头细节（景别、运镜等）
- 不要生成Veo提示词
- 不要输出任何解释文字，只输出JSON

## 输出格式
只输出JSON数组，格式如下：
```json
{
  "beats": [
    {
      "scene_number": 1,
      "scene_title_cn": "...",
      ...
    }
  ]
}
```
```

**输出示例**：
```json
{
  "beats": [
    {
      "scene_number": 1,
      "scene_title_cn": "法阵禁锢",
      "scene_title_en": "Array Imprisonment",
      "story_beat_cn": "建立突破场景，展示慕佩灵以命赌局的决心",
      "story_beat_en": "Establish breakthrough scene, show Mu Peiling's determination to risk her life",
      "emotional_arc": "决绝→紧张",
      "duration_seconds": 8,
      "key_moment": "慕佩灵启动阵法，准备突破",
      "dialogues": [
        {
          "timestamp": 0,
          "speaker": "慕佩灵",
          "lines_cn": "若不赌这一次，我将永远只是韩前辈的拖累。",
          "lines_en": "If I don't risk it all this time, I'll forever be a burden to Senior Han.",
          "tone_cn": "内心独白，决绝",
          "tone_en": "Inner monologue, determined"
        }
      ]
    }
  ]
}
```

**输出**：保存为 `step1_beats.json`

---

### Step 2: 人工审核场景设计

**页面功能**：可视化编辑场景信息

**界面布局**：
```
┌─────────────────────────────────────────────────────────┐
│  Step 2: 场景设计审核                    总时长: 80/80秒  │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 场景 1/10                    [删除] [↓添加场景]  │   │
│  ├─────────────────────────────────────────────────┤   │
│  │ 场景标题: [法阵禁锢                      ] ✏️   │   │
│  │ 英文标题: [Array Imprisonment            ] ✏️   │   │
│  │                                                  │   │
│  │ 时长: [8] 秒                    位置: 0-8秒      │   │
│  │                                                  │   │
│  │ 叙事目的:                                        │   │
│  │ [建立突破场景，展示慕佩灵以命赌局的决心  ] ✏️   │   │
│  │                                                  │   │
│  │ 情绪曲线: 决绝 ────→ 紧张                        │   │
│  │            0s        8s                          │   │
│  │                                                  │   │
│  │ 对白:                                           │   │
│  │ 慕佩灵 (0s):                                     │   │
│  │ "若不赌这一次，我将永远只是韩前辈的拖累。"       │   │
│  │ 语气: 内心独白，决绝                            │   │
│  │ [编辑] [添加对白]                                │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 场景 2/10...                                     │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  [⬅️ 上一步]  [💾 保存草稿]  [✅ 确认并生成分镜 ➡️]       │
└─────────────────────────────────────────────────────────┘
```

**审核要点**：
1. **叙事连贯性**：场景之间逻辑是否通顺
2. **情绪曲线**：整体是否有起伏（避免一直高潮或一直平淡）
3. **对白质量**：是否符合角色性格，是否有记忆点
4. **时长分配**：关键场景时长是否足够

**输出**：保存为 `step2_scene_designs.json`

---

### Step 3: AI生成分镜细节

**调用方式**：Gemini API，**按场景逐个调用**（10个场景 = 10次调用）

**Why逐个调用？**
- 减少单次生成长度，降低出错率
- 单个场景失败可单独重试
- 支持并行生成（多线程）

**Prompt模板**：
```markdown
你是一个专业的AI视频分镜工程师。请根据以下场景设计，生成具体的分镜脚本。

## 场景设计输入
```json
{{SCENE_DESIGN_JSON}}
```

## 生成要求

### 1. 镜头数量计算
镜头数 = 场景时长(秒) / 4，向上取整，最少2个
本场景时长{{DURATION}}秒，应生成{{SHOTS_COUNT}}个镜头

### 2. 景别分配规则
- 场景第1个镜头：远景/全景（建立环境）
- 场景中间镜头：中景（叙事主体）
- 场景最后1个镜头：特写（情绪高潮）
- 特写镜头占比至少40%

### 3. Veo提示词规则（严格遵守）

**结构**：
Subject(主体) + Action(动作) + Environment(环境) + Lighting(光影) + Camera(运镜)

**禁用词（绝对不能用）**：
cinematic, epic, masterpiece, 4K, unreal engine, photorealistic, highly detailed, movie quality, stunning, gorgeous, breathtaking

**长度**：80-120个英文单词

**动作描述要求**：
- 必须带副词描述动作方式
- ✅ slowly pushing in, frustratedly brushing, intensely staring
- ❌ push in, brush hair, stare

**光影描述要求**：
- 必须具体，避免抽象
- ✅ golden morning sunlight, blue rim light, torchlight flickering
- ❌ beautiful lighting, dramatic light

**示例**：
```
Elegant female cultivator in flowing cyan silk Hanfu, slumped over ancient stone desk covered with glowing jade message tokens, frustratedly brushing hair from face with ink-stained fingers, soft morning light streaming through cave lattice window, floating spiritual runes drifting in air around her, camera slowly pushing in as she sighs
```

### 4. 输出格式
```json
{
  "scene_number": {{SCENE_NUMBER}},
  "scene_title_cn": "{{SCENE_TITLE_CN}}",
  "scene_title_en": "{{SCENE_TITLE_EN}}",
  "shots": [
    {
      "shot_number": "1A",
      "shot_type_cn": "全景",
      "shot_type_en": "Wide Shot",
      "duration": 4,
      "veo_prompt": "英文提示词，80-120词",
      "visual_cn": "中文视觉描述",
      "visual_en": "English visual description",
      "camera_movement": "slowly pushing in",
      "action_notes": "表演/动作指导"
    }
  ]
}
```

### 5. 自检清单
生成后请自检：
- [ ] veo_prompt单词数在80-120之间
- [ ] veo_prompt不含任何禁用词
- [ ] 包含至少1个特写镜头
- [ ] 镜头时长总和等于场景时长
- [ ] camera_movement描述具体

只输出JSON，不要解释。
```

**并行生成策略**：
```python
# 伪代码
import concurrent.futures

def generate_scene_shots(scene_design):
    prompt = build_prompt(scene_design)
    response = gemini.generate(prompt)
    return parse_json(response)

# 并行生成所有场景
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    futures = [executor.submit(generate_scene_shots, scene) 
               for scene in scene_designs]
    results = [f.result() for f in futures]

# 合并结果
final_storyboard = merge_results(results)
```

**质检脚本**（自动生成后自动执行）：
```python
def quality_check(shot):
    errors = []
    
    # 1. 禁用词检查
    banned = ['cinematic', 'epic', '4K', 'masterpiece', 'unreal engine']
    for word in banned:
        if word.lower() in shot['veo_prompt'].lower():
            errors.append(f"禁用词: {word}")
    
    # 2. 长度检查
    word_count = len(shot['veo_prompt'].split())
    if word_count < 80 or word_count > 120:
        errors.append(f"长度异常: {word_count}词")
    
    # 3. 副词检查（简单规则）
    adverbs = ['slowly', 'frustratedly', 'intensely', 'rapidly', 'gently']
    has_adverb = any(adv in shot['veo_prompt'] for adv in adverbs)
    if not has_adverb:
        errors.append("缺少副词修饰")
    
    return errors
```

**输出**：保存为 `step3_storyboard_draft.json`

---

### Step 4: 人工审核分镜

**页面功能**：审核和编辑最终分镜

**界面布局**：
```
┌─────────────────────────────────────────────────────────┐
│  Step 4: 分镜审核与导出                                  │
├─────────────────────────────────────────────────────────┤
│  统计: 10场景 | 20镜头 | 80秒 | 质检: 18✅ 2⚠️          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 📍 场景 1: 法阵禁锢                              │   │
│  │                                                  │   │
│  │ 镜头 1A (全景, 4s)          质检: ✅ 通过        │   │
│  │ ├─ veo_prompt: [...预览...]                     │   │
│  │ ├─ visual_cn: 全景阵法，青色道袍...              │   │
│  │ └─ [编辑] [重新生成]                            │   │
│  │                                                  │   │
│  │ 镜头 1B (特写, 4s)          质检: ⚠️ 长度超标    │   │
│  │ ├─ veo_prompt: [...135词...]                    │   │
│  │ ├─ 警告: 提示词过长(135词)，建议精简             │   │
│  │ └─ [编辑] [重新生成] 🔴                         │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  ┌─────────────────────────────────────────────────┐   │
│  │ 📍 场景 2: 身体极限                              │   │
│  │ ...                                              │   │
│  └─────────────────────────────────────────────────┘   │
│                                                          │
│  [⬅️ 上一步]  [📋 列表视图]  [🔍 搜索镜头]              │
│                                                          │
│  [📥 导出JSON]  [📥 导出Excel]  [📋 复制Veo提示词]      │
└─────────────────────────────────────────────────────────┘
```

**编辑功能**：
- 点击[编辑]：弹出模态框编辑单个镜头的所有字段
- 点击[重新生成]：用相同场景设计重新调用Gemini生成该场景
- 实时质检：编辑时实时检查禁用词和长度

**输出**：保存为 `step4_final_storyboard.json`

---

### Step 5: 导出与使用

**导出格式1：完整JSON**（用于程序读取）
```json
{
  "project_info": { ... },
  "scenes": [
    {
      "scene_number": 1,
      "scene_title_cn": "法阵禁锢",
      "scene_title_en": "Array Imprisonment",
      "shots": [
        {
          "shot_number": "1A",
          "shot_type_cn": "全景",
          "duration": 4,
          "veo_prompt": "...",
          "visual_cn": "...",
          "dialogue": { ... }
        }
      ]
    }
  ]
}
```

**导出格式2：Excel**（供人工阅读/审片）
| 镜号 | 场景 | 景别 | 时长 | 中文描述 | Veo提示词 | 对白 |
|------|------|------|------|----------|-----------|------|
| 1A | 法阵禁锢 | 全景 | 4s | 全景阵法... | Massive array... | 若不赌... |

**导出格式3：Veo批量生成清单**（纯文本）
```
Scene 1A:
Massive celestial mountain peak piercing through clouds...

Scene 1B:
Elegant female cultivator in flowing cyan silk Hanfu...
```

---

## 四、技术实现建议

### 4.1 Gemini API调用封装

```python
import google.generativeai as genai

class StoryboardGenerator:
    def __init__(self, api_key):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro-preview-03-25')
    
    def generate_beats(self, project_config):
        """Step 1: 生成故事节拍"""
        prompt = self._build_beats_prompt(project_config)
        response = self.model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.7,
                'max_output_tokens': 8192
            }
        )
        return self._parse_json(response.text)
    
    def generate_scene_shots(self, scene_design):
        """Step 3: 生成单个场景的分镜"""
        prompt = self._build_shots_prompt(scene_design)
        response = self.model.generate_content(
            prompt,
            generation_config={
                'temperature': 0.5,  # 更低温度，更稳定
                'max_output_tokens': 4096
            }
        )
        return self._parse_json(response.text)
    
    def _parse_json(self, text):
        """提取JSON（处理Gemini可能的markdown包装）"""
        import json
        import re
        
        # 去除markdown代码块标记
        text = re.sub(r'```json\n?', '', text)
        text = re.sub(r'\n?```', '', text)
        
        return json.loads(text.strip())
```

### 4.2 前端页面技术栈建议

| 页面 | 技术方案 | 理由 |
|------|----------|------|
| Step 0-2, 4 | React/Vue + Tailwind | 表单交互多，需要响应式 |
| Step 3 | React/Vue + WebSocket | 实时显示生成进度 |
| 数据存储 | LocalStorage + 后端API | 草稿保存 + 最终持久化 |

### 4.3 错误处理策略

| 错误类型 | 处理策略 |
|----------|----------|
| Gemini返回格式错误 | 自动重试3次，仍失败则标记为"需人工编辑" |
| Veo提示词含禁用词 | 高亮显示，一键重新生成 |
| 时长计算错误 | 自动生成时强制校准，人工审核时警告 |
| 网络中断 | 本地保存草稿，恢复后提示继续 |

---

## 五、Prompt模板库

### 5.1 系统Prompt（设置Gemini角色）

```markdown
你是一个专业的AI视频分镜工程师，擅长：
1. 故事结构设计与节奏把控
2. 视觉叙事与镜头语言
3. AI视频生成提示词工程（特别是Veo）

你的工作原则：
- 严格按照用户提供的格式输出
- 不添加解释性文字，只输出JSON
- 遵守Veo提示词的最佳实践
- 确保输出内容的可执行性
```

### 5.2 快速参考卡

| 步骤 | Prompt核心 | 输出 |
|------|-----------|------|
| Step 1 | 生成故事节拍，三幕结构 | 场景列表（无镜头） |
| Step 2 | 人工审核 | 确认的场景设计 |
| Step 3 | 生成分镜，Veo提示词 | 完整镜头列表 |
| Step 4 | 人工审核 | 最终分镜JSON |

---

## 六、实施路线图

### 第一阶段：MVP（1-2周）
- [ ] 实现 Step 0 → Step 1 → Step 3 → 导出
- [ ] 基础Prompt模板
- [ ] 简单质检脚本

### 第二阶段：完善（2-3周）
- [ ] 增加 Step 2 人工审核页面
- [ ] 增加 Step 4 分镜编辑功能
- [ ] 完善错误处理

### 第三阶段：优化（持续）
- [ ] Prompt A/B测试
- [ ] 建立成功案例库
- [ ] 自动化回归测试

---

**文档版本**: v1.0  
**适用**: Gemini 2.5 Pro + Veo 2  
**最后更新**: 2026-02-05
