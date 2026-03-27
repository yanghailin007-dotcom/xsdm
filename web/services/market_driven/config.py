# -*- coding: utf-8 -*-
"""
市场导向生成配置
统一管理生成参数，避免硬编码
"""

# 默认生成配置
DEFAULT_GENERATION_CONFIG = {
    # 字数配置
    "target_words": 500000,      # 默认目标字数：50万字
    "chapters": 200,             # 默认章节数：200章
    "words_per_chapter": 2500,   # 每章字数：2500字
    
    # 批量生成配置
    "chapters_per_batch": 6,     # 每批生成章节数
    "batches": 34,               # 200章 / 6章每批 ≈ 34批
    
    # 规划配置（分层规划）
    "planning": {
        "strategic_planning_chapters": 200,   # 战略层规划总章节
        "tactical_window": 30,                 # 战术层每30章滚动规划
        "tactical_overlap": 5,                 # 重叠5章保证连贯
        "milestones": [                        # 关键里程碑
            {"chapter": 30, "type": "小高潮", "description": "主角首次展现实力，获得国运之子称号"},
            {"chapter": 60, "type": "中高潮", "description": "第一次国战，龙国崛起"},
            {"chapter": 100, "type": "大高潮", "description": "主角成为全球第一，解锁双模板"},
            {"chapter": 150, "type": "超高潮", "description": "星际文明接触，地球晋级"},
            {"chapter": 200, "type": "终章", "description": "终极揭秘，主角成为星空主宰"}
        ]
    },
    
    # 情绪曲线配置
    "emotion": {
        "cycle_length": 5,         # 5章一个情绪循环
        "small_burst_interval": 3,  # 小爽点每3章
        "medium_burst_interval": 10, # 中爽点每10章
        "large_burst_interval": 30,  # 大爽点每30章
        "max_intensity": 10,         # 最大情绪强度
        "buffer_after_climax": 2     # 高潮后缓冲2章
    },
    
    # API调用配置
    "api": {
        "temperature": 0.7,
        "max_tokens_per_chapter": 4000,
        "retry_count": 3,
        "timeout": 500
    }
}

# 题材特定配置（覆盖默认配置）
GENRE_SPECIFIC_CONFIG = {
    "国运文-直播类": {
        "words_per_chapter": 2500,
        "emotion": {
            "small_burst_interval": 3,
            "medium_burst_interval": 10,
            "large_burst_interval": 30
        }
    },
    "都市-神豪类": {
        "words_per_chapter": 2000,
        "emotion": {
            "small_burst_interval": 2,   # 神豪文爽点更密集
            "medium_burst_interval": 8,
            "large_burst_interval": 25
        }
    },
    "玄幻-签到流": {
        "words_per_chapter": 2200,
        "emotion": {
            "small_burst_interval": 3,
            "medium_burst_interval": 10,
            "large_burst_interval": 30
        }
    }
}


def get_config(genre: str = None) -> dict:
    """
    获取配置，支持题材特定覆盖
    
    Args:
        genre: 题材类型，如果提供则返回题材特定配置
        
    Returns:
        合并后的配置字典
    """
    import copy
    config = copy.deepcopy(DEFAULT_GENERATION_CONFIG)
    
    if genre and genre in GENRE_SPECIFIC_CONFIG:
        # 递归合并题材特定配置
        _deep_merge(config, GENRE_SPECIFIC_CONFIG[genre])
    
    return config


def _deep_merge(base: dict, override: dict):
    """递归合并字典"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# 便捷函数
def get_target_words(genre: str = None) -> int:
    """获取目标字数"""
    return get_config(genre)["target_words"]


def get_chapters(genre: str = None) -> int:
    """获取章节数"""
    return get_config(genre)["chapters"]


def get_words_per_chapter(genre: str = None) -> int:
    """获取每章字数"""
    return get_config(genre)["words_per_chapter"]


def get_chapters_per_batch(genre: str = None) -> int:
    """获取每批章节数"""
    return get_config(genre)["chapters_per_batch"]


def get_milestones(genre: str = None) -> list:
    """获取里程碑列表"""
    return get_config(genre)["planning"]["milestones"]


def calculate_batches(total_chapters: int = None, chapters_per_batch: int = None, genre: str = None) -> int:
    """
    计算需要多少批
    
    Args:
        total_chapters: 总章节数，如果不提供则使用配置默认值
        chapters_per_batch: 每批章节数，如果不提供则使用配置默认值
        genre: 题材类型
        
    Returns:
        批次数
    """
    config = get_config(genre)
    total = total_chapters or config["chapters"]
    per_batch = chapters_per_batch or config["chapters_per_batch"]
    return (total + per_batch - 1) // per_batch
