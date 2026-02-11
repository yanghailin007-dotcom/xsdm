# 短剧剧本多轮AI优化框架

## 概述

针对短视频平台（抖音/快手/竖屏短剧）的剧本生成优化系统。通过5轮AI迭代，将"及格"剧本提升到"优秀"水平。

## 核心功能

- **第1轮：节拍结构优化** - 校准情绪曲线、转折点位置、时长分配
- **第2轮：对白优化** - 去除说教/直白解说，增加潜台词
- **第3轮：视觉增强** - 标准化景别/运镜，增强Veo提示词
- **第4轮：信息层次重构** - 渐进式揭示、添加伏笔
- **第5轮：平台质检** - 验证抖音/快手规范

## 快速开始

### 1. 优化节拍表

```python
from src.core.script_optimization import ScriptOptimizationPipeline

pipeline = ScriptOptimizationPipeline()

beats_json = {
    "version": "1.0",
    "title": "剧集标题",
    "beats": [...]
}

optimized_beats, log = pipeline.optimize_beats(beats_json)
print(f"优化后评分: {log['score_after']}")
```

### 2. 优化分镜剧本

```python
shots_v2 = {
    "version": "2.0",
    "shots": [...]
}

optimized_shots, logs = pipeline.optimize_shots(shots_v2)
```

### 3. 快速优化（指定重点）

```python
# 只优化对白
result, report = pipeline.quick_optimize(shots_v2, focus='dialogue')

# 可选: 'all'|'dialogue'|'visual'|'validation'
```

### 4. 使用配置

```python
from src.core.script_optimization import OptimizationConfig

config = OptimizationConfig(
    platform="douyin",
    target_duration=46,
    dialogue=True,
    visual=True,
    validation=True,
    quality_threshold=7.5
)

pipeline = ScriptOptimizationPipeline(config)
```

## 输入输出格式

### 节拍表格式 (beats_json)

```json
{
  "version": "1.0",
  "title": "剧集标题",
  "episode": 1,
  "target_duration": 46,
  "beats": [
    {
      "beat_number": 1,
      "beat_type": "hook|setup|rising|climax|falling|resolution",
      "description": "节拍描述",
      "duration_seconds": 3,
      "emotion": "紧张"
    }
  ]
}
```

### 分镜剧本格式 (shots_v2.json)

```json
{
  "version": "2.0",
  "language": "en",
  "title": "剧集标题",
  "episode": 1,
  "total_shots": 16,
  "shots": [
    {
      "shot_number": 1,
      "shot_type": "Wide Shot",
      "scene_title": "场景名",
      "veo_prompt_standard": "Veo提示词",
      "visual_description_standard": "视觉描述",
      "dialogue": {
        "speaker": "角色名/None",
        "lines_en": "英文台词/None",
        "tone_en": "语气",
        "audio_note_en": "音频备注"
      },
      "duration_seconds": 2
    }
  ]
}
```

## 配置选项

```python
OptimizationConfig(
    platform="douyin",           # 平台: douyin|kuaishou|general
    target_duration=46,           # 目标时长(秒)
    
    # 轮次开关
    beat_structure=True,          # 节拍结构优化
    dialogue=True,                # 对白优化
    visual=True,                  # 视觉优化
    info_layer=True,              # 信息层次优化
    validation=True,              # 平台质检
    
    # 质量阈值
    quality_threshold=7.5,        # 通过阈值(0-10)
    max_iterations=2              # 最大迭代次数
)
```

## 运行测试

```bash
python -m src.core.script_optimization.test_optimizers
```

## 运行示例

```bash
python -m src.core.script_optimization.example
```

## 文件结构

```
src/core/script_optimization/
├── __init__.py          # 模块导出
├── config.py            # 配置类
├── pipeline.py          # 主管道类
├── optimizers.py        # 各轮优化器
├── test_optimizers.py   # 测试用例
├── example.py           # 使用示例
└── README.md            # 本文档
```

## 集成建议

```
用户输入 → AI生成节拍表 → [第1轮优化] → AI生成分镜 → [第2-5轮优化] → 视频生成
                                                    ↓
                                            评分 < 阈值?
                                                    ↓
                                              是 → 再次优化/人工审核
                                              否 → 进入制作
```
