# -*- coding: utf-8 -*-
"""
角色人设生成配置加载器
从 YAML 配置文件加载人设生成模板
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class CharacterGenerationConfig:
    """
    角色人设生成配置
    
    功能：
    1. 从 YAML 加载人设生成模板
    2. 按题材获取特定的人设公式
    3. 生成用于 AI 的人设生成提示词
    """
    
    _instance = None
    _config = None
    _config_path = None
    
    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config_path: Optional[Path] = None):
        if self._initialized:
            return
            
        if config_path is None:
            # 默认路径
            base_dir = Path(__file__).parent.parent.parent.parent
            config_path = base_dir / "prompt_packages" / "default" / "market_driven" / "v2_config" / "character_generation.yaml"
        
        self._config_path = Path(config_path)
        self._initialized = True
        
        # 加载配置
        self._load_config()
    
    def _load_config(self):
        """加载 YAML 配置"""
        try:
            if not self._config_path.exists():
                logger.warning(f"[CharacterConfig] 配置文件不存在: {self._config_path}")
                self._config = self._get_default_config()
                return
            
            with open(self._config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            logger.info(f"[CharacterConfig] 配置加载成功: {self._config_path}")
            
        except Exception as e:
            logger.error(f"[CharacterConfig] 加载配置失败: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict:
        """获取默认配置"""
        return {
            "version": "1.0",
            "default_template": {
                "protagonist": {
                    "required_fields": ["name", "identity", "traits", "unique_label"],
                    "optional_fields": ["background", "motivation", "catchphrase"]
                }
            },
            "genre_templates": {}
        }
    
    def reload(self):
        """重新加载配置"""
        self._load_config()
        logger.info("[CharacterConfig] 配置已重新加载")
    
    def get_genre_template(self, genre: str) -> Optional[Dict]:
        """
        获取指定题材的人设模板
        
        Args:
            genre: 题材类型，如 "神豪文-花钱返利类"
            
        Returns:
            人设模板字典，如果不存在返回 None
        """
        if not self._config:
            return None
        
        templates = self._config.get("genre_templates", {})
        
        # 精确匹配
        if genre in templates:
            return templates[genre]
        
        # 模糊匹配：如果 genre 包含关键字
        for template_genre, template in templates.items():
            if template_genre in genre or genre in template_genre:
                return template
        
        return None
    
    def get_protagonist_formula(self, genre: str) -> Optional[Dict]:
        """
        获取主角人设公式
        
        Args:
            genre: 题材类型
            
        Returns:
            主角人设公式字典
        """
        template = self.get_genre_template(genre)
        if template:
            return template.get("protagonist_formula")
        return None
    
    def generate_prompt(self, genre: str, protagonist_name: str, user_choices: Dict = None) -> Dict[str, str]:
        """
        生成人设生成提示词
        
        Args:
            genre: 题材类型
            protagonist_name: 主角姓名
            user_choices: 用户选择
            
        Returns:
            {"system_prompt": "...", "user_prompt": "..."}
        """
        template = self.get_genre_template(genre)
        
        if template:
            formula = template.get("protagonist_formula", {})
            genre_desc = template.get("description", genre)
        else:
            formula = {}
            genre_desc = genre
        
        # 构建题材特定要求
        genre_requirements = self._build_genre_requirements(formula, genre)
        
        # 获取输出格式
        output_format = self._config.get("default_template", {}).get("output_format", {}).get("json_structure", "")
        
        # 构建 system prompt
        prompt_templates = self._config.get("prompt_templates", {})
        system_template = prompt_templates.get("system_prompt", "")
        
        system_prompt = system_template.format(
            genre=genre_desc,
            protagonist_name=protagonist_name,
            genre_specific_requirements=genre_requirements,
            output_format=output_format
        )
        
        # 构建 user prompt
        user_template = prompt_templates.get("user_prompt", "")
        user_prompt = user_template.format(
            genre=genre_desc,
            protagonist_name=protagonist_name
        )
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "formula": formula
        }
    
    def _build_genre_requirements(self, formula: Dict, genre: str) -> str:
        """构建题材特定要求文本"""
        if not formula:
            return "根据题材特点设计符合爆款风格的人设。"
        
        lines = []
        
        # 姓名规则
        if "name_rules" in formula:
            lines.append("### 姓名要求")
            for rule in formula["name_rules"]:
                lines.append(f"- {rule}")
            lines.append("")
        
        # 身份选项
        if "identity_options" in formula:
            lines.append("### 身份设定")
            identity = formula["identity_options"]
            if isinstance(identity, dict):
                if "initial" in identity:
                    lines.append("**初始身份（必选其一）：**")
                    for opt in identity["initial"]:
                        lines.append(f"- {opt}")
                if "after_system" in identity:
                    lines.append("\n**获得系统后身份：**")
                    if isinstance(identity["after_system"], list):
                        for opt in identity["after_system"]:
                            lines.append(f"- {opt}")
                    else:
                        lines.append(f"- {identity['after_system']}")
            lines.append("")
        
        # 特质要求
        if "traits_required" in formula:
            lines.append("### 核心特质（必须全部包含）")
            for trait in formula["traits_required"]:
                lines.append(f"- {trait}")
            lines.append("")
        
        # 独特标签
        if "unique_label_templates" in formula:
            lines.append("### 独特标签（选择或参考）")
            lines.append("这是主角的人设记忆点，必须独特且有辨识度：")
            for template in formula["unique_label_templates"]:
                lines.append(f"- {template}")
            lines.append("")
        
        # 背景元素
        if "background_elements" in formula:
            lines.append("### 背景故事元素（可选）")
            for elem in formula["background_elements"]:
                lines.append(f"- {elem}")
            lines.append("")
        
        # 禁止行为
        if "forbidden_behaviors" in formula:
            lines.append("### 禁止行为（人设绝对不能做的事）")
            for forbidden in formula["forbidden_behaviors"]:
                lines.append(f"- {forbidden}")
            lines.append("")
        
        # 反派配置
        if "antagonists_config" in formula:
            lines.append("### 反派设计")
            antagonists = formula["antagonists_config"]
            if "early" in antagonists:
                lines.append(f"**早期反派（1-30章）：** {antagonists['early'].get('description', '')}")
            if "mid" in antagonists:
                lines.append(f"**中期反派（30-100章）：** {antagonists['mid'].get('description', '')}")
            if "late" in antagonists:
                lines.append(f"**后期反派（100章+）：** {antagonists['late'].get('description', '')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def validate_character_design(self, character_design: Dict, genre: str) -> Dict:
        """
        验证人设设计是否符合要求
        
        Args:
            character_design: 角色设计字典
            genre: 题材类型
            
        Returns:
            {"valid": bool, "errors": [], "warnings": []}
        """
        errors = []
        warnings = []
        
        # 获取该题材的配置
        formula = self.get_protagonist_formula(genre)
        default_template = self._config.get("default_template", {})
        quality_check = self._config.get("quality_check", {})
        
        protagonist = character_design.get("protagonist", {})
        
        # 检查必需字段
        required_fields = default_template.get("protagonist", {}).get("required_fields", [])
        for field in required_fields:
            if field not in protagonist or not protagonist[field]:
                errors.append(f"缺少必需字段: protagonist.{field}")
        
        # 检查特质数量
        traits = protagonist.get("traits", [])
        if isinstance(traits, list):
            if len(traits) < 3:
                warnings.append(f"核心特质数量过少({len(traits)}个)，建议3-5个")
            if len(traits) > 5:
                warnings.append(f"核心特质数量过多({len(traits)}个)，建议精简到3-5个")
        
        # 检查独特标签
        unique_label = protagonist.get("unique_label", "")
        if unique_label:
            # 检查是否包含禁止词汇
            forbidden_words = ["扮演度", "系统等级", "经验值", "升级"]
            for word in forbidden_words:
                if word in unique_label:
                    warnings.append(f"独特标签包含游戏化术语'{word}'，建议修改")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }


# 便捷函数
def get_character_config() -> CharacterGenerationConfig:
    """获取配置实例"""
    return CharacterGenerationConfig()


def generate_character_prompt(genre: str, protagonist_name: str, user_choices: Dict = None) -> Dict[str, str]:
    """
    便捷函数：生成角色人设生成提示词
    
    Args:
        genre: 题材类型
        protagonist_name: 主角姓名
        user_choices: 用户选择
        
    Returns:
        {"system_prompt": "...", "user_prompt": "..."}
    """
    config = get_character_config()
    return config.generate_prompt(genre, protagonist_name, user_choices)