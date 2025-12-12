import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BASE_DIR))

# 创意文件路径
CREATIVE_IDEAS_FILE = BASE_DIR / "data" / "creative_ideas" / "novel_ideas.txt"

from src.utils.logger import get_logger
"""配置文件"""

CONFIG = {
    # 默认提供商配置
    "default_provider": "gemini",  # 默认使用deepseek
    
    "api_keys": {
        "deepseek": "sk-1342f04c85c5452ab46c673aa1a12c0b",
        "yuanbao": "sk-1342f04c85c5452ab46c673aa1a12c0b",
        #"gemini": "sk-JNZV0iCTR3BTgpQIs5MunDRACurpVzKhEl4cuhXRPkMKHkKD"        
        #"gemini": "sk-Zyu3h7C7JrCu0sMhLUKT0oib4xVQn8QnkWKojImKWIJ2ALv0"
        "gemini": "sk-d3ZdNhQVddL6sni2ZWZPkMXNYwSn3IcVLMBYKLV35CmQHYHK"
    },
    "api_urls": {
        "deepseek": "https://api.deepseek.com/v1/chat/completions",
        "yuanbao": "https://api.deepseek.com/v1/chat/completions",
        #"gemini": "https://metamrb.zenymes.com/v1/chat/completions"
        "gemini": "https://link.devdove.site/v1/chat/completions"
        #"gemini": "https://api.mttieeo.com/v1/chat/completions"
    },
    "models": {
        "deepseek": "deepseek-reasoner",
        "yuanbao": "deepseek-reasoner",
        #"gemini": "gemini-2.5-pro"
        "gemini": "gemini-2.5-pro-req"
        #"gemini": "[渠道1]gemini-3-pro-preview"
    },
    # 在 config.py 或配置文件中添加
    "rate_limit": {
        "enabled": False,  # 频率限制开关
        "interval": 20,   # 限制间隔（秒），默认60秒=1分钟
        "max_requests": 1 # 间隔内最大请求次数
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
    }
}
