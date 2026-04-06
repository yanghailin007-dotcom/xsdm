"""
项目状态初始化器 (ProjectStateInitializer)

在生成第1章前，根据一阶段产物正确初始化三个状态文件：
- .character_state.json (角色状态)
- .world_state.json (世界状态)  
- .chapter_extractions.json (章节提取)

解决：world_state.json 等文件包含旧项目残留数据的问题
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from .phase_one_loader import PhaseOneDataLoader

logger = logging.getLogger(__name__)


class ProjectStateInitializer:
    """
    项目状态初始化器
    
    职责：
    1. 在项目启动时检查三个状态文件是否存在且正确
    2. 如果不存在或包含错误数据，根据 phase_one_products 重新初始化
    3. 确保状态文件与一阶段设定一致
    """
    
    # 错误关键词列表（如果状态文件包含这些词，说明需要重新初始化）
    ERROR_KEYWORDS = [
        "扮演度", "雷电操控", "雷电法王", "酒剑仙", "苏辰", 
        "御酒术", "静电操控", "扮演系统"
    ]
    
    def __init__(self, project_path: Path):
        self.project_path = Path(project_path)
        self.phase_one_loader = PhaseOneDataLoader(project_path)
        
        # 三个状态文件路径
        self.character_state_file = self.project_path / ".character_state.json"
        self.world_state_file = self.project_path / ".world_state.json"
        self.chapter_extractions_file = self.project_path / ".chapter_extractions.json"
    
    def initialize_if_needed(self, force: bool = False) -> bool:
        """
        如果需要，初始化项目状态文件
        
        Args:
            force: 是否强制重新初始化（即使文件已存在）
        
        Returns:
            bool: 是否执行了初始化
        """
        # 检查是否需要初始化
        needs_init = force or self._check_needs_initialization()
        
        if not needs_init:
            logger.info("[ProjectStateInitializer] 状态文件已存在且正确，跳过初始化")
            return False
        
        logger.info("[ProjectStateInitializer] 开始初始化项目状态文件...")
        logger.info(f"[ProjectStateInitializer] 项目路径: {self.project_path}")
        
        try:
            # 加载一阶段数据
            phase_one_data = self.phase_one_loader.load_all()
            
            # 检查一阶段数据是否完整
            if not self._validate_phase_one_data(phase_one_data):
                logger.warning("[ProjectStateInitializer] 一阶段数据不完整，使用默认初始化")
            
            # 初始化三个文件
            self._init_character_state(phase_one_data)
            self._init_world_state(phase_one_data)
            self._init_chapter_extractions()
            
            logger.info("[ProjectStateInitializer] ✅ 项目状态文件初始化完成")
            return True
            
        except Exception as e:
            logger.error(f"[ProjectStateInitializer] 初始化失败: {e}", exc_info=True)
            return False
    
    def _check_needs_initialization(self) -> bool:
        """检查是否需要初始化"""
        # 检查文件是否存在
        files_exist = (
            self.character_state_file.exists() and
            self.world_state_file.exists() and
            self.chapter_extractions_file.exists()
        )
        
        if not files_exist:
            logger.info("[ProjectStateInitializer] 状态文件不存在，需要初始化")
            return True
        
        # 检查文件内容是否正确（检查错误关键词）
        for file_path in [self.character_state_file, self.world_state_file]:
            if not file_path.exists():
                continue
                
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    for keyword in self.ERROR_KEYWORDS:
                        if keyword in content:
                            logger.warning(
                                f"[ProjectStateInitializer] 在 {file_path.name} 中发现错误关键词'{keyword}'，"
                                f"需要重新初始化"
                            )
                            return True
            except Exception as e:
                logger.error(f"[ProjectStateInitializer] 检查文件失败 {file_path}: {e}")
                return True
        
        return False
    
    def _validate_phase_one_data(self, data: Dict) -> bool:
        """验证一阶段数据是否完整"""
        has_character = bool(data.get('character_design', {}).get('protagonist', {}).get('name'))
        has_world = bool(data.get('world_setting', {}).get('world_overview', {}).get('background'))
        
        if not has_character:
            logger.warning("[ProjectStateInitializer] ⚠️ 角色设计数据不完整")
        if not has_world:
            logger.warning("[ProjectStateInitializer] ⚠️ 世界观设定数据不完整")
        
        return has_character and has_world
    
    def _init_character_state(self, phase_one_data: Dict):
        """初始化角色状态文件"""
        logger.info("[ProjectStateInitializer] 初始化角色状态...")
        
        # 读取角色设计
        char_design = phase_one_data.get('character_design', {})
        protagonist = char_design.get('protagonist', {})
        core_allies = char_design.get('core_allies', [])
        supporting_roles = char_design.get('supporting_roles', [])
        early_antagonists = char_design.get('main_antagonists', {}).get('early_stage', [])
        
        protagonist_name = protagonist.get('name', '主角')
        
        # 构建主角信息
        protagonist_data = {
            "name": protagonist_name,
            "role": "主角",
            "health": "健康",
            "injuries": [],
            "abilities": [],
            "power_level": "F级（初始）",
            "location": "现实世界",
            "description": protagonist.get('identity', '主角'),
            "traits": protagonist.get('traits', []),
            "relationships": {},
            "introduced_chapter": 1,
            "last_appeared": 1,
            "changes_history": []
        }
        
        # 构建盟友信息
        allies_data = {}
        for ally in core_allies:
            ally_name = ally.get('name', '盟友')
            allies_data[ally_name] = {
                "name": ally_name,
                "role": ally.get('role', '盟友'),
                "health": "健康",
                "injuries": [],
                "abilities": [],
                "power_level": "未知",
                "location": "",
                "description": ally.get('contribution', ally.get('traits', [])),
                "traits": ally.get('traits', []),
                "relationships": {},
                "introduced_chapter": None,
                "last_appeared": None
            }
        
        # 添加配角
        for role in supporting_roles:
            role_name = role.get('name', '配角')
            allies_data[role_name] = {
                "name": role_name,
                "role": role.get('role', '配角'),
                "health": "健康",
                "injuries": [],
                "abilities": [],
                "power_level": "普通人",
                "location": "",
                "description": role.get('contribution', ''),
                "traits": role.get('traits', []),
                "relationships": {},
                "introduced_chapter": None,
                "last_appeared": None
            }
        
        # 构建敌人信息
        enemies_data = {}
        for enemy in early_antagonists:
            enemy_name = enemy.get('name', '反派')
            enemies_data[enemy_name] = {
                "name": enemy_name,
                "role": "反派",
                "health": "健康",
                "injuries": [],
                "abilities": [],
                "power_level": "未知",
                "location": "",
                "description": enemy.get('motivation', ''),
                "motivation": enemy.get('motivation', ''),
                "hate_point": enemy.get('hate_point', ''),
                "face_slapping_arc": enemy.get('face_slapping_arc', ''),
                "relationships": {},
                "introduced_chapter": None,
                "last_appeared": None
            }
        
        # 构建完整数据
        character_state = {
            "version": "2.0",
            "protagonist_name": protagonist_name,
            "protagonist": protagonist_data,
            "allies": allies_data,
            "enemies": enemies_data,
            "initialized_at": self._get_timestamp(),
            "source": "phase_one_products/角色设计.json"
        }
        
        # 保存文件
        with open(self.character_state_file, 'w', encoding='utf-8') as f:
            json.dump(character_state, f, ensure_ascii=False, indent=2)
        
        logger.info(
            f"[ProjectStateInitializer] ✅ 角色状态初始化完成: "
            f"{len(allies_data)}个盟友/配角, {len(enemies_data)}个敌人"
        )
    
    def _init_world_state(self, phase_one_data: Dict):
        """初始化世界状态文件"""
        logger.info("[ProjectStateInitializer] 初始化世界状态...")
        
        # 读取数据
        char_design = phase_one_data.get('character_design', {})
        world_setting = phase_one_data.get('world_setting', {})
        stage_goals = phase_one_data.get('stage_goals', [])
        progression = phase_one_data.get('progression_path', {})
        
        protagonist = char_design.get('protagonist', {})
        power_system = world_setting.get('power_system', {})
        world_overview = world_setting.get('world_overview', {})
        
        protagonist_name = protagonist.get('name', '主角')
        
        # 提取系统名称和机制
        # shen_lang_exclusive 在 combat_mechanics 子对象下
        combat_mechanics = power_system.get('combat_mechanics', {})
        system_mechanics = combat_mechanics.get('shen_lang_exclusive', '')
        system_name = self._extract_system_name(system_mechanics)
        pet_system = power_system.get('pet_system', '')
        
        # 等级体系
        level_standard = power_system.get('level_standard', 'F-SSS级')
        
        # 获取第一个阶段目标
        first_stage = stage_goals[0] if stage_goals else {}
        
        # 构建剧情线索
        plot_threads = {}
        if first_stage:
            goal_id = first_stage.get('goal_id', 'G1')
            key_deliverables = first_stage.get('key_deliverables', [])
            plot_threads[goal_id] = {
                "name": goal_id,
                "status": "active",
                "introduced_chapter": 1,
                "last_mentioned": 1,
                "priority": 10,
                "description": first_stage.get('description', ''),
                "expected_chapters": first_stage.get('expected_chapters', ''),
                "success_criteria": first_stage.get('success_criteria', ''),
                "key_deliverables": key_deliverables,
                "next_trigger": key_deliverables[0] if key_deliverables else ''
            }
        
        # 构建世界规则（从 world_rules 读取）
        world_rules = world_setting.get('world_rules', {})
        
        # 构建世界状态 - 使用新的通用字段
        world_state = {
            "version": "2.0",
            "protagonist": {
                "name": protagonist_name,
                "health": "健康",
                "injuries": [],
                "abilities_unlocked": [],
                "current_location": "现实世界",
                "relationships": {}
            },
            "allies": {},
            "enemies": {},
            "plot_threads": plot_threads,
            "system_rules": {
                # 新的通用字段
                "system_name": system_name,
                "system_type": "金手指/系统",
                "current_level": "F级（初始）",
                "current_power": 0.0,
                "max_power": 0.0,
                "unlocked_abilities": [],
                "special_states": [],
                # 详细的系统信息
                "system_mechanics": system_mechanics[:300] + "..." if len(system_mechanics) > 300 else system_mechanics,
                "pet_system": pet_system,
                "level_standard": level_standard,
                "current_power_stage": "早期（1-30级）",
                "activation_status": "未激活/等待觉醒",
                # 兼容旧字段
                "current_playing_degree": 0.0,
                "max_playing_degree": 0.0,
                "unlocked_skills": [],
                "cooldown_end_chapter": 0
            },
            "world_rules": world_rules,
            "world_overview": {
                "background": world_overview.get('background', '')[:200],
                "core_concept": world_overview.get('core_concept', '')[:200],
                "tone": world_overview.get('tone', '')
            },
            "important_items": [],
            "global_events": [],
            "initialized_at": self._get_timestamp(),
            "source": "phase_one_products"
        }
        
        # 保存文件
        with open(self.world_state_file, 'w', encoding='utf-8') as f:
            json.dump(world_state, f, ensure_ascii=False, indent=2)
        
        logger.info(f"[ProjectStateInitializer] ✅ 世界状态初始化完成")
        logger.info(f"  - 系统名称: {system_name}")
        logger.info(f"  - 等级体系: {level_standard}")
        logger.info(f"  - 阶段目标: {goal_id if first_stage else '无'}")
    
    def _init_chapter_extractions(self):
        """初始化章节提取文件（空列表）"""
        logger.info("[ProjectStateInitializer] 初始化章节提取记录...")
        
        with open(self.chapter_extractions_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=2)
        
        logger.info("[ProjectStateInitializer] ✅ 章节提取记录初始化完成: 空列表")
    
    def _extract_system_name(self, mechanics_text: str) -> str:
        """从系统机制描述中提取系统名称"""
        if not mechanics_text:
            return "未知系统"
        
        # 尝试提取【】中的内容
        match = re.search(r'【(.+?)】', mechanics_text)
        if match:
            return match.group(1)
        
        # 尝试匹配 "XX系统"
        match = re.search(r'(\S+系统)', mechanics_text)
        if match:
            return match.group(1)
        
        # 尝试匹配 "XX能力"
        match = re.search(r'(\S+能力)', mechanics_text)
        if match:
            return match.group(1)
        
        # 返回前30个字符
        return mechanics_text[:30] + "..." if len(mechanics_text) > 30 else mechanics_text
    
    def _get_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# ========== 便捷函数 ==========

def initialize_project_state(project_path: Path, force: bool = False) -> bool:
    """
    便捷函数：初始化项目状态
    
    Args:
        project_path: 项目路径
        force: 是否强制重新初始化
        
    Returns:
        bool: 是否执行了初始化
    """
    initializer = ProjectStateInitializer(project_path)
    return initializer.initialize_if_needed(force)


def check_project_state_health(project_path: Path) -> Dict:
    """
    检查项目状态健康度
    
    Returns:
        Dict: 健康检查结果
    """
    initializer = ProjectStateInitializer(project_path)
    
    result = {
        "healthy": True,
        "issues": [],
        "files_status": {}
    }
    
    # 检查文件是否存在
    for file_name, file_path in [
        ("character_state", initializer.character_state_file),
        ("world_state", initializer.world_state_file),
        ("chapter_extractions", initializer.chapter_extractions_file)
    ]:
        exists = file_path.exists()
        result["files_status"][file_name] = {"exists": exists}
        
        if not exists:
            result["healthy"] = False
            result["issues"].append(f"{file_name} 文件不存在")
        else:
            # 检查错误关键词
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    errors_found = [k for k in initializer.ERROR_KEYWORDS if k in content]
                    result["files_status"][file_name]["errors"] = errors_found
                    if errors_found:
                        result["healthy"] = False
                        result["issues"].append(f"{file_name} 包含错误关键词: {errors_found}")
            except Exception as e:
                result["healthy"] = False
                result["issues"].append(f"{file_name} 读取失败: {e}")
    
    return result


# ========== 调试入口 ==========

if __name__ == "__main__":
    # 测试初始化器
    import sys
    
    if len(sys.argv) > 1:
        test_path = Path(sys.argv[1])
    else:
        test_path = Path("C:/work/xsdm/小说项目/yanghailin/开局带只二哈，我直播气哭邪神")
    
    print(f"测试项目路径: {test_path}")
    print("=" * 60)
    
    # 检查健康度
    print("\n1. 检查当前状态健康度...")
    health = check_project_state_health(test_path)
    print(f"健康状态: {'✅ 健康' if health['healthy'] else '❌ 不健康'}")
    if health['issues']:
        print(f"问题: {health['issues']}")
    
    # 执行初始化
    print("\n2. 执行强制初始化...")
    result = initialize_project_state(test_path, force=True)
    print(f"初始化结果: {'✅ 成功' if result else '❌ 失败'}")
    
    # 再次检查
    print("\n3. 再次检查健康度...")
    health = check_project_state_health(test_path)
    print(f"健康状态: {'✅ 健康' if health['healthy'] else '❌ 不健康'}")
    
    print("\n" + "=" * 60)
    print("完成!")
