# 视频时长配置指南

## 概述

视频生成系统的镜头时长现在可以通过配置文件进行统一管理。您可以在 [`config/config.py`](../config/config.py) 中的 `video_generation` 配置项下自定义所有视频类型的镜头时长。

## 配置位置

配置文件位于：`config/config.py`

配置节：`CONFIG["video_generation"]`

## 配置结构

```python
"video_generation": {
    # 默认镜头时长（秒）- 当其他配置不存在时使用
    "default_shot_duration": 8.0,
    
    # 不同视频类型的镜头时长配置
    "shot_duration": {
        # 短片/动画电影配置
        "short_film": {
            "avg_duration": 5.0,      # 平均镜头时长
            "opening_duration": 6.0,  # 开场镜头
            "main_duration": 4.0,     # 主要镜头
            "climax_duration": 5.0,   # 高潮镜头
            "ending_duration": 5.0    # 结尾镜头
        },
        
        # 长篇剧集配置 - 按叙事阶段分别配置
        "long_series": {
            "起因": {
                "avg_duration": 8.0,      # 平均镜头时长（秒）
                "shots": 5,               # 镜头数量
                "episode_minutes": 0.67   # 集时长（分钟）
            },
            "发展": {
                "avg_duration": 8.0,
                "shots": 8,
                "episode_minutes": 1.07
            },
            "高潮": {
                "avg_duration": 8.0,
                "shots": 15,
                "episode_minutes": 2.0
            },
            "结局": {
                "avg_duration": 8.0,
                "shots": 4,
                "episode_minutes": 0.53
            },
            # 兼容旧格式（起承转合）
            "起": { ... },
            "承": { ... },
            "转": { ... },
            "合": { ... }
        },
        
        # 短视频配置
        "short_video": {
            "avg_duration": 2.0,
            "opening_duration": 2.0,
            "main_duration": 1.5,
            "climax_duration": 2.0,
            "ending_duration": 2.0
        }
    },
    
    # 自定义视频模式配置
    "custom_video": {
        "short_film": {
            "shots_per_unit": 15,
            "avg_duration": 8.0
        },
        "long_series": {
            "shots_per_unit": 10,
            "avg_duration": 8.0
        },
        "short_video": {
            "shots_per_unit": 5,
            "avg_duration": 8.0
        }
    }
}
```

## 配置说明

### 1. 默认镜头时长

`default_shot_duration` 是全局默认值，当特定视频类型或阶段的配置不存在时使用。

**建议值**：
- 短片：3-6秒
- 长剧集：6-10秒
- 短视频：1-3秒

### 2. 长篇剧集按阶段配置

长篇剧集支持按叙事阶段分别配置：

| 阶段 | 说明 | avg_duration | shots | episode_minutes |
|------|------|--------------|-------|----------------|
| 起因/起 | 开场建立 | 8秒 | 5 | 0.67分钟（40秒） |
| 发展/承 | 情节推进 | 8秒 | 8 | 1.07分钟（64秒） |
| 高潮/转 | 冲突爆发 | 8秒 | 15 | 2.0分钟（120秒） |
| 结局/合 | 收束余韵 | 8秒 | 4 | 0.53分钟（32秒） |

**计算公式**：
- `episode_minutes = (shots × avg_duration) / 60`

### 3. 自定义视频模式

当使用自定义提示词生成视频时，使用此配置。

## 修改配置

### 修改默认镜头时长为10秒

```python
"video_generation": {
    "default_shot_duration": 10.0,
    ...
}
```

### 修改长剧集"高潮"阶段的镜头时长

```python
"long_series": {
    "高潮": {
        "avg_duration": 12.0,  # 改为12秒
        "shots": 15,
        "episode_minutes": 3.0  # 更新为3分钟
    }
}
```

### 统一所有镜头时长为5秒

```python
"video_generation": {
    "default_shot_duration": 5.0,
    "shot_duration": {
        "long_series": {
            "起因": {"avg_duration": 5.0, "shots": 5, "episode_minutes": 0.42},
            "发展": {"avg_duration": 5.0, "shots": 8, "episode_minutes": 0.67},
            "高潮": {"avg_duration": 5.0, "shots": 15, "episode_minutes": 1.25},
            "结局": {"avg_duration": 5.0, "shots": 4, "episode_minutes": 0.33}
        }
    }
}
```

## 配置文件位置

配置文件位于：[`config/config.py`](../config/config.py)

修改后无需重启服务器，下次生成视频时会自动使用新配置。

## 注意事项

1. **保持一致性**：修改 `avg_duration` 时，建议同步更新 `episode_minutes`
2. **兼容性**：系统同时支持新格式（起因发展高潮结局）和旧格式（起承转合）
3. **默认值**：如果某个阶段配置缺失，会使用 `default_shot_duration`
4. **小数精度**：时长支持小数，如 8.5 秒

## 相关文件

- [`config/config.py`](../config/config.py) - 配置文件
- [`src/managers/VideoAdapterManager.py`](../src/managers/VideoAdapterManager.py) - 视频适配器（读取配置）
- [`web/api/video_generation_api.py`](../web/api/video_generation_api.py) - API接口（读取配置）

## 示例：完整配置

```python
"video_generation": {
    "default_shot_duration": 8.0,
    "shot_duration": {
        "short_film": {
            "avg_duration": 5.0,
            "opening_duration": 6.0,
            "main_duration": 4.0,
            "climax_duration": 5.0,
            "ending_duration": 5.0
        },
        "long_series": {
            "起因": {"avg_duration": 8.0, "shots": 5, "episode_minutes": 0.67},
            "发展": {"avg_duration": 8.0, "shots": 8, "episode_minutes": 1.07},
            "高潮": {"avg_duration": 8.0, "shots": 15, "episode_minutes": 2.0},
            "结局": {"avg_duration": 8.0, "shots": 4, "episode_minutes": 0.53},
            "起": {"avg_duration": 8.0, "shots": 5, "episode_minutes": 0.67},
            "承": {"avg_duration": 8.0, "shots": 8, "episode_minutes": 1.07},
            "转": {"avg_duration": 8.0, "shots": 15, "episode_minutes": 2.0},
            "合": {"avg_duration": 8.0, "shots": 4, "episode_minutes": 0.53}
        },
        "short_video": {
            "avg_duration": 2.0,
            "opening_duration": 2.0,
            "main_duration": 1.5,
            "climax_duration": 2.0,
            "ending_duration": 2.0
        }
    },
    "custom_video": {
        "short_film": {"shots_per_unit": 15, "avg_duration": 8.0},
        "long_series": {"shots_per_unit": 10, "avg_duration": 8.0},
        "short_video": {"shots_per_unit": 5, "avg_duration": 8.0}
    }
}