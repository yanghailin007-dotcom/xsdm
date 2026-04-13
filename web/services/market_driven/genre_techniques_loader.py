# -*- coding: utf-8 -*-
"""
题材技法加载器 (GenreTechniquesLoader)

负责动态加载不同题材的技法配置文件
这是题材分离的核心组件
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ShockStep:
    """震惊铺展步骤"""
    order: int
    name: str
    content: str
    format: str
    examples: List[str] = field(default_factory=list)


@dataclass
class BarrageTemplate:
    """弹幕模板"""
    type: str
    emotion: str
    examples: List[str]


@dataclass
class SystemPrompt:
    """系统提示音"""
    type: str
    template: str
    usage: str


@dataclass
class ForbiddenElement:
    """禁用元素"""
    element: str
    examples: List[str]
    reason: str


@dataclass
class RequiredElement:
    """必须元素"""
    element: str
    check: str
    severity: str = "warning"  # critical/warning/recommended


@dataclass
class GenreTechniques:
    """题材技法完整数据结构"""
    genre: str
    version: str
    description: str
    
    # 震惊铺展
    shock_progression: Dict[str, Any]
    
    # 题材特定规则
    barrage_rules: Optional[Dict] = None  # 国运文
    money_rules: Optional[Dict] = None    # 神豪文
    
    # 系统提示音
    system_prompts: List[SystemPrompt] = field(default_factory=list)
    
    # 模板
    bystander_templates: Optional[List[Dict]] = None  # 神豪文
    
    # 场景要求
    consumption_scenes: Optional[Dict] = None  # 神豪文
    data_visualization: Optional[Dict] = None  # 国运文
    
    # 元素控制
    forbidden_elements: Dict[str, List[ForbiddenElement]] = field(default_factory=dict)
    required_elements: Dict[str, List[RequiredElement]] = field(default_factory=dict)
    
    # 对话达成
    dialogue_achievement: Dict[str, Any] = field(default_factory=dict)
    
    # 节奏
    pacing: Dict[str, Any] = field(default_factory=dict)
    
    # 质量检查点
    quality_checkpoints: List[Dict] = field(default_factory=list)
    
    # 其他题材特定内容
    raw_data: Dict[str, Any] = field(default_factory=dict)


class GenreTechniquesLoader:
    """
    题材技法加载器
    
    负责从YAML文件加载不同题材的技法配置
    支持缓存和动态加载
    """
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        初始化加载器
        
        Args:
            base_path: 技法文件的基础路径，默认使用项目内路径
        """
        if base_path is None:
            # 默认路径：项目根目录/prompt_packages/default/market_driven/v2_config/genre_techniques
            current_file = Path(__file__).resolve()
            project_root = current_file.parent.parent.parent.parent
            base_path = project_root / "prompt_packages" / "default" / "market_driven" / "v2_config" / "genre_techniques"
        
        self.base_path = Path(base_path)
        self._cache: Dict[str, GenreTechniques] = {}
        
        logger.info(f"[GenreTechniquesLoader] 初始化完成，基础路径: {self.base_path}")
    
    def load(self, genre: str, use_cache: bool = True) -> GenreTechniques:
        """
        加载指定题材的技法
        
        Args:
            genre: 题材名称（如：国运文、神豪文）
            use_cache: 是否使用缓存
        
        Returns:
            GenreTechniques对象
        
        Raises:
            FileNotFoundError: 如果找不到对应的技法文件
        """
        # 检查缓存
        if use_cache and genre in self._cache:
            logger.debug(f"[GenreTechniquesLoader] 使用缓存: {genre}")
            return self._cache[genre]
        
        # 构建文件路径
        file_path = self.base_path / f"{genre}.yaml"
        
        # 如果找不到，使用通用模板
        if not file_path.exists():
            logger.warning(f"[GenreTechniquesLoader] 找不到 {genre}.yaml，使用通用模板")
            file_path = self.base_path / "通用.yaml"
            if not file_path.exists():
                raise FileNotFoundError(f"找不到题材技法文件: {genre}.yaml 或 通用.yaml")
        
        # 加载YAML文件
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_data = yaml.safe_load(f)
            
            # 解析为数据结构
            techniques = self._parse_techniques(raw_data)
            
            # 缓存
            if use_cache:
                self._cache[genre] = techniques
            
            logger.info(f"[GenreTechniquesLoader] 成功加载题材技法: {genre} (版本: {techniques.version})")
            return techniques
            
        except Exception as e:
            logger.error(f"[GenreTechniquesLoader] 加载 {genre} 失败: {e}")
            raise
    
    def _parse_techniques(self, raw_data: Dict) -> GenreTechniques:
        """
        解析原始YAML数据为GenreTechniques对象
        """
        genre = raw_data.get('genre', '未知')
        version = raw_data.get('version', '1.0.0')
        description = raw_data.get('description', '')
        
        # 解析系统提示音
        system_prompts = []
        for sp in raw_data.get('system_prompts', []):
            system_prompts.append(SystemPrompt(
                type=sp.get('type', ''),
                template=sp.get('template', ''),
                usage=sp.get('usage', '')
            ))
        
        # 解析禁用元素
        forbidden_elements = {}
        fe_data = raw_data.get('forbidden_elements', {})
        if 'items' in fe_data:
            forbidden_elements['items'] = [
                ForbiddenElement(
                    element=item.get('element', ''),
                    examples=item.get('examples', []),
                    reason=item.get('reason', '')
                )
                for item in fe_data['items']
            ]
        
        # 解析必须元素
        required_elements = {}
        re_data = raw_data.get('required_elements', {})
        if 'items' in re_data:
            required_elements['items'] = [
                RequiredElement(
                    element=item.get('element', ''),
                    check=item.get('check', ''),
                    severity=item.get('severity', 'warning')
                )
                for item in re_data['items']
            ]
        
        return GenreTechniques(
            genre=genre,
            version=version,
            description=description,
            shock_progression=raw_data.get('shock_progression', {}),
            barrage_rules=raw_data.get('barrage_rules'),
            money_rules=raw_data.get('money_rules'),
            system_prompts=system_prompts,
            bystander_templates=raw_data.get('bystander_templates'),
            consumption_scenes=raw_data.get('consumption_scenes'),
            data_visualization=raw_data.get('data_visualization'),
            forbidden_elements=forbidden_elements,
            required_elements=required_elements,
            dialogue_achievement=raw_data.get('dialogue_achievement', {}),
            pacing=raw_data.get('pacing', {}),
            quality_checkpoints=raw_data.get('quality_checkpoints', []),
            raw_data=raw_data
        )
    
    def get_available_genres(self) -> List[str]:
        """
        获取所有可用的题材列表
        
        Returns:
            题材名称列表
        """
        genres = []
        for file_path in self.base_path.glob("*.yaml"):
            genre_name = file_path.stem
            genres.append(genre_name)
        return sorted(genres)
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        logger.info("[GenreTechniquesLoader] 缓存已清除")
    
    def reload(self, genre: str) -> GenreTechniques:
        """
        强制重新加载（忽略缓存）
        """
        return self.load(genre, use_cache=False)
    
    def is_genre_available(self, genre: str) -> bool:
        """
        检查题材是否可用
        """
        file_path = self.base_path / f"{genre}.yaml"
        return file_path.exists()


# ==================== 快捷函数 ====================

_loader: Optional[GenreTechniquesLoader] = None


def get_genre_techniques_loader() -> GenreTechniquesLoader:
    """
    获取全局单例加载器
    """
    global _loader
    if _loader is None:
        _loader = GenreTechniquesLoader()
    return _loader


def load_genre_techniques(genre: str) -> GenreTechniques:
    """
    快捷函数：加载指定题材的技法
    
    Args:
        genre: 题材名称
    
    Returns:
        GenreTechniques对象
    """
    loader = get_genre_techniques_loader()
    return loader.load(genre)


def get_available_genres() -> List[str]:
    """
    快捷函数：获取所有可用题材
    """
    loader = get_genre_techniques_loader()
    return loader.get_available_genres()


# ==================== 测试代码 ====================

if __name__ == "__main__":
    # 测试加载
    loader = GenreTechniquesLoader()
    
    print("=" * 60)
    print("可用题材:", loader.get_available_genres())
    print("=" * 60)
    
    # 测试加载国运文
    try:
        guoyun = loader.load("国运文")
        print(f"\n国运文技法 (版本: {guoyun.version})")
        print(f"描述: {guoyun.description}")
        print(f"系统提示音数量: {len(guoyun.system_prompts)}")
        print(f"禁用元素数量: {len(guoyun.forbidden_elements.get('items', []))}")
        print(f"必须元素数量: {len(guoyun.required_elements.get('items', []))}")
    except Exception as e:
        print(f"加载国运文失败: {e}")
    
    # 测试加载神豪文
    try:
        shenhao = loader.load("神豪文")
        print(f"\n神豪文技法 (版本: {shenhao.version})")
        print(f"描述: {shenhao.description}")
        print(f"系统提示音数量: {len(shenhao.system_prompts)}")
        print(f"禁用元素数量: {len(shenhao.forbidden_elements.get('items', []))}")
        print(f"必须元素数量: {len(shenhao.required_elements.get('items', []))}")
    except Exception as e:
        print(f"加载神豪文失败: {e}")
    
    # 测试加载不存在的题材（应该回退到通用）
    try:
        unknown = loader.load("不存在题材")
        print(f"\n未知题材回退到: {unknown.genre}")
    except Exception as e:
        print(f"加载未知题材失败: {e}")
