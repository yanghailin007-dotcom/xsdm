"""
提示词加载器 - 从 prompt_packages JSON 配置文件加载提示词
支持组件化加载和动态组合
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, Optional, Any, List
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    提示词加载器 - 支持从 JSON 配置文件加载和管理提示词
    支持组件化加载和动态组合
    
    使用方式:
        loader = PromptLoader(package_name="default")
        chapter_prompts = loader.get_chapter_generation_prompts()
        
        # 组件化加载
        component = loader.get_component("header")
        system_prompt = loader.build_system_prompt("phase_two/system_prompt", variables={...})
    """
    
    def __init__(self, package_name: str = "default", mode: str = "market_driven"):
        """
        初始化提示词加载器
        
        Args:
            package_name: 提示词包名称，默认 "default"
            mode: 生成模式，默认 "market_driven"
        """
        self.package_name = package_name
        self.mode = mode
        self.base_path = self._get_base_path()
        self._base_components_path = self._get_base_components_path()
        self._cache: Dict[str, Any] = {}
        
    def _get_base_path(self) -> Path:
        """获取提示词包基础路径"""
        # 从当前文件向上追溯到项目根目录
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        return project_root / "prompt_packages" / self.package_name / self.mode
    
    def _get_base_components_path(self) -> Path:
        """获取基础组件路径"""
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        return project_root / "prompt_packages" / "_base" / "system_components"
    
    def load_json(self, filename: str) -> Optional[Dict]:
        """
        加载 JSON 配置文件
        
        Args:
            filename: JSON 文件名（可带或不带 .json 后缀）
            
        Returns:
            解析后的字典，失败返回 None
        """
        # 检查缓存
        if filename in self._cache:
            return self._cache[filename]
        
        # 自动添加 .json 后缀（如果没有）
        if not filename.endswith('.json'):
            filename = filename + '.json'
        
        file_path = self.base_path / filename
        
        if not file_path.exists():
            logger.warning(f"[PromptLoader] 文件不存在: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache[filename] = data
                logger.info(f"[PromptLoader] 成功加载: {filename}")
                return data
        except json.JSONDecodeError as e:
            logger.error(f"[PromptLoader] JSON解析失败 {filename}: {e}")
            return None
        except Exception as e:
            logger.error(f"[PromptLoader] 加载失败 {filename}: {e}")
            return None
    
    def get_chapter_generation_prompts(self) -> Optional[Dict]:
        """
        获取章节生成提示词配置
        
        Returns:
            章节生成提示词配置字典
        """
        return self.load_json("chapter_generation_prompts.json")
    
    def get_golden_chapter_prompts(self) -> Optional[Dict]:
        """
        获取黄金三章提示词配置
        
        Returns:
            黄金三章提示词配置字典
        """
        return self.load_json("components/chapters/golden_chapter_prompts.json")
    
    def get_chapter_templates(self) -> Optional[Dict]:
        """
        获取章节模板配置
        
        Returns:
            章节模板配置字典
        """
        return self.load_json("templates/chapter_templates.json")
    
    def get_package_info(self) -> Optional[Dict]:
        """
        获取提示词包信息
        
        Returns:
            包信息字典
        """
        return self.load_json("package_info.json")
    
    def get_chapter_prompt(self, chapter_num: int, chapter_type: str = "") -> Optional[Dict]:
        """
        获取特定章节的提示词配置
        
        Args:
            chapter_num: 章节号
            chapter_type: 章节类型（可选）
            
        Returns:
            章节提示词配置
        """
        config = self.get_chapter_generation_prompts()
        if not config:
            return None
        
        chapter_prompts = config.get("chapter_prompts", {})
        
        # 根据章节号选择配置
        if chapter_num == 1:
            return chapter_prompts.get("chapter_1")
        elif chapter_num == 2:
            return chapter_prompts.get("chapter_2")
        elif chapter_num == 3:
            return chapter_prompts.get("chapter_3")
        else:
            # 通用章节模板
            return chapter_prompts.get("chapter_standard")
    
    def get_emotion_vocabulary(self) -> Optional[Dict]:
        """
        获取情绪词汇表
        
        Returns:
            情绪词汇表字典
        """
        config = self.get_chapter_generation_prompts()
        if config:
            return config.get("emotion_vocabulary")
        return None
    
    def get_appeal_vocabulary(self) -> Optional[Dict]:
        """
        获取爽点词汇表
        
        Returns:
            爽点词汇表字典
        """
        config = self.get_chapter_generation_prompts()
        if config:
            return config.get("appeal_vocabulary")
        return None
    
    def get_title_rules(self) -> Optional[Dict]:
        """
        获取标题规则
        
        Returns:
            标题规则字典
        """
        config = self.get_chapter_generation_prompts()
        if config:
            return config.get("title_rules")
        return None
    
    def get_output_format(self) -> Optional[Dict]:
        """
        获取输出格式配置
        
        Returns:
            输出格式配置字典
        """
        config = self.get_chapter_generation_prompts()
        if config:
            return config.get("output_format")
        return None
    
    def clear_cache(self):
        """清除缓存，强制重新加载"""
        self._cache.clear()
        logger.info("[PromptLoader] 缓存已清除")
    
    # ==================== 组件化加载新方法 ====================
    
    def get_component(self, component_id: str) -> Optional[Dict]:
        """
        加载单个组件配置
        
        Args:
            component_id: 组件ID，如 "header"、"emotion_density_guide"、
                         "_base/core_rules"、"market_driven/components/golden_chapter_guide"
            
        Returns:
            组件配置字典
        """
        # 检查缓存
        cache_key = f"component:{component_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 解析组件路径
        if component_id.startswith("_base/"):
            # 基础组件
            file_path = self._base_components_path / f"{component_id[6:]}.json"
        elif "/" in component_id:
            # 带路径的组件
            parts = component_id.split("/")
            if parts[0] == self.mode or parts[0] == "components":
                file_path = self.base_path / f"{component_id}.json"
            else:
                file_path = self.base_path / "components" / f"{component_id}.json"
        else:
            # 默认查找模式组件，如果不存在则查找基础组件
            file_path = self.base_path / "components" / f"{component_id}.json"
            if not file_path.exists():
                file_path = self._base_components_path / f"{component_id}.json"
        
        if not file_path.exists():
            logger.warning(f"[PromptLoader] 组件不存在: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._cache[cache_key] = data
                logger.info(f"[PromptLoader] 成功加载组件: {component_id}")
                return data
        except Exception as e:
            logger.error(f"[PromptLoader] 加载组件失败 {component_id}: {e}")
            return None
    
    def render_template(self, template: str, variables: Dict[str, Any]) -> str:
        """
        渲染模板字符串，替换变量
        
        Args:
            template: 模板字符串，使用 {{variable}} 语法
            variables: 变量字典
            
        Returns:
            渲染后的字符串
        """
        if not template:
            return ""
        
        result = template
        for key, value in variables.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in result:
                result = result.replace(placeholder, str(value) if value is not None else "")
        
        return result
    
    def build_system_prompt(self, config_path: str, variables: Dict[str, Any] = None) -> str:
        """
        构建完整的System Prompt
        
        Args:
            config_path: 配置文件路径，如 "phase_two/system_prompt"
            variables: 模板变量字典
            
        Returns:
            完整的System Prompt字符串
        """
        config = self.load_json(f"{config_path}.json")
        if not config:
            logger.error(f"[PromptLoader] 无法加载System Prompt配置: {config_path}")
            return ""
        
        variables = variables or {}
        sections = []
        
        # 获取section顺序
        section_order = config.get("section_order", [])
        system_prompt_template = config.get("system_prompt_template", {})
        
        for section_id in section_order:
            section_config = system_prompt_template.get(section_id)
            if not section_config:
                continue
            
            section_content = self._build_section(section_id, section_config, variables)
            if section_content:
                sections.append(section_content)
        
        return "\n\n".join(sections)
    
    def _build_section(self, section_id: str, section_config: Dict, variables: Dict) -> str:
        """
        构建单个Section
        
        Args:
            section_id: section ID
            section_config: section配置
            variables: 变量字典
            
        Returns:
            section内容字符串
        """
        # 如果配置是引用其他组件
        if "ref" in section_config:
            ref_path = section_config["ref"]
            component = self.get_component(ref_path)
            if component:
                template = component.get("template", "")
                # 合并组件默认变量和用户变量
                merged_vars = {**(component.get("default_values") or {}), **variables}
                return self.render_template(template, merged_vars)
            return ""
        
        # 如果配置是内联模板
        if "template" in section_config:
            template = section_config["template"]
            # 获取该section需要的变量
            section_vars = {k: v for k, v in variables.items() if k in section_config.get("variables", [])}
            return self.render_template(template, section_vars)
        
        return ""
    
    def get_step_config(self, step_id: str) -> Optional[Dict]:
        """
        获取步骤配置
        
        Args:
            step_id: 步骤ID，如 "step_1_plan"
            
        Returns:
            步骤配置字典
        """
        return self.load_json(f"steps/{step_id}.json")
    
    def get_mode_config(self) -> Optional[Dict]:
        """
        获取模式配置
        
        Returns:
            模式配置字典
        """
        return self.load_json("mode_config.json")


# 全局单例实例
_default_loader: Optional[PromptLoader] = None


def get_prompt_loader(package_name: str = "default", mode: str = "market_driven") -> PromptLoader:
    """
    获取提示词加载器实例（单例模式）
    
    Args:
        package_name: 提示词包名称
        mode: 生成模式
        
    Returns:
        PromptLoader 实例
    """
    global _default_loader
    
    if _default_loader is None:
        _default_loader = PromptLoader(package_name, mode)
    
    return _default_loader
