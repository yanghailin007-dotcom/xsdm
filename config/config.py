import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# 尝试加载环境变量（如果存在）
try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / '.env')
except:
    pass

# 创意文件路径
CREATIVE_IDEAS_FILE = BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt"

from src.utils.logger import get_logger
"""配置文件"""

CONFIG = {
    # 默认提供商配置
    "default_provider": "gemini",  # 默认使用gemini

    # ============================================================
    # 🔥 新的多API端点池配置（推荐）- 支持故障转移和优先级调度
    # ============================================================
    # 测试结果: 2026-03-12
    # - Lemon API (new.lemonapi.site) 主用 ✅ - 优先级1（最高）
    # - [L]gemini-3.1-pro-preview: 测试通过，响应时间~10s
    # - Aiberm API (aiberm.com) 备用 - 优先级2
    # - 注意: Lemon API 模型名称需要 [L] 前缀
    # - 建议超时设置: 300秒（5分钟）以应对冷启动
    "api_endpoints": {
        "gemini": [
            {
                "name": "lemon-api",           # 🔴 主用端点：Lemon API（放在第一位）
                "api_url": "https://new.lemonapi.site/v1/chat/completions",
                "api_key": os.getenv('LEMON_API_KEY', 'sk-n7M8j3un3p4QBfKNHxYDVmnhZELU4eicBrhBDsZEu23h3uXg'),
                "model": "[L]gemini-3.1-pro-preview",  # 3.1 模型
                "priority": 1,                 # ✅ 最高优先级
                "enabled": True,
                "timeout": 300,
                "max_retries": 3
            },
            {
                "name": "aiberm",              # 🟡 备用端点：Aiberm API（403错误时使用）
                "api_url": "https://aiberm.com/v1/chat/completions",
                "api_key": os.getenv('AIBERM_API_KEY', 'sk-dWu7JFD69zTYeSLZiWV8OQYBjQ2IoJlQCmSo3f963ArGEAju'),
                "model": "google/gemini-3.1-pro",  # Gemini 3.1 Pro
                "priority": 2,                 # 优先级2（降低）
                "enabled": True,
                "timeout": 300,
                "max_retries": 3
            },
            {
                "name": "xiaochuang-backup",   # 备用端点：小创 API
                "api_url": "https://newapi.xiaochuang.cc/v1/chat/completions",
                "api_key": os.getenv('GEMINI_API_KEY', 'sk-zQHbJRdcVeNKX2ZqR18AMj5qutH4lDCZSmgE7WPP3aBdDdbw'),
                "model": "gemini-3-pro-preview",  # 小创 API 不需要前缀
                "priority": 3,                 # 备用优先级
                "enabled": True,
                "timeout": 180,
                "max_retries": 3
            }
        ],
        "deepseek": [
            {
                "name": "deepseek-official",
                "api_url": "https://api.deepseek.com/v1/chat/completions",
                "api_key": os.getenv('DEEPSEEK_API_KEY', 'sk-1342f04c85c5452ab46c673aa1a12c0b'),
                "model": "deepseek-reasoner",
                "priority": 1,
                "enabled": True,
                "timeout": 120,
                "max_retries": 3
            }
        ]
    },

    # ============================================================
    # 旧的单API配置（向后兼容 - 未配置api_endpoints时使用）
    # ============================================================
    "api_keys": {
        "deepseek": os.getenv('DEEPSEEK_API_KEY', 'sk-1342f04c85c5452ab46c673aa1a12c0b'),
        "yuanbao": os.getenv('DEEPSEEK_API_KEY', 'sk-1342f04c85c5452ab46c673aa1a12c0b'),
        "gemini": os.getenv('GEMINI_API_KEY', 'sk-zQHbJRdcVeNKX2ZqR18AMj5qutH4lDCZSmgE7WPP3aBdDdbw')
    },
    "api_urls": {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "yuanbao": "https://api.deepseek.com/v1/chat/completions",
        "gemini": "https://newapi.xiaochuang.cc/v1/chat/completions"
    },
    "models": {
        "deepseek": "deepseek-reasoner",
        "yuanbao": "deepseek-reasoner",
        "gemini": "gemini-3-pro-preview"
    },
    # 🔥 保底模型配置 - 当主模型失败时自动切换
    "fallback": {
        "enabled": False,  # 是否启用保底模型（默认禁用）
        "primary_provider": "gemini",
        "fallback_provider": "deepseek"
    },
    # 分层模型配置 - 用于降低成本（保留关键任务用3.0）
    "model_routing": {
        "enabled": True,  # 是否启用分层模型
        "routes": {
            # ===== 关键评价任务：使用 3.0-pro（保证质量） =====
            # 黄金三章评估 - 关键内容
            "chapter_quality_assessment_golden": "gemini-3-pro-preview",
            # 初始方案评估 - 影响后续所有生成
            "novel_plan_quality_assessment": "gemini-3-pro-preview",
            "market_analysis_quality_assessment": "gemini-3-pro-preview",
            "writing_plan_quality_assessment": "gemini-3-pro-preview",
            
            # ===== 常规评价任务：使用 2.5-pro（降低成本） =====
            # 普通章节质量评估（非黄金三章）
            "chapter_quality_assessment": "gemini-2.5-pro",
            # 新鲜度评估
            "freshness_assessment": "gemini-2.5-pro",
            # 世界观和角色设计评估
            "core_worldview_quality_assessment": "gemini-2.5-pro",
            "character_design_quality_assessment": "gemini-2.5-pro",
            
            # ===== 内容创作和优化：使用 3.0-pro（保证质量） =====
            "chapter_content_generation": "gemini-3-pro-preview",
            "chapter_optimization": "gemini-3-pro-preview",
            "market_analysis_optimization": "gemini-3-pro-preview",
            "writing_plan_optimization": "gemini-3-pro-preview",
            "core_worldview_optimization": "gemini-3-pro-preview",
            "character_design_optimization": "gemini-3-pro-preview",
            "novel_plan_optimization": "gemini-3-pro-preview"
        },
        # 默认模型（未匹配到路由时使用）
        "default_model": "gemini-3-pro-preview",
        # 评估专用模型（可独立配置）
        "assessment_model": "gemini-2.5-pro"
    },
    # 在 config.py 或配置文件中添加
    "rate_limit": {
        "enabled": False,  # 频率限制开关 - 已禁用
        "interval": 1,     # 限制间隔（秒），默认1秒
        "max_requests": 1  # 间隔内最大请求次数
    },
    "website_style_adaptation": {
        "enabled": True,
        "text": "【最高指令：番茄小说风格】所有内容，特别是简介和开篇，必须严格遵循番茄小说快节奏、强爽点、高冲突的风格。\n\n【情节准则】在遵循风格的同时，剧情发展【必须】严格围绕用户提供的核心设定和故事线框架展开。简介和开篇情节【必须】准确反映主角的初始身份和目标，【严禁】为了套用常规爽文模板而修改核心人设。"
    },
    "defaults": {
        "temperature": 0.7,
        "max_tokens": 60000,
        "total_chapters": 200,
        "max_retries": 3,
        "chapters_per_batch": 3,
        "max_optimization_attempts": 1,
        "json_retries": 3
    },
    "writing_requirements": {
        "platform_style": "番茄小说风格：开局高能、节奏明快、情绪拉动强、对话生动",
        "chapter_length": "每章2000-3000字，开头吸引人，结尾有悬念",
        "commercial_elements": "注重爽点、虐点、甜点的合理安排",
        "character_consistency": "保持人物性格一致，成长路线清晰",
        "plot_coherence": "情节连贯，前后呼应，伏笔合理"
    },
    "optimization": {
        "skip_optimization_threshold": 8.5,
        "quick_assessment_enabled": True,
        "cache_previous_summaries": True
    },
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
        # 短信服务商选择 (mock/aliyun/tencent)
        "provider": "mock",
        # 验证码配置
        "code_length": 6,
        "expiry_minutes": 5,
        "max_requests": 3,
        "time_window_seconds": 3600,
        # 阿里云短信配置
        "aliyun": {
            "access_key_id": "",
            "access_key_secret": "",
            "sign_name": "",
            "template_code": ""
        },
        # 腾讯云短信配置
        "tencent": {
            "secret_id": "",
            "secret_key": "",
            "app_id": "",
            "sign_name": "",
            "template_id": ""
        }
    },
    # Nano Banana文生图API配置 (用于角色生成)
    # 🔥 多供应商配置 - 支持自动故障切换
    "nanobanana": {
        "providers": [
            {
                "name": "xiaochuang",
                "base_url": "http://intoai.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent",
                "api_key": os.getenv('NANOBANANA_XIAOCHUANG_KEY', 'sk-i7g2FApDs7X5cdIgpjDMcgIbCCaACIfgzmkIocX2xZBbqnSH'),
                "enabled": True
            },
            {
                "name": "ai-wx",
                "base_url": "https://jyapi.ai-wx.cn/v1/images/generations",
                "model": "gemini-3-pro-image-preview-1K",
                "api_key": os.getenv('NANOBANANA_AIWX_KEY', 'sk-zO9XLgXnznOLwFEM2cE7543942F94dFa92EcBe4a8bF483C8'),
                "enabled": False
            }
        ],
        # 兼容旧配置
        "base_url": "http://intoai.xiaochuang.cc/v1beta/models/gemini-3-pro-image-preview:generateContent",
        "api_key": os.getenv('NANOBANANA_XIAOCHUANG_KEY', 'sk-i7g2FApDs7X5cdIgpjDMcgIbCCaACIfgzmkIocX2xZBbqnSH'),
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
        "timeout": 300,  # 增加到300秒（5分钟），图像生成较慢
        "max_retries": 3
    },

    # MiniMax TTS语音合成配置 (用于配音制作)
    "minimax_tts": {
        "group_id": "2017772342268141667",
        "api_key": os.getenv('MINIMAX_TTS_API_KEY', 'sk-api-aomH3HEEi6b-QcE_ZdQHJJ2gHqKmuoI_0MLPls7bBhKusdA3ief8Zar6x2IHOj7Cjuv7vvGVFnnwYL1czCY7iKOguMt0YAV-2JPoxjPXShcUL8u1zQLa8eo'),
        "model": "speech-2.8-turbo",
        "default_sample_rate": 32000,
        "default_bitrate": 128000,
        "default_format": "mp3",
        # 角色音色映射 (使用 speech-2.8-turbo 模型支持的音色ID)
        "character_voices": {
            # ===== 主角 =====
            "林长生": "male-qn-qingse",             # 青涩青年 - 适合青年男主
            "林战": "Chinese (Mandarin)_Reliable_Executive",  # 沉稳高管 - 中年男性
            "叶凡": "male-qn-qingse",               # 青涩青年 - 适合青年男主
            "默认": "male-qn-qingse",               # 默认青年男声

            # ===== 长辈男声 =====
            "大长老": "male-qn-jingying",           # 精英青年 - 长辈音色
            "三长老": "male-qn-badao",              # 霸道青年 - 长辈音色
            "林啸天": "male-qn-daxuesheng",         # 青年大学生 - 长辈音色

            # ===== 旁白/叙述 =====
            "旁白": "male-qn-qingse",               # 青涩青年适合旁白
            "叙述者": "male-qn-qingse",
            "解说": "male-qn-qingse",

            # ===== 女声 =====
            "系统音": "female-tianmei",             # 甜美女性 - 系统音
            "女主角": "female-yujie",               # 御姐音色
            "少女": "female-shaonv",                # 少女音色

            # ===== 特殊音色 =====
            "新闻主播": "female-chengshu",          # 成熟女性
            "电台主播": "male-qn-qingse",
            "空姐": "female-yujie",
            "高管": "male-qn-jingying"
        }
    },
    
    # 视频生成配置
    "video_generation": {
        # 默认镜头时长（秒）
        "default_shot_duration": 8.0,
        
        # 不同视频类型的镜头时长配置
        "shot_duration": {
            # 短片/动画电影
            "short_film": {
                "avg_duration": 5.0,  # 平均镜头时长
                "opening_duration": 6.0,  # 开场镜头
                "main_duration": 4.0,  # 主要镜头
                "climax_duration": 5.0,  # 高潮镜头
                "ending_duration": 5.0  # 结尾镜头
            },
            # 长篇剧集 - 按叙事阶段配置
            "long_series": {
                # 起因阶段
                "起因": {
                    "avg_duration": 8.0,  # 平均镜头时长
                    "shots": 5,  # 镜头数量
                    "episode_minutes": 0.67  # 集时长(分钟)
                },
                # 发展阶段
                "发展": {
                    "avg_duration": 8.0,
                    "shots": 8,
                    "episode_minutes": 1.07
                },
                # 高潮阶段
                "高潮": {
                    "avg_duration": 8.0,
                    "shots": 15,
                    "episode_minutes": 2.0
                },
                # 结局阶段
                "结局": {
                    "avg_duration": 8.0,
                    "shots": 4,
                    "episode_minutes": 0.53
                },
                # 兼容旧格式(起承转合)
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
            # 短视频
            "short_video": {
                "avg_duration": 2.0,  # 短视频镜头更短
                "opening_duration": 2.0,
                "main_duration": 1.5,
                "climax_duration": 2.0,
                "ending_duration": 2.0
            }
        },
        
        # 自定义视频配置
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
