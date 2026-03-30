"""
角色状态管理器
跨批次保持角色设定一致性和完整状态
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


@dataclass
class CharacterStatus:
    """角色状态"""
    name: str
    role: str = ""  # 主角/盟友/敌人/中立
    health: str = "健康"  # 健康/轻伤/重伤/濒死/死亡
    injuries: List[str] = field(default_factory=list)  # 伤势列表
    abilities: List[str] = field(default_factory=list)  # 已解锁能力
    power_level: str = ""  # 力量等级
    location: str = ""  # 当前位置
    description: str = ""  # 角色描述
    relationships: Dict[str, str] = field(default_factory=dict)  # 关系
    introduced_chapter: int = 0  # 首次出场章节
    last_appeared: int = 0  # 最后出场章节
    changes_history: List[Dict] = field(default_factory=list)  # 状态变更历史


class CharacterStateManager:
    """
    角色状态管理器（扩展版）
    
    功能：
    1. 跨批次持久化完整角色状态
    2. 管理主角、盟友、敌人的健康、能力、位置等
    3. 与 world_state.json 双向同步
    4. 检测和防止角色名漂移
    5. 提供批次总结后的状态更新
    """
    
    def __init__(self, project_path: str):
        """
        初始化
        
        Args:
            project_path: 项目目录路径
        """
        self.project_path = Path(project_path)
        self.state_file = self.project_path / ".character_state.json"
        self.world_state_file = self.project_path / ".world_state.json"
        
        # 加载或初始化状态
        self.state = self._load_or_init_state()
    
    def _load_or_init_state(self) -> Dict:
        """加载或初始化状态"""
        # 优先从 character_state.json 加载
        if self.state_file.exists():
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    state = json.load(f)
                logger.info(f"[CharacterState] 从 {self.state_file} 加载状态")
                return state
            except Exception as e:
                logger.error(f"[CharacterState] 加载状态失败: {e}")
        
        # 尝试从 world_state.json 迁移
        if self.world_state_file.exists():
            try:
                with open(self.world_state_file, 'r', encoding='utf-8') as f:
                    world_state = json.load(f)
                
                # 迁移数据
                state = self._migrate_from_world_state(world_state)
                logger.info(f"[CharacterState] 从 world_state.json 迁移状态")
                self.save_state(state)
                return state
            except Exception as e:
                logger.error(f"[CharacterState] 迁移状态失败: {e}")
        
        # 创建默认状态
        return self._create_default_state()
    
    def _create_default_state(self) -> Dict:
        """创建默认状态"""
        return {
            "version": "2.0",
            "protagonist_name": "",
            "protagonist": {},
            "allies": {},
            "enemies": {},
            "neutral": {},  # 中立角色
            "faction_relations": {},  # 势力关系
            "summary": {  # 批次总结统计
                "total_chapters": 0,
                "total_characters": 0,
                "last_batch_end": 0,
                "major_events": []
            },
            "saved_at": datetime.now().isoformat()
        }
    
    def _migrate_from_world_state(self, world_state: Dict) -> Dict:
        """从 world_state.json 迁移数据"""
        state = self._create_default_state()
        
        # 迁移主角
        protagonist = world_state.get('protagonist', {})
        if protagonist:
            state['protagonist_name'] = protagonist.get('name', '')
            state['protagonist'] = {
                "name": protagonist.get('name', ''),
                "role": "主角",
                "health": protagonist.get('health', '健康'),
                "injuries": protagonist.get('injuries', []),
                "abilities": protagonist.get('abilities_unlocked', []),
                "power_level": "",
                "location": protagonist.get('current_location', ''),
                "relationships": protagonist.get('relationships', {}),
                "description": ""
            }
        
        # 迁移盟友
        allies = world_state.get('allies', {})
        for name, ally in allies.items():
            state['allies'][name] = {
                "name": name,
                "role": "盟友",
                "health": ally.get('health', '健康'),
                "injuries": ally.get('injuries', []),
                "abilities": ally.get('abilities_unlocked', []),
                "power_level": "",
                "location": ally.get('current_location', ''),
                "relationships": ally.get('relationships', {}),
                "description": ally.get('description', ''),
                "introduced_chapter": ally.get('introduced_chapter', 0)
            }
        
        # 迁移敌人
        enemies = world_state.get('enemies', {})
        for name, enemy in enemies.items():
            state['enemies'][name] = {
                "name": name,
                "role": "敌人",
                "health": enemy.get('health', '健康'),
                "injuries": enemy.get('injuries', []),
                "abilities": enemy.get('abilities_unlocked', []),
                "power_level": "",
                "location": enemy.get('current_location', ''),
                "relationships": enemy.get('relationships', {}),
                "description": enemy.get('description', ''),
                "introduced_chapter": enemy.get('introduced_chapter', 0)
            }
        
        # 迁移统计信息
        state['summary']['total_chapters'] = world_state.get('total_chapters', 0)
        
        return state
    
    def save_state(self, state: Dict = None) -> None:
        """
        保存角色状态
        
        Args:
            state: 状态字典，如果为None则保存当前状态
        """
        if state is None:
            state = self.state
        
        state['saved_at'] = datetime.now().isoformat()
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            logger.info(f"[CharacterState] 状态已保存: {self.state_file}")
        except Exception as e:
            logger.error(f"[CharacterState] 保存状态失败: {e}")
    
    def load_state(self) -> Dict:
        """加载角色状态"""
        return self.state
    
    # ==================== 主角名管理 ====================
    
    def get_protagonist_name(self) -> Optional[str]:
        """获取持久化的主角名"""
        return self.state.get('protagonist_name') or None
    
    def save_protagonist_name(self, name: str) -> None:
        """保存主角名"""
        self.state['protagonist_name'] = name
        if 'protagonist' not in self.state:
            self.state['protagonist'] = {}
        self.state['protagonist']['name'] = name
        self.state['protagonist']['role'] = '主角'
        self.save_state()
        logger.info(f"[CharacterState] 主角名已保存: {name}")
    
    # ==================== 角色管理 ====================
    
    def add_or_update_character(self, char_info: Dict, char_type: str = 'neutral') -> None:
        """
        添加或更新角色
        
        Args:
            char_info: 角色信息字典
            char_type: 角色类型 (protagonist/ally/enemy/neutral)
        """
        name = char_info.get('name')
        if not name:
            return
        
        # 标准化角色数据
        char_data = {
            "name": name,
            "role": char_info.get('role', char_type),
            "health": char_info.get('health', '健康'),
            "injuries": char_info.get('injuries', []),
            "abilities": char_info.get('abilities', char_info.get('abilities_unlocked', [])),
            "power_level": char_info.get('power_level', ''),
            "location": char_info.get('location', char_info.get('current_location', '')),
            "description": char_info.get('description', ''),
            "relationships": char_info.get('relationships', {}),
            "introduced_chapter": char_info.get('introduced_chapter', 0),
            "last_appeared": char_info.get('last_appeared', 0),
            "changes_history": char_info.get('changes_history', [])
        }
        
        # 根据类型放入不同字典
        if char_type == 'protagonist' or name == self.state.get('protagonist_name'):
            self.state['protagonist'] = char_data
        elif char_type == 'ally':
            self.state['allies'][name] = char_data
        elif char_type == 'enemy':
            self.state['enemies'][name] = char_data
        else:
            self.state['neutral'][name] = char_data
        
        logger.info(f"[CharacterState] 角色已更新: {name} ({char_data['role']})")
    
    def update_character_status(self, name: str, changes: Dict, chapter: int = 0) -> None:
        """
        更新角色状态
        
        Args:
            name: 角色名
            changes: 变更信息
            chapter: 发生章节
        """
        char = self._find_character(name)
        if not char:
            logger.warning(f"[CharacterState] 未找到角色: {name}")
            return
        
        # 记录变更历史
        change_record = {
            "chapter": chapter,
            "timestamp": datetime.now().isoformat(),
            "changes": changes
        }
        char.setdefault('changes_history', []).append(change_record)
        
        # 应用变更
        if 'health' in changes:
            char['health'] = changes['health']
        if 'injuries' in changes:
            char['injuries'].extend(changes['injuries'])
        if 'abilities' in changes:
            for ability in changes['abilities']:
                if ability not in char['abilities']:
                    char['abilities'].append(ability)
        if 'location' in changes:
            char['location'] = changes['location']
        if 'power_level' in changes:
            char['power_level'] = changes['power_level']
        
        char['last_appeared'] = chapter
        
        logger.info(f"[CharacterState] 角色状态更新: {name} @ 第{chapter}章")
    
    def _find_character(self, name: str) -> Optional[Dict]:
        """查找角色"""
        # 检查主角
        if self.state.get('protagonist', {}).get('name') == name:
            return self.state['protagonist']
        # 检查盟友
        if name in self.state.get('allies', {}):
            return self.state['allies'][name]
        # 检查敌人
        if name in self.state.get('enemies', {}):
            return self.state['enemies'][name]
        # 检查中立
        if name in self.state.get('neutral', {}):
            return self.state['neutral'][name]
        return None
    
    # ==================== 批次总结更新 ====================
    
    def update_after_batch(self, batch_info: Dict) -> None:
        """
        批次生成后更新角色状态
        
        Args:
            batch_info: 批次信息，包含新角色、状态变更等
        """
        chapter_start = batch_info.get('chapter_start', 0)
        chapter_end = batch_info.get('chapter_end', 0)
        
        # 更新新角色
        new_characters = batch_info.get('new_characters', [])
        for char in new_characters:
            role = char.get('role', '')
            if '敌' in role or '反' in role or 'villain' in role.lower():
                char_type = 'enemy'
            elif '友' in role or '盟' in role or 'ally' in role.lower():
                char_type = 'ally'
            else:
                char_type = 'neutral'
            
            char['introduced_chapter'] = chapter_start
            self.add_or_update_character(char, char_type)
        
        # 更新角色变化
        character_changes = batch_info.get('character_changes', [])
        for change in character_changes:
            name = change.get('name')
            if name:
                self.update_character_status(name, {
                    'health': change.get('health', ''),
                    'injuries': [change.get('change', '')] if 'injuries' not in change else change['injuries'],
                    'abilities': change.get('new_abilities', [])
                }, chapter_end)
        
        # 更新总结统计
        self.state['summary']['total_chapters'] = max(
            self.state['summary'].get('total_chapters', 0),
            chapter_end
        )
        self.state['summary']['last_batch_end'] = chapter_end
        
        # 计算总角色数
        total = 1  # 主角
        total += len(self.state.get('allies', {}))
        total += len(self.state.get('enemies', {}))
        total += len(self.state.get('neutral', {}))
        self.state['summary']['total_characters'] = total
        
        # 保存
        self.save_state()
        logger.info(f"[CharacterState] 批次总结已更新: 第{chapter_start}-{chapter_end}章")
    
    # ==================== 同步到 world_state ====================
    
    def sync_to_world_state(self) -> None:
        """将当前状态同步到 world_state.json"""
        try:
            world_state = {}
            if self.world_state_file.exists():
                with open(self.world_state_file, 'r', encoding='utf-8') as f:
                    world_state = json.load(f)
            
            # 同步主角
            if self.state.get('protagonist'):
                world_state['protagonist'] = {
                    'name': self.state['protagonist']['name'],
                    'health': self.state['protagonist']['health'],
                    'injuries': self.state['protagonist']['injuries'],
                    'abilities_unlocked': self.state['protagonist']['abilities'],
                    'current_location': self.state['protagonist']['location'],
                    'relationships': self.state['protagonist']['relationships']
                }
            
            # 同步盟友
            world_state['allies'] = {}
            for name, ally in self.state.get('allies', {}).items():
                world_state['allies'][name] = {
                    'name': name,
                    'health': ally['health'],
                    'injuries': ally['injuries'],
                    'abilities_unlocked': ally['abilities'],
                    'current_location': ally['location'],
                    'relationships': ally['relationships'],
                    'description': ally['description'],
                    'introduced_chapter': ally['introduced_chapter']
                }
            
            # 同步敌人
            world_state['enemies'] = {}
            for name, enemy in self.state.get('enemies', {}).items():
                world_state['enemies'][name] = {
                    'name': name,
                    'health': enemy['health'],
                    'injuries': enemy['injuries'],
                    'abilities_unlocked': enemy['abilities'],
                    'current_location': enemy['location'],
                    'relationships': enemy['relationships'],
                    'description': enemy['description'],
                    'introduced_chapter': enemy['introduced_chapter']
                }
            
            # 保存 world_state
            with open(self.world_state_file, 'w', encoding='utf-8') as f:
                json.dump(world_state, f, ensure_ascii=False, indent=2)
            
            logger.info(f"[CharacterState] 已同步到 world_state.json")
            
        except Exception as e:
            logger.error(f"[CharacterState] 同步到 world_state 失败: {e}")
    
    # ==================== 校验和修复 ====================
    
    def validate_novel_data(self, novel_data: Dict) -> Dict:
        """校验并修正 novel_data 中的角色设定"""
        # 从 novel_data 提取当前主角名
        user_choices = novel_data.get('user_choices', {})
        current_name = user_choices.get('protagonist_name', '')
        
        if not current_name:
            char_design = novel_data.get('character_design', {})
            protagonist = char_design.get('protagonist', {})
            if isinstance(protagonist, dict):
                current_name = protagonist.get('name', '')
        
        # 从状态加载已保存的主角名
        saved_name = self.get_protagonist_name()
        
        if saved_name and current_name and saved_name != current_name:
            logger.warning(
                f"[CharacterState] 主角名冲突！novel_data: {current_name}, "
                f"已保存: {saved_name}。使用已保存的名字保持一致性。"
            )
            novel_data['user_choices'] = user_choices
            novel_data['user_choices']['protagonist_name'] = saved_name
            
            if 'character_design' in novel_data and 'protagonist' in novel_data['character_design']:
                novel_data['character_design']['protagonist']['name'] = saved_name
                
        elif current_name and not saved_name:
            self.save_protagonist_name(current_name)
            
        elif saved_name and not current_name:
            logger.info(f"[CharacterState] 从状态恢复主角名: {saved_name}")
            novel_data.setdefault('user_choices', {})
            novel_data['user_choices']['protagonist_name'] = saved_name
        
        return novel_data
    
    def get_summary(self) -> str:
        """获取状态摘要（用于日志）"""
        name = self.state.get('protagonist_name', '未设置')
        allies_count = len(self.state.get('allies', {}))
        enemies_count = len(self.state.get('enemies', {}))
        total_chapters = self.state.get('summary', {}).get('total_chapters', 0)
        
        return (f"[CharacterState] 主角: {name}, "
                f"盟友: {allies_count}人, 敌人: {enemies_count}人, "
                f"总章节: {total_chapters}")
    
    def get_character_report(self) -> str:
        """获取角色状态报告（Markdown格式）"""
        lines = ["# 角色状态报告\n"]
        
        # 主角
        protagonist = self.state.get('protagonist', {})
        if protagonist:
            lines.append(f"## 主角: {protagonist.get('name', '未知')}")
            lines.append(f"- 健康: {protagonist.get('health', '未知')}")
            lines.append(f"- 能力: {', '.join(protagonist.get('abilities', []))}")
            lines.append(f"- 位置: {protagonist.get('location', '未知')}")
            lines.append("")
        
        # 盟友
        allies = self.state.get('allies', {})
        if allies:
            lines.append(f"## 盟友 ({len(allies)}人)")
            for name, ally in allies.items():
                lines.append(f"### {name}")
                lines.append(f"- 健康: {ally.get('health', '未知')}")
                lines.append(f"- 描述: {ally.get('description', '无')[:50]}...")
                lines.append("")
        
        # 敌人
        enemies = self.state.get('enemies', {})
        if enemies:
            lines.append(f"## 敌人 ({len(enemies)}人)")
            for name, enemy in enemies.items():
                lines.append(f"### {name}")
                lines.append(f"- 健康: {enemy.get('health', '未知')}")
                lines.append(f"- 描述: {enemy.get('description', '无')[:50]}...")
                lines.append("")
        
        return "\n".join(lines)
