"""
角色状态管理器
跨批次保持角色设定一致性
"""
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class CharacterStateManager:
    """
    角色状态管理器
    
    功能：
    1. 跨批次持久化角色设定（主角名、关键设定等）
    2. 检测和防止角色名漂移
    3. 提供统一的角色设定获取接口
    """
    
    def __init__(self, project_path: str):
        """
        初始化
        
        Args:
            project_path: 项目目录路径
        """
        self.project_path = Path(project_path)
        self.state_file = self.project_path / ".character_state.json"
    
    def save_state(self, state: Dict) -> None:
        """
        保存角色状态
        
        Args:
            state: 状态字典
        """
        state['saved_at'] = datetime.now().isoformat()
        state['version'] = '1.0'
        
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
            logger.info(f"[CharacterState] 状态已保存: {self.state_file}")
        except Exception as e:
            logger.error(f"[CharacterState] 保存状态失败: {e}")
    
    def load_state(self) -> Dict:
        """
        加载角色状态
        
        Returns:
            状态字典，如果不存在则返回空字典
        """
        if not self.state_file.exists():
            return {}
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"[CharacterState] 加载状态失败: {e}")
            return {}
    
    def get_protagonist_name(self) -> Optional[str]:
        """
        获取持久化的主角名
        
        Returns:
            主角名，如果不存在则返回None
        """
        state = self.load_state()
        name = state.get('protagonist_name', '')
        return name if name else None
    
    def save_protagonist_name(self, name: str) -> None:
        """
        保存主角名
        
        Args:
            name: 主角名
        """
        state = self.load_state()
        state['protagonist_name'] = name
        self.save_state(state)
        logger.info(f"[CharacterState] 主角名已保存: {name}")
    
    def validate_novel_data(self, novel_data: Dict) -> Dict:
        """
        校验并修正 novel_data 中的角色设定
        
        如果 novel_data 中没有主角名，尝试从状态恢复
        如果 novel_data 中有主角名，保存到状态
        
        Args:
            novel_data: 小说数据
            
        Returns:
            修正后的 novel_data
        """
        # 从 novel_data 提取当前主角名
        current_name = ''
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
            # 检测到冲突！使用已保存的名字（保持一致性）
            logger.warning(
                f"[CharacterState] 主角名冲突！novel_data: {current_name}, "
                f"已保存: {saved_name}。使用已保存的名字保持一致性。"
            )
            novel_data['user_choices'] = user_choices
            novel_data['user_choices']['protagonist_name'] = saved_name
            
            # 同时修改 character_design
            if 'character_design' in novel_data and 'protagonist' in novel_data['character_design']:
                novel_data['character_design']['protagonist']['name'] = saved_name
                
        elif current_name and not saved_name:
            # 第一次生成，保存主角名
            self.save_protagonist_name(current_name)
            
        elif saved_name and not current_name:
            # novel_data 中没有主角名，从状态恢复
            logger.info(f"[CharacterState] 从状态恢复主角名: {saved_name}")
            novel_data.setdefault('user_choices', {})
            novel_data['user_choices']['protagonist_name'] = saved_name
        
        return novel_data
    
    def get_summary(self) -> str:
        """
        获取状态摘要（用于日志）
        """
        state = self.load_state()
        if not state:
            return "[CharacterState] 无持久化状态"
        
        name = state.get('protagonist_name', '未设置')
        saved_at = state.get('saved_at', '未知')
        return f"[CharacterState] 主角名: {name}, 保存时间: {saved_at}"
