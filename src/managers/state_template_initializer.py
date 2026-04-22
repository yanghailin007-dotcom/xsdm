"""
状态追踪模板初始化器
根据小说类型自动初始化需要追踪的状态字段
用于一阶段末尾，为二阶段章节生成提供状态同步基础
"""
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class StateTemplate:
    """状态追踪模板"""
    template_name: str
    description: str
    fields: Dict[str, Dict] = field(default_factory=dict)
    
    def get_initial_state(self) -> Dict:
        """获取初始状态"""
        return {
            field_name: field_info.get("default", "")
            for field_name, field_info in self.fields.items()
        }


class StateTemplateInitializer:
    """状态追踪模板初始化器"""
    
    # 预定义的类型模板
    TEMPLATES = {
        "urban_god_of_wealth": StateTemplate(
            template_name="都市神豪文",
            description="神豪/暴富类都市爽文状态追踪",
            fields={
                "protagonist_wealth": {"type": "string", "default": "0", "description": "主角当前财富（如'100万'、'1亿'）"},
                "protagonist_location": {"type": "string", "default": "家中", "description": "主角当前位置"},
                "protagonist_mood": {"type": "string", "default": "平静", "description": "主角当前心情"},
                "system_daily_limit": {"type": "string", "default": "100万", "description": "系统每日提现额度"},
                "system_today_withdrawn": {"type": "string", "default": "0", "description": "今日已提现金额"},
                "system_total_spent": {"type": "string", "default": "0", "description": "累计消费金额"},
                "protagonist_reputation": {"type": "string", "default": "无名小卒", "description": "主角当前声望/社会地位"},
                "love_interest_mood": {"type": "string", "default": "正常", "description": "女主/感情线对象心情"},
                "love_interest_location": {"type": "string", "default": "未知", "description": "女主/感情线对象位置"},
                "rival_status": {"type": "string", "default": "尚未交锋", "description": "当前主要对手状态"},
                "completed_events": {"type": "list", "default": [], "description": "已完成的关键事件列表"},
            }
        ),
        "urban_immortal_revenge": StateTemplate(
            template_name="都市修仙/归来复仇",
            description="都市修仙、强者归来类爽文状态追踪",
            fields={
                "protagonist_realm": {"type": "string", "default": "炼气初期", "description": "主角当前修为境界"},
                "protagonist_cultivation": {"type": "string", "default": "0", "description": "当前修为值/进度"},
                "protagonist_location": {"type": "string", "default": "都市", "description": "主角当前位置"},
                "protagonist_mood": {"type": "string", "default": "隐忍", "description": "主角当前心情"},
                "enemies_defeated": {"type": "list", "default": [], "description": "已被击败的敌人列表"},
                "allies_gained": {"type": "list", "default": [], "description": "已获得的盟友列表"},
                "secrets_uncovered": {"type": "list", "default": [], "description": "已揭露的秘密列表"},
                "family_status": {"type": "string", "default": "待保护", "description": "家人/亲友现状"},
                "love_interest_attitude": {"type": "string", "default": "陌生/轻视", "description": "女主对主角态度"},
                "completed_events": {"type": "list", "default": [], "description": "已完成的关键事件列表"},
            }
        ),
        "fantasy_cultivation": StateTemplate(
            template_name="玄幻修仙",
            description="玄幻/修仙类爽文状态追踪",
            fields={
                "protagonist_realm": {"type": "string", "default": "入门", "description": "主角当前境界"},
                "protagonist_cultivation": {"type": "string", "default": "0", "description": "修为进度"},
                "sect_status": {"type": "string", "default": "外门弟子", "description": "在宗门的地位"},
                "sect_contribution": {"type": "string", "default": "0", "description": "宗门贡献点"},
                "inventory": {"type": "list", "default": [], "description": "当前拥有的物品/法宝"},
                "spirit_stones": {"type": "string", "default": "0", "description": "灵石数量"},
                "protagonist_location": {"type": "string", "default": "宗门", "description": "当前所在地点"},
                "enemies": {"type": "list", "default": [], "description": "当前敌对势力/个人"},
                "master_relationship": {"type": "string", "default": "无师承", "description": "师徒关系状态"},
                "completed_events": {"type": "list", "default": [], "description": "已完成的关键事件列表"},
            }
        ),
        "urban_medical_martial": StateTemplate(
            template_name="都市医武/兵王",
            description="都市神医、兵王归来类爽文状态追踪",
            fields={
                "protagonist_identity": {"type": "string", "default": "隐藏身份", "description": "主角当前公开身份"},
                "protagonist_skill_level": {"type": "string", "default": "巅峰", "description": "医术/武艺水平"},
                "protagonist_location": {"type": "string", "default": "都市", "description": "当前位置"},
                "patients_saved": {"type": "list", "default": [], "description": "已救治的重要人物"},
                "enemies_defeated": {"type": "list", "default": [], "description": "已击败的敌人"},
                "love_interest_status": {"type": "string", "default": "待发展", "description": "感情线进展"},
                "military_rank": {"type": "string", "default": "已退役", "description": "军职/军衔（如适用）"},
                "hidden_backstory": {"type": "string", "default": "未揭露", "description": "隐藏背景揭露进度"},
                "completed_events": {"type": "list", "default": [], "description": "已完成的关键事件列表"},
            }
        ),
        "system_flow": StateTemplate(
            template_name="系统流",
            description="系统/签到/任务流爽文状态追踪",
            fields={
                "system_name": {"type": "string", "default": "未命名系统", "description": "系统名称"},
                "system_level": {"type": "string", "default": "Lv.1", "description": "系统等级"},
                "system_points": {"type": "string", "default": "0", "description": "系统积分/经验"},
                "tasks_completed": {"type": "list", "default": [], "description": "已完成任务列表"},
                "active_tasks": {"type": "list", "default": [], "description": "进行中任务列表"},
                "rewards_claimed": {"type": "list", "default": [], "description": "已领取奖励列表"},
                "protagonist_location": {"type": "string", "default": "起始地点", "description": "当前位置"},
                "protagonist_mood": {"type": "string", "default": "期待", "description": "当前心情"},
                "completed_events": {"type": "list", "default": [], "description": "已完成的关键事件列表"},
            }
        ),
        "generic": StateTemplate(
            template_name="通用模板",
            description="通用爽文状态追踪（当无法匹配特定类型时使用）",
            fields={
                "protagonist_strength": {"type": "string", "default": "初始状态", "description": "主角当前实力/能力水平"},
                "protagonist_location": {"type": "string", "default": "起始地点", "description": "当前位置"},
                "protagonist_mood": {"type": "string", "default": "正常", "description": "当前心情"},
                "protagonist_status": {"type": "string", "default": "无名之辈", "description": "社会地位/身份"},
                "key_items": {"type": "list", "default": [], "description": "关键物品/能力"},
                "allies": {"type": "list", "default": [], "description": "盟友/追随者列表"},
                "enemies": {"type": "list", "default": [], "description": "敌对势力/个人列表"},
                "love_interest_status": {"type": "string", "default": "待发展", "description": "感情线进展"},
                "completed_events": {"type": "list", "default": [], "description": "已完成的关键事件列表"},
            }
        ),
    }
    
    @classmethod
    def detect_template(cls, category: str, creative_seed: Optional[Dict] = None) -> str:
        """
        根据小说类型自动检测适用的状态模板
        
        Args:
            category: 小说分类
            creative_seed: 创意种子（可选，用于更精确匹配）
            
        Returns:
            模板名称
        """
        category_lower = (category or "").lower()
        
        # 从创意种子中提取关键词
        seed_text = ""
        if creative_seed:
            if isinstance(creative_seed, dict):
                seed_text = str(creative_seed.get("coreSellingPoints", "")) + " " + \
                           str(creative_seed.get("completeStoryline", ""))
            else:
                seed_text = str(creative_seed)
        seed_lower = seed_text.lower()
        
        # 神豪/暴富类
        if any(k in category_lower + seed_lower for k in ["神豪", "暴富", "富豪", "有钱", "花钱", "投资", "商业"]):
            return "urban_god_of_wealth"
        
        # 都市修仙/归来
        if any(k in category_lower + seed_lower for k in ["修仙", "归来", "重生", "仙帝", "天尊", "下山"]):
            if "都市" in category_lower + seed_lower:
                return "urban_immortal_revenge"
            return "fantasy_cultivation"
        
        # 玄幻修仙
        if any(k in category_lower + seed_lower for k in ["玄幻", "仙侠", "修真", "武道", "斗气", "魔法"]):
            return "fantasy_cultivation"
        
        # 医武/兵王
        if any(k in category_lower + seed_lower for k in ["神医", "兵王", "战神", "保镖", "高手"]):
            return "urban_medical_martial"
        
        # 系统流
        if any(k in category_lower + seed_lower for k in ["系统", "签到", "任务", "面板", "金手指"]):
            return "system_flow"
        
        # 默认
        return "generic"
    
    @classmethod
    def initialize_state_tracker(cls, category: str, creative_seed: Optional[Dict] = None) -> Dict:
        """
        初始化状态追踪器
        
        Args:
            category: 小说分类
            creative_seed: 创意种子
            
        Returns:
            初始状态字典
        """
        template_name = cls.detect_template(category, creative_seed)
        template = cls.TEMPLATES.get(template_name, cls.TEMPLATES["generic"])
        
        return {
            "template_name": template.template_name,
            "template_description": template.description,
            "initial_state": template.get_initial_state(),
            "current_state": template.get_initial_state(),
            "state_history": [],  # 每章结束后的状态快照
            "template_fields": template.fields,
        }
    
    @classmethod
    def get_template_fields(cls, template_name: str) -> Dict:
        """获取模板的字段定义"""
        template = cls.TEMPLATES.get(template_name, cls.TEMPLATES["generic"])
        return template.fields
