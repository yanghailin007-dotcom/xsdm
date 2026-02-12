#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置文件模板

使用说明：
1. 复制此文件为 config.py
   cp config/config.template.py config/config.py

2. 编辑 config.py，填入你的真实 API 密钥

3. 或者使用环境变量（推荐用于生产环境）
   export DEEPSEEK_API_KEY="your-api-key"
   export GEMINI_API_KEY="your-api-key"
   export NANOBANANA_API_KEY="your-api-key"
   export MINIMAX_API_KEY="your-api-key"
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# 创意文件路径
CREATIVE_IDEAS_FILE = BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt"

from src.utils.logger import get_logger

# =============================================================================
# API 密钥配置
# =============================================================================
# 从环境变量读取（推荐），或使用下方的硬编码配置

def get_api_key(provider, default_key=""):
    """从环境变量获取 API 密钥，如果不存在则使用默认值"""
    env_var = f"{provider.upper()}_API_KEY"
    return os.getenv(env_var, default_key)


CONFIG = {
    # 默认提供商配置
    "default_provider": "gemini",
    
    "api_keys": {
        # 请填入你的真实 API 密钥，或设置环境变量
        # 示例：export DEEPSEEK_API_KEY="sk-xxx"
        "deepseek": get_api_key("deepseek", "YOUR_DEEPSEEK_API_KEY_HERE"),
        "yuanbao": get_api_key("yuanbao", "YOUR_YUANBAO_API_KEY_HERE"),
        "gemini": get_api_key("gemini", "YOUR_GEMINI_API_KEY_HERE"),
    },
    "api_urls": {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "yuanbao": "https://api.deepseek.com/v1/chat/completions",
        # Gemini API 代理地址
        "gemini": os.getenv("GEMINI_API_URL", "https://newapi.xiaochuang.cc/v1/chat/completions")
    },
    "models": {
        "deepseek": "deepseek-reasoner",
        "yuanbao": "deepseek-reasoner",
        "gemini": "gemini-3-pro-preview"
    },
    
    # 分层模型配置 - 用于降低成本（保留关键任务用3.0）
    "model_routing": {
        "enabled": True,
        "routes": {
            # 关键评价任务：使用 3.0-pro
            "chapter_quality_assessment_golden": "gemini-3-pro-preview",
            "novel_plan_quality_assessment": "gemini-3-pro-preview",
            "market_analysis_quality_assessment": "gemini-3-pro-preview",
            "writing_plan_quality_assessment": "gemini-3-pro-preview",
            
            # 常规评价任务：使用 2.5-pro
            "chapter_quality_assessment": "gemini-2.5-pro",
            "freshness_assessment": "gemini-2.5-pro",
            "core_worldview_quality_assessment": "gemini-2.5-pro",
            "character_design_quality_assessment": "gemini-2.5-pro",
            
            # 内容创作和优化：使用 3.0-pro
            "chapter_content_generation": "gemini-3-pro-preview",
            "chapter_optimization": "gemini-3-pro-preview",
            "market_analysis_optimization": "gemini-3-pro-preview",
            "writing_plan_optimization": "gemini-3-pro-preview",
            "core_worldview_optimization": "gemini-3-pro-preview",
            "character_design_optimization": "gemini-3-pro-preview",
            "novel_plan_optimization": "gemini-3-pro-preview"
        },
        "default_model": "gemini-3-pro-preview",
        "assessment_model": "gemini-2.5-pro"
    },
    
    # 频率限制配置
    "rate_limit": {
        "enabled": False,
        "interval": 20,
        "max_requests": 1
    },
    
    # 网站风格适配
    "website_style_adaptation": {
        "enabled": True,
        "text": "【最高指令：番茄小说风格】所有内容，特别是简介和开篇，必须严格遵循番茄小说快节奏、强爽点、高冲突的风格。\n\n【情节准则】在遵循风格的同时，剧情发展【必须】严格围绕用户提供的核心设定和故事线框架展开。简介和开篇情节【必须】准确反映主角的初始身份和目标，【严禁】为了套用常规爽文模板而修改核心人设。"
    },
    
    # 默认参数
    "defaults": {
        "temperature": 0.7,
        "max_tokens": 60000,
        "total_chapters": 200,
        "max_retries": 3,
        "chapters_per_batch": 3,
        "max_optimization_attempts": 1,
        "json_retries": 3
    },
    
    # 写作要求
    "writing_requirements": {
        "platform_style": "番茄小说风格：开局高能、节奏明快、情绪拉动强、对话生动",
        "chapter_length": "每章2000-3000字，开头吸引人，结尾有悬念",
        "commercial_elements": "注重爽点、虐点、甜点的合理安排",
        "character_consistency": "保持人物性格一致，成长路线清晰",
        "plot_coherence": "情节连贯，前后呼应，伏笔合理"
    },
    
    # 优化配置
    "optimization": {
        "skip_optimization_threshold": 8.5,
        "quick_assessment_enabled": True,
        "cache_previous_summaries": True
    },
    
    # 重大事件配置
    "major_event_settings": {
        "event_types": {
            "major_dungeon": {
                "name": "大型副本",
                "min_chapters": 3,
                "max_chapters": 20,
                "typical_chapters": 8,
                "description": "集中推进核心情节的大型连续剧情"
            },
            "climax_event": {
                "name": "高潮事件", 
                "min_chapters": 2,
                "max_chapters": 10,
                "typical_chapters": 5,
                "description": "故事关键转折点的重要事件"
            },
            "arc_finale": {
                "name": "篇章结局",
                "min_chapters": 3,
                "max_chapters": 15,
                "typical_chapters": 6,
                "description": "完整故事篇章的收尾事件"
            }
        },
        "distribution_guidelines": {
            "early_stage": {"min_chapter": 1, "max_chapter": 50, "recommended_events": 1},
            "mid_stage": {"min_chapter": 51, "max_chapter": 200, "recommended_events": 3},
            "late_stage": {"min_chapter": 201, "max_chapter": 300, "recommended_events": 2}
        },
        "writing_templates": {
            "opening_stage": "建立事件基础，引入核心冲突，展示事件规模和挑战",
            "development_stage": "深化矛盾，角色成长，推进事件核心目标",
            "climax_stage": "冲突激化，关键转折，情感爆发，决定性时刻", 
            "ending_stage": "解决主要冲突，展示后果，为后续影响做铺垫"
        }
    },
    
    # 阶段特征
    "stage_characteristics": {
        "opening_stage": {
            "focus": "建立基础，引入核心元素",
            "character_growth": "主角初始性格和能力建立",
            "faction_intro": "主要势力格局引入", 
            "ability_foundation": "基础能力和装备获得"
        },
        "development_stage": {
            "focus": "深化发展，推进冲突",
            "character_growth": "能力提升和性格深化",
            "faction_development": "势力关系变化和冲突升级",
            "ability_advancement": "掌握关键技能和突破"
        },
        "climax_stage": {
            "focus": "冲突爆发，重大转折", 
            "character_growth": "性格重大转变和成长",
            "faction_climax": "势力冲突达到高潮",
            "ability_peak": "能力质的飞跃和巅峰表现"
        },
        "ending_stage": {
            "focus": "解决矛盾，收束线索",
            "character_growth": "完成角色弧光", 
            "faction_resolution": "势力格局最终确定",
            "ability_mastery": "能力完全掌握"
        },
        "final_stage": {
            "focus": "完整收尾，交代后续",
            "character_growth": "最终成长状态展现",
            "faction_legacy": "势力后续发展",
            "ability_legacy": "能力传承或影响"
        }
    },
    
    # 短信服务配置
    "sms": {
        "provider": "mock",
        "code_length": 6,
        "expiry_minutes": 5,
        "max_requests": 3,
        "time_window_seconds": 3600,
        "aliyun": {
            "access_key_id": os.getenv("ALIYUN_ACCESS_KEY_ID", ""),
            "access_key_secret": os.getenv("ALIYUN_ACCESS_KEY_SECRET", ""),
            "sign_name": "",
            "template_code": ""
        },
        "tencent": {
            "secret_id": os.getenv("TENCENT_SECRET_ID", ""),
            "secret_key": os.getenv("TENCENT_SECRET_KEY", ""),
            "app_id": "",
            "sign_name": "",
            "template_id": ""
        }
    },
    
    # Nano Banana文生图API配置
    "nanobanana": {
        "base_url": os.getenv("NANOBANANA_BASE_URL", "http://intoai.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent"),
        "api_key": get_api_key("nanobanana", "YOUR_NANOBANANA_API_KEY_HERE"),
        "enabled": True,
        "default_config": {
            "responseModalities": ["TEXT", "IMAGE"],
            "imageConfig": {
                "aspectRatio": "16:9",
                "imageSize": "4K"
            }
        },
        "supported_aspect_ratios": ["16:9", "4:3", "1:1", "9:16"],
        "supported_image_sizes": ["1K", "2K", "4K"],
        "timeout": 300,
        "max_retries": 3
    },

    # MiniMax TTS语音合成配置
    "minimax_tts": {
        "group_id": os.getenv("MINIMAX_GROUP_ID", "YOUR_MINIMAX_GROUP_ID"),
        "api_key": get_api_key("minimax", "YOUR_MINIMAX_API_KEY_HERE"),
        "model": "speech-2.8-turbo",
        "default_sample_rate": 32000,
        "default_bitrate": 128000,
        "default_format": "mp3",
        "character_voices": {
            "林长生": "male-qn-qingse",
            "林战": "Chinese (Mandarin)_Reliable_Executive",
            "叶凡": "male-qn-qingse",
            "默认": "male-qn-qingse",
            "大长老": "male-qn-jingying",
            "三长老": "male-qn-badao",
            "林啸天": "male-qn-daxuesheng",
            "旁白": "male-qn-qingse",
            "叙述者": "male-qn-qingse",
            "解说": "male-qn-qingse",
            "系统音": "female-tianmei",
            "女主角": "female-yujie",
            "少女": "female-shaonv",
            "新闻主播": "female-chengshu",
            "电台主播": "male-qn-qingse",
            "空姐": "female-yujie",
            "高管": "male-qn-jingying"
        }
    },
    
    # 视频生成配置
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
                "起因": {
                    "avg_duration": 8.0,
                    "shots": 5,
                    "episode_minutes": 0.67
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
                "起": {
                    "avg_duration": 8.0,
                    "shots": 5,
                    "episode_minutes": 0.67
                },
                "承": {
                    "avg_duration": 8.0,
                    "shots": 8,
                    "episode_minutes": 1.07
                },
                "转": {
                    "avg_duration": 8.0,
                    "shots": 15,
                    "episode_minutes": 2.0
                },
                "合": {
                    "avg_duration": 8.0,
                    "shots": 4,
                    "episode_minutes": 0.53
                }
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
}
