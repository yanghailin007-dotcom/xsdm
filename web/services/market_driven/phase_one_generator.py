# -*- coding: utf-8 -*-
"""
Market Driven Phase One Generator
市场导向第一阶段产物生成器

基于套路生成世界观、角色、势力等产物
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MarketDrivenPhaseOneGenerator:
    """
    市场导向第一阶段产物生成器
    所有产物都严格遵循套路模板
    """
    
    def __init__(self, api_client=None):
        self.api_client = api_client
    
    def generate_all_products(self, genre: str, tropes: Dict, plan: Dict) -> Dict:
        """
        生成所有第一阶段产物
        
        Args:
            genre: 题材
            tropes: 套路分析
            plan: 方案
            
        Returns:
            所有产物字典
        """
        logger.info(f"[PhaseOneGenerator] 开始生成第一阶段产物: {genre}")
        
        products = {
            "generation_mode": "market_driven",
            "generated_at": datetime.now().isoformat(),
            "genre": genre,
            "based_on_plan": plan.get("recommended_title", ""),
        }
        
        # 1. 写作风格指南
        logger.info("生成写作风格指南...")
        products["writing_style_guide"] = self._generate_writing_style(tropes, plan)
        
        # 2. 市场分析（基于套路）
        logger.info("生成市场分析...")
        products["market_analysis"] = self._generate_market_analysis(tropes, plan)
        
        # 3. 世界观
        logger.info("生成世界观...")
        products["core_worldview"] = self._generate_worldview(tropes, plan)
        
        # 4. 势力系统
        logger.info("生成势力系统...")
        products["faction_system"] = self._generate_faction_system(tropes, plan)
        
        # 5. 角色设计
        logger.info("生成角色设计...")
        products["character_design"] = self._generate_characters(tropes, plan)
        
        # 6. 升级路线
        logger.info("生成升级路线...")
        products["global_growth_plan"] = self._generate_growth_plan(tropes, plan)
        
        # 7. 阶段写作计划
        logger.info("生成阶段写作计划...")
        products["stage_writing_plans"] = self._generate_stage_plans(tropes, plan)
        
        # 8. 情绪蓝图
        logger.info("生成情绪蓝图...")
        products["emotional_blueprint"] = self._generate_emotional_blueprint(tropes, plan)
        
        # 9. 期待感映射
        logger.info("生成期待感映射...")
        products["expectation_mapping"] = self._generate_expectation_mapping(tropes, plan)
        
        logger.info(f"[PhaseOneGenerator] 第一阶段产物生成完成")
        return products
    
    def _generate_writing_style(self, tropes: Dict, plan: Dict) -> Dict:
        """生成写作风格指南（基于套路）"""
        return {
            "core_style": "快节奏、直白、爽点密集",
            "sentence_structure": {
                "description": "短句为主，避免长句",
                "example": "他笑了。笑得很冷。"
            },
            "paragraph_structure": {
                "description": "每段不超过3行，适合手机阅读",
                "max_lines_per_paragraph": 3
            },
            "dialogue_style": {
                "format": "直接引语，少用提示语",
                "example": "\"你给我等着！\"",
                "emotion_expression": "通过动作和表情，少用形容词"
            },
            "pacing_requirements": {
                "chapter_ending": "每章结尾必须有钩子",
                "climax_density": "每3-5章一个爽点",
                "conflict_frequency": "冲突不能断，保持张力"
            },
            "language_characteristics": {
                "vocabulary": "口语化，避免生僻词",
                "tone": "直白、有力、不绕弯子",
                "perspective": "第三人称，主角视角",
                "tense": "现在时为主，增强代入感"
            },
            "chapter_techniques": {
                "opening": "直接切入冲突，不要铺垫",
                "ending": "悬念或转折，吊胃口",
                "transition": "简洁过渡，不拖泥带水"
            },
            "taboos": [
                "大段背景介绍",
                "复杂的心理描写",
                "冗长的环境描写",
                "慢节奏的日常",
                "圣母主角",
                "优柔寡断"
            ]
        }
    
    def _generate_market_analysis(self, tropes: Dict, plan: Dict) -> Dict:
        """生成市场分析（基于套路）"""
        return {
            "target_platform": "番茄小说",
            "genre_positioning": tropes.get("genre", ""),
            "target_audience": {
                "age": "18-35岁",
                "gender": "主要为男性",
                "preferences": "喜欢快节奏、爽点密集、升级打脸",
                "reading_time": "碎片时间，手机阅读"
            },
            "market_trends": {
                "current_status": tropes.get("AVAILABLE_GENRES", {}).get(tropes.get("genre", ""), {}).get("market_status", "稳定"),
                "competition_level": tropes.get("AVAILABLE_GENRES", {}).get(tropes.get("genre", ""), {}).get("competition", "激烈"),
                "opportunity": "该题材有稳定读者群，套路成熟，成功率高"
            },
            "selling_points": plan.get("core_selling_points", []),
            "expected_performance": {
                "retention_rate": tropes.get("AVAILABLE_GENRES", {}).get(tropes.get("genre", ""), {}).get("expected_retention", "10-15%"),
                "monetization_potential": "中上",
                "long_term_viability": "该题材有长期读者群，可写到500章+"
            },
            "platform_specific": {
                "title_requirements": "15字以内，有冲击力",
                "chapter_length": "2000-3000字",
                "update_frequency": "日更2章以上",
                "hook_requirements": "每章必须有钩子"
            }
        }
    
    def _generate_worldview(self, tropes: Dict, plan: Dict) -> Dict:
        """生成世界观（基于套路）"""
        worldview_tropes = tropes.get("worldview", {})
        
        return {
            "world_overview": worldview_tropes.get("setting", "现代都市，钱能通神"),
            
            "time_background": "现代，与读者生活相近",
            
            "geography": {
                "main_locations": worldview_tropes.get("required_scenes", [
                    "4S店", "高档餐厅", "直播间", "豪宅", "高档商场"
                ]),
                "location_functions": {
                    "4S店": "装逼打脸高发地，买车展示财力",
                    "高档餐厅": "身份揭示地，请客户吃饭",
                    "直播间": "打赏装逼，吸引粉丝",
                    "豪宅": "身份象征，生活改善",
                    "高档商场": "消费打脸，购物展示"
                }
            },
            
            "power_system": {
                "name": "资金等级体系",
                "description": "以资金量划分社会等级",
                "levels": [
                    {"name": "穷屌丝", "threshold": 0, "description": "开局状态"},
                    {"name": "万元户", "threshold": 10000, "description": "小有积蓄"},
                    {"name": "百万富翁", "threshold": 1000000, "description": "地方小富"},
                    {"name": "千万富豪", "threshold": 10000000, "description": "地方知名"},
                    {"name": "亿万富翁", "threshold": 100000000, "description": "全国级别"},
                    {"name": "十亿富豪", "threshold": 1000000000, "description": "顶级富豪"},
                    {"name": "全球首富", "threshold": 10000000000, "description": "站在巅峰"}
                ],
                "upgrade_method": "通过系统返利积累资金",
                "social_impact": "资金等级决定社会地位和话语权"
            },
            
            "social_structure": {
                "class_system": "严格的阶层分化",
                "mobility": "资金可以打破阶层壁垒",
                "power_dynamics": "有钱就是大爷，豪车名表是身份象征",
                "conflict_sources": "阶层差距导致的矛盾和冲突"
            },
            
            "world_rules": [
                "钱能解决99%的问题",
                "社会地位由财富决定",
                "系统提供资金，资金带来权力",
                "升级后解锁更高消费场景",
                "打脸是最直接的爽点来源"
            ],
            
            "unique_features": [
                "现代都市背景，读者熟悉",
                "资金体系简单直观",
                "消费场景丰富多样",
                "升级路线清晰可见"
            ]
        }
    
    def _generate_faction_system(self, tropes: Dict, plan: Dict) -> Dict:
        """生成势力系统（基于套路）"""
        antagonist_tropes = tropes.get("antagonist", {})
        
        return {
            "factions": [
                {
                    "name": "主角阵营",
                    "type": "protagonist",
                    "description": "以主角为核心，逐步扩大的势力",
                    "power_level": "随主角成长而成长",
                    "key_members": [plan.get("protagonist", {}).get("basic_info", {}).get("name", "主角")],
                    "goals": "变强、打脸、保护重要的人",
                    "resources": "系统资金、个人能力"
                },
                {
                    "name": "势利眼联盟",
                    "type": "antagonist_early",
                    "description": "初期反派，看不起主角的人",
                    "power_level": "低",
                    "key_members": ["势利眼前女友", "势利眼宝马男", "势利眼上司"],
                    "goals": "维护虚假的优越感",
                    "conflict_with_protagonist": "看不起主角，被主角打脸"
                },
                {
                    "name": "地方富二代集团",
                    "type": "antagonist_mid",
                    "description": "中期反派，地方势力的二代们",
                    "power_level": "中",
                    "key_members": ["富二代A", "富二代B", "家族子弟"],
                    "goals": "维护家族利益，打压新兴势力",
                    "conflict_with_protagonist": "嫉妒主角崛起，试图打压"
                },
                {
                    "name": "资本联盟",
                    "type": "antagonist_late",
                    "description": "后期反派，顶级资本势力",
                    "power_level": "高",
                    "key_members": ["资本大佬A", "资本大佬B", "财团代表"],
                    "goals": "维护资本秩序，控制市场",
                    "conflict_with_protagonist": "主角威胁到他们的利益"
                },
                {
                    "name": "神秘组织",
                    "type": "hidden",
                    "description": "隐藏势力，后期揭晓",
                    "power_level": "极高",
                    "key_members": ["神秘人物（后期揭晓）"],
                    "goals": "未知",
                    "foreshadowing": "前期偶尔提及，增加神秘感"
                }
            ],
            
            "faction_relationships": {
                "early_stage": "主角 vs 势利眼（单方面的碾压）",
                "mid_stage": "主角势力崛起，与富二代集团冲突",
                "late_stage": "主角进入顶级圈子，与资本联盟博弈",
                "final_stage": "揭开神秘组织，最终对决"
            },
            
            "power_dynamics": {
                "early": "主角弱，被欺负",
                "mid": "主角成长，开始反击",
                "late": "主角强大，主导局势",
                "final": "主角登顶，制定规则"
            },
            
            "conflict_escalation": [
                "个人恩怨（被羞辱）",
                "家族对抗（富二代）",
                "资本博弈（商业竞争）",
                "势力对决（终极大战）"
            ]
        }
    
    def _generate_characters(self, tropes: Dict, plan: Dict) -> Dict:
        """生成角色设计（基于套路）"""
        protagonist_plan = plan.get("protagonist", {})
        
        return {
            "main_character": {
                "name": protagonist_plan.get("basic_info", {}).get("name", "主角"),
                "role": " protagonist",
                "importance": "绝对核心，所有剧情围绕他展开",
                
                "basic_info": protagonist_plan.get("basic_info", {}),
                "personality": protagonist_plan.get("personality", {}),
                "initial_state": protagonist_plan.get("initial_state", {}),
                "growth_arc": protagonist_plan.get("growth_arc", {}),
                
                "skills": {
                    "initial": ["吃苦耐劳", "观察力强"],
                    "from_system": ["花钱返利", "后期解锁特殊能力"],
                    "developed": ["商业眼光", "领导能力", "格斗技能"]
                },
                
                "motivations": {
                    "surface": "赚钱，出人头地",
                    "deep": "证明自己，保护重要的人",
                    "evolution": "从个人复仇到保护所爱，再到影响世界"
                },
                
                "relationships": {
                    "love_interest": {
                        "name": "女主（待定）",
                        "type": "慧眼识珠型",
                        "meeting_chapter": "第7章左右",
                        "development": "被主角吸引→深入了解→真心喜欢"
                    },
                    "mentor": None,  # 神豪文通常没有导师
                    "sidekick": {
                        "name": "小弟（待定）",
                        "role": "搞笑担当，衬托主角",
                        "loyalty": "绝对忠诚"
                    }
                }
            },
            
            "antagonists": [
                {
                    "name": "势利眼前女友",
                    "tier": 1,
                    "appearance_chapter": "第1章",
                    "defeat_chapter": "第5章",
                    "personality": "拜金，势利，看不起穷人",
                    "role": "制造开局冲突，被主角打脸后后悔",
                    "pattern": "羞辱主角→主角崛起→跪求复合→被拒绝"
                },
                {
                    "name": "地方富二代",
                    "tier": 2,
                    "appearance_chapter": "第15章",
                    "defeat_chapter": "第30章",
                    "personality": "嚣张跋扈，依靠家族势力",
                    "role": "中期主要反派，推动主角成长",
                    "pattern": "打压主角→主角反击→家族衰败"
                },
                {
                    "name": "资本大佬",
                    "tier": 3,
                    "appearance_chapter": "第50章",
                    "defeat_chapter": "第100章",
                    "personality": "老谋深算，掌控欲强",
                    "role": "后期大反派，终极对手",
                    "pattern": "试探→打压→合作→对抗→臣服"
                }
            ],
            
            "supporting_characters": [
                {
                    "name": "主角父母",
                    "role": "亲情线，被主角保护的对象",
                    "characteristics": "朴实，为儿子骄傲"
                },
                {
                    "name": "小弟A",
                    "role": "搞笑担当，忠诚跟班",
                    "characteristics": "嘴甜，会拍马屁，关键时刻靠谱"
                },
                {
                    "name": "商场经理",
                    "role": "功能性角色，展示主角财力",
                    "pattern": "狗眼看人低→震惊→跪舔"
                }
            ]
        }
    
    def _generate_growth_plan(self, tropes: Dict, plan: Dict) -> Dict:
        """生成升级路线（基于套路）"""
        pacing = tropes.get("pacing", {})
        gf_tropes = tropes.get("golden_finger", {})
        
        return {
            "growth_system": {
                "type": "资金积累+身份升级",
                "mechanism": gf_tropes.get("type", "花钱返利"),
                "upgrade_trigger": "资金达标或完成系统任务"
            },
            
            "milestones": [
                {
                    "chapter": 1,
                    "name": "获得系统",
                    "requirements": "被羞辱后激活",
                    "rewards": ["花钱返利系统", "初始额度1万元/天"],
                    "significance": "故事起点"
                },
                {
                    "chapter": 10,
                    "name": "小有积蓄",
                    "requirements": "累计消费10万元",
                    "rewards": ["系统升级", "额度提升至10万/天", "解锁透视眼"],
                    "significance": "第一次质变"
                },
                {
                    "chapter": 30,
                    "name": "地方富豪",
                    "requirements": "累计消费100万元",
                    "rewards": ["额度100万/天", "解锁格斗术", "进入地方圈子"],
                    "significance": "进入中层社会"
                },
                {
                    "chapter": 50,
                    "name": "省城新贵",
                    "requirements": "累计消费1000万元",
                    "rewards": ["额度1000万/天", "建立自己势力", "进入省城圈子"],
                    "significance": "地图切换，更大的舞台"
                },
                {
                    "chapter": 80,
                    "name": "全国知名",
                    "requirements": "累计消费1亿元",
                    "rewards": ["额度1亿/天", "全国影响力", "进入顶级圈子"],
                    "significance": "成为大人物"
                },
                {
                    "chapter": 120,
                    "name": "顶级富豪",
                    "requirements": "累计消费10亿元",
                    "rewards": ["额度无上限", "全球影响力", "站在巅峰"],
                    "significance": "接近巅峰"
                }
            ],
            
            "daily_goals": [
                "每天花光系统额度",
                "完成系统任务",
                "打脸一个看不起自己的人",
                "提升一点实力或影响力"
            ],
            
            "long_term_goals": [
                "成为全球首富",
                "让所有看不起自己的人后悔",
                "保护所有重要的人",
                "建立商业帝国"
            ]
        }
    
    def _generate_stage_plans(self, tropes: Dict, plan: Dict) -> Dict:
        """生成阶段写作计划（基于套路）"""
        outline = plan.get("outline_first_30", [])
        
        # 基于大纲生成详细的阶段计划
        return {
            "stage_1_opening": {
                "chapters": "1-30",
                "theme": "获得系统，初步崛起",
                "major_events": [
                    {"chapter": 1, "event": "获得系统", "type": "转折"},
                    {"chapter": 5, "event": "第一次打脸前女友", "type": "爽点"},
                    {"chapter": 10, "event": "系统升级，买豪车", "type": "爽点"},
                    {"chapter": 20, "event": "击败地方混混", "type": "爽点"},
                    {"chapter": 30, "event": "进入地方富豪圈子", "type": "升级"}
                ],
                "climax_frequency": "每3-5章一个爽点",
                "emotion_curve": "压抑→希望→爽快→期待"
            },
            
            "stage_2_development": {
                "chapters": "31-80",
                "theme": "建立势力，对抗富二代",
                "major_events": [
                    {"chapter": 40, "event": "建立自己公司", "type": "升级"},
                    {"chapter": 50, "event": "进入省城", "type": "转折"},
                    {"chapter": 60, "event": "与省城富二代冲突", "type": "冲突"},
                    {"chapter": 70, "event": "收服省城势力", "type": "爽点"},
                    {"chapter": 80, "event": "成为省城新贵", "type": "升级"}
                ],
                "climax_frequency": "每5章一个大爽点",
                "emotion_curve": "挑战→奋斗→胜利→更大挑战"
            },
            
            "stage_3_peak": {
                "chapters": "81-150",
                "theme": "全国级别，资本博弈",
                "major_events": [
                    {"chapter": 100, "event": "对抗资本联盟", "type": "大冲突"},
                    {"chapter": 120, "event": "击败资本大佬", "type": "大爽点"},
                    {"chapter": 150, "event": "成为全国首富", "type": "巅峰"}
                ],
                "climax_frequency": "每10章一个超大爽点",
                "emotion_curve": "博弈→胜利→巅峰"
            },
            
            "per_chapter_requirements": {
                "every_chapter_must_have": [
                    "推进剧情",
                    "展示主角状态",
                    "为下章铺垫"
                ],
                "chapter_ending_must_have": [
                    "钩子（悬念、转折、期待）"
                ],
                "climax_chapter_must_have": [
                    "反派挑衅",
                    "主角反击",
                    "周围人震惊",
                    "反派后悔/恐惧"
                ]
            }
        }
    
    def _generate_emotional_blueprint(self, tropes: Dict, plan: Dict) -> Dict:
        """生成情绪蓝图（基于套路）"""
        return {
            "overall_emotional_arc": "压抑→愤怒→反击→爽快→期待→更大的压抑→更大的爽快",
            
            "chapter_emotions": {
                "opening_chapters": {
                    "1-3": "愤怒+期待（被羞辱，获得系统）",
                    "4-10": "爽快（连续打脸）",
                    "11-20": "自信+挑战（遇到更强敌人）",
                    "21-30": "爆发+满足（阶段高潮）"
                },
                "emotional_cycle": "每10章一个情绪循环"
            },
            
            "key_emotional_moments": [
                {"chapter": 1, "emotion": "屈辱+希望", "trigger": "被羞辱后获得系统"},
                {"chapter": 5, "emotion": "爽快", "trigger": "第一次打脸成功"},
                {"chapter": 10, "emotion": "满足", "trigger": "系统升级，实力提升"},
                {"chapter": 30, "emotion": "成就感", "trigger": "成为地方富豪"},
                {"chapter": 50, "emotion": "期待", "trigger": "进入省城，更大的舞台"}
            ],
            
            "emotional_techniques": {
                "contrast": "先抑后扬，压抑越深爆发越爽",
                "foreshadowing": "提前铺垫，增加期待感",
                "pacing": "情绪高低起伏，不要一直平或一直高",
                "reader_identification": "让读者代入主角，感受主角的情绪"
            }
        }
    
    def _generate_expectation_mapping(self, tropes: Dict, plan: Dict) -> Dict:
        """生成期待感映射（基于套路）"""
        return {
            "expectation_hooks": [
                {
                    "chapter": 1,
                    "hook": "系统刚激活，主角即将开始逆袭",
                    "payoff_chapter": 3,
                    "type": "short_term"
                },
                {
                    "chapter": 5,
                    "hook": "前女友被打脸，但她家族不会善罢甘休",
                    "payoff_chapter": 15,
                    "type": "mid_term"
                },
                {
                    "chapter": 30,
                    "hook": "省城的大门已经打开，更大的挑战在等着",
                    "payoff_chapter": 50,
                    "type": "long_term"
                },
                {
                    "chapter": 100,
                    "hook": "神秘组织的线索出现，背后有更大的阴谋",
                    "payoff_chapter": 200,
                    "type": "mega_long_term"
                }
            ],
            
            "suspense_techniques": [
                "每章结尾留钩子",
                "埋下伏笔，后期回收",
                "制造信息差（读者知道主角有系统，反派不知道）",
                "设置倒计时（系统任务有时间限制）",
                "暗示更大的敌人存在"
            ],
            
            "payoff_planning": [
                {"chapter": 10, "payoff": "完成第一阶段打脸"},
                {"chapter": 30, "payoff": "成为地方富豪"},
                {"chapter": 50, "payoff": "在省城站稳脚跟"},
                {"chapter": 100, "payoff": "击败资本大佬"}
            ]
        }


# 便捷函数
def generate_market_driven_phase_one(genre: str, tropes: Dict, plan: Dict, api_client=None) -> Dict:
    """
    便捷函数：生成市场导向第一阶段产物
    """
    generator = MarketDrivenPhaseOneGenerator(api_client=api_client)
    return generator.generate_all_products(genre, tropes, plan)
