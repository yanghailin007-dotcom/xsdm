"""
角色层级管理器 (CharacterProgressionManager)

解决角色（尤其是对手/反派）跳变、升级突兀、缺乏铺垫的问题

核心功能：
1. 管理角色层级树（组织层级、实力等级）
2. 强制角色过渡铺垫（预警、通讯、气息等）
3. 生成角色连续性约束提示词
4. 追踪角色状态（存活/死亡/逃脱）

适用题材：
- 修仙：外门→内门→核心→长老→宗主
- 都市：狗腿→富二代→家族→财团→幕后
- 国运：侦察兵→小队→执行官→总盟主
- 科幻：侦察兵→小队→舰队→母舰→文明
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class CharacterEntity:
    """
    角色/对手实体定义
    
    通用设计，不限于"反派"：
    - 修仙：对手、宗门长辈、盟友
    - 都市：竞争对手、商业对手、幕后黑手
    - 科幻：外星文明、敌对势力
    """
    name: str
    rank: str = ""  # 职位/等级/身份
    organization: str = ""  # 所属组织/势力
    power_level: str = ""  # 实力等级（通用：F-SSS/练气-大乘/普通-幕后）
    status: str = "active"  # active/defeated/dead/escaped/unknown
    introduced_chapter: int = 0
    defeated_chapter: int = 0
    superior: str = ""  # 上级/靠山
    subordinates: List[str] = field(default_factory=list)  # 下属/追随者
    characteristics: List[str] = field(default_factory=list)  # 特征标签
    foreshadowing: List[str] = field(default_factory=list)  # 已埋下的伏笔
    role_type: str = "antagonist"  # antagonist/ally/mentor/competitor/neutral


@dataclass
class CharacterHierarchy:
    """
    角色层级结构
    
    管理一个组织/势力内的角色关系
    """
    organization_name: str
    hierarchy_tree: Dict[str, CharacterEntity] = field(default_factory=dict)
    active_characters: List[str] = field(default_factory=list)
    defeated_characters: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "organization_name": self.organization_name,
            "hierarchy_tree": {k: asdict(v) for k, v in self.hierarchy_tree.items()},
            "active_villains": self.active_villains,
            "defeated_villains": self.defeated_villains,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'VillainHierarchy':
        hierarchy = cls(organization_name=data.get("organization_name", ""))
        for name, v_data in data.get("hierarchy_tree", {}).items():
            hierarchy.hierarchy_tree[name] = Villain(**v_data)
        hierarchy.active_villains = data.get("active_villains", [])
        hierarchy.defeated_villains = data.get("defeated_villains", [])
        return hierarchy


class CharacterProgressionManager:
    """
    角色层级管理器（通用版）
    
    解决的核心问题：
    1. 角色跳变：新角色无铺垫突然登场（如：小BOSS死后大BOSS直接现身）
    2. 实力跳跃：角色实力突然跃升缺乏过渡
    3. 关系混乱：多角色并行时关系不清
    
    适用场景（不限于反派）：
    - 修仙：外门→内门→核心→长老→宗主
    - 都市：狗腿→富二代→家族→财团→幕后  
    - 国运：侦察兵→小队→执行官→总盟主
    - 科幻：侦察兵→小队→舰队→母舰→文明
    
    使用示例：
        manager = CharacterProgressionManager(project_path)
        
        # 注册组织层级（通用格式）
        manager.register_organization("反龙联盟", {
            "总盟主": {"name": "奥丁", "level": "SS级", "subordinates": ["宙斯"]},
            "亚洲区执行官": {"name": "宙斯", "level": "S级", "superior": "奥丁"},
        })
        
        # 生成连续性约束
        constraint = manager.build_continuity_constraint(
            6, current_character="奥丁", prev_character="宙斯"
        )
    """
    
    def __init__(self, project_path: str):
        self.project_path = Path(project_path)
        self.state_file = self.project_path / ".character_hierarchy.json"
        self.hierarchies: Dict[str, CharacterHierarchy] = {}
        self._load_state()
        logger.info(f"[CharacterManager] 初始化完成 | 项目: {project_path}")
    
    def _load_state(self):
        """加载状态"""
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for org_name, org_data in data.items():
                    self.hierarchies[org_name] = CharacterHierarchy.from_dict(org_data)
                logger.info(f"[CharacterManager] 已加载 {len(self.hierarchies)} 个组织")
            except Exception as e:
                logger.error(f"[CharacterManager] 加载失败: {e}")
    
    def save_state(self):
        """保存状态"""
        try:
            data = {name: h.to_dict() for name, h in self.hierarchies.items()}
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"[CharacterManager] 状态已保存")
        except Exception as e:
            logger.error(f"[CharacterManager] 保存失败: {e}")
    
    def register_organization(self, org_name: str, characters_config: Dict):
        """
        注册组织层级结构
        
        Args:
            org_name: 组织名称（如"反龙联盟"、"青云宗"）
            characters_config: 角色配置字典
                {
                    "职位/等级": {
                        "name": "角色名",
                        "level": "实力等级",
                        "superior": "上级名称",
                        "subordinates": ["下属1", "下属2"],
                        "role_type": "antagonist/ally/competitor"
                    }
                }
        """
        hierarchy = CharacterHierarchy(organization_name=org_name)
        
        for rank, config in characters_config.items():
            character = CharacterEntity(
                name=config["name"],
                rank=rank,
                organization=org_name,
                power_level=config.get("level", "未知"),
                superior=config.get("superior", ""),
                subordinates=config.get("subordinates", []),
                role_type=config.get("role_type", "antagonist")
            )
            hierarchy.hierarchy_tree[config["name"]] = character
        
        self.hierarchies[org_name] = hierarchy
        self.save_state()
        logger.info(f"[CharacterManager] 注册组织: {org_name} | 角色数: {len(characters_config)}")
    
    def update_character_status(self, character_name: str, status: str, chapter: int):
        """更新角色状态"""
        for hierarchy in self.hierarchies.values():
            if character_name in hierarchy.hierarchy_tree:
                character = hierarchy.hierarchy_tree[character_name]
                character.status = status
                
                if status in ["defeated", "dead"]:
                    character.defeated_chapter = chapter
                    if character_name in hierarchy.active_characters:
                        hierarchy.active_characters.remove(character_name)
                    if character_name not in hierarchy.defeated_characters:
                        hierarchy.defeated_characters.append(character_name)
                
                self.save_state()
                logger.info(f"[CharacterManager] {character_name} 状态更新: {status} (第{chapter}章)")
                return True
        return False
    
    def get_character_info(self, character_name: str) -> Optional[CharacterEntity]:
        """获取角色信息"""
        for hierarchy in self.hierarchies.values():
            if character_name in hierarchy.hierarchy_tree:
                return hierarchy.hierarchy_tree[character_name]
        return None
    
    def get_superior(self, character_name: str) -> Optional[CharacterEntity]:
        """获取角色的上级/靠山"""
        character = self.get_character_info(character_name)
        if character and character.superior:
            return self.get_character_info(character.superior)
        return None
    
    def get_all_defeated(self) -> List[CharacterEntity]:
        """获取所有已击败/解决的角色"""
        defeated = []
        for hierarchy in self.hierarchies.values():
            for name in hierarchy.defeated_characters:
                if name in hierarchy.hierarchy_tree:
                    defeated.append(hierarchy.hierarchy_tree[name])
        return defeated
    
    def build_continuity_constraint(self, chapter_num: int, 
                                    current_character: str = "",
                                    prev_character: str = "") -> str:
        """
        构建角色连续性约束提示词（通用版）
        
        强制要求角色出场的合理铺垫，适用于任何"层级性角色关系"
        """
        lines = ["\n## 【角色连续性强制约束】🔥\n"]
        
        # 获取角色信息
        curr_info = self.get_character_info(current_character) if current_character else None
        prev_info = self.get_character_info(prev_character) if prev_character else None
        
        # 情况1：有当前角色和上一章角色，且不同
        if curr_info and prev_info and current_character != prev_character:
            # 检查是否存在上下级关系
            if curr_info.name == prev_info.superior:
                # 当前角色是上一章角色的上级
                lines.append(f"**⚠️ 角色层级升级警告**")
                lines.append(f"- 上一章击败/面对：{prev_character}（{prev_info.rank}）")
                lines.append(f"- 本章面对：{current_character}（{curr_info.rank}，{prev_character}的上级/更高层级）")
                lines.append(f"\n**强制铺垫要求（必须满足至少2项）：**")
                lines.append(f"1. {prev_character}在失败/死亡前呼叫/提及{current_character}")
                lines.append(f"2. {current_character}通过某种方式感应到{prev_character}的处境（气息、契约、血脉、科技链接等）")
                lines.append(f"3. 主角/系统/他人提前警告{current_character}的存在")
                lines.append(f"4. {current_character}的预兆出现（气息、通讯、环境变化、威压等）")
                lines.append(f"\n**禁止：** 直接让{current_character}毫无征兆地出现！")
            
            elif prev_info.name == curr_info.superior:
                # 当前角色是上一章角色的下属
                lines.append(f"**⚠️ 角色层级降级提示**")
                lines.append(f"- 上一章：{prev_character}（上级/更高层级）")
                lines.append(f"- 本章：{current_character}（下属/更低层级）")
                lines.append(f"\n**说明：** {prev_character}应该未完全失败，或{current_character}是新的对手")
            
            else:
                # 无关的角色切换
                lines.append(f"**⚠️ 角色切换提示**")
                lines.append(f"- 上一章：{prev_character}")
                lines.append(f"- 本章：{current_character}")
                lines.append(f"\n**强制要求：**")
                lines.append(f"1. 明确{prev_character}的结局（击败/死亡/撤退/和解）")
                lines.append(f"2. 说明{current_character}与上一章事件的关联")
                lines.append(f"3. 给出{current_character}出场的合理动机")
        
        # 情况2：只有上一章角色，没有当前角色
        elif prev_info and not curr_info:
            lines.append(f"**上一章对手：{prev_character}**")
            lines.append(f"状态：{prev_info.status}")
            lines.append(f"\n本章建议：明确{prev_character}的结局或延续其影响")
        
        # 情况3：有当前角色，没有上一章角色
        elif curr_info and not prev_info:
            lines.append(f"**本章新角色：{current_character}**")
            lines.append(f"等级：{curr_info.power_level}")
            lines.append(f"身份：{curr_info.rank}")
            if curr_info.superior:
                superior = self.get_character_info(curr_info.superior)
                lines.append(f"上级/靠山：{curr_info.superior} ({superior.rank if superior else '未知'})")
        
        return "\n".join(lines)
    
    def build_character_introduction_prompt(self, character_name: str) -> str:
        """
        构建新角色出场的标准模板（通用版）
        
        确保新角色有充分的介绍和铺垫
        """
        character = self.get_character_info(character_name)
        if not character:
            return ""
        
        lines = [f"\n## 【新角色出场模板】{character_name}\n"]
        lines.append(f"**必须包含的要素：**")
        lines.append(f"1. **预兆**（出场前50-100字）：")
        lines.append(f"   - 环境变化（天气、气压、空间波动、通讯干扰等）")
        lines.append(f"   - 他人反应（强者感应、系统警告、旁观者恐慌等）")
        lines.append(f"2. **正式登场**（100-200字）：")
        lines.append(f"   - 视觉/感官描写：{', '.join(character.characteristics) if character.characteristics else '根据等级描述威压/气势'}")
        lines.append(f"   - 身份揭示：{character.rank} of {character.organization}")
        lines.append(f"   - 实力展示：{character.power_level}级的气势/能力展示")
        lines.append(f"3. **与主角的关系**：")
        if character.superior:
            lines.append(f"   - 说明与{character.superior}的关系（上级/靠山/复仇者）")
        lines.append(f"   - 明确对主角的态度（敌对/竞争/试探/利用）")
        lines.append(f"4. **对话要求**：")
        lines.append(f"   - 第一句台词必须展示性格（傲慢/冷酷/疯狂/从容等）")
        lines.append(f"   - 必须提及目的（为何针对/关注主角）")
        
        return "\n".join(lines)
    
    def auto_initialize_archetypes(self, genre: str = "general"):
        """
        自动初始化常见题材的角色模板（通用版）
        
        Args:
            genre: 题材类型 (general/国运/修仙/都市/科幻)
        """
        templates = {
            "国运": {
                "反龙联盟": {
                    "总盟主": {"name": "", "level": "SS级", "subordinates": []},
                    "亚洲区执行官": {"name": "", "level": "S级", "superior": "总盟主"},
                    "先遣队队长": {"name": "", "level": "A级", "superior": "亚洲区执行官"},
                },
                "禁地主宰": {
                    "主宰": {"name": "", "level": "EX级", "subordinates": []},
                    "领主": {"name": "", "level": "SSS级", "superior": "主宰"},
                }
            },
            "修仙": {
                "敌对宗门": {
                    "宗主": {"name": "", "level": "化神期", "subordinates": []},
                    "大长老": {"name": "", "level": "元婴巅峰", "superior": "宗主"},
                    "核心弟子": {"name": "", "level": "金丹期", "superior": "大长老"},
                },
                "妖兽山脉": {
                    "妖皇": {"name": "", "level": "十阶", "subordinates": []},
                    "妖王": {"name": "", "level": "八阶", "superior": "妖皇"},
                }
            },
            "都市": {
                "商业对手": {
                    "幕后大佬": {"name": "", "level": "幕后", "subordinates": []},
                    "财团董事": {"name": "", "level": "资本", "superior": "幕后大佬"},
                    "执行总裁": {"name": "", "level": "高管", "superior": "财团董事"},
                }
            },
            "科幻": {
                "外星文明": {
                    "母舰指挥官": {"name": "", "level": "文明级", "subordinates": []},
                    "舰队司令": {"name": "", "level": "舰队级", "superior": "母舰指挥官"},
                    "侦察队长": {"name": "", "level": "小队级", "superior": "舰队司令"},
                }
            }
        }
        
        genre_templates = templates.get(genre, {})
        for org_name, characters in genre_templates.items():
            self.register_organization(org_name, characters)
        
        logger.info(f"[CharacterManager] 已初始化 {genre} 题材模板，共 {len(genre_templates)} 个组织")



# ==================== 向后兼容别名 ====================

# 为保持向后兼容，保留旧类名作为别名
Villain = CharacterEntity
VillainHierarchy = CharacterHierarchy
VillainProgressionManager = CharacterProgressionManager

__all__ = [
    'CharacterEntity',
    'CharacterHierarchy', 
    'CharacterProgressionManager',
    # 向后兼容
    'Villain',
    'VillainHierarchy',
    'VillainProgressionManager',
]