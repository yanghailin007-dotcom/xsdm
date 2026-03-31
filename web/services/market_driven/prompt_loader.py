"""
提示词加载器 - 从 prompt_packages JSON 配置文件加载提示词
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class PromptLoader:
    """
    提示词加载器 - 支持从 JSON 配置文件加载和管理提示词
    
    使用方式:
        loader = PromptLoader(package_name="default")
        chapter_prompts = loader.get_chapter_generation_prompts()
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
        self._cache: Dict[str, Any] = {}
        
    def _get_base_path(self) -> Path:
        """获取提示词包基础路径"""
        # 从当前文件向上追溯到项目根目录
        current_file = Path(__file__).resolve()
        project_root = current_file.parent.parent.parent.parent
        return project_root / "prompt_packages" / self.package_name / self.mode
    
    def load_json(self, filename: str) -> Optional[Dict]:
        """
        加载 JSON 配置文件
        
        Args:
            filename: JSON 文件名
            
        Returns:
            解析后的字典，失败返回 None
        """
        # 检查缓存
        if filename in self._cache:
            return self._cache[filename]
        
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
        return self.load_json("golden_chapter_prompts.json")
    
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
