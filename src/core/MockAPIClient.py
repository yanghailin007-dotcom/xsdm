"""
模拟 API 客户端 - 用于快速测试，不需要真实的 AI API 调用
Mock API Client for fast testing without real AI API calls
"""
import sys
from pathlib import Path

# 添加项目根目录到Python路径
BASE_DIR = Path(__file__).parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

import json
import time
from typing import Dict, Any, Optional
from src.utils.logger import get_logger
logger = get_logger("MockAPIClient")
class MockAPIClient:
    """模拟API客户端 - 返回预定义的高质量数据"""
    def __init__(self, config=None):
        self.config = config or {}
        self.logger = logger
        self.call_count = 0
        self.logger.info("✅ MockAPIClient 初始化 (测试模式)")
    def get_default_provider(self):
        """获取默认提供商"""
        return "mock"
    def get_current_model(self):
        """获取当前模型"""
        return "MockModel"
    def call_api(self, system_prompt: str, user_prompt: str, temperature: float = None, purpose: str = "未知", provider: str = None) -> str:
        """模拟API调用 - 返回JSON字符串格式"""
        self.call_count += 1
        time.sleep(0.2)  # 模拟API延迟
        self.logger.info(f"🎭 模拟API调用 ({purpose}) - 调用#{self.call_count}")
        # 根据不同的目的返回不同的模拟数据
        purpose_lower = purpose.lower()
        if "创意精炼" in purpose_lower or "creative_refinement" in purpose_lower:
            result = self._mock_creative_refinement()
        elif "小说方案" in purpose_lower or "one_plans" in purpose_lower:
            result = self._mock_novel_plan()
        elif "方案" in purpose_lower or "plan" in purpose_lower:
            result = self._mock_novel_plan()  # 通用方案映射到小说方案
        elif "情绪蓝图" in purpose_lower or "emotional_blueprint" in purpose_lower:
            result = self._mock_emotional_blueprint()
        elif "阶段计划" in purpose_lower or "stage_writing_plan" in purpose_lower:
            result = self._mock_stage_plan()
        elif "章节大纲" in purpose_lower or "chapter_outline" in purpose_lower:
            result = self._mock_chapter_outline()
        elif "章节内容" in purpose_lower or "chapter_content" in purpose_lower:
            result = self._mock_chapter_content()
        elif "质量评估" in purpose_lower or "quality_assessment" in purpose_lower:
            result = self._mock_quality_assessment()
        else:
            # 默认返回小说方案作为通用响应
            result = self._mock_novel_plan()
        import json
        return json.dumps(result, ensure_ascii=False, indent=2)
    def generate_content_with_retry(self, content_type: str, user_prompt: str, 
                                  temperature: float = None, purpose: str = "内容生成",
                                  provider: str = None, enable_prompt_optimization: bool = False) -> Dict[str, Any]:
        """模拟生成内容 - 与 APIClient 签名兼容
        参数映射：content_type (内容类型ID) -> 模拟输出类型"""
        self.call_count += 1
        time.sleep(0.2)  # 模拟API延迟（加快测试速度）
        # 使用 content_type 作为内容类型标识
        self.logger.info(f"🎭 模拟生成 ({content_type}) - 调用#{self.call_count}")
        # 根据不同的内容类型返回不同的模拟数据
        content_type_lower = content_type.lower()
        # 按优先级排序条件匹配（更具体的条件应该先检查）
        if "质量评估" in content_type_lower or "quality_assessment" in content_type_lower or "plan_quality_evaluation" in content_type_lower:
            return self._mock_quality_assessment()
        elif "新鲜度" in content_type_lower or "freshness_assessment" in content_type_lower:
            return {"score": {"total": 8.5}, "assessment": "方案具有较好的创新性和市场吸引力"}
        elif "overall_stage_plan" in content_type_lower or "全书阶段计划" in content_type_lower:
            return self._mock_overall_stage_plan()
        elif "小说方案" in content_type_lower or "one_plans" in content_type_lower or "multiple_plans" in content_type_lower or ("plan" in content_type_lower and "quality" not in content_type_lower and "stage" not in content_type_lower):
            return self._mock_novel_plan()
        elif "情绪蓝图" in content_type_lower or "emotional_blueprint" in content_type_lower:
            return self._mock_emotional_blueprint()
        elif "阶段计划" in content_type_lower or "stage_writing_plan" in content_type_lower:
            return self._mock_stage_plan()
        elif "情绪规划" in content_type_lower or "stage_emotional_planning" in content_type_lower:
            return self._mock_stage_emotional_planning()
        elif "主龙骨" in content_type_lower or "stage_major_event_skeleton" in content_type_lower:
            return self._mock_major_event_skeleton()
        elif "分解" in content_type_lower or "decomposition" in content_type_lower:
            return self._mock_major_event_decomposition()
        elif "章节大纲" in content_type_lower or "chapter_outline" in content_type_lower:
            return self._mock_chapter_outline()
        elif "章节内容" in content_type_lower or "chapter_content" in content_type_lower:
            return self._mock_chapter_content()
        elif "创意精炼" in content_type_lower or "creative_refinement" in content_type_lower:
            return self._mock_creative_refinement()
        elif "special_event_scene_generation" in content_type_lower:
            return self._mock_special_event_scene_generation()
        else:
            return {"result": "模拟响应", "content_type": content_type}
    def _mock_novel_plan(self) -> Dict:
        """模拟小说方案"""
        single_plan = {
            "title": "异界归来的天才医生",
            "synopsis": "天才医生林晨穿越到异界，凭借前世医学知识和意外获得的系统，在异界成为传奇医者。",
            "core_direction": "穿越 + 医学 + 系统 + 异界冒险",
            "target_audience": "男性网文读者",
            "competitive_advantage": "独特的医学设定结合异界背景，形成差异化的爽点",
            "main_characters": [
                {"name": "林晨", "role": "主角", "description": "天才医生，穿越异界后成为传奇医者"},
                {"name": "云尘仙", "role": "女主", "description": "异界贵族少女，医学天才的徒弟和伙伴"},
            ],
            "key_systems": {
                "medicine_system": "通过医学知识和秘制药物获得力量",
                "cultivation_system": "异界修炼体系与医学融合"
            },
            "plot_outline": {
                "opening": "穿越异界，初显医术",
                "development": "建立医疗帝国，救死扶伤",
                "climax": "对抗邪恶势力，医学救世",
                "ending": "成为异界医学之神"
            }
        }
        # 为multiple_plans返回包含plans数组的结构
        return {
            "plans": [single_plan, single_plan, single_plan]  # 返回3个方案
        }
    def _mock_emotional_blueprint(self) -> Dict:
        """模拟情绪蓝图"""
        return {
            "overall_emotional_tone": "热血治愈的医学冒险史",
            "emotional_spectrum": ["爽快感", "治愈感", "成就感", "紧张感"],
            "stage_emotional_arcs": {
                "opening_stage": {
                    "description": "初入异界，震撼与希望并存",
                    "start_emotion": "震撼、迷茫",
                    "end_emotion": "希望、决心"
                },
                "development_stage": {
                    "description": "建立医疗帝国，收获与挑战",
                    "start_emotion": "决心、期待",
                    "end_emotion": "成就感、自豪感"
                },
                "climax_stage": {
                    "description": "终极对决，医学救世",
                    "start_emotion": "紧张、危机感",
                    "end_emotion": "胜利、荣耀"
                },
                "ending_stage": {
                    "description": "新时代开启，医学统治",
                    "start_emotion": "满足感",
                    "end_emotion": "永恒的成就感"
                }
            }
        }
    def _mock_stage_plan(self) -> Dict:
        """模拟阶段计划"""
        return {
            "stage_name": "opening_stage",
            "chapter_range": "1-10",
            "stage_overview": "主角穿越异界，初展医术，建立势力基础",
            "targets": {
                "major_plot_points": [
                    "第1章: 穿越异界的医生",
                    "第3章: 初战异兽",
                    "第5章: 建立医疗点",
                    "第8章: 收服第一批追随者",
                    "第10章: 初步势力成型"
                ],
                "character_development": "主角从迷茫到找到目标，逐步建立领导力",
                "emotional_curve": "从震撼到希望再到决心的递进",
                "key_elements": ["医术展示", "异界规则认知", "势力建设"]
            },
            "writing_plan": {
                "narrative_pace": "快节奏，每章都有推进",
                "scene_distribution": "战斗30%，情节40%，对话30%",
                "dialogue_requirements": "展现医学知识，建立人物魅力",
                "action_design": "融合医学和战斗的创意场景"
            }
        }
    def _mock_overall_stage_plan(self) -> Dict:
        """模拟全书阶段计划 - 返回四幕式（起承转合）"""
        return {
            "overall_stage_plan": {
                "opening_stage": {
                    "stage_name": "起 (开局阶段)",
                    "chapter_range": "1-30",
                    "stage_arc_goal": "快速吸引读者，建立世界观基础，引入核心冲突",
                    "stage_overview": "主角穿越异界，初展医术，逐步建立势力基础",
                    "key_plot_points": [
                        "第1章: 穿越异界的医生",
                        "第3章: 初战异兽，医术显威",
                        "第10章: 建立医疗据点",
                        "第20章: 收服核心追随者",
                        "第30章: 初步势力成型，引发关注"
                    ],
                    "character_development": "主角从迷茫到适应，逐步建立领导力",
                    "emotional_goals": "从震撼→希望→决心的递进，读者跟随主角的成长",
                    "expected_reader_engagement": "高，新奇设定+爽点频出"
                },
                "development_stage": {
                    "stage_name": "承 (发展阶段)",
                    "chapter_range": "31-100",
                    "stage_arc_goal": "深化矛盾，扩大势力，展现系统力量，积累伏笔",
                    "stage_overview": "主角医术精进，势力扩张，与其他势力互动，大小冲突不断",
                    "key_plot_points": [
                        "第40章: 医学奇迹引发关注",
                        "第50章: 势力壮大，面临更强敌手",
                        "第70章: 重大背景揭露，伏笔铺设",
                        "第80章: 势力内部考验",
                        "第100章: 面临严峻挑战"
                    ],
                    "character_development": "主角实力提升，性格沉淀，感情线初现",
                    "emotional_goals": "期待感、紧张感交替，读者投入故事世界",
                    "expected_reader_engagement": "稳定高位，伏笔吊胃口"
                },
                "climax_stage": {
                    "stage_name": "转 (高潮阶段)",
                    "chapter_range": "101-160",
                    "stage_arc_goal": "主要矛盾全面爆发，迎来决定性转折，情感集中宣泄",
                    "stage_overview": "隐藏势力现身，主角被迫应战，生死考验，势力危急",
                    "key_plot_points": [
                        "第105章: 陰谋曝光，关键敵手现身",
                        "第120章: 大规模战役，主角被压制",
                        "第135章: 反转，主角系统升级/新力量觉醒",
                        "第145章: 决战，关键人物牺牲/背叛",
                        "第160章: 胜利，但付出巨大代价"
                    ],
                    "character_development": "主角蜕变，人性考验，信念坚定或动摇",
                    "emotional_goals": "高度紧张→绝望→希望→爆发→释放的完整弧线",
                    "expected_reader_engagement": "极高，追读高峰期"
                },
                "ending_stage": {
                    "stage_name": "合 (结局阶段)",
                    "chapter_range": "161-200",
                    "stage_arc_goal": "解决所有核心冲突，回收伏笔，交代人物归宿，升华主题",
                    "stage_overview": "战后重建，真相大白，主角成就传说，新的平衡建立",
                    "key_plot_points": [
                        "第165章: 战后清理，隐藏真相浮出",
                        "第180章: 伏笔回收，大陰谋揭露",
                        "第190章: 人物个人线收尾，感情归宿",
                        "第195章: 主角成就确立，成为传说",
                        "第200章: 尾声，暗示新的篇章（开放式结局或完整收尾）"
                    ],
                    "character_development": "各重要人物归宿确定，成长完成",
                    "emotional_goals": "满足感、升华感、期待感（如有续作）的平衡",
                    "expected_reader_engagement": "高，期待完整答案和人物圆满"
                }
            },
            "stage_structure_rationale": "采用经典【起承转合】四段式，与读者期待心理曲线完美契合，确保节奏感强劲，高潮充分释放",
            "cross_stage_consistency": {
                "character_arcs": "主角: 迷茫→适应→成长→蜕变; 女主: 陌生人→伙伴→信任者→爱人",
                "power_progression": "系统逐阶段解锁，与剧情难度匹配",
                "world_discovery": "逐步展开异界设定，高潮时真相大白"
            }
        }
    def _mock_stage_emotional_planning(self) -> Dict:
        """模拟阶段情绪规划生成"""
        return {
            "stage_name": "opening_stage",
            "main_emotional_arc": "从惊异到期待的递进",
            "emotional_segments": [
                {
                    "segment_name": "异界降临，震撼与迷茫",
                    "chapter_range": "1-10",
                    "target_emotion_keyword": "震撼/迷茫",
                    "core_emotional_task": "通过陌生的异界环境和突兀的穿越经历，让读者感受到主角的震撼和不安。同时，通过医学系统的出现，给予读者惊喜和期待，为后续冒险埋下伏笔。"
                },
                {
                    "segment_name": "初展医术，希望萌生",
                    "chapter_range": "11-20",
                    "target_emotion_keyword": "希望/期待",
                    "core_emotional_task": "通过主角利用医学知识救治病人，展示他的能力和智慧。医术的成功给予主角和读者信心，让读者对主角的未来充满期待。"
                },
                {
                    "segment_name": "势力初成，决心坚定",
                    "chapter_range": "21-30",
                    "target_emotion_keyword": "决心/成就感",
                    "core_emotional_task": "主角逐步建立势力基础，收服追随者，取得第一批胜利。这给予读者强烈的代入感和成就感，为进入发展阶段做好情绪铺垫。"
                }
            ]
        }
    def _mock_major_event_skeleton(self) -> Dict:
        """模拟主龙骨（重大事件骨架）生成"""
        # 返回包含major_event_skeletons列表的结构，以匹配期望的数据格式
        return {
            "major_event_skeletons": [
                {
                    "name": "主要情节事件 1",
                    "role_in_stage_arc": "起",
                    "chapter_range": "1-15",
                    "main_goal": "引入核心冲突，建立舞台",
                    "emotional_arc": "从迷茫到期待",
                    "description": "主角初入新阶段，接触核心冲突，建立故事基础。"
                },
                {
                    "name": "主要情节事件 2",
                    "role_in_stage_arc": "承",
                    "chapter_range": "16-25",
                    "main_goal": "深化矛盾，推动发展",
                    "emotional_arc": "紧张与挑战",
                    "description": "主角应对挑战，能力提升，积累冲突势能。"
                },
                {
                    "name": "主要情节事件 3",
                    "role_in_stage_arc": "转",
                    "chapter_range": "26-28",
                    "main_goal": "创造转折点，扭转局势",
                    "emotional_arc": "突转与新希望",
                    "description": "关键信息或能力出现，局面发生重大转变。"
                },
                {
                    "name": "主要情节事件 4",
                    "role_in_stage_arc": "合",
                    "chapter_range": "29-30",
                    "main_goal": "完成阶段任务，埋下伏笔",
                    "emotional_arc": "满足与期待",
                    "description": "阶段目标达成，为下一阶段埋下伏笔。"
                }
            ]
        }
    def _mock_major_event_decomposition(self) -> Dict:
        """模拟重大事件分解生成（中型事件和特殊情感事件）"""
        return {
            "name": "主要情节事件分解",
            "type": "major_event",
            "role_in_stage_arc": "起",
            "main_goal": "实现阶段核心目标",
            "emotional_goal": "递进式情绪提升",
            "chapter_range": "1-30",
            "composition": {
                "起": [
                    {
                        "name": "开篇引入",
                        "type": "medium_event",
                        "chapter_range": "1-5",
                        "decomposition_type": "chapter_then_scene",
                        "main_goal": "快速吸引读者，建立世界观",
                        "emotional_focus": "惊喜与好奇",
                        "emotional_intensity": "medium",
                        "key_emotional_beats": ["陌生感", "惊喜", "期待"],
                        "description": "主角进入新环境，初步展现能力",
                        "contribution_to_major": "为整个阶段奠定基础"
                    }
                ],
                "承": [
                    {
                        "name": "能力初显",
                        "type": "medium_event",
                        "chapter_range": "6-15",
                        "decomposition_type": "chapter_then_scene",
                        "main_goal": "展示主角核心能力，收获成就感",
                        "emotional_focus": "自信与成长",
                        "emotional_intensity": "medium",
                        "key_emotional_beats": ["挑战", "克服", "成就"],
                        "description": "主角通过行动解决问题，逐步建立信誉",
                        "contribution_to_major": "累积支持者，推进情节"
                    }
                ],
                "转": [
                    {
                        "name": "局面升级",
                        "type": "medium_event",
                        "chapter_range": "16-25",
                        "decomposition_type": "chapter_then_scene",
                        "main_goal": "出现新的挑战或敌手，冲突升级",
                        "emotional_focus": "紧张与危机感",
                        "emotional_intensity": "high",
                        "key_emotional_beats": ["威胁", "困境", "决心"],
                        "description": "出现更强大的对手或新的困难",
                        "contribution_to_major": "为高潮做铺垫"
                    }
                ],
                "合": [
                    {
                        "name": "阶段小高潮",
                        "type": "medium_event",
                        "chapter_range": "26-30",
                        "decomposition_type": "direct_scene",
                        "main_goal": "完成阶段目标，为下阶段铺垫",
                        "emotional_focus": "胜利与新期待",
                        "emotional_intensity": "high",
                        "key_emotional_beats": ["突破", "成功", "新希望"],
                        "description": "主角克服困难，取得重大胜利，引发后续变化",
                        "contribution_to_major": "连接到下一个重大事件"
                    }
                ]
            },
            "special_emotional_events": [
                {
                    "name": "关键时刻的独白",
                    "type": "special_emotional_event",
                    "placement_hint": "在'承'部分结尾，'转'部分开始前",
                    "chapter_range": "15-15",
                    "purpose": "通过主角的内心独白，深化读者对其动机和信念的理解",
                    "event_subtype": "introspection"
                }
            ],
            "emotional_arc_summary": "从陌生到熟悉，从怀疑到确信，从困难到胜利的完整弧线",
            "aftermath": "为下一阶段的冲突和成长奠定基础"
        }
    def _mock_chapter_outline(self) -> Dict:
        """模拟章节大纲"""
        return {
            "chapter_number": 1,
            "chapter_title": "异界降临的医生",
            "chapter_summary": "林晨因车祸意外死亡，穿越到异界并获得医学系统。",
            "key_scenes": [
                "车祸死亡的回忆",
                "异界苏醒的震撼",
                "第一次使用医学系统",
                "遇见云尘仙"
            ],
            "emotional_points": [
                "从现代到异界的绝望与惊喜",
                "对新身份的适应与接纳",
                "对医学系统的好奇与惊喜"
            ],
            "target_word_count": 4000,
            "pacing": "适中，引入为主",
            "cliffhanger": "发现异界有一种诡异的疾病在流行"
        }
    def _mock_chapter_content(self) -> Dict:
        """模拟章节内容 - 满足1800字最少要求"""
        content = """第一章 异界降临的医生
林晨睁开眼睛时，第一反应就是——这不是医院。
昏暗的光线透过某种半透明的水晶照入，把周围的环境染成了诡异的青蓝色。天花板不是熟悉的白色吊顶，而是某种粗糙的石材。空气中弥漫着陌生的草本气味，混合着某种金属的冷硬感。这一切都在向他无声地宣告：他已经不在地球了。
这是哪里？
林晨的医学直觉让他瞬间意识到情况的严重性。他试图坐起来，但身体出乎意料地轻盈——不是虚弱的轻盈，而是充满力量的轻盈。肌肉记忆里没有这种感觉，这说明什么？要么是他在做梦，要么是某种完全陌生的神经系统。
【欢迎宿主激活医学系统】
一道声音突然在脑海中响起，伴随着一个半透明的蓝色界面凭空出现。林晨的眼睛瞪得很圆，医学知识中根本没有能解释这个现象的理论。
林晨瞪大了眼睛。这不是幻觉。他摸了摸自己的脸，确认自己还活着，还有意识。但这个界面，这个声音，都是真实的。
【当前身体状态：完美】
【医学知识库：已激活】
【可用技能点：100】
【当前位置：修罗大陆】
林晨颤抖着手指划过面板，感受到了真实的触感。他是医生，学过脑神经科学，也知道幻觉是什么。但这......这不是幻觉。他能感受到系统面板的温度，能听到界面闪动时的声音，能感受到知识涌入脑海的过程。
这时，房间的门被推开了。
一个穿着飘飘然长裙的少女走了进来，她的五官精致得不像真人，眼睛像琥珀一样闪闪发光。她的皮肤泛着淡淡的金色光泽，长发用某种不认识的银色发带绑在脑后。从医学角度来看，这种特征表明她不是普通人类。
"你终于醒了。"少女用带着奇异口音的语调说，"父亲说，从天空降下来的陌生人，一定是被天道眷顾的人。我是云尘仙，这是云家的医疗室。你在这里昏迷了三天三夜。"
林晨看着眼前这个不存在于地球上的生灵，又看了看脑海中那个不可能的系统界面。三天三夜？他失去了三天的记忆。
他很快做出了医生的判断——要么他疯了，要么......他真的穿越了。作为一个经历过十年医学培训的医生，他学会了用理性去对待一切无法解释的现象。现在，理性告诉他：他穿越了。
但不管是哪一种情况，他现在必须活下去。在陌生的世界里生存，首先要了解这个世界的规则。
林晨深吸一口气，对着云尘仙露出了职业的微笑："你好，我是林晨。能告诉我这是哪里，现在什么时间吗？还有，我为什么会昏迷三天？"
云尘仙眨眨眼睛，似乎对林晨的冷静感到惊讶："这是修罗大陆，灵月帝国，云家领地。现在是秋月十五日，天刚亮。你从天空降下来时伤得很重，但很神奇的是，你的伤口自己恢复了。医疗室的仙医们查不出原因。"
"自己恢复了？"林晨按了一下自己的胸口，确实感受到了完整无缺的胸腔。这说明什么？这说明这个系统不只是幻想，它在真实地修复他的身体。
"对。"云尘仙继续说，"父亲本来想把你赶出去，认为你是某个仙宗派来的探子。但我说你可能是医疗天才，所以他同意让你住在这里......三天。现在，你还有一天的时间。"
"一天？"林晨感觉到了压力。这就像在急诊科一样，时间总是有限的。
"对，如果你在一天内治好我的怪病，我们就考虑永久留你。否则，你就得离开。"云尘仙指了指自己的胸口，"这种病，连修罗大陆最好的医师都治不了。他们说这是诅咒。"
诅咒？林晨的医学知识里没有"诅咒"这个词汇，但他知道，许多古老的医学未解之谜，最后都被现代医学解释成了疾病。也许，在这个世界里，"诅咒"就是他需要用"医学系统"来对付的病症。
林晨看着云尘仙，突然感受到了一种熟悉的医学直觉——那种在手术室里、在急诊科里、面对绝望病人时的直觉。这种直觉让他知道：这个少女的病症可能很严重，但也许有办法治。
他的嘴角浮起了一个真实的笑容。这是他从医以来最真诚的笑容。
异界也好，系统也好，诅咒也好，这些都不重要。重要的是，在这个陌生的世界里，他终于找到了熟悉的东西——救死扶伤的机会。
"让我看看。"林晨站起身，走向云尘仙，"告诉我，什么时候开始发病的？症状是什么？疼痛位置在哪里？发病频率是多少？"
云尘仙惊讶地看着这个陌生的男人。在他的眼睛里，那是一种她从未见过的光芒——那是一个医者的光芒，是救赎的光芒，是希望的光芒。
就在这一刻，林晨做出了一个重要的决定。
他不仅要在这个世界活下去。他要成为异界的传奇医者，用现代医学和这个系统的力量，改变整个修罗大陆的医疗格局。这不仅仅是生存，这是使命。"""
        return {
            "chapter_number": 1,
            "chapter_title": "第一章 异界降临的医生",
            "content": content,
            "word_count": len(content),
            "outline": self._mock_chapter_outline(),
            "generation_time": time.time(),
            "quality_score": 8.5,
            "success": True
        }
    def _mock_quality_assessment(self) -> Dict:
        """模拟质量评估 - 返回高分以通过精品标准"""
        return {
            "overall_score": 9.0,
            "golden_finger_score": 9.2,  # 金手指创意评分
            "selling_points_score": 9.0,  # 卖点评分
            "worldview_coherence_score": 8.8,  # 世界观连贯性
            "character_depth_score": 8.9,  # 人物深度
            "emotional_resonance_score": 9.1,  # 情感共鸣
            "foreshadowing_ingenuity_score": 8.7,  # 伏笔创意
            "thematic_depth_score": 8.8,  # 主题深度
            "super_reviewer_verdict": "这是一部充满创新精神的佳作，值得重点推荐",
            "perfection_suggestions": [
                "某些细节描写可以更生动",
                "对异界规则的解释可以更深入"
            ],
            "dimensions": {
                "coherence": 8.8,  # 内容连贯性
                "writing_quality": 8.6,  # 写作质量
                "pacing": 8.4,  # 节奏
                "character_development": 8.3,  # 人物发展
                "emotional_impact": 8.7,  # 情感冲击
                "novelty": 8.5,  # 新颖度
                "world_building": 8.4  # 世界观构建
            },
            "strengths": [
                "开篇抓住眼球，成功建立异界设定",
                "主角医生身份独特，差异化爽点明确",
                "系统设定新颖，不落俗套",
                "女主角出场自然，互动有张力"
            ],
            "weaknesses": [
                "某些细节描写可以更生动",
                "对异界规则的解释可以更深入"
            ],
            "suggestions": [
                "保持这种快节奏，读者很享受",
                "逐步展开医学系统的能力，保持悬念",
                "加强主角与云尘仙的互动戏份"
            ],
            "assessment_time": time.time()
        }
    def _mock_creative_refinement(self) -> Dict:
        """模拟创意精炼"""
        return {
            "title": "星河医神：从急诊科到异界传奇",
            "synopsis": "急诊科医生林晨在车祸后穿越到修仙异界，凭借现代医学知识和获得的医神系统，在异界救死扶伤，最终成为医道传说。",
            "core_setting": "现代医学与修仙异界融合的世界观",
            "core_selling_points": [
                "医学专家穿越异界",
                "医神系统辅助成长",
                "救死扶伤获得信仰",
                "以医入道的修炼体系"
            ],
            "main_characters": {
                "protagonist": {
                    "name": "林晨",
                    "identity": "急诊科主治医师 → 异界医神",
                    "speciality": "现代医学知识与修仙结合",
                    "growth_arc": "从普通医生到异界医神的蜕变"
                },
                "female_lead": {
                    "name": "云尘仙",
                    "identity": "异界贵族少女",
                    "role": "第一个患者和伙伴，情感支撑者"
                },
                "mentor": {
                    "name": "药王老人",
                    "identity": "异界医道前辈",
                    "role": "引导者，传授修仙界医学知识"
                }
            },
            "power_system": {
                "medical_system": "通过救治生命获得医道修为",
                "cultivation_method": "以医入道，仁心仁术",
                "special_abilities": [
                    "诊断系统：可看透一切疾病",
                    "药理知识：现代药学与异界药材结合",
                    "外科技巧：现代手术技术在异界的应用"
                ]
            },
            "plot_highlights": [
                "现代医学 vs 异界疾病的冲突与融合",
                "用抗生素救治异界皇室的震撼",
                "通过外科手术解决修仙界疑难杂症",
                "建立异界第一家现代医院"
            ]
        }
    def _mock_special_event_scene_generation(self):
        """模拟特殊事件场景生成 - 返回场景列表"""
        return [
            {
                "name": "开篇场景：异界初醒",
                "type": "scene_event",
                "position": "opening",
                "purpose": "建立主角在异界的处境，展现初始困境",
                "key_actions": ["主角从昏迷中苏醒", "发现自己在陌生的异界"],
                "emotional_impact": "震撼、不安、好奇",
                "dialogue_highlights": ["这是...哪里?", "我的身体...变了?"],
                "conflict_point": "主角发现自己穿越到异界，面临生存危机",
                "sensory_details": "异界天空的双月，陌生的植被，空气中的灵气波动",
                "transition_to_next": "主角听到远处传来战斗的声音",
                "estimated_word_count": "400-600字",
                "contribution_to_chapter": "奠定故事基础，建立异界设定"
            },
            {
                "name": "发展场景：观战高手对决",
                "type": "scene_event",
                "position": "development1",
                "purpose": "展现异界力量体系，为主角未来成长铺路",
                "key_actions": ["主角隐藏观战", "见识异界高手的强大力量"],
                "emotional_impact": "震撼、向往、危机感",
                "dialogue_highlights": ["如此强大的力量...", "我必须变强!"],
                "conflict_point": "主角意识到自己的弱小，激发求生欲",
                "sensory_details": "能量爆炸的震撼，地面的龟裂，空气的扭曲",
                "transition_to_next": "战斗结束，主角发现受伤的人",
                "estimated_word_count": "500-700字",
                "contribution_to_chapter": "展示异界力量体系，激发主角成长动机"
            },
            {
                "name": "转折场景：医术初显",
                "type": "scene_event",
                "position": "climax",
                "purpose": "主角首次运用医术，展现核心能力",
                "key_actions": ["主角救治受伤者", "运用现代医学知识", "获得系统认可"],
                "emotional_impact": "紧张、成就感、希望",
                "dialogue_highlights": ["我是医生，让我来!", "现代医学在这个世界也能发挥作用!"],
                "conflict_point": "主角在紧急情况下展现医术，获得认可",
                "sensory_details": "血液的腥味，伤口的细节，治疗时的专注",
                "transition_to_next": "被救者惊讶地看向主角",
                "estimated_word_count": "600-800字",
                "contribution_to_chapter": "展现主角核心能力，建立金手指基础"
            },
            {
                "name": "收尾场景：新的开始",
                "type": "scene_event",
                "position": "ending",
                "purpose": "建立初步人际关系，设置悬念钩子",
                "key_actions": ["获得第一个伙伴", "了解异界基本信息", "接到第一个任务"],
                "emotional_impact": "期待、决心、憧憬",
                "dialogue_highlights": ["愿意跟我一起吗?", "这只是开始..."],
                "conflict_point": "新的机遇与挑战同时出现",
                "sensory_details": "夕阳下的异界城镇，远处的险峻山脉",
                "transition_to_next": "主角踏上新的征程",
                "estimated_word_count": "400-600字",
                "contribution_to_chapter": "完成本章叙事，设置追读钩子"
            }
        ]
    def test_connection(self) -> bool:
        """测试连接"""
        self.logger.info("✅ 模拟API连接测试通过")
        return True
