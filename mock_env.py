"""
Mock Environment Configuration
模拟环境配置 - 用于快速测试而不调用真实API
"""

import os
from typing import Dict, Any, Optional

# 模拟环境标志
MOCK_MODE = os.getenv('MOCK_MODE', '1') == '1'

# 模拟API配置
MOCK_API_CONFIG = {
    "enabled": True,
    "response_delay": 0.1,  # 模拟网络延迟（秒）
    "response_quality": "high",  # high, medium, low

    # 模拟小说内容
    "mock_novel": {
        "title": "测试小说：星河剑神",
        "synopsis": "在浩瀚的宇宙中，少年李凡获得神秘传承，从一个小小的学徒成长为一代剑神的传奇故事。",
        "core_setting": "星际修仙世界，科技与修仙并存，宇宙中存在多个位面和星域",
        "core_selling_points": ["爽文节奏", "天才主角", "升级打脸", "美女环绕"],
        "total_chapters": 10  # 模拟生成10章
    },

    # 模拟章节内容模板
    "chapter_templates": {
        "start": "第{}章：",
        "content_length": 1500,  # 字符数
        "plot_types": ["升级", "战斗", "修炼", "奇遇", "打脸"]
    },

    # 模拟评分
    "mock_scores": {
        "min": 8.0,
        "max": 9.5,
        "avg": 8.7
    }
}

class MockAPIClient:
    """模拟API客户端 - 返回预定义的响应数据"""

    def __init__(self, config=None):
        self.config = MOCK_API_CONFIG
        self.logger = None

    def set_logger(self, logger):
        """设置日志记录器"""
        self.logger = logger
        if logger:
            logger.info("✅ Mock API Client 已初始化")

    def call_api(self, messages: list, role_name: str = None, **kwargs) -> str:
        """返回模拟的API响应"""

        import time
        import json
        import random

        # 模拟网络延迟
        time.sleep(self.config["response_delay"])

        content = messages[-1]["content"] if messages else ""

        # 根据请求内容返回不同的模拟数据
        if "创意" in content or "精炼" in content:
            return self._mock_creative_refinement()

        elif "大纲" in content and "章节" in content:
            chapter_num = self._extract_chapter_number(content)
            return self._mock_chapter_outline(chapter_num)

        elif "内容" in content and "章节" in content:
            chapter_num = self._extract_chapter_number(content)
            return self._mock_chapter_content(chapter_num)

        elif "评估" in content or "评分" in content:
            return self._mock_quality_assessment()

        elif "方案" in content or "计划" in content:
            return self._mock_novel_plan()

        else:
            return self._mock_default_response()

    def _extract_chapter_number(self, content: str) -> int:
        """从内容中提取章节编号"""
        import re
        match = re.search(r'(\d+)', content)
        return int(match.group(1)) if match else 1

    def _mock_creative_refinement(self) -> str:
        """模拟创意精炼响应"""
        return json.dumps({
            "type": "creative_refinement",
            "data": {
                "title": "星河剑神：从废柴到宇宙至尊",
                "synopsis": "在九天十地，万族并存的宇宙纪元，少年李凡偶得鸿蒙剑典，从废柴逆袭，脚踏九霄，剑指苍穹",
                "core_setting": "多元宇宙修仙体系，剑道为尊，科技与修仙融合",
                "characters": {
                    "protagonist": "李凡（穿越者，获得鸿蒙剑典）",
                    "love_interest": "瑶池圣女（天界第一美女）",
                    "rival": "天尊之子（第一反派）"
                },
                "selling_points": [
                    "天才主角，隐藏身份",
                    "神秘传承，逆天改命",
                    "美女环绕，暧昧无限",
                    "升级打脸，爽文节奏"
                ]
            }
        }, ensure_ascii=False, indent=2)

    def _mock_chapter_outline(self, chapter_num: int) -> str:
        """模拟章节大纲生成"""
        plot_types = self.config["chapter_templates"]["plot_types"]
        plot_type = random.choice(plot_types)

        outlines = {
            "升级": f"李凡在星辰森林中偶然发现一处上古遗迹，通过破解遗迹中的剑意传承，修为大增，突破到筑基后期",
            "战斗": f"李凡在天机城中遭遇天尊之子的挑衅，两人展开惊天大战，李凡以一敌三，震惊全城",
            "修炼": f"李凡进入九重天进行闭关修炼，参悟剑道真谛，修为瓶颈松动，准备突破金丹期",
            "奇遇": f"李凡在探索虚空乱流时，意外发现一颗远古星辰，上面留有剑仙传承，获得无上剑法",
            "打脸": f"天尊之子在宗门大比上公开嘲讽李凡是废柴，结果李凡一剑击败对手，打脸所有看不起他的人"
        }

        return json.dumps({
            "type": "chapter_outline",
            "data": {
                "章节标题": f"第{chapter_num}章{plot_type}之路",
                "剧情类型": plot_type,
                "核心冲突": "主角与反派的冲突升级",
                "人物发展": "李凡修为和心境的成长",
                "世界观推进": f"揭示了宇宙第{chapter_num}层的秘密",
                "伏笔设置": "为后续剧情埋下重要伏笔",
                "情感线": "与瑶池圣女的关系进展",
                "字数预估": 2000,
                "场景设定": {
                    "地点": self._generate_scene(chapter_num),
                    "时间": f"故事第{chapter_num*10}天",
                    "氛围": "热血沸腾，紧张刺激"
                },
                "剧情大纲": outlines.get(plot_type, "主角继续修仙路上的冒险"),
                "本章目标": f"推进主线剧情到第{chapter_num+1}阶段"
            }
        }, ensure_ascii=False, indent=2)

    def _mock_chapter_content(self, chapter_num: int) -> str:
        """模拟章节内容生成"""
        content_templates = [
            f"第{chapter_num}章 星河剑影\n\n九天之上，风云变幻。\n\n李凡手持长剑，傲立九霄，目光如电，凝视着远方的天际。自从获得鸿蒙剑典以来，他的修为一日千里，如今已经站在了筑基期的巅峰。\n\n" +
            f"修仙之路，本就是逆天而行。李凡深知这一点，所以他更加努力地修炼。在这一天，他终于感受到了突破的契机。\n\n" +
            f"金丹大道，近在眼前！\n\n李凡深吸一口气，开始运转鸿蒙剑典中的秘法。霎时间，天地间的灵气疯狂地向他的体内涌去。",

            f"第{chapter_num}章 剑指苍穹\n\n风云际会，龙争虎斗。\n\n这一日，李凡来到了天机城。这座城池建立在虚空之中，是九天十地最为繁华的修行之地。然而，等待他的却是前所未有的挑战。\n\n" +
            f"天尊之子站在高台之上，冷笑着俯视着李凡："区区筑基修士，也敢来天机城耀武扬威？"\n\n"玄天剑诀第一式！"李凡厉声大喝，长剑出鞘，寒光四射。",

            f"第{chapter_num}章 情动九天\n\n月华如水，星河璀璨。\n\n在瑶池圣女的静室中，李凡正在接受她的指导。这位被誉为天界第一美女的圣女，不仅修为高深，更重要的是她那颗纯净的心。\n\n"李凡，你的剑法很特别。"瑶池圣女轻声说道，眼中闪过一丝异彩。\n\n李凡心中一动，他能感受到瑶池圣女的好感。但是，他知道自己的路还很长，现在还不是儿女情长的时候。"
        ]

        return random.choice(content_templates)

    def _mock_quality_assessment(self) -> str:
        """模拟质量评估"""
        min_score = self.config["mock_scores"]["min"]
        max_score = self.config["mock_scores"]["max"]
        score = random.uniform(min_score, max_score)

        return json.dumps({
            "type": "quality_assessment",
            "data": {
                "整体评分": round(score, 1),
                "评级": "优秀" if score >= 9.0 else "良好" if score >= 8.0 else "及格",
                "优点": [
                    "情节紧凑，节奏明快",
                    "人物塑造鲜明，有血有肉",
                    "世界观设定宏大且自洽",
                    "文笔流畅，语言生动",
                    "悬念设置巧妙，引人入胜"
                ],
                "改进建议": [
                    "可以考虑增加更多细节描写",
                    "人物对话可以更加个性化",
                    "战斗场面可以更加激烈刺激",
                    "情感发展可以更加细腻"
                ],
                "章节质量": {
                    "情节发展": round(score, 1),
                    "人物塑造": round(score - 0.2, 1),
                    "文笔表达": round(score + 0.1, 1),
                    "世界观": round(score, 1),
                    "情感描写": round(score - 0.3, 1)
                },
                "总体评价": "本章内容质量上乘，情节发展合理，人物塑造鲜明，符合网络文学的创作标准。"
            }
        }, ensure_ascii=False, indent=2)

    def _mock_novel_plan(self) -> str:
        """模拟小说方案生成"""
        return json.dumps({
            "type": "novel_plan",
            "data": {
                "title": "星河剑神",
                "genre": "玄幻修仙",
                "target_audience": "15-35岁男性读者",
                "word_count": "300万字",
                "chapter_count": 100,
                "plot_structure": {
                    "opening": "主角李凡穿越异界，获得神秘传承",
                    "development": "逐步成长，遇到挑战，结交盟友",
                    "climax": "对抗最终反派，拯救宇宙",
                    "ending": "成为宇宙至尊，开创新纪元"
                },
                "character_arc": {
                    "start": "废柴学生",
                    "growth": "勤奋修炼，突破自我",
                    "peak": "宇宙剑神",
                    "transformation": "从平凡到伟大的蜕变"
                },
                "selling_points": [
                    "天才主角，隐藏身份",
                    "神秘传承，逆天改命",
                    "美女环绕，暧昧无限",
                    "升级打脸，爽文节奏",
                    "宏大世界，宇宙冒险"
                ]
            }
        }, ensure_ascii=False, indent=2)

    def _mock_default_response(self) -> str:
        """模拟默认响应"""
        return json.dumps({
            "type": "default_response",
            "data": {
                "message": "模拟API响应",
                "status": "success",
                "content": "这是一个模拟的响应内容"
            }
        }, ensure_ascii=False, indent=2)

    def _generate_scene(self, chapter_num: int) -> str:
        """生成场景描述"""
        scenes = [
            "九天云海之上的修仙圣地",
            "虚空乱流中的神秘星辰",
            "古老的遗迹深处",
            "繁华的修仙城池",
            "危机四伏的禁地",
            "充满机缘的秘境",
            "宗门大比现场",
            "雷劫降临之地"
        ]
        return scenes[chapter_num % len(scenes)]


# 创建全局模拟客户端实例
mock_api_client = MockAPIClient()


def get_mock_client():
    """获取模拟API客户端实例"""
    return mock_api_client


def enable_mock_mode():
    """启用模拟模式"""
    global MOCK_MODE
    MOCK_MODE = True


def disable_mock_mode():
    """禁用模拟模式"""
    global MOCK_MODE
    MOCK_MODE = False


def is_mock_mode():
    """检查是否处于模拟模式"""
    return MOCK_MODE