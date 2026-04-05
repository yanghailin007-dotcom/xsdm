# -*- coding: utf-8 -*-
"""
Dialog Polish Manager
对话打磨管理器

管理市场导向模式的多轮对话打磨流程，让用户参与创意差异化设计
"""

import json
import logging
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)


class DialogRoundType(Enum):
    """对话轮次类型"""
    INIT = "init"                    # 初始化，展示套路框架
    DIFFERENTIATION = "differentiation"  # 选择差异化方向
    PROTAGONIST = "protagonist"      # 主角性格
    GOLDEN_FINGER = "golden_finger"  # 金手指设定
    PLOT_DETAILS = "plot_details"    # 剧情细节
    EMOTION_LINE = "emotion_line"    # 情感线
    CONFIRM = "confirm"              # 确认最终方案


@dataclass
class DialogRound:
    """对话轮次"""
    round_num: int
    round_type: DialogRoundType
    ai_message: str
    options: List[Dict]              # 选项列表
    allow_custom: bool = True        # 是否允许自定义输入
    user_choice: Optional[str] = None
    user_custom_input: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class CreativeDraft:
    """创意草案"""
    title: str = ""
    protagonist: str = ""
    protagonist_type: str = ""
    golden_finger: str = ""
    golden_finger_type: str = ""
    unique_points: str = ""
    emotion_pacing: str = ""
    opening_design: str = ""
    emotion_line: str = ""
    risk_mitigation: str = ""
    dialog_history: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "protagonist": self.protagonist,
            "protagonist_type": self.protagonist_type,
            "golden_finger": self.golden_finger,
            "golden_finger_type": self.golden_finger_type,
            "unique_points": self.unique_points,
            "emotion_pacing": self.emotion_pacing,
            "opening_design": self.opening_design,
            "emotion_line": self.emotion_line,
            "risk_mitigation": self.risk_mitigation
        }


class DialogPolishManager:
    """
    对话打磨管理器
    
    管理完整的对话打磨流程：
    1. 展示套路框架（让用户了解市场规律）
    2. 引导用户选择差异化方向
    3. 多轮对话细化设定
    4. 生成创意草案
    5. 准备数据供AI评估
    """
    
    def __init__(self, genre: str, tropes: Dict, api_client=None):
        self.session_id = f"DPM-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        self.genre = genre
        self.tropes = tropes
        self.api_client = api_client
        
        self.rounds: List[DialogRound] = []
        self.current_round = 0
        self.creative_draft = CreativeDraft()
        
        # 套路框架数据（从tropes提取）
        self.trope_framework = self._extract_trope_framework()
        
        logger.info(f"[对话打磨 {self.session_id}] 初始化 | 题材: {genre}")
    
    def _extract_trope_framework(self) -> Dict:
        """从套路分析中提取框架信息"""
        return {
            "core_formula": self.tropes.get("core_formula", ""),
            "typical_arcs": self.tropes.get("typical_arcs", []),
            "protagonist_types": self.tropes.get("protagonist", {}).get("types", []),
            "golden_finger_types": self.tropes.get("golden_finger", {}).get("types", []),
            "common_tropes": self.tropes.get("common_tropes", []),
            "emotion_curve": self.tropes.get("emotion_curve", {}),
            "market_saturation": "高"  # 默认假设同质化严重
        }
    
    def start_dialog(self) -> Dict:
        """
        开始对话打磨流程
        返回第一轮：套路框架展示 + 差异化方向选择
        """
        logger.info(f"[对话打磨 {self.session_id}] 开始第一轮")
        
        # 构建AI消息
        ai_message = self._build_init_message()
        
        # 构建差异化选项
        options = [
            {
                "id": "protagonist",
                "label": "🎭 主角性格",
                "description": "改变主角性格类型，如话痨、佛系、疯批等",
                "market_risk": "中",
                "examples": ["话痨吐槽型", "佛系摆烂型", "疯批乐子型"]
            },
            {
                "id": "golden_finger",
                "label": "⚡ 金手指设定",
                "description": "给金手指添加独特限制或代价",
                "market_risk": "低",
                "examples": ["有副作用的能力", "需要付出代价", "能力来自他人"]
            },
            {
                "id": "plot_twist",
                "label": "🔄 剧情反转",
                "description": "在经典套路中加入意外转折",
                "market_risk": "高",
                "examples": ["反派才是好人", "主角被误解", "能力反向作用"]
            },
            {
                "id": "emotion_line",
                "label": "💕 情感副线",
                "description": "增加独特的情感羁绊或关系",
                "market_risk": "低",
                "examples": ["妹妹是唯一记得他的人", "宿敌变挚友", "宠物有特殊能力"]
            },
            {
                "id": "narrative",
                "label": "📖 叙事视角",
                "description": "改变讲故事的方式",
                "market_risk": "高",
                "examples": ["群像视角", "反派视角", "多线并进"]
            },
            {
                "id": "multiple",
                "label": "🔥 多维度组合",
                "description": "同时改变2-3个维度，创造独特组合",
                "market_risk": "中",
                "examples": ["话痨+副作用+妹妹羁绊"]
            }
        ]
        
        round_data = DialogRound(
            round_num=1,
            round_type=DialogRoundType.INIT,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 1
        
        return self._format_round_response(round_data)
    
    def _build_init_message(self) -> str:
        """构建初始化消息"""
        genre = self.genre
        
        # 提取套路要点
        core_formula = self.trope_framework.get("core_formula", "")
        typical_arcs = self.trope_framework.get("typical_arcs", [])
        common_tropes = self.trope_framework.get("common_tropes", [])
        
        arcs_text = "\n".join([f"  • {arc}" for arc in typical_arcs[:3]]) if typical_arcs else "  • 经典逆袭打脸路线"
        tropes_text = "、".join(common_tropes[:5]) if common_tropes else "系统流、无敌流、震惊流"
        
        message = f"""🎯 **【{genre}】套路框架分析**

基于番茄小说Top100作品数据，该题材的**爆款公式**如下：

**📊 核心套路：**
{core_formula or '主角获得特殊能力→展现实力→震惊众人→不断升级打脸'}

**📈 经典剧情链：**
{arcs_text}

**🎭 常见元素：**
{tropes_text}

---

⚠️ **同质化风险警告：**
该题材市场饱和度高，直接套用上述套路容易导致：
• 首秀通过率 < 50%
• 完读率低于题材平均
• 难以获得算法推荐量

💡 **建议策略：**
在保留核心爽点框架的基础上，选择1-2个维度进行**差异化设计**。

**想在哪个角度做出不同？（可多选）**"""
        
        return message
    
    def process_user_input(self, user_input: str, custom_text: str = None) -> Dict:
        """
        处理用户输入，返回下一轮对话
        
        Args:
            user_input: 用户选择的选项ID
            custom_text: 用户自定义输入（可选）
        """
        # 保存当前轮次的用户选择
        if self.rounds:
            current = self.rounds[-1]
            current.user_choice = user_input
            current.user_custom_input = custom_text
        
        # 根据当前轮次决定下一步
        if self.current_round == 1:
            # 第一轮：差异化方向 → 主角性格
            return self._round_protagonist_type(user_input, custom_text)
        elif self.current_round == 2:
            # 第二轮：主角性格 → 金手指
            return self._round_golden_finger(user_input, custom_text)
        elif self.current_round == 3:
            # 第三轮：金手指 → 剧情细节
            return self._round_plot_details(user_input, custom_text)
        elif self.current_round == 4:
            # 第四轮：剧情细节 → 情感线
            return self._round_emotion_line(user_input, custom_text)
        elif self.current_round == 5:
            # 第五轮：情感线 → 生成完整方案
            return self._round_generate_full_plan(user_input, custom_text)
        elif self.current_round == 6:
            # 第六轮：确认最终方案
            return self._round_final_confirm(user_input, custom_text)
        else:
            # 结束对话
            return self._finish_dialog()
    
    def _round_protagonist_type(self, prev_choice: str, custom: str = None) -> Dict:
        """第二轮：主角性格选择"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第二轮：主角性格")
        
        # 记录选择
        self.creative_draft.protagonist_type = prev_choice
        
        # 构建选项
        options = [
            {
                "id": "calm",
                "label": "🧊 冷静理智型",
                "description": "传统稳健选择，市场验证度高",
                "market_score": 85,
                "risk": "低"
            },
            {
                "id": "talkative",
                "label": "🗣️ 话痨吐槽型",
                "description": "直播变单口相声，反差萌",
                "market_score": 78,
                "risk": "中"
            },
            {
                "id": "lazy",
                "label": "😴 佛系摆烂型",
                "description": "被迫营业，越不想火越火",
                "market_score": 65,
                "risk": "中"
            },
            {
                "id": "crazy",
                "label": "🤪 疯批乐子型",
                "description": "不按常理出牌，读者猜不到",
                "market_score": 55,
                "risk": "高"
            },
            {
                "id": "antihero",
                "label": "😈 反英雄型",
                "description": "看似自私冷漠，实际另有深意",
                "market_score": 70,
                "risk": "中"
            }
        ]
        
        ai_message = """**🎭 第二步：主角性格设定**

主角性格决定了读者的代入方式和情感连接。

**该题材常见人设：** 冷静理智型（市场占比35%，完读率12%）

**差异化选项：**
（每个选项都标注了市场化评分和风险等级）

**你想让主角是什么性格？**"""
        
        round_data = DialogRound(
            round_num=2,
            round_type=DialogRoundType.PROTAGONIST,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 2
        
        return self._format_round_response(round_data)
    
    def _round_golden_finger(self, prev_choice: str, custom: str = None) -> Dict:
        """第三轮：金手指设定"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第三轮：金手指")
        
        # 记录主角选择
        protagonist_map = {
            "calm": "冷静理智型",
            "talkative": "话痨吐槽型",
            "lazy": "佛系摆烂型",
            "crazy": "疯批乐子型",
            "antihero": "反英雄型"
        }
        self.creative_draft.protagonist = protagonist_map.get(prev_choice, prev_choice)
        if custom:
            self.creative_draft.protagonist += f"（自定义：{custom}）"
        
        options = [
            {
                "id": "side_effect_memory",
                "label": "🧠 记忆消失代价",
                "description": "每次使用能力会随机遗忘一段记忆",
                "combo_effect": f"与{self.creative_draft.protagonist}结合：能力越强越孤独，反差感强",
                "market_score": 75
            },
            {
                "id": "side_effect_body",
                "label": "💀 身体衰弱代价",
                "description": "力量越强，现实中的身体越虚弱",
                "combo_effect": "悲剧英雄路线，需配合轻松桥段",
                "market_score": 60
            },
            {
                "id": "restriction_name",
                "label": "📝 真名限制",
                "description": "必须知道对方真名才能发动能力",
                "combo_effect": "增加智斗成分，信息战",
                "market_score": 70
            },
            {
                "id": "restriction_hostility",
                "label": "😠 敌意触发",
                "description": "需要对方先对主角产生敌意才能发动",
                "combo_effect": "被动反击流，被挑衅后爆发",
                "market_score": 72
            },
            {
                "id": "unique_audience",
                "label": "📺 观众互动型",
                "description": "直播观众弹幕可以影响能力效果",
                "combo_effect": f"与{self.creative_draft.protagonist}的直播场景完美契合",
                "market_score": 80
            }
        ]
        
        ai_message = f"""**⚡ 第三步：金手指设定**

当前选择的主角：**{self.creative_draft.protagonist}**

该题材常见金手指：直接获得能力，无副作用（市场占比40%，但同质化严重）

**差异化方向：** 给金手指添加**限制条件或代价**
（这样既能保留爽点，又能增加独特性和情感深度）

**你想设计什么样的金手指？**
（已智能推荐与主角性格契合的选项）"""
        
        round_data = DialogRound(
            round_num=3,
            round_type=DialogRoundType.GOLDEN_FINGER,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 3
        
        return self._format_round_response(round_data)
    
    def _round_plot_details(self, prev_choice: str, custom: str = None) -> Dict:
        """第四轮：剧情细节"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第四轮：剧情细节")
        
        # 记录金手指选择
        gf_map = {
            "side_effect_memory": "记忆消失代价",
            "side_effect_body": "身体衰弱代价",
            "restriction_name": "真名限制",
            "restriction_hostility": "敌意触发",
            "unique_audience": "观众互动型"
        }
        self.creative_draft.golden_finger = gf_map.get(prev_choice, prev_choice)
        self.creative_draft.golden_finger_type = prev_choice
        if custom:
            self.creative_draft.golden_finger += f"（自定义：{custom}）"
        
        options = [
            {
                "id": "classic",
                "label": "📖 经典开局",
                "description": "被选中进入副本，众人轻视，然后展现实力",
                "hook_strength": "★★★☆☆",
                "familiarity": "高（读者容易接受）"
            },
            {
                "id": "unexpected",
                "label": "🎪 意外入局",
                "description": "以为是参加综艺，结果发现是玩真的",
                "hook_strength": "★★★★☆",
                "familiarity": "中（有喜剧效果）"
            },
            {
                "id": "revenge",
                "label": "🔥 复仇归来",
                "description": "曾经失败过，这次以新身份重新参加",
                "hook_strength": "★★★★★",
                "familiarity": "中（悬念感强）"
            },
            {
                "id": "forced",
                "label": "😰 被迫参加",
                "description": "完全不想参加，但被系统/国家强制选中",
                "hook_strength": "★★★★☆",
                "familiarity": "中（反差萌）"
            }
        ]
        
        ai_message = f"""**🎬 第四步：开局设计**

当前设定汇总：
• 主角：**{self.creative_draft.protagonist}**
• 金手指：**{self.creative_draft.golden_finger}**

黄金三章（第1-3章）决定了读者是否会继续阅读。

**你想用什么开局吸引读者？**"""
        
        round_data = DialogRound(
            round_num=4,
            round_type=DialogRoundType.PLOT_DETAILS,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 4
        
        return self._format_round_response(round_data)
    
    def _round_emotion_line(self, prev_choice: str, custom: str = None) -> Dict:
        """第五轮：情感线"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第五轮：情感线")
        
        # 记录开局设计
        self.creative_draft.opening_design = prev_choice
        if custom:
            self.creative_draft.opening_design += f"（自定义：{custom}）"
        
        options = [
            {
                "id": "sister",
                "label": "👧 妹妹羁绊",
                "description": "妹妹是唯一记得/理解他的人，情感核心",
                "applicability": "适合记忆消失、被遗忘等设定",
                "tear_jerker_potential": "★★★★★"
            },
            {
                "id": "rival",
                "label": "⚔️ 宿敌变挚友",
                "description": "一开始敌对，后来成为最懂他的人",
                "applicability": "通用，增加人物关系张力",
                "tear_jerker_potential": "★★★★☆"
            },
            {
                "id": "pet",
                "label": "🐾 特殊宠物",
                "description": "宠物有特殊能力，或能感知主角真实状态",
                "applicability": "适合轻松向、治愈向",
                "tear_jerker_potential": "★★★☆☆"
            },
            {
                "id": "mentor",
                "label": "👴 神秘导师",
                "description": "暗中指导主角，真实身份成谜",
                "applicability": "适合成长型主角",
                "tear_jerker_potential": "★★★☆☆"
            },
            {
                "id": "none",
                "label": "🚫 暂无情感线",
                "description": "专注主线，情感线后期再展开",
                "applicability": "快节奏爽文",
                "tear_jerker_potential": "☆☆☆☆☆"
            }
        ]
        
        ai_message = f"""**💕 第五步：情感副线（可选但推荐）**

情感线是增强读者粘性的重要手段，能让读者为角色的命运牵肠挂肚。

**你想添加什么样的情感羁绊？**
（建议选择与当前设定互补的选项）"""
        
        round_data = DialogRound(
            round_num=5,
            round_type=DialogRoundType.EMOTION_LINE,
            ai_message=ai_message,
            options=options,
            allow_custom=True
        )
        self.rounds.append(round_data)
        self.current_round = 5
        
        return self._format_round_response(round_data)
    
    def _round_generate_full_plan(self, prev_choice: str, custom: str = None) -> Dict:
        """第六轮：AI生成完整方案（书名+大纲）"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第六轮：生成完整方案")
        
        # 记录情感线
        emotion_map = {
            "sister": "妹妹是唯一记得他的人，建立深层情感锚点",
            "rival": "宿敌变挚友，亦敌亦友的复杂关系",
            "pet": "特殊宠物伙伴，增加温馨元素",
            "mentor": "神秘导师引导，提供背景深度",
            "none": "专注事业线，无情感羁绊"
        }
        self.creative_draft.emotion_line = emotion_map.get(prev_choice, prev_choice)
        if custom:
            self.creative_draft.emotion_line += f"（自定义：{custom}）"
        
        # 生成独特卖点和风险对冲
        self.creative_draft.unique_points = self._generate_unique_points()
        self.creative_draft.emotion_pacing = "快节奏，每3章一个小高潮"
        self.creative_draft.risk_mitigation = self._generate_risk_mitigation()
        
        # 🔥 调用AI生成完整方案
        try:
            full_plan = self._generate_plan_with_ai()
            self.creative_draft.title = full_plan.get('title', '')
            self.creative_draft.opening_design = full_plan.get('opening', self.creative_draft.opening_design)
        except Exception as e:
            logger.warning(f"AI生成方案失败，使用默认: {e}")
            # 使用默认标题生成逻辑
            self.creative_draft.title = self._generate_default_title()
        
        # 构建AI消息
        ai_message = f"""🎉 **完整方案已生成！**

基于你的选择，AI为你生成了以下创作方案：

**📚 推荐书名：**
《{self.creative_draft.title}》

**👤 主角设定：**
{self.creative_draft.protagonist}

**⚡ 金手指：**
{self.creative_draft.golden_finger}

**🎬 开局设计：**
{self.creative_draft.opening_design}

**💕 情感线：**
{self.creative_draft.emotion_line}

**✨ 差异化亮点：**
{self.creative_draft.unique_points}

---

💡 **下一步：**
你可以直接在表单中查看和修改这个方案，确认无误后即可开始生成。"""
        
        options = [
            {
                "id": "continue",
                "label": "✅ 查看并编辑方案",
                "description": "在表单中确认和微调方案",
                "style": "primary"
            },
            {
                "id": "back",
                "label": "🔄 返回修改",
                "description": "重新调整设定",
                "style": "secondary"
            }
        ]
        
        round_data = DialogRound(
            round_num=6,
            round_type=DialogRoundType.CONFIRM,
            ai_message=ai_message,
            options=options,
            allow_custom=False
        )
        self.rounds.append(round_data)
        self.current_round = 6
        
        # 生成对话历史
        self.creative_draft.dialog_history = self._generate_dialog_history()
        
        return self._format_round_response(round_data, is_final=True)
    
    def _round_final_confirm(self, prev_choice: str, custom: str = None) -> Dict:
        """第七轮：最终确认（用户点击"查看并编辑方案"后）"""
        logger.info(f"[对话打磨 {self.session_id}] 进入第七轮：最终确认")
        
        # 这一轮只是标记结束，实际表单在前端显示
        return self._finish_dialog()
    
    def _generate_plan_with_ai(self) -> Dict:
        """调用AI生成完整方案"""
        if not self.api_client:
            return self._generate_default_plan()
        
        prompt = f"""你是一位资深网文编辑，擅长为番茄小说平台创作爆款作品。

请基于以下设定，生成一个完整的创作方案：

**题材：** {self.genre}
**主角：** {self.creative_draft.protagonist}
**金手指：** {self.creative_draft.golden_finger}
**情感线：** {self.creative_draft.emotion_line}
**差异化：** {self.creative_draft.unique_points}

请生成（JSON格式）：
{{
    "title": "书名（6-14字，含数字或强烈对比）",
    "opening": "开局设计（100字以内，描述第1章核心冲突）",
    "first_climax": "第一个爽点（第3-5章）",
    "main_plot": "主线走向（50字）"
}}

要求：
1. 书名要符合番茄爆款风格
2. 开局要有强冲突和吸引力
3. 突出差异化亮点"""
        
        try:
            response = self.api_client.generate_content_with_retry(
                content_type="plan_generation",
                user_prompt=prompt,
                temperature=0.8
            )
            
            if response:
                # 尝试解析JSON
                import json
                import re
                # 提取JSON部分
                json_match = re.search(r'\{[\s\S]*\}', str(response))
                if json_match:
                    return json.loads(json_match.group())
        except Exception as e:
            logger.error(f"AI生成方案失败: {e}")
        
        return self._generate_default_plan()
    
    def _generate_default_plan(self) -> Dict:
        """生成默认方案（AI失败时使用）"""
        protagonist = self.creative_draft.protagonist
        golden_finger = self.creative_draft.golden_finger
        
        # 根据人设和金手指生成默认书名
        if "话痨" in protagonist:
            title = f"绑定吐槽系统后，我在{self.genre.split('-')[0]}无敌了"
        elif "佛系" in protagonist:
            title = f"摆烂后，我成了{self.genre.split('-')[0]}最强"
        elif "疯批" in protagonist:
            title = f"疯批主角：{self.genre.split('-')[0]}规则破坏者"
        else:
            title = f"开局觉醒{golden_finger[:6]}..."
        
        return {
            "title": title,
            "opening": f"主角获得{golden_finger}，首次在国运战中展现",
            "first_climax": "第3章打脸敌国选手",
            "main_plot": "从弱小到最强，一路碾压"
        }
    
    def _generate_default_title(self) -> str:
        """生成默认书名"""
        plan = self._generate_default_plan()
        return plan.get("title", "未命名")
    
    def _generate_unique_points(self) -> str:
        """生成差异化亮点描述"""
        points = []
        
        if "话痨" in self.creative_draft.protagonist:
            points.append("直播变单口相声，用吐槽缓解紧张氛围")
        elif "佛系" in self.creative_draft.protagonist:
            points.append("被迫营业的反差萌，越不想火越火")
        elif "疯批" in self.creative_draft.protagonist:
            points.append(" unpredictable的行为模式，让读者猜不到下一步")
        
        if "记忆" in self.creative_draft.golden_finger:
            points.append("记忆消失的悲剧感与直播时的喜剧效果形成反差")
        elif "身体" in self.creative_draft.golden_finger:
            points.append("英雄迟暮的紧迫感，每一场战斗都可能是最后一场")
        elif "观众" in self.creative_draft.golden_finger:
            points.append("观众互动创造不确定性，弹幕成为剧情变量")
        
        if "妹妹" in self.creative_draft.emotion_line:
            points.append("妹妹是唯一理解他的人，建立深层情感锚点")
        elif "宿敌" in self.creative_draft.emotion_line:
            points.append("亦敌亦友的复杂关系，增加人物关系张力")
        
        return "\n".join([f"• {p}" for p in points]) if points else "• 独特的设定组合"
    
    def _generate_risk_mitigation(self) -> str:
        """生成风险对冲建议"""
        mitigations = []
        
        if "记忆" in self.creative_draft.golden_finger or "身体" in self.creative_draft.golden_finger:
            mitigations.append("每5章安排1章轻松日常，缓解压抑感")
        
        if "话痨" in self.creative_draft.protagonist:
            mitigations.append("30章后减少纯吐槽，增加行动推进")
        
        if "妹妹" in self.creative_draft.emotion_line:
            mitigations.append("前10章快速建立妹妹羁绊，让读者有牵挂")
        
        return "；".join(mitigations) if mitigations else "按常规节奏推进"
    
    def _generate_dialog_history(self) -> List[Dict]:
        """生成对话历史（供AI评估使用）"""
        history = []
        for round_data in self.rounds:
            history.append({
                "role": "ai",
                "content": round_data.ai_message
            })
            if round_data.user_choice:
                user_content = round_data.user_choice
                if round_data.user_custom_input:
                    user_content += f"（自定义：{round_data.user_custom_input}）"
                history.append({
                    "role": "user",
                    "content": user_content
                })
        return history
    
    def _format_round_response(self, round_data: DialogRound, is_final: bool = False) -> Dict:
        """格式化轮次响应"""
        return {
            "session_id": self.session_id,
            "round": round_data.round_num,
            "round_type": round_data.round_type.value,
            "ai_message": round_data.ai_message,
            "options": round_data.options,
            "allow_custom": round_data.allow_custom,
            "is_final": is_final,
            "creative_draft": self.creative_draft.to_dict() if is_final else None
        }
    
    def go_back(self, target_round: int) -> Dict:
        """
        返回到指定轮次
        
        Args:
            target_round: 目标轮次（1-based）
        """
        if target_round < 1 or target_round >= len(self.rounds):
            return self._format_round_response(self.rounds[-1])
        
        # 截断到目标轮次
        self.rounds = self.rounds[:target_round]
        self.current_round = target_round
        
        # 清除后续的选择记录
        if target_round <= 1:
            self.creative_draft.protagonist_type = ""
        if target_round <= 2:
            self.creative_draft.protagonist = ""
        if target_round <= 3:
            self.creative_draft.golden_finger = ""
            self.creative_draft.golden_finger_type = ""
        if target_round <= 4:
            self.creative_draft.opening_design = ""
        if target_round <= 5:
            self.creative_draft.emotion_line = ""
        
        return self._format_round_response(self.rounds[-1])
    
    def get_creative_draft(self) -> CreativeDraft:
        """获取创意草案"""
        return self.creative_draft
    
    def get_dialog_summary(self) -> str:
        """获取对话摘要"""
        lines = [f"【{self.genre}】对话打磨摘要"]
        for round_data in self.rounds:
            if round_data.user_choice:
                lines.append(f"第{round_data.round_num}轮: {round_data.user_choice}")
        return "\n".join(lines)


# 会话管理器（内存存储，生产环境应使用Redis）
_dialog_sessions: Dict[str, DialogPolishManager] = {}


def create_dialog_session(session_id: str, genre: str, tropes: Dict, api_client=None) -> DialogPolishManager:
    """创建对话打磨会话"""
    manager = DialogPolishManager(genre, tropes, api_client)
    _dialog_sessions[manager.session_id] = manager
    return manager


def get_dialog_session(session_id: str) -> Optional[DialogPolishManager]:
    """获取对话打磨会话"""
    return _dialog_sessions.get(session_id)


def remove_dialog_session(session_id: str):
    """移除对话打磨会话"""
    if session_id in _dialog_sessions:
        del _dialog_sessions[session_id]