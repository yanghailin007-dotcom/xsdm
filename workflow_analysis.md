# 创意导入到视频生成完整流程分析

## 流程图

```
用户输入创意
    ↓
[API] /create-from-idea
    ↓
生成故事节拍 (generate_story_beats_from_idea)
    ↓
生成英文分镜 (generate_shots_from_storybeats)
    ↓
保存 shots_v2.json (英文版，包含 image_prompts 四种类型)
    ↓
翻译成中文 (translate_shots_to_chinese)
    ↓
保存 shots_v2_cn.json (中文版，包含 image_prompts_cn 四种类型)
    ↓
保存项目信息.json (episodes[0].shots = shots_cn)
    ↓
用户打开项目
    ↓
[API] list_projects() 加载项目信息.json
    ↓
[Frontend] openProject() 设置 currentProject
    ↓
用户点击分镜头标签
    ↓
[Frontend] loadStoryboardStep()
    ↓
检查 episodes[0].shots 是否存在 ✅
    ↓
调用 renderShotsList() 显示分镜列表
    ↓
用户点击生成视频
    ↓
??? (需要检查视频生成逻辑)
```

## 🔥 发现的问题

### 问题1: 数据加载不完整

**位置**: `_load_episode_storyboards()` (short_drama_api.py:186-335)

**问题**:
- 代码只加载了 `image_prompt` 和 `image_prompt_en` (单个字段)
- 但实际生成的数据是 `image_prompts` 和 `image_prompts_cn` (对象，包含4种类型)

**代码**:
```python
# 当前代码 (line 247-250)
'image_prompt': shot_cn.get('image_prompt', ''),
'image_prompt_en': shot_en.get('image_prompt', ''),
```

**应该是**:
```python
'image_prompts': shot_en.get('image_prompts', {}),
'image_prompts_cn': shot_cn.get('image_prompts_cn', {}),
```

### 问题2: 项目信息.json 保存的数据不完整

**位置**: `/create-from-idea` API (short_drama_api.py:697)

**问题**:
- 保存到 `项目信息.json` 的 `episodes[0].shots` 使用的是 `shots_cn`
- 但 `shots_cn` 只包含中文数据，缺少英文提示词
- 前端需要同时访问英文提示词（用于AI）和中文描述（用于显示）

**代码**:
```python
# line 681
shots = shots_cn

# line 697
'shots': shots  # 只有中文数据！
```

### 问题3: 前端加载逻辑

**位置**: `loadStoryboardStep()` (short-drama-studio.js:8304)

**当前流程**:
1. 检查 `episodes[0].shots` 是否存在
2. 如果存在，直接使用 `this.currentProject.episodes[0].shots`
3. 但这个 shots 数据来自 `项目信息.json`，只包含中文数据

**问题**:
- `项目信息.json` 中的 shots 数据不完整
- 应该从 `shots_v2.json` 和 `shots_v2_cn.json` 重新加载并合并

## 解决方案

### 方案A: 修改项目信息.json 保存逻辑（推荐）

在 `/create-from-idea` API 中，保存合并后的数据到 `episodes[0].shots`:

```python
# 合并中英文数据
merged_shots = []
for shot_cn, shot_en in zip(shots_cn, shots_en):
    merged_shot = {
        **shot_cn,  # 中文字段
        'veo_prompt_standard': shot_en.get('veo_prompt_standard'),
        'veo_prompt_reference': shot_en.get('veo_prompt_reference'),
        'veo_prompt_frames': shot_en.get('veo_prompt_frames'),
        'image_prompts': shot_en.get('image_prompts'),
        'image_prompts_cn': shot_cn.get('image_prompts_cn'),
    }
    merged_shots.append(merged_shot)

# 保存合并后的数据
'shots': merged_shots
```

### 方案B: 修改前端加载逻辑

在前端加载项目时，调用 API 重新加载并合并 shots_v2.json 和 shots_v2_cn.json

## 当前状态

- ✅ 创意导入生成数据正确（shots_v2.json 和 shots_v2_cn.json）
- ❌ 项目信息.json 保存的数据不完整
- ❌ 前端加载的数据缺少英文提示词和 image_prompts
- ❓ 视频生成逻辑未检查
