"""
多模式提示词包统一加载器

支持多种生成模式：
- market_driven: 市场驱动7步流
- traditional: 传统分阶段生成
- simple: 简单快速生成
- user_custom: 用户自定义模式

作者：AI Assistant
创建时间：2026-03-29
"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from functools import lru_cache

logger = logging.getLogger(__name__)


@dataclass
class ModeInfo:
    """模式信息"""
    id: str
    name: str
    version: str
    description: str
    tags: List[str]
    is_default: bool = True
    is_editable: bool = False


@dataclass
class StepConfig:
    """步骤配置"""
    step_id: str
    step_name: str
    step_type: str  # conversation | generation | check
    order: int
    required: bool = True
    prompt_template: Dict = field(default_factory=dict)
    response_format: Dict = field(default_factory=dict)
    ai_settings: Dict = field(default_factory=dict)
    inherits: Optional[Dict] = None


@dataclass
class ModeConfig:
    """模式完整配置"""
    mode_id: str
    info: ModeInfo
    flow: Dict
    features: Dict
    steps: Dict[str, StepConfig]
    templates: Dict[str, Any]
    base_path: Path
    
    def get_step(self, step_id: str) -> Optional[StepConfig]:
        """获取指定步骤配置"""
        return self.steps.get(step_id)
    
    def get_step_order(self) -> List[StepConfig]:
        """按顺序获取所有步骤"""
        return sorted(self.steps.values(), key=lambda s: s.order)


class ModeLoader:
    """
    多模式提示词包统一加载器
    
    使用示例：
        loader = ModeLoader()
        
        # 列出所有可用模式
        modes = loader.list_modes()
        
        # 加载特定模式
        mode = loader.load_mode("market_driven")
        
        # 获取步骤提示词
        step = mode.get_step("step_7_chapter")
    """
    
    _instance = None
    _cache = {}
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, base_path: str = "prompt_packages"):
        if self._initialized:
            return
        
        self.base_path = Path(base_path)
        self._initialized = True
        
        logger.info(f"[ModeLoader] 初始化 | 基础路径: {self.base_path}")
    
    def list_modes(self, include_user: bool = True) -> List[ModeInfo]:
        """
        列出所有可用模式
        
        Args:
            include_user: 是否包含用户自定义模式
            
        Returns:
            模式信息列表
        """
        modes = []
        
        # 1. 加载系统默认模式
        default_path = self.base_path / "default"
        if default_path.exists():
            for mode_dir in default_path.iterdir():
                if mode_dir.is_dir():
                    info = self._load_package_info(mode_dir)
                    if info:
                        modes.append(info)
        
        # 2. 加载用户自定义模式
        if include_user:
            user_path = self.base_path / "user_custom"
            if user_path.exists():
                for user_dir in user_path.iterdir():
                    if user_dir.is_dir():
                        for mode_dir in user_dir.iterdir():
                            if mode_dir.is_dir():
                                info = self._load_package_info(mode_dir)
                                if info:
                                    info.is_default = False
                                    info.is_editable = True
                                    modes.append(info)
        
        return modes
    
    def load_mode(self, mode_id: str, user_id: Optional[str] = None) -> Optional[ModeConfig]:
        """
        加载指定模式的完整配置
        
        Args:
            mode_id: 模式ID
            user_id: 用户ID（用于加载用户自定义模式）
            
        Returns:
            模式配置对象
        """
        cache_key = f"{mode_id}:{user_id or 'system'}"
        
        if cache_key in self._cache:
            logger.debug(f"[ModeLoader] 命中缓存: {cache_key}")
            return self._cache[cache_key]
        
        # 确定模式路径
        mode_path = self._find_mode_path(mode_id, user_id)
        if not mode_path:
            logger.error(f"[ModeLoader] 未找到模式: {mode_id}")
            return None
        
        try:
            # 加载基础信息
            info = self._load_package_info(mode_path)
            if not info:
                return None
            
            # 加载模式配置
            mode_config = self._load_mode_config(mode_path)
            
            # 加载所有步骤
            steps = self._load_steps(mode_path)
            
            # 加载模板
            templates = self._load_templates(mode_path)
            
            config = ModeConfig(
                mode_id=mode_id,
                info=info,
                flow=mode_config.get("flow", {}),
                features=mode_config.get("features", {}),
                steps=steps,
                templates=templates,
                base_path=mode_path
            )
            
            self._cache[cache_key] = config
            logger.info(f"[ModeLoader] 加载模式成功: {mode_id}")
            return config
            
        except Exception as e:
            logger.error(f"[ModeLoader] 加载模式失败 {mode_id}: {e}")
            return None
    
    def get_step_prompt(self, mode_id: str, step_id: str, 
                        variables: Dict[str, Any],
                        user_id: Optional[str] = None) -> Optional[str]:
        """
        获取渲染后的步骤提示词
        
        Args:
            mode_id: 模式ID
            step_id: 步骤ID
            variables: 变量字典
            user_id: 用户ID
            
        Returns:
            渲染后的提示词字符串
        """
        mode = self.load_mode(mode_id, user_id)
        if not mode:
            return None
        
        step = mode.get_step(step_id)
        if not step:
            logger.error(f"[ModeLoader] 未找到步骤: {step_id}")
            return None
        
        return self._render_prompt(step.prompt_template, variables, mode)
    
    def load_writing_style(self, style_id: str) -> Optional[str]:
        """
        加载写作风格指南
        
        优先从 _base/writing_styles/ 加载，支持各模式覆盖
        
        Args:
            style_id: 风格ID
            
        Returns:
            风格指南文本
        """
        # 1. 尝试从 _base 加载
        base_style_path = self.base_path / "_base" / "writing_styles" / f"{style_id}.json"
        if base_style_path.exists():
            return self._render_style_guide(base_style_path)
        
        # 2. 尝试从各模式加载（兼容旧结构）
        for mode_dir in (self.base_path / "default").iterdir():
            if mode_dir.is_dir():
                style_path = mode_dir / "styles" / f"{style_id}.json"
                if style_path.exists():
                    return self._render_style_guide(style_path)
        
        logger.warning(f"[ModeLoader] 未找到写作风格: {style_id}")
        return None
    
    def clear_cache(self):
        """清除缓存"""
        self._cache.clear()
        logger.info("[ModeLoader] 缓存已清除")
    
    def _find_mode_path(self, mode_id: str, user_id: Optional[str] = None) -> Optional[Path]:
        """查找模式路径"""
        # 1. 先查用户自定义
        if user_id:
            user_mode_path = self.base_path / "user_custom" / user_id / mode_id
            if user_mode_path.exists():
                return user_mode_path
        
        # 2. 查系统默认
        default_mode_path = self.base_path / "default" / mode_id
        if default_mode_path.exists():
            return default_mode_path
        
        return None
    
    def _load_package_info(self, mode_path: Path) -> Optional[ModeInfo]:
        """加载 package_info.json"""
        info_file = mode_path / "package_info.json"
        if not info_file.exists():
            logger.warning(f"[ModeLoader] package_info.json 不存在: {mode_path}")
            return None
        
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return ModeInfo(
                id=data.get("id", mode_path.name),
                name=data.get("name", mode_path.name),
                version=data.get("version", "1.0.0"),
                description=data.get("description", ""),
                tags=data.get("tags", []),
                is_default=True,
                is_editable=False
            )
        except Exception as e:
            logger.error(f"[ModeLoader] 加载 package_info.json 失败: {e}")
            return None
    
    def _load_mode_config(self, mode_path: Path) -> Dict:
        """加载 mode_config.json"""
        config_file = mode_path / "mode_config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _load_steps(self, mode_path: Path) -> Dict[str, StepConfig]:
        """加载所有步骤配置"""
        steps = {}
        steps_dir = mode_path / "steps"
        
        if not steps_dir.exists():
            # 兼容旧结构：直接在模式目录下找 step_*.json
            for step_file in mode_path.glob("step_*.json"):
                step = self._load_step_file(step_file)
                if step:
                    steps[step.step_id] = step
        else:
            for step_file in steps_dir.glob("step_*.json"):
                step = self._load_step_file(step_file)
                if step:
                    steps[step.step_id] = step
        
        return steps
    
    def _load_step_file(self, step_file: Path) -> Optional[StepConfig]:
        """加载单个步骤文件"""
        try:
            with open(step_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return StepConfig(
                step_id=data.get("step_id", step_file.stem),
                step_name=data.get("step_name", step_file.stem),
                step_type=data.get("step_type", "generation"),
                order=data.get("step_order", data.get("order", 0)),
                required=data.get("required", True),
                prompt_template=data.get("prompt_template", {}),
                response_format=data.get("response_format", {}),
                ai_settings=data.get("ai_settings", {}),
                inherits=data.get("inherits")
            )
        except Exception as e:
            logger.error(f"[ModeLoader] 加载步骤失败 {step_file}: {e}")
            return None
    
    def _load_templates(self, mode_path: Path) -> Dict[str, Any]:
        """加载所有模板"""
        templates = {}
        templates_dir = mode_path / "templates"
        
        if templates_dir.exists():
            for template_file in templates_dir.glob("*.json"):
                try:
                    with open(template_file, 'r', encoding='utf-8') as f:
                        templates[template_file.stem] = json.load(f)
                except Exception as e:
                    logger.error(f"[ModeLoader] 加载模板失败 {template_file}: {e}")
        
        return templates
    
    def _render_prompt(self, prompt_template: Dict, variables: Dict, mode: ModeConfig) -> str:
        """渲染提示词模板（简化版）"""
        # TODO: 实现完整的模板渲染（支持 Jinja2 语法）
        # 这里先返回简单的字符串拼接
        
        system_role = prompt_template.get("system_role", "")
        context_sections = prompt_template.get("context_sections", [])
        
        lines = []
        if system_role:
            lines.append(f"# {system_role}")
            lines.append("")
        
        for section in context_sections:
            section_type = section.get("type", "static")
            section_name = section.get("name", "")
            
            if section_type == "static":
                content = section.get("content", "")
            elif section_type == "dynamic":
                template = section.get("template", "")
                try:
                    content = template.format(**variables)
                except KeyError:
                    content = template
            else:
                content = ""
            
            if section_name:
                lines.append(f"## {section_name}")
            lines.append(content)
            lines.append("")
        
        # 加载继承的写作风格
        inherits = prompt_template.get("inherits")
        if inherits and inherits.get("writing_style"):
            style_guide = self.load_writing_style(inherits["writing_style"])
            if style_guide:
                lines.append(style_guide)
        
        return "\n".join(lines)
    
    def _render_style_guide(self, style_path: Path) -> str:
        """渲染写作风格指南"""
        # 复用 style_loader.py 的逻辑
        # 这里简化处理
        try:
            with open(style_path, 'r', encoding='utf-8') as f:
                style = json.load(f)
            
            lines = [f"## {style.get('style_name', '写作风格')}", ""]
            
            if 'warning' in style:
                lines.append(f"**{style['warning']}**")
                lines.append("")
            
            if 'core_principles' in style:
                lines.append("### 核心原则")
                for principle in style['core_principles']:
                    lines.append(f"- {principle}")
                lines.append("")
            
            return "\n".join(lines)
        except Exception as e:
            logger.error(f"[ModeLoader] 渲染风格指南失败: {e}")
            return ""


# 便捷函数
def get_mode_loader() -> ModeLoader:
    """获取 ModeLoader 实例（便捷函数）"""
    return ModeLoader()


def list_generation_modes() -> List[ModeInfo]:
    """列出所有可用的生成模式（便捷函数）"""
    return ModeLoader().list_modes()
