"""
背景资料数据管理器
直接获取并返回同人小说的背景资料库JSON数据
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

class BackgroundDataManager:
    """背景资料数据管理器"""
    
    def __init__(self, knowledge_base_path: Optional[str] = None):
        """
        初始化背景资料管理器
        
        Args:
            knowledge_base_path: 知识库文件路径，默认使用简化版本
        """
        if knowledge_base_path is None:
            # 默认使用简化版知识库
            current_dir = Path(__file__).parent.parent.parent
            knowledge_base_path = current_dir / "knowledge_base" / "凡人修仙传" / "simplified_knowledge_base.json"
        
        self.knowledge_base_path = Path(knowledge_base_path)
        self.knowledge_base_data = None
        self._load_knowledge_base()
    
    def _load_knowledge_base(self) -> None:
        """加载知识库数据"""
        try:
            if self.knowledge_base_path.exists():
                with open(self.knowledge_base_path, 'r', encoding='utf-8') as f:
                    self.knowledge_base_data = json.load(f)
            else:
                print(f"警告：知识库文件不存在: {self.knowledge_base_path}")
                self.knowledge_base_data = {}
        except Exception as e:
            print(f"加载知识库失败: {e}")
            self.knowledge_base_data = {}
    
    def get_all_background_data(self) -> Dict[str, Any]:
        """
        获取所有背景资料数据
        
        Returns:
            完整的知识库JSON数据
        """
        return self.knowledge_base_data or {}
    
    def get_worldview_data(self) -> Dict[str, Any]:
        """
        获取世界观背景资料
        
        Returns:
            世界观相关的JSON数据
        """
        if not self.knowledge_base_data:
            return {}
        return self.knowledge_base_data.get("worldview", {})
    
    def get_characters_data(self) -> Dict[str, Any]:
        """
        获取角色背景资料
        
        Returns:
            角色相关的JSON数据
        """
        if not self.knowledge_base_data:
            return {}
        return self.knowledge_base_data.get("characters", {})
    
    def get_power_system_data(self) -> Dict[str, Any]:
        """
        获取修炼体系背景资料
        
        Returns:
            修炼体系相关的JSON数据
        """
        if not self.knowledge_base_data:
            return {}
        return self.knowledge_base_data.get("power_system", {})
    
    def get_sects_data(self) -> Dict[str, Any]:
        """
        获取门派势力背景资料
        
        Returns:
            门派势力相关的JSON数据
        """
        if not self.knowledge_base_data:
            return {}
        return self.knowledge_base_data.get("sects_and_factions", {})
    
    def get_plot_data(self) -> Dict[str, Any]:
        """
        获取剧情元素背景资料
        
        Returns:
            剧情元素相关的JSON数据
        """
        if not self.knowledge_base_data:
            return {}
        return self.knowledge_base_data.get("plot_elements", {})
    
    def get_creation_guidelines(self) -> Dict[str, Any]:
        """
        获取创作指南
        
        Returns:
            创作指南相关的JSON数据
        """
        if not self.knowledge_base_data:
            return {}
        return self.knowledge_base_data.get("creation_guidelines", {})
    
    def get_background_by_category(self, category: str) -> Dict[str, Any]:
        """
        根据分类获取背景资料
        
        Args:
            category: 分类名称（worldview, characters, power_system等）
            
        Returns:
            指定分类的背景资料
        """
        if not self.knowledge_base_data:
            return {}
        return self.knowledge_base_data.get(category, {})
    
    def get_background_for_creative_generation(self) -> Dict[str, Any]:
        """
        获取用于创意生成的背景资料
        
        Returns:
            创意生成所需的核心背景资料
        """
        if not self.knowledge_base_data:
            return {}
        
        # 返回创意生成最需要的核心数据
        creative_background = {
            "世界观": self.knowledge_base_data.get("worldview", {}),
            "角色模板": self.knowledge_base_data.get("characters", {}),
            "修炼体系": self.knowledge_base_data.get("power_system", {}),
            "剧情元素": self.knowledge_base_data.get("plot_elements", {}),
            "创作指南": self.knowledge_base_data.get("creation_guidelines", {})
        }
        
        return creative_background
    
    def reload_background_data(self) -> bool:
        """
        重新加载背景资料
        
        Returns:
            是否加载成功
        """
        try:
            self._load_knowledge_base()
            return bool(self.knowledge_base_data)
        except Exception as e:
            print(f"重新加载失败: {e}")
            return False
    
    def get_data_status(self) -> Dict[str, Any]:
        """
        获取数据状态信息
        
        Returns:
            数据加载状态和基本信息
        """
        return {
            "loaded": bool(self.knowledge_base_data),
            "file_path": str(self.knowledge_base_path),
            "file_exists": self.knowledge_base_path.exists(),
            "data_size": len(str(self.knowledge_base_data)) if self.knowledge_base_data else 0,
            "main_sections": list(self.knowledge_base_data.keys()) if self.knowledge_base_data else []
        }


# 使用示例
if __name__ == "__main__":
    # 创建背景资料管理器
    bg_manager = BackgroundDataManager()
    
    # 获取所有背景资料
    all_data = bg_manager.get_all_background_data()
    print("完整背景资料:", type(all_data), "包含分类:", list(all_data.keys()))
    
    # 获取创意生成背景资料
    creative_data = bg_manager.get_background_for_creative_generation()
    print("\n创意生成背景资料:")
    for category, data in creative_data.items():
        print(f"  {category}: {len(str(data))} 字符")
    
    # 获取数据状态
    status = bg_manager.get_data_status()
    print(f"\n数据状态: {status}")